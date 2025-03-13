"""Rufus Scraper - A web scraping and content synthesis tool."""

__version__ = "0.1.0"

from client import RufusClient
from crawler import WebCrawler, crawl_website
from scraper import ContentAnalyzer, scrape_content
from clsynthesizer import synthesize_document
