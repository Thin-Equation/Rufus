import os
import logging
from .crawler import crawl_website
from .scraper import scrape_content, ContentAnalyzer
from .synthesizer import synthesize_document
from .logger import setup_logger, logger
from .utils import extract_domain
from .rate_limiter import RateLimiter

class RufusClient:
    def __init__(self, api_key=None, nim_api_key=None, log_level=logging.INFO, log_file=None,
                 requests_per_minute=20, use_selenium=True, max_depth=2, max_pages=50,
                 output_dir="outputs", respect_robots=True, same_domain_only=True):
        """
        Initialize the Rufus web scraping client.
        
        Args:
            api_key: API key for the Rufus service
            nim_api_key: API key for NVIDIA NIM
            log_level: Logging level (DEBUG, INFO, etc.)
            log_file: Path to the log file
            requests_per_minute: Maximum requests per minute to a domain
            use_selenium: Whether to use Selenium for JavaScript rendering
            max_depth: Maximum crawling depth
            max_pages: Maximum number of pages to crawl
            output_dir: Directory to store output files
            respect_robots: Whether to respect robots.txt
            same_domain_only: Whether to only crawl pages on the same domain
        """
        # Configure logging if custom settings are provided
        if log_level != logging.INFO or log_file:
            setup_logger(log_level=log_level, log_file=log_file)
            
        logger.info("Initializing RufusClient")
        
        self.api_key = api_key or os.getenv('Rufus_API_KEY')
        self.nim_api_key = nim_api_key or os.getenv('NVIDIA_NIM_API_KEY')
        
        if not self.api_key:
            logger.error("API key is missing")
            raise ValueError("API key is required for RufusClient initialization")
            
        if not self.nim_api_key:
            logger.error("NVIDIA NIM API key is missing")
            raise ValueError("NVIDIA NIM API key is required for synthesizer integration")
        
        # Store configuration
        self.requests_per_minute = requests_per_minute
        self.use_selenium = use_selenium
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.output_dir = output_dir
        self.respect_robots = respect_robots
        self.same_domain_only = same_domain_only
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize content analyzer
        self.content_analyzer = ContentAnalyzer()
            
        logger.info("RufusClient initialized successfully")

    def scrape(self, url, instructions="", max_depth=None, max_pages=None):
        """
        Scrape content from a URL and synthesize it based on instructions.
        
        Args:
            url: The URL to scrape
            instructions: Instructions for content filtering and synthesis
            max_depth: Maximum crawling depth (overrides the client setting)
            max_pages: Maximum number of pages to crawl (overrides the client setting)
            
        Returns:
            Structured document synthesized from the scraped content
        """
        logger.info(f"Starting scrape operation for URL: {url}")
        
        # Use override values if provided
        max_depth = max_depth if max_depth is not None else self.max_depth
        max_pages = max_pages if max_pages is not None else self.max_pages
        
        # Step 1: Crawl the website to retrieve raw HTML pages
        logger.info(f"Step 1: Crawling website with depth {max_depth} and max pages {max_pages}")
        raw_pages = crawl_website(
            url, 
            max_depth=max_depth,
            max_pages=max_pages,
            requests_per_minute=self.requests_per_minute,
            use_selenium=self.use_selenium,
            respect_robots=self.respect_robots,
            same_domain_only=self.same_domain_only
        )
        
        if not raw_pages:
            logger.warning("No pages retrieved during crawling")
            return {"response": "NO WEB CONTENT"}
            
        logger.info(f"Crawling complete. Retrieved {len(raw_pages)} pages")
        
        # Step 2: Filter and extract relevant content based on the given instructions
        logger.info("Step 2: Extracting relevant content")
        scraped_data = scrape_content(raw_pages, instructions)
        
        if not scraped_data:
            logger.warning("No relevant content found")
            return {"response": "NO RELEVANT CONTENT"}
            
        logger.info(f"Extraction complete. Processed {len(scraped_data)} pages")
        
        # Step 3: Synthesize the scraped data into a structured document using Nvidia NIM API
        logger.info("Step 3: Synthesizing document")
        document = synthesize_document(
            scraped_data, 
            instructions, 
            nim_api_key=self.nim_api_key,
            output_dir=self.output_dir
        )
        logger.info("Document synthesis complete")
        
        return document
