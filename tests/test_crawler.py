import unittest
from unittest.mock import patch, MagicMock
import responses
import os
import sys
import requests
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler import WebCrawler
from utils import normalize_url, extract_domain

class TestCrawler(unittest.TestCase):
    def setUp(self):
        self.crawler = WebCrawler(requests_per_minute=60, use_selenium=False)
        self.test_url = "https://example.com"
        
    def tearDown(self):
        if self.crawler.driver:
            self.crawler.close()
    
    def test_normalize_url(self):
        """Test URL normalization functionality"""
        # Test relative URL normalization
        self.assertEqual(
            normalize_url("/page1.html", self.test_url),
            "https://example.com/page1.html"
        )
        
        # Test fragment removal
        self.assertEqual(
            normalize_url("https://example.com/page#section", ""),
            "https://example.com/page"
        )
        
        # Test non-HTTP URL filtering
        self.assertEqual(normalize_url("ftp://example.com", ""), "")
        
        # Test tracking parameter removal
        self.assertEqual(
            normalize_url("https://example.com/page?utm_source=test", ""),
            "https://example.com/page"
        )
    
    @responses.activate
    def test_robots_txt_parsing(self):
        """Test robots.txt parsing"""
        # Mock robots.txt response
        robots_content = """
        User-agent: *
        Disallow: /private/
        Allow: /public/
        """
        responses.add(responses.GET, "https://example.com/robots.txt", 
                     body=robots_content, status=200)
        
        # Test allowed URL
        self.assertTrue(self.crawler._check_robots_txt("https://example.com/public/page"))
        
        # Test disallowed URL
        self.assertFalse(self.crawler._check_robots_txt("https://example.com/private/page"))
    
    @patch('requests.get')
    def test_rate_limiting(self, mock_get):
        """Test rate limiting behavior"""
        mock_get.return_value.text = "<html><body>Test</body></html>"
        mock_get.return_value.status_code = 200
        
        # Create a crawler with very low rate limit
        slow_crawler = WebCrawler(requests_per_minute=2, use_selenium=False)
        
        # Time how long it takes to make 3 requests
        import time
        start_time = time.time()
        slow_crawler._get_page_content("https://example.com/1")
        slow_crawler._get_page_content("https://example.com/2")
        slow_crawler._get_page_content("https://example.com/3")
        total_time = time.time() - start_time
        
        # With 2 requests per minute, 3 requests should take >30 seconds
        self.assertGreater(total_time, 30)
    
    @responses.activate
    def test_error_handling(self):
        """Test error handling for various HTTP errors"""
        # Timeout error
        responses.add(responses.GET, "https://example.com/timeout", 
                     body=requests.exceptions.Timeout())
        
        # 404 error
        responses.add(responses.GET, "https://example.com/404", 
                     status=404)
        
        # 500 error
        responses.add(responses.GET, "https://example.com/500", 
                     status=500)
        
        # Check that none of these errors crash the crawler
        self.assertIsNone(self.crawler._get_page_content("https://example.com/timeout"))
        self.assertIsNone(self.crawler._get_page_content("https://example.com/404"))
        self.assertIsNone(self.crawler._get_page_content("https://example.com/500"))

if __name__ == '__main__':
    unittest.main()
