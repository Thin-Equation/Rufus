import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import time
import random
from urllib.parse import urlparse
from logger import logger
from utils import normalize_url, is_same_domain, clean_text
from rate_limiter import RateLimiter

class WebCrawler:
    def __init__(self, requests_per_minute=20, use_selenium=True, headless=True, 
                 respect_robots=True, user_agent=None, same_domain_only=True):
        """
        Initialize the web crawler.
        
        Args:
            requests_per_minute: Maximum requests per minute to a domain
            use_selenium: Whether to use Selenium for JavaScript rendering
            headless: Whether to run the browser in headless mode
            respect_robots: Whether to respect robots.txt
            user_agent: Custom user agent string
            same_domain_only: Whether to only crawl pages on the same domain
        """
        self.rate_limiter = RateLimiter(requests_per_minute=requests_per_minute)
        self.use_selenium = use_selenium
        self.headless = headless
        self.respect_robots = respect_robots
        self.same_domain_only = same_domain_only
        
        # Set up user agent
        self.user_agent = user_agent or 'Rufus Web Crawler/1.0'
        
        # Initialize Selenium if needed
        self.driver = None
        if use_selenium:
            self._init_selenium()
        
        # Store robots.txt rules
        self.robots_rules = {}
    
    def _init_selenium(self):
        """Initialize Selenium WebDriver."""
        try:
            options = Options()
            if self.headless:
                options.add_argument('--headless')
            
            options.add_argument(f'user-agent={self.user_agent}')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            # Set up Chrome WebDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(30)  # Set timeout to 30 seconds
            
            logger.info("Selenium WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Selenium: {str(e)}")
            self.use_selenium = False
    
    def _check_robots_txt(self, url):
        """Check if crawling is allowed by robots.txt."""
        if not self.respect_robots:
            return True
        
        domain = urlparse(url).netloc
        
        # If we've already checked this domain's robots.txt
        if domain in self.robots_rules:
            return self.robots_rules[domain]
        
        # Otherwise, fetch and parse robots.txt
        try:
            robots_url = f"{urlparse(url).scheme}://{domain}/robots.txt"
            response = requests.get(robots_url, timeout=10)
            
            if response.status_code == 200:
                # Very simple robots.txt parsing - just check if our user agent is disallowed
                lines = response.text.lower().split('\n')
                user_agent_applies = False
                disallowed = False
                
                for line in lines:
                    if line.startswith('user-agent:'):
                        agent = line.split(':', 1)[1].strip()
                        if agent == '*' or self.user_agent.lower() in agent:
                            user_agent_applies = True
                        else:
                            user_agent_applies = False
                    
                    if user_agent_applies and line.startswith('disallow:'):
                        path = line.split(':', 1)[1].strip()
                        if path and urlparse(url).path.startswith(path):
                            disallowed = True
                            break
                
                self.robots_rules[domain] = not disallowed
                return not disallowed
            
            # If robots.txt doesn't exist or can't be parsed, assume crawling is allowed
            self.robots_rules[domain] = True
            return True
            
        except Exception as e:
            logger.warning(f"Error checking robots.txt for {domain}: {str(e)}")
            # If there's an error, assume crawling is allowed
            self.robots_rules[domain] = True
            return True
    
    def _get_page_content(self, url):
        """
        Get the HTML content of a page, using either requests or Selenium.
        """
        domain = urlparse(url).netloc
        
        # Apply rate limiting
        self.rate_limiter.wait_if_needed(domain)
        
        # Check robots.txt
        if not self._check_robots_txt(url):
            logger.info(f"Skipping {url} - disallowed by robots.txt")
            return None
        
        try:
            if self.use_selenium and self.driver:
                try:
                    logger.debug(f"Fetching {url} with Selenium")
                    self.driver.get(url)
                    
                    # Wait for dynamic content to load
                    time.sleep(random.uniform(1, 3))
                    
                    # Get the page source after JavaScript execution
                    html = self.driver.page_source
                    return html
                except TimeoutException:
                    logger.warning(f"Selenium timeout for {url}, falling back to requests")
                except Exception as e:
                    logger.warning(f"Selenium error for {url}: {str(e)}, falling back to requests")
            
            # Fall back to requests if Selenium fails or is disabled
            logger.debug(f"Fetching {url} with requests")
            headers = {'User-Agent': self.user_agent}
            
            # Use rate limiter's backoff mechanism for the request
            response = self.rate_limiter.make_request_with_backoff(
                requests.get, 
                url, 
                timeout=15, 
                headers=headers
            )
            
            return response.text
            
        except Exception as e:
            logger.warning(f"Failed to retrieve {url}: {str(e)}")
            return None
    
    def crawl(self, start_url, max_depth=1, max_pages=100):
        """
        Crawl a website starting from the given URL.
        
        Args:
            start_url: The URL to start crawling from
            max_depth: Maximum crawl depth
            max_pages: Maximum number of pages to crawl
            
        Returns:
            Dictionary mapping URLs to their HTML content
        """
        visited = set()
        to_visit = [(start_url, 0)]  # (url, depth)
        pages = {}
        start_domain = urlparse(start_url).netloc
        
        logger.info(f"Starting crawl from {start_url} with max depth {max_depth} and max pages {max_pages}")
        
        while to_visit and len(pages) < max_pages:
            url, depth = to_visit.pop(0)
            
            if url in visited or depth > max_depth:
                continue
            
            visited.add(url)
            
            # Check if we should only crawl the same domain
            if self.same_domain_only and urlparse(url).netloc != start_domain:
                logger.debug(f"Skipping {url} - different domain from start URL")
                continue
            
            logger.info(f"Crawling: {url} (depth: {depth})")
            
            html = self._get_page_content(url)
            if not html:
                continue
            
            pages[url] = html
            logger.debug(f"Successfully retrieved content from {url} ({len(html)} bytes)")
            
            # If we've reached the maximum depth, don't extract more links
            if depth >= max_depth:
                continue
            
            # Extract links for the next level
            try:
                soup = BeautifulSoup(html, "html.parser")
                links = []
                
                for a_tag in soup.find_all('a', href=True):
                    link = normalize_url(a_tag['href'], base=url)
                    if link and link not in visited:
                        links.append((link, depth + 1))
                
                logger.debug(f"Found {len(links)} links on {url}")
                
                # Add links to the queue
                to_visit.extend(links)
                
                # Shuffle to_visit to avoid crawling patterns
                random.shuffle(to_visit)
                
            except Exception as e:
                logger.warning(f"Error extracting links from {url}: {str(e)}")
        
        logger.info(f"Crawl complete. Retrieved {len(pages)} pages")
        return pages
    
    def close(self):
        """Close the Selenium WebDriver if it's open."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Selenium WebDriver closed")
            except Exception as e:
                logger.warning(f"Error closing Selenium WebDriver: {str(e)}")

def crawl_website(url, max_depth=1, max_pages=100, **kwargs):
    """
    Wrapper function for the WebCrawler class.
    
    Args:
        url: The URL to start crawling from
        max_depth: Maximum crawl depth
        max_pages: Maximum number of pages to crawl
        **kwargs: Additional arguments to pass to WebCrawler
        
    Returns:
        Dictionary mapping URLs to their HTML content
    """
    crawler = WebCrawler(**kwargs)
    try:
        return crawler.crawl(url, max_depth=max_depth, max_pages=max_pages)
    finally:
        crawler.close()
