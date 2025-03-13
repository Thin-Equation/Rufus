import unittest
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper import extract_content_multi_method, ContentAnalyzer, clean_text

class TestScraper(unittest.TestCase):
    def setUp(self):
        self.analyzer = ContentAnalyzer()
        self.fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures', 'html_samples')
    
    def load_fixture(self, filename):
        """Load HTML fixture file"""
        file_path = os.path.join(self.fixtures_dir, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def test_extraction_from_simple_html(self):
        """Test content extraction from simple HTML"""
        # Create a simple HTML file if it doesn't exist
        simple_html_path = os.path.join(self.fixtures_dir, 'simple_page.html')
        if not os.path.exists(simple_html_path):
            os.makedirs(os.path.dirname(simple_html_path), exist_ok=True)
            with open(simple_html_path, 'w', encoding='utf-8') as f:
                f.write("""
                <html>
                <head><title>Test Page</title></head>
                <body>
                    <h1>Welcome to Test Page</h1>
                    <p>This is a paragraph of test content.</p>
                    <p>Another paragraph with <b>bold text</b>.</p>
                </body>
                </html>
                """)
        
        html = self.load_fixture('simple_page.html')
        content = extract_content_multi_method(html, "https://example.com/test")
        
        self.assertIn("Welcome to Test Page", content)
        self.assertIn("This is a paragraph of test content", content)
        self.assertIn("Another paragraph with bold text", content)
    
    def test_extraction_from_malformed_html(self):
        """Test content extraction from malformed HTML"""
        # Create a malformed HTML file if it doesn't exist
        malformed_html_path = os.path.join(self.fixtures_dir, 'malformed_page.html')
        if not os.path.exists(malformed_html_path):
            os.makedirs(os.path.dirname(malformed_html_path), exist_ok=True)
            with open(malformed_html_path, 'w', encoding='utf-8') as f:
                f.write("""
                <html>
                <head><title>Malformed Page</title>
                <body>
                    <h1>Malformed HTML Example</h2>
                    <p>This HTML has unclosed tags.
                    <div>This div is never closed.
                    <p>Another paragraph.
                </html>
                """)
        
        html = self.load_fixture('malformed_page.html')
        content = extract_content_multi_method(html, "https://example.com/malformed")
        
        # Despite malformed HTML, extraction should still get something
        self.assertIn("Malformed HTML Example", content)
        self.assertIn("This HTML has unclosed tags", content)
    
    def test_empty_content_handling(self):
        """Test handling of empty or minimal content"""
        # Create an empty HTML file if it doesn't exist
        empty_html_path = os.path.join(self.fixtures_dir, 'empty_page.html')
        if not os.path.exists(empty_html_path):
            os.makedirs(os.path.dirname(empty_html_path), exist_ok=True)
            with open(empty_html_path, 'w', encoding='utf-8') as f:
                f.write("<html><body></body></html>")
        
        html = self.load_fixture('empty_page.html')
        content = extract_content_multi_method(html, "https://example.com/empty")
        
        # Should return a message about empty content
        self.assertIn("Empty or minimal content", content)
    
    def test_entity_extraction(self):
        """Test entity extraction functionality"""
        text = "Contact us at info@example.com or call (555) 123-4567. Visit us at https://example.com"
        entities = self.analyzer.extract_entities(text)
        
        # Check if entities were correctly extracted
        email_found = False
        phone_found = False
        url_found = False
        
        for entity in entities:
            if entity['type'] == 'email' and entity['text'] == 'info@example.com':
                email_found = True
            elif entity['type'] == 'phone' and '5551234567' in entity['text'].replace('-', '').replace(' ', ''):
                phone_found = True
            elif entity['type'] == 'url' and entity['text'] == 'https://example.com':
                url_found = True
        
        self.assertTrue(email_found, "Failed to extract email")
        self.assertTrue(phone_found, "Failed to extract phone")
        self.assertTrue(url_found, "Failed to extract URL")
    
    def test_keyword_extraction(self):
        """Test keyword extraction"""
        text = "Climate change is a major global challenge. The effects of climate change include rising temperatures, extreme weather events, and sea level rise. Addressing climate change requires global cooperation."
        
        keywords = self.analyzer.extract_keywords(text, top_n=5)
        
        self.assertIn("climate", keywords)
        self.assertIn("change", keywords)
        self.assertIn("global", keywords)
        
        # Stop words should be excluded
        self.assertNotIn("is", keywords)
        self.assertNotIn("a", keywords)
        self.assertNotIn("the", keywords)
    
    def test_text_cleaning(self):
        """Test text cleaning functionality"""
        dirty_text = "  This has\n\nextra   spaces \t and tabs.   "
        cleaned = clean_text(dirty_text)
        
        self.assertEqual(cleaned, "This has extra spaces and tabs.")
        
        html_text = "This has <b>HTML</b> tags and &nbsp; entities."
        cleaned = clean_text(html_text)
        
        self.assertNotIn("<b>", cleaned)
        self.assertNotIn("</b>", cleaned)
        self.assertNotIn("&nbsp;", cleaned)

if __name__ == '__main__':
    unittest.main()
