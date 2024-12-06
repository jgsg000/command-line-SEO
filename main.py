import argparse
import re
import os
import sys
import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging
from urllib.parse import urljoin, urlparse, urlunparse
import concurrent.futures
import time
from tqdm import tqdm
import threading

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('seo_audit.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class SEOCrawler:
    def __init__(self, domain, max_depth=3, max_pages=50):
        if not re.match(r'^https?://', domain):
            domain = f'http://{domain}'
        
        self.domain = domain
        self.base_domain = urlparse(domain).netloc
        self.max_depth = max_depth
        self.max_pages = max_pages
        
        self.visited_urls = set()
        self.to_visit_urls = set([domain])
        self.seo_results = []
        self.crawl_complete = False
        self.crawl_error = None

    def _is_valid_url(self, url):
        """Check if URL is valid and within the same domain."""
        try:
            parsed_url = urlparse(url)
            return (
                parsed_url.netloc == self.base_domain and 
                parsed_url.scheme in ['http', 'https'] and
                not any(ext in url for ext in ['.pdf', '.jpg', '.png', '.gif', '.css', '.js'])
            )
        except Exception:
            return False

    def _get_page_seo_issues(self, url, soup):
        """Analyze SEO issues for a single page."""
        seo_issues = {
            'URL': url,
            'Title Issues': [],
            'Meta Description Issues': [],
            'Heading Structure Issues': [],
            'Link Issues': [],
            'Image SEO Issues': []
        }

        title_tag = soup.find('title')
        if not title_tag or not title_tag.text.strip():
            seo_issues['Title Issues'].append('Missing Title Tag')
        elif title_tag and (len(title_tag.text) < 10 or len(title_tag.text) > 60):
            seo_issues['Title Issues'].append(f'Title Tag Length Issue (Current: {len(title_tag.text)} chars)')

        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if not meta_desc or not meta_desc.get('content', '').strip():
            seo_issues['Meta Description Issues'].append('Missing Meta Description')
        elif meta_desc and (len(meta_desc.get('content', '')) < 50 or len(meta_desc.get('content', '')) > 160):
            seo_issues['Meta Description Issues'].append(f'Meta Description Length Issue (Current: {len(meta_desc.get("content", ""))} chars)')

        headings = {f'h{i}': soup.find_all(f'h{i}') for i in range(1, 7)}
        if not headings['h1']:
            seo_issues['Heading Structure Issues'].append('No H1 Tag Found')
        elif len(headings['h1']) > 1:
            seo_issues['Heading Structure Issues'].append('Multiple H1 Tags')

        for i in range(1, 6):
            if headings[f'h{i}'] and not headings[f'h{i+1}']:
                seo_issues['Heading Structure Issues'].append(f'Potential Heading Hierarchy Issue (Missing H{i+1})')

        links = soup.find_all('a', href=True)
        external_links = [link['href'] for link in links if urlparse(link['href']).netloc != self.base_domain]
        if len(external_links) > 10:
            seo_issues['Link Issues'].append(f'High Number of External Links ({len(external_links)})')

        images = soup.find_all('img')
        images_without_alt = [img.get('src', 'Unknown') for img in images if not img.get('alt')]
        if images_without_alt:
            seo_issues['Image SEO Issues'].append(f'{len(images_without_alt)} Images Missing Alt Text')

        seo_issues = {k: v for k, v in seo_issues.items() if v}
        return seo_issues

    def crawl(self):
        """Comprehensive website crawling method."""
        try:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'SEOAuditTool/1.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            })

            while self.to_visit_urls and len(self.visited_urls) < self.max_pages:
                current_url = self.to_visit_urls.pop()
                
                if current_url in self.visited_urls:
                    continue

                try:
                    response = session.get(current_url, timeout=10)
                    
                    if 'text/html' not in response.headers.get('Content-Type', '').lower():
                        continue

                    soup = BeautifulSoup(response.text, 'html.parser')
                    page_issues = self._get_page_seo_issues(current_url, soup)
                    if page_issues:
                        self.seo_results.append(page_issues)

                    self.visited_urls.add(current_url)
                    links = soup.find_all('a', href=True)
                    for link in links:
                        full_url = urljoin(current_url, link['href'])
                        if (self._is_valid_url(full_url) and 
                            full_url not in self.visited_urls and 
                            full_url not in self.to_visit_urls):
                            self.to_visit_urls.add(full_url)

                except requests.RequestException as e:
                    logging.warning(f"Error crawling {current_url}: {e}")
                except Exception as e:
                    logging.error(f"Unexpected error crawling {current_url}: {e}")

            self.crawl_complete = True
            return self.seo_results
        except Exception as e:
            self.crawl_error = e
            self.crawl_complete = True
            return []

def display_seo_results(results):
    """Display SEO analysis results."""
    if not results:
        print("No SEO issues found or unable to crawl the website.")
        return None
    
    print("\n--- SEO AUDIT RESULTS ---")
    for result in results:
        print(f"\nURL: {result['URL']}")
        for issue_type, issues in result.items():
            if issue_type != 'URL' and issues:
                print(f"{issue_type}:")
                for issue in issues:
                    print(f"  - {issue}")
    
    return results

def save_output(seo_results):
    """Save SEO audit results to a file."""
    save_choice = input("\nDo you want to save the results? (yes/no) [y/n]: ").lower()
    if save_choice not in ['y', 'yes']:
        print("Output not saved.")
        return

    print("\nSelect file type (1-4):")
    file_types = {
        '1': ('txt', 'Text File'),
        '2': ('csv', 'CSV File'),
        '3': ('xlsx', 'Excel File'),
        '4': ('md', 'Markdown File')
    }
    
    for key, (ext, name) in file_types.items():
        print(f"{key}- {name} (.{ext})")
    
    file_type_choice = input("Enter the number of the file type (default is 1): ").strip() or '1'
    
    if file_type_choice not in file_types:
        print("Invalid choice. Defaulting to .txt")
        file_type_choice = '1'
    
    file_ext = file_types[file_type_choice][0]
    
    while True:
        save_path = input("Enter the directory path to save the file (default is current directory): ").strip() or '.'
        if not os.path.isdir(save_path):
            print("Invalid path. Please enter a valid directory.")
            continue
        
        filename = f"audit-results.{file_ext}"
        full_path = os.path.join(save_path, filename)
        
        try:
            if file_ext == 'txt':
                with open(full_path, 'w') as f:
                    for result in seo_results:
                        f.write(f"URL: {result['URL']}\n")
                        for issue_type, issues in result.items():
                            if issue_type != 'URL' and issues:
                                f.write(f"{issue_type}:\n")
                                for issue in issues:
                                    f.write(f"  - {issue}\n")
                        f.write("\n")
            
            elif file_ext == 'csv':
                df = pd.DataFrame(seo_results)
                df.to_csv(full_path, index=False)
            
            elif file_ext == 'xlsx':
                df = pd.DataFrame(seo_results)
                df.to_excel(full_path, index=False)
            
            elif file_ext == 'md':
                with open(full_path, 'w') as f:
                    f.write("# SEO Audit Results\n\n")
                    for result in seo_results:
                        f.write(f"## {result['URL']}\n\n")
                        for issue_type, issues in result.items():
                            if issue_type != 'URL' and issues:
                                f.write(f"### {issue_type}\n")
                                for issue in issues:
                                    f.write(f"- {issue}\n")
                        f.write("\n")
            
            print(f"\n{filename} saved in {save_path}")
            break
        
        except Exception as e:
            print(f"Error saving file: {e}")
            retry = input("Do you want to try again? (yes/no) [y/n]: ").lower()
            if retry not in ['y', 'yes']:
                break

def crawl_with_progress(crawler):
    """Crawl website with a progress bar."""
    with tqdm(total=crawler.max_pages, desc="Crawling", unit="page", 
              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} pages") as pbar:
        def crawl_thread():
            crawler.crawl()
            pbar.close()

        thread = threading.Thread(target=crawl_thread)
        thread.start()

        while not crawler.crawl_complete:
            pbar.n = len(crawler.visited_urls)
            pbar.refresh()
            time.sleep(0.5)

        thread.join()

        if crawler.crawl_error:
            print(f"\nCrawling error: {crawler.crawl_error}")
            return None

    return crawler.seo_results

def main():
    parser = argparse.ArgumentParser(
        description='SEO Website Crawler - Comprehensive SEO Analysis Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s example.com                   # Basic crawl
  %(prog)s example.com -d 5 -p 100       # Crawl with 5 depth and 100 max pages
  %(prog)s example.com --depth 3         # Specify crawl depth
  %(prog)s example.com -m 75             # Limit max pages to crawl
'''
    )
    
    parser.add_argument('domain', 
                        help='Domain to crawl (e.g., example.com)')
    parser.add_argument('-d', '--depth', 
                        type=int, 
                        default=3, 
                        help='Maximum crawl depth (default: 3, min: 1)')
    parser.add_argument('-p', '--max-pages', 
                        type=int, 
                        default=50, 
                        help='Maximum pages to crawl (default: 50, min: 10)')
    parser.add_argument('-v', '--verbose', 
                        action='store_true', 
                        help='Enable verbose logging')
    
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.depth < 1:
        parser.error("Depth must be at least 1")
    if args.max_pages < 10:
        parser.error("Minimum pages must be 10")

    crawler = SEOCrawler(args.domain, max_depth=args.depth, max_pages=args.max_pages)
    
    # Crawl with progress bar
    results = crawl_with_progress(crawler)
    
    # Display and save results
    if results:
        display_seo_results(results)
        save_output(results)
    else:
        print("No results to display.")

if __name__ == "__main__":
    main()