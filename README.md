# Rufus

A Python-based scraping utility designed for extracting and processing web content with flexibility and ease.

## Overview

Rufus is a versatile web scraping tool that helps developers extract, process, and analyze content from various websites. Built with Python, Rufus aims to provide a powerful yet easy-to-use interface for all your data extraction needs.

## Features

- Fast and efficient web scraping capabilities
- Flexible parsing options for different HTML structures
- Output formatting in multiple formats (JSON, CSV, etc.)
- Customizable scraping workflows
- Rate limiting and politeness controls to avoid server overloading
- Comprehensive logging system

## Installation

```bash
# Clone the repository
git clone https://github.com/Thin-Equation/Rufus.git

# Navigate to the project directory
cd Rufus

# Install required dependencies
pip install -r requirements.txt
```

## Usage

Basic usage example:

```python
# Import the scraper module
from rufus.client import RufusClient

# Initialize a new scraper instance
scraper = RufusClient(api_key="YOUR RUFUS API KEY", nim_api_key="YOUR NVIDIA NIM API KEY")

# Configure and run a scraping job
results = scraper.scrape(
    url="https://example.com",
    instructions="your instructions"
)

# Process the results
print(results)
```

For more detailed examples, see `example_api_flow.py` in the repository.

## Project Structure

- `Rufus/` - Core scraping engine
- `fixtures/` - Test fixtures and sample HTML files
- `tests/` - Test suite
- `outputs/` - Default directory for scraping outputs
- `example_api_flow.py` - Example implementation

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Note:** This project is under active development. Features and API may change as the project evolves.
