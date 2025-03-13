import time
from collections import defaultdict
from logger import logger
import random

class RateLimiter:
    def __init__(self, requests_per_minute=20):
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # seconds
        self.timestamps = defaultdict(list)
    
    def wait_if_needed(self, domain):
        """
        Check if we need to wait before making another request to this domain.
        """
        current_time = time.time()
        
        # Clean up old timestamps
        self.timestamps[domain] = [ts for ts in self.timestamps[domain] 
                                  if current_time - ts < self.window_size]
        
        # Check if we've hit the rate limit
        if len(self.timestamps[domain]) >= self.requests_per_minute:
            # Calculate how long to wait
            oldest_timestamp = min(self.timestamps[domain])
            sleep_time = self.window_size - (current_time - oldest_timestamp)
            
            if sleep_time > 0:
                # Add a small random jitter to avoid synchronized requests
                sleep_time += random.uniform(0.1, 1.0)
                logger.info(f"Rate limiting for {domain}. Waiting {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
        
        # Add current timestamp
        self.timestamps[domain].append(time.time())
        
    def make_request_with_backoff(self, request_func, url, max_retries=5, base_delay=3, **kwargs):
        """
        Make a request with exponential backoff for rate limiting.
        
        Args:
            request_func: The function to make the request (e.g., requests.get)
            url: The URL to request
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            **kwargs: Additional arguments to pass to the request function
            
        Returns:
            The response from the request function
        """
        for attempt in range(max_retries):
            try:
                response = request_func(url, **kwargs)
                response.raise_for_status()
                return response
            except Exception as e:
                # Check if it's a rate limiting error (status code 429)
                if hasattr(e, 'response') and getattr(e.response, 'status_code', None) == 429:
                    # Calculate delay with exponential backoff and jitter
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Rate limited on {url}. Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                    continue
                elif attempt < max_retries - 1:
                    # For other errors, retry with backoff if we have attempts left
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Request failed for {url}: {str(e)}. Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                    continue
                else:
                    # If we've exhausted our retries, raise the exception
                    logger.error(f"Max retries exceeded for {url}: {str(e)}")
                    raise
        
        # This should not be reached due to the raise in the loop
        raise Exception(f"Unexpected error in make_request_with_backoff for {url}")
