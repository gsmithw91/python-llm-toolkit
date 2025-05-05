# tools.py

from typing import List, Dict, Any
from pathlib import Path
from python_llm_toolkit.scraper import WebScraper, SEARCH_TERMS, FILE_EXTENSIONS

DEFAULT_OUTPUT_DIR = str(Path("downloads").resolve())


def get_page_metadata(urls: List[str]) -> List[Dict[str, str]]:
    """
    Extract metadata (title and description) from a list of web pages.

    Args:
        urls (List[str]): List of target URLs.

    Returns:
        List[Dict[str, str]]: List of metadata dictionaries for each page.
    """
    scraper = WebScraper(
        urls=urls,
        output_dir=DEFAULT_OUTPUT_DIR,
        file_types=FILE_EXTENSIONS,
        search_terms=SEARCH_TERMS,
        max_depth=5
    )
    return scraper.get_meta_data()


def download_files_by_type(urls: List[str], file_extensions: List[str]) -> List[str]:
    """
    Download files matching the given file extensions from the specified URLs.

    Args:
        urls (List[str]): List of target URLs.
        file_extensions (List[str]): File extensions to download (e.g., ['.pdf', '.csv']).

    Returns:
        List[str]: List of local file paths for downloaded files.
    """
    scraper = WebScraper(
        urls=urls,
        output_dir=DEFAULT_OUTPUT_DIR,
        file_types=file_extensions,
        search_terms=SEARCH_TERMS,
        max_depth=5
    )

    links = scraper.fetch_links_from_url()
    filtered = scraper.filter_links_by_file_type(links)
    return scraper.download_files(filtered)


def get_structured_snapshots(urls: List[str]) -> List[Dict[str, Any]]:
    """
    Retrieve a structured snapshot (title, headings, links, etc.) from each web page.

    Args:
        urls (List[str]): List of target URLs.

    Returns:
        List[Dict[str, Any]]: Snapshot data per URL as dictionaries.
    """
    scraper = WebScraper(
        urls=urls,
        output_dir=DEFAULT_OUTPUT_DIR,
        file_types=FILE_EXTENSIONS,
        search_terms=SEARCH_TERMS,
        max_depth=5
    )

    snapshots = scraper.get_structured_page_snapshot()
    return [snap.to_dict() for snap in snapshots]


def search_keywords_in_page(urls: List[str], keywords: List[str]) -> Dict[str, List[str]]:
    """
    Search for specific keywords on each page.

    Args:
        urls (List[str]): List of URLs to scan.
        keywords (List[str]): Keywords to search for.

    Returns:
        Dict[str, List[str]]: Dictionary mapping URLs to matched keywords.
    """
    scraper = WebScraper(
        urls=urls,
        output_dir=DEFAULT_OUTPUT_DIR,
        file_types=FILE_EXTENSIONS,
        search_terms=keywords,
        max_depth=5
    )

    return scraper.search_text_for_keywords()


def extract_tables_from_page(urls: List[str]) -> Dict[str, List[List[List[str]]]]:
    """
    Extract HTML tables from each URL.

    Args:
        urls (List[str]): List of URLs containing tables.

    Returns:
        Dict[str, List[List[List[str]]]]: Tables per page (page -> list of tables -> rows -> cells).
    """
    scraper = WebScraper(
        urls=urls,
        output_dir=DEFAULT_OUTPUT_DIR,
        file_types=FILE_EXTENSIONS,
        search_terms=SEARCH_TERMS,
        max_depth=5
    )

    return scraper.extract_tables()


TOOLS = [
    get_page_metadata,
    get_structured_snapshots,
    download_files_by_type,
    search_keywords_in_page,
    extract_tables_from_page
]

