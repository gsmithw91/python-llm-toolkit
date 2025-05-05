#scraper.py
import os
import csv
import json
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass
import asyncio
import aiofiles 
import httpx
from bs4 import BeautifulSoup
from bs4.element import Comment

SEARCH_TERMS = ['price', 'cost', 'patients', 'transparency', 'estimates']
FILE_EXTENSIONS = ['.pdf', '.xlsx', 'csv']


def is_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'meta', '[document]']:
        return False
    if isinstance(element, Comment):
        return False
    return True


@dataclass
class PageSnapshot:
    url: str
    title: str
    headings: Dict[str, List[str]]
    main_text_snippet: str
    json_ld: List[Dict[str, Any]]
    links: List[Dict[str, str]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "headings": self.headings,
            "main_text_snippet": self.main_text_snippet,
            "json_ld": self.json_ld,
            "links": self.links
        }


class WebScraper:
    def __init__(self,
                 search_terms: Optional[List[str]] = None,
                 file_types: Optional[List[str]] = None,
                 max_depth: Optional[int] = 2,
                 output_dir: Optional[str] = "downloads",
                 urls: Optional[List[str]] = None):

        self.search_terms = search_terms if search_terms is not None else SEARCH_TERMS
        self.file_types = file_types if file_types is not None else FILE_EXTENSIONS
        self.max_depth = max_depth
        self.output_dir = output_dir
        self.visited_sites = set()
        self.files_downloaded = []
        self.found_files = []
        self.urls = urls if urls else []

        os.makedirs(self.output_dir, exist_ok=True)

    @staticmethod
    def is_valid_http_url(url: str) -> bool:
        parsed = urlparse(url)
        return parsed.scheme in ('http', 'https') and bool(parsed.netloc)

    async def fetch_links_from_url(self, client: httpx.AsyncClient, url: str) -> List[str]:
        links = []
        try:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                full_url = urljoin(url, a_tag["href"])
                if self.is_valid_http_url(full_url):
                    links.append(full_url)
        except Exception as e:
            print(f"[fetch_links_from_url] Failed on {url}: {e}")
        return links

    async def get_meta_data(self, client: httpx.AsyncClient, url: str) -> Dict[str, str]:
        try:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.title.string.strip() if soup.title else ""
            meta = soup.find('meta', attrs={'name': 'description'})
            description = meta['content'].strip() if meta and 'content' in meta.attrs else ""
            return {'url': url, 'title': title, 'description': description}
        except Exception as e:
            print(f"[get_meta_data] Failed on {url}: {e}")
            return {'url': url, 'title': '', 'description': ''}

    async def extract_main_text(self, client: httpx.AsyncClient, url: str) -> str:
        try:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            texts = soup.find_all(string=True)
            visible_texts = filter(is_visible, texts)
            return " ".join(t.strip() for t in visible_texts if t.strip())
        except Exception as e:
            print(f"[extract_main_text] Failed on {url}: {e}")
            return ""

    async def search_text_for_keywords(self, client: httpx.AsyncClient, url: str) -> List[str]:
        try:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text(separator=' ').lower()
            return [keyword for keyword in self.search_terms if keyword.lower() in text]
        except Exception as e:
            print(f"[search_text_for_keywords] Failed on {url}: {e}")
            return []

    async def extract_links_with_text(self, client: httpx.AsyncClient, url: str) -> List[Dict[str, str]]:
        links = []
        try:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                links.append({
                    "text": a_tag.get_text(strip=True),
                    "href": urljoin(url, a_tag["href"])
                })
        except Exception as e:
            print(f"[extract_links_with_text] Failed on {url}: {e}")
        return links

    async def extract_json_ld(self, client: httpx.AsyncClient, url: str) -> List[Dict[str, Any]]:
        data = []
        try:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            scripts = soup.find_all("script", type="application/ld+json")
            for script in scripts:
                try:
                    if script.string:
                        parsed = json.loads(script.string)
                        data.extend(parsed if isinstance(parsed, list) else [parsed])
                except Exception as e:
                    print(f"[extract_json_ld] Error parsing JSON-LD on {url}: {e}")
        except Exception as e:
            print(f"[extract_json_ld] Failed on {url}: {e}")
        return data


    async def export_snapshots_to_json(self, filepath: str, snapshots: List[PageSnapshot]) -> None:
        data = [snap.to_dict() for snap in snapshots]
        async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=2))

    async def load_snapshots_from_json(self, path: str) -> List[PageSnapshot]:
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            raw = await f.read()
            data = json.loads(raw)
        return [PageSnapshot(**item) for item in data]

    async def export_snapshots_to_csv(self, filepath: str, snapshots: List[PageSnapshot]) -> None:
        rows = [
            {
                "url": snap.url,
                "title": snap.title,
                "main_text_snippet": snap.main_text_snippet[:300],
                "num_links": len(snap.links),
                "num_headings": sum(len(hs) for hs in snap.headings.values()),
                "num_json_ld": len(snap.json_ld)
            }
            for snap in snapshots
        ]
        async with aiofiles.open(filepath, mode="w", newline="", encoding="utf-8") as f:
            header = list(rows[0].keys()) if rows else []
            await f.write(",".join(header) + "\n")
            for row in rows:
                line = ",".join(str(row[k]).replace("\n", " ").replace(",", " ") for k in header)
                await f.write(line + "\n")

    async def get_structured_snapshot(self, client: httpx.AsyncClient, url: str) -> PageSnapshot:
        def is_visible(element):
            if element.parent.name in ['style', 'script', 'head', 'meta', '[document]']:
                return False
            if isinstance(element, Comment):
                return False
            return True

        try:
            response = await client.get(url)
            soup = BeautifulSoup(response.text, "html.parser")

            title = soup.title.string.strip() if soup.title else ""
            headings = {
                f"h{i}": [tag.get_text(strip=True) for tag in soup.find_all(f"h{i}")]
                for i in range(1, 7)
            }
            texts = soup.find_all(string=True)
            visible_texts = filter(is_visible, texts)
            joined_text = " ".join(t.strip() for t in visible_texts if t.strip())
            snippet = joined_text[:1000] + "..." if len(joined_text) > 1000 else joined_text

            json_ld = []
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    parsed = json.loads(script.string)
                    json_ld.extend(parsed if isinstance(parsed, list) else [parsed])
                except Exception:
                    continue

            links = [
                {"text": a.get_text(strip=True), "href": urljoin(url, a["href"])}
                for a in soup.find_all("a", href=True)
            ]

            return PageSnapshot(
                url=url,
                title=title,
                headings=headings,
                main_text_snippet=snippet,
                json_ld=json_ld,
                links=links
            )

        except Exception as e:
            print(f"Snapshot Failed for {url}: {e}")
            return PageSnapshot(
                url=url,
                title="",
                headings={f"h{i}": [] for i in range(1, 7)},
                main_text_snippet="",
                json_ld=[],
                links=[]
            )


    def filter_links_by_file_type(self, links: List[str]) -> List[str]:
       return [link for link in links if any(link.lower().endswith(ext) for ext in self.file_types)]

    def download_files(self, links: List[str]) -> List[str]:
        downloaded = []
        for url in links:
            try:
                response = httpx.get(url)
                response.raise_for_status()
                parsed_url = urlparse(url)
                domain = parsed_url.netloc.replace('.', '_')
                ext = os.path.splitext(parsed_url.path)[-1].lstrip('.')
                folder = os.path.join(self.output_dir, domain, ext)
                os.makedirs(folder, exist_ok=True)
                filename = os.path.basename(parsed_url.path) or "index"
                filepath = os.path.join(folder, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                downloaded.append(filepath)
            except Exception as e:
                print(f"[download_files] Failed for {url}: {e}")
        return downloaded
    
    
    async def crawl(
        self,
        start_urls: List[str] | None = None,
        max_depth: int | None = None,
        concurrency: int = 10
    ):
        """
        Asynchronous breadth-first crawler that respects max_depth and avoids revisiting URLs.
        Also collects PageSnapshot objects and downloads matched files.
    
        Args:
            start_urls (List[str] | None): Seed URLs to begin crawling (defaults to self.urls).
            max_depth (int | None): Maximum depth to crawl (defaults to self.max_depth).
            concurrency (int): Maximum concurrent requests.
        """
        start_urls = start_urls or self.urls
        max_depth = max_depth if max_depth is not None else self.max_depth
        self.snapshots = []
        self.files_downloaded = []
        visited = set()
        queue = asyncio.Queue()
    
        for url in start_urls:
            await queue.put((url, 0))
    
        async with httpx.AsyncClient(timeout=10) as client:
            semaphore = asyncio.Semaphore(concurrency)
    
            async def worker():
                while not queue.empty():
                    url, depth = await queue.get()
                    if url in visited or depth > max_depth:
                        continue
                    visited.add(url)
    
                    async with semaphore:
                        try:
                            print(f"[CRAWL] Depth {depth}: {url}")
    
                            # Keyword filtering
                            keyword_matches = await self.search_text_for_keywords(client, url)
                            if not keyword_matches:
                                print(f"[SKIP] No keyword match for {url}")
                                return
    
                            # Snapshot collection
                            snapshot = await self.get_structured_snapshot(client, url)
                            self.snapshots.append(snapshot)
    
                            # File discovery and download
                            links = await self.fetch_links_from_url(client, url)
                            file_links = self.filter_links_by_file_type(links)
                            downloaded = self.download_files(file_links)
                            self.files_downloaded.extend(downloaded)
    
                            # Queue additional links
                            for link in links:
                                if link not in visited:
                                    await queue.put((link, depth + 1))
    
                        except Exception as e:
                            print(f"[ERROR] {url}: {e}")
    
            workers = [asyncio.create_task(worker()) for _ in range(concurrency)]
            await asyncio.gather(*workers)
    
