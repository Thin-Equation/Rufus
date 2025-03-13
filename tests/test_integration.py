import unittest
import os
import sys
import tempfile
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client import RufusClient
import responses

class TestIntegration(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for outputs
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock API keys
        self.api_key = "mock_api_key"
        self.nim_api_key = "mock_nim_api_key"
        
        # Initialize client with test configuration
        self.client = RufusClient(
            api_key=self.api_key,
            nim_api_key=self.nim_api_key,
            output_dir=self.temp_dir,
            use_selenium=False,
            max_depth=1,
            max_pages=5,
            requests_per_minute=60
        )
    
    def tearDown(self):
        # Clean up temp directory after tests
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @responses.activate
    def test_full_pipeline(self):
        """Test the full pipeline from crawling to synthesis"""
        # Mock website responses
        main_html = """
        <html>
        <head><title>Test Site</title></head>
        <body>
            <h1>Welcome to Test Site</h1>
            <p>This is a sample website for testing.</p>
            <p>It contains information about <b>climate change</b>.</p>
            <a href="/page1.html">Page 1</a>
            <a href="/page2.html">Page 2</a>
        </body>
        </html>
        """
        
        page1_html = """
        <html>
        <head><title>Page 1</title></head>
        <body>
            <h1>Page 1: Climate Effects</h1>
            <p>Climate change has many effects on our planet.</p>
            <p>Rising temperatures are a major concern.</p>
        </body>
        </html>
        """
        
        page2_html = """
        <html>
        <head><title>Page 2</title></head>
        <body>
            <h1>Page 2: Solutions</h1>
            <p>There are many solutions to address climate change.</p>
            <p>Renewable energy is one important approach.</p>
        </body>
        </html>
        """
        
        # Mock robots.txt
        robots_txt = """
        User-agent: *
        Allow: /
        """
        
        # Add mock responses
        responses.add(responses.GET, "https://example.com/robots.txt", body=robots_txt, status=200)
        responses.add(responses.GET, "https://example.com", body=main_html, status=200)
        responses.add(responses.GET, "https://example.com/page1.html", body=page1_html, status=200)
        responses.add(responses.GET, "https://example.com/page2.html", body=page2_html, status=200)
        
        # Mock the NIM API response
        nim_response = {
            "title": "Climate Change Overview",
            "summary": "This is a collection of pages about climate change, its effects, and solutions.",
            "key_points": [
                "Climate change is affecting our planet",
                "Rising temperatures are a major concern",
                "Renewable energy is an important solution"
            ],
            "content_sections": [
                {
                    "heading": "Introduction",
                    "content": "This website provides information about climate change."
                },
                {
                    "heading": "Effects",
                    "content": "Climate change has many effects including rising temperatures."
                },
                {
                    "heading": "Solutions",
                    "content": "Renewable energy is one approach to addressing climate change."
                }
            ],
            "metadata": {
                "sources": ["https://example.com", "https://example.com/page1.html", "https://example.com/page2.html"],
                "page_count": 3
            }
        }
        
        # Mock the OpenAI/NIM API call
        with unittest.mock.patch('openai.OpenAI') as mock_openai:
            mock_client = unittest.mock.MagicMock()
            mock_openai.return_value = mock_client
            
            mock_response = unittest.mock.MagicMock()
            mock_response.choices = [unittest.mock.MagicMock()]
            mock_response.choices[0].message.content = json.dumps(nim_response)
            
            mock_client.chat.completions.create.return_value = mock_response
            
            # Run the full pipeline
            result = self.client.scrape("https://example.com", "Information about climate change")
            
            # Verify output
            self.assertIn("title", result)
            self.assertIn("summary", result)
            self.assertIn("key_points", result)
            self.assertEqual(result["title"], "Climate Change Overview")
            
            # Check for output files
            output_files = os.listdir(self.temp_dir)
            self.assertGreaterEqual(len(output_files), 2)  # Should have at least 2 files (content and JSON)

if __name__ == '__main__':
    unittest.main()
