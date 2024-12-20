#cat scrape.py
from selenium.webdriver import Remote, ChromeOptions
from selenium.webdriver.chromium.remote_connection import ChromiumRemoteConnection
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import time
import re

load_dotenv()

SBR_WEBDRIVER = os.getenv("SBR_WEBDRIVER")

def wait_for_elements(driver, timeout=10):
    """Wait for common product elements to load"""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        # Wait for dynamic content to load
        time.sleep(3)
    except Exception as e:
        print(f"Warning: Timeout waiting for elements - {str(e)}")

def scroll_page(driver, max_scrolls=10):
    """Enhanced scrolling mechanism to load more products"""
    print("Starting page scroll to load more products...")
    scrolls = 0
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while scrolls < max_scrolls:
        # Scroll down
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Wait for content to load
        
        # Try clicking "Load More" or similar buttons
        try:
            load_more_patterns = [
                "//button[contains(text(), 'Load More')]",
                "//button[contains(text(), 'Show More')]",
                "//a[contains(text(), 'Load More')]",
                "//span[contains(text(), 'Load More')]"
            ]
            for pattern in load_more_patterns:
                buttons = driver.find_elements(By.XPATH, pattern)
                for button in buttons:
                    if button.is_displayed():
                        button.click()
                        time.sleep(2)
        except Exception:
            pass
        
        # Calculate new scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            # Try one more scroll after a longer wait
            time.sleep(3)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
        
        last_height = new_height
        scrolls += 1
        print(f"Completed scroll {scrolls}/{max_scrolls}")

def scrape_website(website):
    if not SBR_WEBDRIVER:
        raise ValueError("SBR_WEBDRIVER environment variable is not set")
        
    print("Connecting to Scraping Browser...")
    sbr_connection = ChromiumRemoteConnection(SBR_WEBDRIVER, "goog", "chrome")
    options = ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36')
    
    with Remote(sbr_connection, options=options) as driver:
        print("Navigating to website...")
        driver.get(website)
        
        # Wait for initial content to load
        time.sleep(5)
        
        # Scroll to load more products
        scroll_page(driver)
        
        print("Scraping page content...")
        html = driver.page_source
        return html


def clean_body_content(body_content):
    """Enhanced product information extractor with better rating and review patterns"""
    soup = BeautifulSoup(body_content, "html.parser")
    
    # Remove unwanted elements
    for element in soup(['script', 'style', 'nav', 'footer', 'iframe']):
        element.decompose()
    
    products = []
    
    # Enhanced product container patterns
    container_patterns = [
        {'tag': 'div', 'attrs': {'data-component-type': 's-search-result'}},
        {'tag': 'div', 'attrs': {'class': ['s-result-item']}},
        {'tag': 'div', 'attrs': {'class': ['_1AtVbE', 'col-12-12']}},
        {'tag': 'li', 'attrs': {'class': ['s-item']}},
        {'tag': 'div', 'attrs': {'class': ['product-item']}},
        {'tag': 'div', 'attrs': {'class': ['product-container']}},
        {'tag': 'div', 'attrs': {'class': lambda x: x and 'product' in str(x).lower()}},
    ]
    
    # Try each pattern to find product containers
    product_containers = []
    for pattern in container_patterns:
        containers = soup.find_all(pattern['tag'], pattern['attrs'])
        if containers:
            product_containers.extend(containers)
    
    # Enhanced rating patterns
    rating_patterns = [
        {'class': lambda x: x and any(term in str(x).lower() for term in ['rating', 'stars', 'rate'])},
        {'class': ['a-icon-alt', '_3LWZlK', 'rating-stars']},
        {'aria-label': lambda x: x and 'rating' in str(x).lower()},
        {'data-rating': True},
    ]
    
    # Enhanced review patterns
    review_patterns = [
        {'class': lambda x: x and any(term in str(x).lower() for term in ['review', 'rating-count', 'reviews'])},
        {'class': ['a-size-base', '_2_R_DZ', 'review-count']},
        {'href': lambda x: x and 'review' in str(x).lower()},
    ]
    
    for container in product_containers:
        try:
            product = {}
            
            # Product Name (existing code)
            name_elements = container.find_all(['h2', 'h3', 'h4', 'a'], 
                class_=lambda x: x and any(term in str(x).lower() for term in ['title', 'name', 'product']))
            for elem in name_elements:
                text = elem.get_text().strip()
                if text and len(text) > 5:
                    product['name'] = text
                    break
            
            # Price (existing code)
            price_patterns = [
                {'class': lambda x: x and 'price' in str(x).lower()},
                {'class': ['a-price', 'price', '_30jeq3']},
            ]
            
            # Enhanced rating extraction
            for pattern in rating_patterns:
                rating_elem = container.find(['span', 'div', 'i'], pattern)
                if rating_elem:
                    rating_text = rating_elem.get_text().strip()
                    # Try to extract numeric rating
                    import re
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    if rating_match:
                        rating = float(rating_match.group(1))
                        if rating <= 5:  # Validate rating is out of 5
                            product['rating'] = f"{rating} out of 5"
                            break
            
            # Enhanced review extraction
            for pattern in review_patterns:
                review_elem = container.find(['span', 'div', 'a'], pattern)
                if review_elem:
                    review_text = review_elem.get_text().strip()
                    # Extract numeric review count
                    review_match = re.search(r'(\d+(?:,\d{3})*)', review_text)
                    if review_match:
                        reviews = review_match.group(1).replace(',', '')
                        product['reviews'] = reviews
                        break
            
            # Only add products with at least name and price
            if product.get('name') and product.get('price'):
                products.append(
                    f"{product.get('name', 'N/A')} | "
                    f"{product.get('price', 'N/A')} | "
                    f"{product.get('rating', 'N/A')} | "
                    f"{product.get('reviews', 'N/A')}"
                )
                
        except Exception as e:
            print(f"Error processing product: {e}")
            continue
    
    return "\n".join(products)

def split_dom_content(content, max_chunk_size=8000):
    """Split the DOM content into smaller chunks"""
    if not content:
        return []
    
    # Split content by newlines to maintain product information integrity
    lines = content.split('\n')
    chunks = []
    current_chunk = []
    current_size = 0
    
    for line in lines:
        line_size = len(line)
        if current_size + line_size > max_chunk_size and current_chunk:
            chunks.append('\n'.join(current_chunk))
            current_chunk = []
            current_size = 0
        current_chunk.append(line)
        current_size += line_size
    
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    
    return chunks
