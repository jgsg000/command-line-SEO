# SEO Audit Tool

This is a command-line tool made to crawl a website, and analyze its pages for common SEO issues. Made by: Jorge Santana

## Features
- **Web Crawling Technology**:
  - Concurrent threading for faster crawling
  - Configurable crawling depth

- **SEO Detection:**
  - Title tags
  - Meta descriptions
  - Broken links
  - Image alt text
  - Heading tags

- **Adaptive Output:**
  - Multiple file format support
  - Detailed SEO issue reporting

## Requirements
- Python
- pip
- Virtual environment (venv)
- requirements.txt

## Installation

1. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Start
Run the SEO audit tool with a domain:
```bash
python main.py example.com
```
## Troubleshooting
- Ensure you have the latest version of Python
- Check all dependencies are installed
- Review `seo_audit.log` for detailed error info

**PERFORMANCE MAY DEPEND ON WEBSITE STRUCTURE, SIZE, ETC:**