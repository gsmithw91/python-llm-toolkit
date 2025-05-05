 # scraper.py

import requests 
from bs4 import BeautifulSoup 
from bs4.element import Comment 
from typing import List, dataclass_transform
from urllib.parse import urljoin 
from urllib.parse import urlparse
from typing import List, Dict, Any, Callable, Optional
import os 
import json 
from dataclasses import dataclass
import csv


SEARCH_TERMS = ['price','cost','patients','transparecny','estimates']
FILE_EXTENSIONS = ['.pdf','.xlsx','csv']

@dataclass 
class PageSnapshot:
    url: str
    title: str 
    headings: Dict[str,List[str]]
    main_text_snippet: str 
    json_ld : List[Dict[str,Any]]
    links: List[Dict[str,str]]
    
    def to_dict(self)->Dict[str,Any]:
        return{
                "url": self.url,
                "title": self.title,
                "headings": self.headings ,
                "main_text_snippet": self.main_text_snippet,
                "json_ld": self.json_ld,
                "links": self.links
                }

def is_visible(element):
    if element.parent.name in ['style','script','head','meat','[document]']:
        return False 
    if isinstance(element,Comment):
        return False 
    return True 


class WebScraper:
    '''
    Class based webscraper for modular maintainable workflows. 
    Encapsulated configuration ,state, and sraping logic 

    '''

    def __init__(self,
                 search_terms: Optional[List[str]],
                 file_types: Optional[List[str]],
                 max_depth: Optional[int],
                 output_dir : Optional[str],
                 urls : Optional[List[str]],
                 ):
        self.search_terms = search_terms if search_terms is not None else SEARCH_TERMS 
        self.file_types = file_types if file_types is not None else FILE_EXTENSIONS
        self.max_depth = max_depth
        self.output_dir = output_dir
        self.visited_sites = set()
        self.files_downloaded = []
        self.found_files = []
        self.urls = urls 

        os.makedirs(self.output_dir,exist_ok=True)
    
    def __repr__(self):
        return f"<Webscraper urls={len(self.urls)} terms ={self.search_terms}"


    @staticmethod
    def is_valid_http_url(url: str) ->bool:
        parsed = urlparse(url)
        return parsed.scheme in ('http','https') and bool(parsed.netloc)


    def fetch_links_from_url (self) -> List[str]:
        """
        Fetch all hyperlinks from the given URL. 
        Args:
            url(str): The url to  scrape 
        Returns:
            List[str]: A list of hyperlink URLs found on the page 
        """
        links = [] 

        for url in self.urls:
            try:
                response = requests.get(url)
                soup = BeautifulSoup(response.text, "html.parser")
            
                for a_tag in soup.find_all("a",href=True):
                       full_url = urljoin(url,a_tag["href"])
                       links.append(full_url)
               
            except Exception as e: 
                print(f"Failed to fetch from {e}")
        return links
    

    def get_image_urls(self) ->List[str]:
        """
        Fetch all image hyperlinks from the given url 
        Args:
            url(str): The urls to  scrape 
        Returns:
            List[str]: A list of urls for the images found on the page
        """
        images = []


        for url in self.urls:
            try:
                response = requests.get(url)
                soup = BeautifulSoup(response.text,"html.parser")

                for img_tag in soup.find_all("img",src=True):
                    full_url = urljoin(url,img_tag["src"])
                    images.append(full_url)

            except Exception as e:
                print(f"Failed to get images form {url}")

        return images


    def get_meta_data(self) -> List[Dict[str, str]]:
        results = []

        for url in self.urls:
            try:
                response = requests.get(url)
                soup = BeautifulSoup(response.text, "html.parser")

                title = soup.title.string.strip() if soup.title else ""
                meta = soup.find('meta', attrs={'name': 'description'})
                description = meta['content'].strip() if meta and 'content' in meta.attrs else ""

                results.append({
                    'url': url,
                    'title': title,
                    'description': description
                })
            except Exception as e:
                print(f"Failed to extract metadata from {url}: {e}")

        return results
    

    def filter_links_by_file_type(self,links: List[str]) -> List[str]:
        return [link for link in links if any(link.lower().endswith(ex)for ex in self.file_types)]

    

    def create_output_directory(self, subfolder: Optional[str] = None) -> str: 
        """
        Ensure the base output directory (or subfolder inside it) exists 

        Args:
            subfolder(Optional[str]): An Optional subdirectory to create  within the output_folder

        Returns:
            str: Full path to created directory.

        """
        
        path = os.path.join(self.output_dir, subfolder) if subfolder else self.output_dir
        os.makedirs(path,exist_ok=True)
        return path 



    def download_files(self, links: List[str]) -> List[str]:
        downloaded = []

        for link in links:
            try:
                filename = os.path.basename(urlparse(link).path)
                
                if not filename :
                    continue 
        
                domain = urlparse(link).netloc
                ext = os.path.splitext(filename)[1].lstrip(".") or "unknown"
                save_dir = self.create_output_directory(f"{domain}/{ext}")
                

                response = requests.get(link)
                response.raise_for_status()


                filepath = os.path.join(save_dir,filename)


                with open(filepath,'wb' ) as f:
                    f.write(response.content)
                
                downloaded.append(filepath)
            except Exception as e:
                print(f"Failed to download {link}: {e}")
    
        self.files_downloaded.extend(downloaded)
        print(f"Downloaded {len(downloaded)} files.")
        return downloaded
    
    def get_heading(self) -> Dict[str, List[str]]:
        result = {f"h{i}": [] for i in range(1, 7)}
    
        for url in self.urls:
            try:
                response = requests.get(url)
                soup = BeautifulSoup(response.text, "html.parser")
    
                for i in range(1, 7):
                    tags = soup.find_all(f"h{i}")
                    result[f"h{i}"].extend([tag.get_text(strip=True) for tag in tags])
    
            except Exception as e:
                print(f"Failed to extract headings from {url}: {e}")
    
        return result
    
    def search_text_for_keywords(self) -> Dict[str,List[str]]:
        """
        Search each page for configured keywords (self.search_terms)

        Returns:
            Dict[str, List[str]]: a dictionary mapping each URL to a list of matched keywords
        """
        keyword_hits = {}

        for url in self.urls:

            try:
                response = requests.get(url)
                soup = BeautifulSoup(response.text,'html.parser')
                text = soup.get_text(separator=' ').lower()

                matches = [keyword for keyword in self.search_terms if keyword.lower() in text] 

                keyword_hits[url] = matches 
    
            except Exception as e:
                print(f"Failed to search {url}: {e}")
                keyword_hits[url]= []
        return keyword_hits

    def extract_links_with_text(self) -> Dict[str,List[Dict[str,str]]]:
        """
        Extracts all links along with their anchor text. 

        Returns:
            Dict[str,List[Dict[str,str]]]: Url -> [{text:...,href: ...}]

        """

        results = {}


        for url in self.urls:
            try:
                response = requests.get(url)
                soup = BeautifulSoup(response.text,"html.parser")

                link_data = []

                for a_tag in soup.find_all("a",href=True):
                    link_data.append({
                        "text": a_tag.get_text(strip=True),
                        "href": urljoin(url,a_tag["href"])
                        })
    
                results[url] = link_data 


            except Exception as e:
                print(f"Failed to extract links with text from {url}: {e}") 
                results[url] = []
        return results
  

    def extract_tables(self)-> Dict[str,List[List[List[str]]]]:
        """
        Extract HTML tables from HTML 

        Returns:
            Dictp[str,List[Listp[List[str]]]] , where each table is a list of rows and each row is a list of strings 
        """

        table_data = {}

        for url in self.urls:
            try:
                response = requests.get(url)
                soup = BeautifulSoup(response.text,"html.parser")
                tables = soup.find_all("table")

                url_tables = []

                for table in tables: 
                    rows =  []
                    for row in table.find_all("tr"):
                        cells = row.find_all(["th","td"])
                        cell_text = [cell.get_text(strip=True) for cell in cells]
                        if cell_text:
                            rows.append(cell_text)

                    if rows:
                        url_tables.append(rows)

                table_data[url] = url_tables

            except Exception as e:
                print(f"Failed to extract tables from {url}")
                table_data[url] = []

            return table_data



    def extract_main_text(self)->Dict[str, str]:
        """
        Extracts the main text from a URL

        Returns:
            
        """


        
        result = {}

        for url in self.urls :
            try:
                response = requests.get(url)
                soup = BeautifulSoup(response.text, "html.parser")

                texts = soup.find_all(string=True)
                visible_texts= filter(is_visible, texts)
                joined = " ".join(t.strip() for t in visible_texts if t.strip())

                result[url] = joined 

            except Exception as e:
                print(f"Failed to extract main text from {url}: {e}")
                result[url] = []


        return result 


    def extract_json_ld(self)->Dict[str,List[Dict]]:

        """
        Extract JSON-LD structured data from each page


        Returns:
            Dict[str,List[Dict]]: Mapping of URL -> List of JSON-LD object

        """
        
        json_data = {}

        for url in self.urls:
            try:
                response = requests.get(url)
                soup = BeautifulSoup(response.text,"html.parser")

                scripts = soup.find_all("script", type="application/json")

                data  = []

                for script in scripts:
                    try:
                        parsed = json.loads(script.string)

                        if isinstance(parsed,list):
                            data.extend(parsed)
                        else:
                            data.append(parsed)


                    except Exception as inner_e:
                        print(f"Error parsing JSON-LD on {url}:{inner_e}")
            except Exception as e:
                print(f"Failed to extract JSON-LD from {url}:{e}")
                json_data[url]= []


        return json_data


    def get_structured_page_snapshot(self)->List[PageSnapshot]:
        """
        Returns a structured summary of each URL's content.
        Includes title, headings, main text snippet, JSON-LD, and links with text.

        Returns:
            List[Dict]: one dict per URL 
        """
        

        snapshots = [] 

        for url in self.urls:
            try:
                response = requests.get(url)
                soup = BeautifulSoup(response.text,"html.parser")

                # Title
                title = soup.title.string.strip() if soup.title else"" 

                # Headings 
                headings = {
                        f"h{i}":[tag.get_text(strip=True) for tag in soup.find_all(f"h{i}")]
                        for i in range(1,7)
                        }
                
                # JSON-LD
                texts = soup.find_all(string=True)
                visible_texts = filter(is_visible,texts)
                joined_text = " ".join(t.strip() for t in visible_texts if t.strip())
                snippet = joined_text[:1000] + "..." if len(joined_text)>1000 else joined_text

                json_ld = []

                for script in soup.find_all("script",type="application/ld+json"):
                    try:
                        parsed = json.loads(script.string)
                        json_ld.extend(parsed if isinstance(parsed,list) else [parsed])


                    except Exception as e:
                        continue 
    
                
                links = [
                        {"text": a.get_text(strip=True),"href": urljoin(url,a["href"])}
                        for a in soup.find_all("a",href=True)
                        ]

                snapshots.append(PageSnapshot(
                    url = url,
                    title = title,
                    headings = headings, 
                    main_text_snippet = snippet,
                    json_ld= json_ld,
                    links = links

                    ))
            except Exception as e:
                print(f"Snapshot Failed for {url}:{e}")
                snapshots.append(PageSnapshot(
                    url = url ,
                    title = "",
                    headings={f"h{i}": [] for i in range(1,7)},
                    main_text_snippet="",
                    json_ld=[],
                    links=[]
                    ))
        return snapshots


    def export_snapshots_to_json(self,filepath: str, snapshots: List[PageSnapshot])-> None:
        """
        Serializes a list of PageSnapshot obeject to A JSON file .


        Args:
            filepath(str) :Path to output JSON file 
            snapshots (List[PageSnapshot]): Snapshots to write
        """

        data = [snap.to_dict() for snap in snapshots]
        with open(filepath,"w",encoding="utf-8") as f:
            json.dump(data,f,ensure_ascii=False, indent=2)
    
    def load_snapshots_from_json(self, path: str) -> List[PageSnapshot]:
        with open(path,'r',encoding="utf-8") as f:
            data = json.load(f)
        return [PageSnapshot(**item) for item in data]


    def export_snapshots_to_csv(self, filepath: str, snapshots: List[PageSnapshot]) -> None:
        """
        Exports snapshots to a flat CSV file (summary view).
        Each row includes basic fields plus heading and link counts.
    
        Args:
            filepath (str): Path to CSV file to write.
            snapshots (List[PageSnapshot]): Snapshots to serialize.
        """
        with open(filepath, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "url", "title", "main_text_snippet", 
                "num_links", "num_headings", "num_json_ld"
            ])
            writer.writeheader()
            for snap in snapshots:
                writer.writerow({
                    "url": snap.url,
                    "title": snap.title,
                    "main_text_snippet": snap.main_text_snippet[:300],  # shorten snippet
                    "num_links": len(snap.links),
                    "num_headings": sum(len(hs) for hs in snap.headings.values()),
                    "num_json_ld": len(snap.json_ld)
                })
    
    
    def load_snapshots_from_csv(self, path: str) -> List[Dict[str, Any]]:
        """
        Loads summary snapshot data from a CSV file.
    
        Returns:
            List[Dict[str, Any]]
        """
        with open(path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return [row for row in reader]
