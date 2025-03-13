from urllib.parse import urljoin, urlparse
from logger import logger
import re

def normalize_url(href, base):
    """
    Normalize relative URLs against a base URL and return a complete URL.
    Removes fragments and ensures the URL starts with a valid HTTP scheme.
    """
    url = urljoin(base, href)
    parsed = urlparse(url)
    
    # Skip non-HTTP URLs
    if not parsed.scheme.startswith("http"):
        logger.debug(f"Skipping non-HTTP URL: {url}")
        return ""
    
    # Skip URLs with file extensions that are typically not HTML
    if parsed.path:
        file_ext = parsed.path.split('.')[-1].lower()
        skip_extensions = ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'css', 'js', 'xml', 'zip', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx']
        if file_ext in skip_extensions:
            logger.debug(f"Skipping non-HTML file: {url}")
            return ""
    
    # Remove any fragment identifiers
    normalized = url.split("#")[0]
    
    # Remove query parameters if they're for tracking
    if '?' in normalized:
        base_url = normalized.split('?')[0]
        query = normalized.split('?')[1]
        
        # List of common tracking parameters to remove
        tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'fbclid', 'gclid']
        
        # Keep only non-tracking parameters
        params = query.split('&')
        filtered_params = []
        
        for param in params:
            if '=' in param:
                param_name = param.split('=')[0]
                if not any(tracking in param_name.lower() for tracking in tracking_params):
                    filtered_params.append(param)
        
        if filtered_params:
            normalized = base_url + '?' + '&'.join(filtered_params)
        else:
            normalized = base_url
    
    if normalized != url:
        logger.debug(f"Normalized URL from {url} to {normalized}")
        
    return normalized

def extract_domain(url):
    """Extract the domain from a URL."""
    return urlparse(url).netloc

def is_same_domain(url1, url2):
    """Check if two URLs belong to the same domain."""
    return extract_domain(url1) == extract_domain(url2)

def clean_text(text):
    """Clean extracted text by removing extra whitespace."""
    # Replace multiple spaces, newlines, and tabs with a single space
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace
    text = text.strip()
    return text
