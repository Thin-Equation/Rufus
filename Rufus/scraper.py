from bs4 import BeautifulSoup
from logger import logger
from utils import clean_text as utils_clean_text
import re
import time
import json
import requests
from urllib.parse import urlparse
import traceback

# Try to import optional packages with fallbacks
try:
    import trafilatura
except ImportError:
    logger.warning("Trafilatura not available. Some extraction methods will be disabled.")
    trafilatura = None

try:
    from goose3 import Goose
except ImportError:
    logger.warning("Goose3 not available. Some extraction methods will be disabled.")
    Goose = None

try:
    from readability import Document
except ImportError:
    logger.warning("Readability-lxml not available. Some extraction methods will be disabled.")
    Document = None

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    logger.warning("Selenium not available. JavaScript rendering will be disabled.")
    SELENIUM_AVAILABLE = False

def scrape_content(raw_pages, instructions):
    """
    Filter raw HTML pages to extract text that matches the user-defined instructions.
    Uses multiple content extraction methods for better results.
    """
    logger.info(f"Scraping content with instructions: {instructions}")
    
    filtered_content = {}
    keywords = instructions.lower().split() if instructions else []
    
    if keywords:
        logger.debug(f"Using keywords for filtering: {keywords}")
    
    for url, html in raw_pages.items():
        logger.debug(f"Processing HTML from {url}")
        
        if not html or len(html) < 100:
            logger.warning(f"HTML content from {url} is too small or empty")
            continue
        
        # Try multiple content extraction methods
        extracted_content = extract_content_multi_method(html, url)
        
        if not extracted_content or extracted_content.startswith('[No content'):
            logger.debug(f"No content extracted from {url}")
            continue
        
        if keywords:
            matches = [keyword for keyword in keywords if keyword in extracted_content.lower()]
            if matches:
                logger.debug(f"Content at {url} matched keywords: {matches}")
                filtered_content[url] = extracted_content
            else:
                logger.debug(f"Content at {url} did not match any keywords")
        else:
            logger.debug(f"No keywords specified, including all content from {url}")
            filtered_content[url] = extracted_content
    
    logger.info(f"Filtered content from {len(raw_pages)} pages down to {len(filtered_content)} pages")
    
    # If no content was filtered, but we had pages, return at least the first page
    if len(filtered_content) == 0 and len(raw_pages) > 0:
        # Get the first URL and its content
        first_url = next(iter(raw_pages))
        first_html = raw_pages[first_url]
        extracted = extract_content_multi_method(first_html, first_url)
        filtered_content[first_url] = extracted
        logger.info("No content matched filters. Returning the first page by default.")
    
    return filtered_content

def extract_content_multi_method(html, url):
    """
    Extract content using multiple methods with better fallbacks.
    
    Args:
        html: HTML content of the page
        url: URL of the page
        
    Returns:
        Extracted text content or placeholder if extraction fails
    """
    logger.info(f"Attempting content extraction from {url}")
    extracted_text = ""
    extraction_attempts = 0
    
    # Check if HTML is not None and not empty
    if not html or len(html.strip()) < 100:
        logger.warning(f"HTML content from {url} is too small or empty")
        return f"[Empty or minimal content from {url}]"
    
    # Method 1: Try Trafilatura (good for news articles and blog posts)
    if trafilatura:
        try:
            extraction_attempts += 1
            logger.debug(f"Attempting extraction with Trafilatura for {url}")
            trafilatura_text = trafilatura.extract(html, include_comments=False, 
                                                include_tables=True, 
                                                output_format="text",
                                                favor_precision=True)
            if trafilatura_text and len(trafilatura_text) > 50:  # Lower minimum for minimal sites
                extracted_text = trafilatura_text
                logger.debug(f"Successfully extracted content with Trafilatura: {len(extracted_text)} chars")
                return clean_text(extracted_text)
        except Exception as e:
            logger.debug(f"Trafilatura extraction failed for {url}: {str(e)}")
    
    # Method 2: Try Readability (Mozilla's algorithm)
    if Document:
        try:
            extraction_attempts += 1
            logger.debug(f"Attempting extraction with Readability for {url}")
            doc = Document(html)
            readable_text = doc.summary()
            # Convert the HTML summary to plain text
            readable_soup = BeautifulSoup(readable_text, "html.parser")
            readable_text = readable_soup.get_text(separator=' ', strip=True)
            
            if readable_text and len(readable_text) > 50:
                extracted_text = readable_text
                logger.debug(f"Successfully extracted content with Readability: {len(extracted_text)} chars")
                return clean_text(extracted_text)
        except Exception as e:
            logger.debug(f"Readability extraction failed for {url}: {str(e)}")
    
    # Method 3: Try Goose (good for news articles)
    if Goose:
        try:
            extraction_attempts += 1
            logger.debug(f"Attempting extraction with Goose for {url}")
            g = Goose({'browser_user_agent': 'Mozilla/5.0'})
            article = g.extract(raw_html=html)
            goose_text = article.cleaned_text
            if goose_text and len(goose_text) > 50:
                extracted_text = goose_text
                logger.debug(f"Successfully extracted content with Goose: {len(extracted_text)} chars")
                return clean_text(extracted_text)
        except Exception as e:
            logger.debug(f"Goose extraction failed for {url}: {str(e)}")
    
    # Method 4: BeautifulSoup fallback with more relaxed criteria
    try:
        extraction_attempts += 1
        logger.debug(f"Attempting extraction with BeautifulSoup for {url}")
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()
        
        # First try to find the main content
        content_elements = soup.select('article, main, #content, .content, #main, .main, .post, .article, .page-content, .entry-content, .post-content')
        if content_elements:
            main_content = max(content_elements, key=lambda x: len(x.get_text()))
            bs_text = main_content.get_text(separator=' ', strip=True)
        else:
            # If no content containers found, use the body with paragraphs
            paragraphs = soup.find_all('p')
            if paragraphs:
                bs_text = ' '.join([p.get_text(strip=True) for p in paragraphs])
            else:
                # Last resort: just get all text from body
                bs_text = soup.body.get_text(separator=' ', strip=True) if soup.body else ""
        
        if bs_text and len(bs_text) > 30:  # Very low threshold for basic sites
            extracted_text = bs_text
            logger.debug(f"Successfully extracted content with BeautifulSoup: {len(extracted_text)} chars")
            return clean_text(extracted_text)
    except Exception as e:
        logger.debug(f"BeautifulSoup extraction failed for {url}: {str(e)}")
    
    # Method 5: Raw HTML extractor - simplest possible approach
    try:
        extraction_attempts += 1
        logger.debug(f"Attempting raw text extraction for {url}")
        # Strip HTML tags using regex
        raw_text = re.sub(r'<[^>]+>', ' ', html)
        # Remove extra whitespace
        raw_text = re.sub(r'\s+', ' ', raw_text).strip()
        
        if raw_text and len(raw_text) > 20:  # Extremely low threshold
            logger.debug(f"Extracted raw text: {len(raw_text)} chars")
            return clean_text(raw_text)
    except Exception as e:
        logger.debug(f"Raw text extraction failed for {url}: {str(e)}")
    
    # If we reached this point, all extraction methods failed
    logger.warning(f"All {extraction_attempts} content extraction methods failed for {url}")
    
    # Look for any text in the HTML as a last resort
    try:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string if soup.title else ""
        h1_text = " ".join([h.get_text() for h in soup.find_all('h1')]) if soup.find_all('h1') else ""
        
        if title or h1_text:
            fallback_text = f"Title: {title}\n{h1_text}"
            logger.debug(f"Using title and headings as fallback: {fallback_text[:50]}...")
            return clean_text(fallback_text)
    except Exception:
        pass
    
    # Return a placeholder rather than empty string
    return f"[No content could be extracted from {url}]"

def extract_with_selenium(url, timeout=30):
    """
    Extract content using Selenium for JavaScript-rendered pages.
    
    Args:
        url: URL to extract content from
        timeout: Maximum time to wait for page load in seconds
        
    Returns:
        Page source HTML or None if extraction fails
    """
    if not SELENIUM_AVAILABLE:
        logger.warning("Selenium extraction requested but Selenium is not available")
        return None
        
    try:
        logger.info(f"Extracting content from {url} using Selenium")
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # Specify Chrome binary location explicitly for Mac
        options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        
        # Initialize WebDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(timeout)
        
        driver.get(url)
        # Wait for JavaScript to render
        time.sleep(5)
        
        page_source = driver.page_source
        driver.quit()
        
        return page_source
    except Exception as e:
        logger.error(f"Selenium extraction failed for {url}: {str(e)}")
        logger.debug(traceback.format_exc())
        return None

def clean_text(text):
    """
    Clean extracted text by removing extra whitespace, normalizing characters,
    and fixing common extraction artifacts.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
        
    # Use the utility clean_text function first
    text = utils_clean_text(text)
    
    # Replace multiple spaces, newlines, and tabs with a single space
    text = re.sub(r'\s+', ' ', text)
    
    # Remove any remaining HTML entities
    text = re.sub(r'&[a-zA-Z]+;', ' ', text)
    
    # Fix broken sentences (no space after period)
    text = re.sub(r'\.([A-Z])', '. \\1', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text

class ContentAnalyzer:
    """
    Advanced content analysis to extract structured information from text.
    """
    def __init__(self):
        self.common_stop_words = {
            'a', 'an', 'the', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 
            'be', 'been', 'being', 'to', 'of', 'for', 'in', 'on', 'at', 'by', 
            'with', 'about', 'against', 'between', 'into', 'through', 'during', 
            'before', 'after', 'above', 'below', 'from', 'up', 'down', 'that', 
            'this', 'these', 'those', 'it', 'they', 'we', 'you', 'he', 'she', 'i'
        }
    
    def extract_entities(self, text):
        """
        Extract named entities from text using regex patterns.
        This is a simple implementation - in production you might use 
        a proper NLP library like spaCy.
        
        Args:
            text: Text to extract entities from
            
        Returns:
            List of extracted entities with type information
        """
        entities = []
        
        # Simple patterns for common entity types
        patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b(\+\d{1,2}\s)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b',
            'url': r'https?://[^\s]+',
            'date': r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            'time': r'\b\d{1,2}:\d{2}(:\d{2})?\s*([aApP][mM])?\b',
            'money': r'\$\d+(\.\d{2})?',
            'percentage': r'\d+(\.\d+)?\s*%',
            'address': r'\d+\s+[A-Za-z0-9\s,]+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Place|Pl|Square|Sq)\b'
        }
        
        for entity_type, pattern in patterns.items():
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):  # Some regex captures return tuples
                    match = ''.join([m for m in match if m])
                
                # Avoid duplicates
                if not any(e['text'] == match for e in entities):
                    entities.append({
                        'text': match,
                        'type': entity_type
                    })
        
        return entities
    
    def extract_keywords(self, text, top_n=10):
        """
        Extract important keywords from text.
        Simple implementation using word frequency.
        
        Args:
            text: Text to extract keywords from
            top_n: Number of top keywords to return
            
        Returns:
            List of extracted keywords
        """
        if not text:
            return []
            
        # Remove punctuation and convert to lowercase
        text = re.sub(r'[^\w\s]', '', text.lower())
        
        # Split into words
        words = text.split()
        
        # Remove common stop words
        filtered_words = [word for word in words if word not in self.common_stop_words and len(word) > 2]
        
        # Count word frequencies
        word_freq = {}
        for word in filtered_words:
            if word in word_freq:
                word_freq[word] += 1
            else:
                word_freq[word] = 1
        
        # Get top N keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:top_n]]
    
    def estimate_reading_time(self, text):
        """
        Estimate reading time for text.
        
        Args:
            text: Text to estimate reading time for
            
        Returns:
            Estimated reading time in minutes
        """
        # Average reading speed: 200-250 words per minute
        word_count = len(text.split())
        reading_time = round(word_count / 200, 1)
        return max(0.5, reading_time)  # Minimum 0.5 minutes
    
    def analyze_content(self, text):
        """
        Perform comprehensive content analysis.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with analysis results
        """
        if not text or len(text) < 100:
            return {
                'word_count': 0,
                'reading_time_minutes': 0,
                'entities': [],
                'keywords': [],
                'quality': 'insufficient'
            }
            
        # Get basic metrics
        word_count = len(text.split())
        sentence_count = len(re.split(r'[.!?]+', text))
        
        # Extract entities and keywords
        entities = self.extract_entities(text)
        keywords = self.extract_keywords(text)
        
        # Estimate reading time
        reading_time = self.estimate_reading_time(text)
        
        # Assess content quality
        avg_sentence_length = word_count / max(1, sentence_count)
        quality = 'high' if word_count > 300 and avg_sentence_length > 10 else 'medium' if word_count > 100 else 'low'
        
        return {
            'word_count': word_count,
            'sentence_count': sentence_count,
            'reading_time_minutes': reading_time,
            'entities': entities,
            'keywords': keywords,
            'quality': quality,
            'avg_sentence_length': round(avg_sentence_length, 1)
        }
    
    def extract_faq(self, text):
        """
        Attempt to extract FAQ-like question-answer pairs from text.
        
        Args:
            text: Text to extract FAQs from
            
        Returns:
            List of extracted FAQ pairs
        """
        faqs = []
        
        # Look for question-answer patterns
        # Pattern 1: Q: ... A: ...
        qa_pattern1 = re.compile(r'Q:(.+?)A:(.+?)(?=Q:|$)', re.DOTALL)
        
        # Pattern 2: Question... Answer...
        qa_pattern2 = re.compile(r'(?:^|\n)(.+\?)\s*(.+?)(?=\n.+\?|$)', re.DOTALL)
        
        # Try the first pattern
        matches = qa_pattern1.findall(text)
        if matches:
            for q, a in matches:
                faqs.append({
                    'question': clean_text(q),
                    'answer': clean_text(a)
                })
        
        # If no matches with first pattern, try the second
        if not faqs:
            matches = qa_pattern2.findall(text)
            if matches:
                for q, a in matches:
                    # Filter out false positives (too short answers)
                    if len(a.strip()) > 10:
                        faqs.append({
                            'question': clean_text(q),
                            'answer': clean_text(a)
                        })
        
        return faqs
    
    def extract_contact_info(self, text):
        """
        Extract contact information from text.
        
        Args:
            text: Text to extract contact info from
            
        Returns:
            Dictionary with extracted contact information
        """
        contact_info = {
            'emails': [],
            'phones': [],
            'addresses': []
        }
        
        # Extract emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        contact_info['emails'] = re.findall(email_pattern, text)
        
        # Extract phone numbers
        phone_pattern = r'\b(\+\d{1,2}\s)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b'
        contact_info['phones'] = re.findall(phone_pattern, text)
        
        # Extract addresses
        address_pattern = r'\d+\s+[A-Za-z0-9\s,]+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Place|Pl|Square|Sq)\b'
        contact_info['addresses'] = re.findall(address_pattern, text, re.IGNORECASE)
        
        return contact_info
