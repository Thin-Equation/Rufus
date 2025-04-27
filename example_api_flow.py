import os
import json
import logging
import argparse

# Removed sys.path manipulation as Rufus should be installed as a package
# import sys
# current_dir = os.path.dirname(os.path.realpath(__file__))
# sys.path.append(os.path.join(current_dir, 'Rufus'))

from Rufus.client import RufusClient


def main():
    parser = argparse.ArgumentParser(description="Rufus Web Scraper")
    parser.add_argument("--url", default="https://example.com", help="URL to scrape")
    parser.add_argument("--instructions", default="Find Information", 
                        help="Scraping instructions")
    parser.add_argument("--depth", type=int, default=2, help="Maximum crawl depth")
    parser.add_argument("--pages", type=int, default=20, help="Maximum pages to crawl")
    parser.add_argument("--selenium", action="store_true", help="Use Selenium for JavaScript rendering")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                        default="INFO", help="Logging level")
    parser.add_argument("--log-file", default="rufus_scrape.log", help="Log file path")
    parser.add_argument("--output-dir", default="outputs", help="Directory for output files")
    
    args = parser.parse_args()
    
    # Configure logging based on arguments
    log_level = getattr(logging, args.log_level)
    
    # Retrieve API keys
    api_key = os.getenv('Rufus_API_KEY', 'dummy_api_key')
    nim_api_key = os.getenv('NVIDIA_NIM_API_KEY', 'dummy_nvidia_nim_api_key')
    
    print(f"Starting web scraping of {args.url}")
    print(f"Instructions: '{args.instructions}'")
    print(f"Maximum depth: {args.depth}, Maximum pages: {args.pages}")
    print(f"Using Selenium: {args.selenium}")
    print(f"Log level: {args.log_level}, Log file: {args.log_file}")
    print(f"Output directory: {args.output_dir}")
    print("-------------------------")
    
    # Initialize client with configuration
    client = RufusClient(
        api_key=api_key,
        nim_api_key=nim_api_key,
        log_level=log_level,
        log_file=args.log_file,
        use_selenium=args.selenium,
        max_depth=args.depth,
        max_pages=args.pages,
        output_dir=args.output_dir
    )
    
    # Perform the scrape
    result = client.scrape(args.url, args.instructions)
    
    # Print results
    print("\nSynthesis Result:")
    print(json.dumps(result, indent=2))
    
    print(f"\nComplete log available in: {args.log_file}")
    print(f"Output files stored in: {args.output_dir}")

if __name__ == "__main__":
    main()
