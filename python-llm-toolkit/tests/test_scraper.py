
# test_scraper.py

import os
import json
import pytest
import tempfile
import httpx
import aiofiles
from typing import List, Dict
from python_llm_toolkit.scraper import WebScraper, SEARCH_TERMS, FILE_EXTENSIONS, PageSnapshot
import pytest_asyncio

pytestmark = pytest.mark.asyncio

home_dir = os.getcwd()

@pytest_asyncio.fixture
async def async_scraper():
    return WebScraper(
        search_terms=SEARCH_TERMS,
        file_types=FILE_EXTENSIONS,
        output_dir=os.path.join(home_dir, "downloads"),
        max_depth=5,
        urls=["https://smithtech.io", "https://google.com", "https://www.uchicagomedicine.org/"]
    )

async def test_WebScraper_Creation(async_scraper):
    assert isinstance(async_scraper, WebScraper)

async def test_fetch_links_from_url(async_scraper):
    async with httpx.AsyncClient() as client:
        links = await async_scraper.fetch_links_from_url(client, async_scraper.urls[0])
        assert isinstance(links, list)

async def test_get_meta_data(async_scraper):
    async with httpx.AsyncClient() as client:
        result = await async_scraper.get_meta_data(client, async_scraper.urls[0])
        assert isinstance(result, dict)
        assert "url" in result
        assert "title" in result

async def test_extract_main_text(async_scraper):
    async with httpx.AsyncClient() as client:
        text = await async_scraper.extract_main_text(client, async_scraper.urls[0])
        assert isinstance(text, str)

async def test_search_text_for_keywords(async_scraper):
    async with httpx.AsyncClient() as client:
        result = await async_scraper.search_text_for_keywords(client, async_scraper.urls[0])
        assert isinstance(result, list)
        assert all(isinstance(k, str) for k in result)

async def test_extract_links_with_text(async_scraper):
    async with httpx.AsyncClient() as client:
        links = await async_scraper.extract_links_with_text(client, async_scraper.urls[0])
        assert isinstance(links, list)
        if links:
            assert "href" in links[0]
            assert "text" in links[0]

async def test_extract_json_ld(async_scraper):
    async with httpx.AsyncClient() as client:
        data = await async_scraper.extract_json_ld(client, async_scraper.urls[0])
        assert isinstance(data, list)
        for item in data:
            assert isinstance(item, dict)

@pytest_asyncio.fixture
async def test_scraper():
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield WebScraper(
            search_terms=[],
            file_types=['.txt'],
            max_depth=1,
            output_dir=tmp_dir,
            urls=["https://www.w3.org/TR/PNG/iso_8859-1.txt"]
        )

def test_download_files_create_files():
    with tempfile.TemporaryDirectory() as tmp_dir:
        scraper = WebScraper([], ['.txt'], 1, tmp_dir, ["https://www.w3.org/TR/PNG/iso_8859-1.txt"])
        links = ["https://www.w3.org/TR/PNG/iso_8859-1.txt"]
        filtered = scraper.filter_links_by_file_type(links)
        downloaded = scraper.download_files(filtered)
        assert isinstance(downloaded, list)
        assert len(downloaded) > 0
        for path in downloaded:
            assert os.path.exists(path)
            assert os.path.isfile(path)

def test_downloaded_files_handles_bad_link():
    with tempfile.TemporaryDirectory() as tmp_dir:
        scraper = WebScraper([], ['.txt'], 1, tmp_dir, ["https://example.com/thisfiledoesnotexist.pdf"])
        result = scraper.download_files(scraper.urls)
        assert result == []
        assert len(scraper.files_downloaded) == 0

def test_download_files_creates_subfolders():
    with tempfile.TemporaryDirectory() as tmp_dir:
        scraper = WebScraper([], ['.txt'], 1, tmp_dir, ["https://www.w3.org/TR/PNG/iso_8859-1.txt"])
        links = ["https://www.w3.org/TR/PNG/iso_8859-1.txt"]
        downloaded = scraper.download_files(links)
        assert len(downloaded) == 1
        file_path = downloaded[0]
        assert "w3.org" in file_path
        assert "txt" in file_path

async def test_async_get_structured_snapshot(async_scraper):
    async with httpx.AsyncClient() as client:
        snapshot = await async_scraper.get_structured_snapshot(client, async_scraper.urls[0])
    assert isinstance(snapshot, PageSnapshot)
    assert snapshot.url == async_scraper.urls[0]

async def test_async_export_and_load_snapshots_json(tmp_path, async_scraper):
    async with httpx.AsyncClient() as client:
        snap = await async_scraper.get_structured_snapshot(client, async_scraper.urls[0])
    path = tmp_path / "snapshot.json"
    await async_scraper.async_export_snapshots_to_json(str(path), [snap])
    assert path.exists()
    loaded = await async_scraper.load_snapshots_from_json(str(path))
    assert isinstance(loaded, list)
    assert isinstance(loaded[0], PageSnapshot)
    assert loaded[0].url == snap.url

async def test_async_export_snapshots_to_csv(tmp_path, async_scraper):
    async with httpx.AsyncClient() as client:
        snap = await async_scraper.get_structured_snapshot(client, async_scraper.urls[0])
    csv_path = tmp_path / "snapshot.csv"
    await async_scraper.export_snapshots_to_csv(str(csv_path), [snap])
    assert csv_path.exists()
    async with aiofiles.open(csv_path, mode="r") as f:
        content = await f.read()
        assert "url" in content and snap.url in content



