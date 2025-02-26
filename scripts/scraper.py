#!/usr/bin/env python3

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import html2text
import json

def scrape_website(base_url, output_dir="scraped_data"):
    """
    Recursively scrape all pages from the given base_url, storing
    the page data (HTML and Markdown) in JSON files.
    """
    # A set to keep track of visited URLs to avoid infinite loops
    visited_urls = set()
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    def is_same_domain(url):
        """
        Check if `url` is on the same domain as `base_url`.
        """
        base_domain = urlparse(base_url).netloc
        target_domain = urlparse(url).netloc
        return (target_domain == base_domain or target_domain.endswith(base_domain))
    
    def scrape_page(url):
        """
        Scrape a single page, parse out links, store metadata & content, 
        and recursively scrape sub-pages.
        """
        if url in visited_urls:
            return
        visited_urls.add(url)
        
        print(f"Scraping: {url}")
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                print(f"Warning: Non-200 status code received ({response.status_code}) for URL: {url}")
                return
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return
        
        page_html = response.text
        soup = BeautifulSoup(page_html, "html.parser")
        
        # Extract title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""
        
        # Extract meta description (if present)
        meta_description = ""
        description_tag = soup.find("meta", attrs={"name": "description"})
        if description_tag and "content" in description_tag.attrs:
            meta_description = description_tag["content"]
        
        # Convert HTML to Markdown
        # (html2text can be somewhat "chatty" with footnotes, etc. Adjust as needed)
        h2t = html2text.HTML2Text()
        h2t.ignore_links = False  # If you want to keep links in markdown
        page_markdown = h2t.handle(page_html)
        
        # Prepare JSON data
        page_data = {
            "url": url,
            "title": title,
            "meta_description": meta_description,
            "content_html": page_html,
            "content_markdown": page_markdown
        }
        
        # Use the URL to create a filename-friendly identifier
        filename = url_to_filename(url) + ".json"
        filepath = os.path.join(output_dir, filename)
        
        # Write the JSON data
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(page_data, f, ensure_ascii=False, indent=2)
        
        # Recursively follow links on the same domain
        for link_tag in soup.find_all("a", href=True):
            href = link_tag["href"]
            next_url = urljoin(url, href)
            
            # Only crawl same-domain links (avoiding external links)
            if is_same_domain(next_url):
                scrape_page(next_url)
    
    # Utility function to transform a URL into a filesystem-friendly name
    def url_to_filename(url):
        """
        Replace non-alphanumeric characters with underscores to make
        a safe filename.
        """
        return (
            url.replace("http://", "")
               .replace("https://", "")
               .replace("/", "_")
               .replace("?", "_")
               .replace("=", "_")
               .replace("&", "_")
               .replace(":", "_")
        )
    
    # Start scraping from the base URL
    scrape_page(base_url)


if __name__ == "__main__":
    # Example usage:
    BASE_URL = "https://example.com"
    OUTPUT_DIR = "scraped_data"
    
    scrape_website(BASE_URL, OUTPUT_DIR)
