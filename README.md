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

# Install the package (editable mode recommended for development)
pip install -e .

# To install development dependencies (for testing, linting, etc.)
pip install -e .[dev]
```

## Usage

Basic usage example:

```python
# Import the client
from Rufus.client import RufusClient # Corrected import path

# Initialize a new client instance
# Ensure you have RUFUS_API_KEY and NVIDIA_NIM_API_KEY set as environment variables
# or pass them directly: RufusClient(api_key="YOUR...", nim_api_key="YOUR...")
client = RufusClient()

# Configure and run a scraping job
results = client.scrape(
    url="https://example.com",
    instructions="Extract the main title and the first paragraph."
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

---

**Note:** This project is under active development. Features and API may change as the project evolves.
