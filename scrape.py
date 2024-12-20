
from selenium.webdriver import Remote, ChromeOptions
from selenium.webdriver.chromium.remote_connection import ChromiumRemoteConnection
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import time

load_dotenv()

SBR_WEBDRIVER = os.getenv("SBR_WEBDRIVER")

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
        
        # Wait for page to load
        time.sleep(5)  # Initial wait
        
        # Scroll down to load dynamic content
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            
        print("Scraping page content...")
        html = driver.page_source
        return html

def clean_body_content(body_content):
    """Universal product information extractor for e-commerce sites"""
    soup = BeautifulSoup(body_content, "html.parser")
    
    # Remove unwanted elements
    for element in soup(['script', 'style', 'nav', 'footer', 'iframe']):
        element.decompose()
    
    products = []
    
    # Common product container patterns
    container_patterns = [
        {'tag': 'div', 'attrs': {'data-component-type': 's-search-result'}},  # Amazon
        {'tag': 'div', 'attrs': {'class': ['s-result-item']}},  # Amazon alternative
        {'tag': 'div', 'attrs': {'class': ['_1AtVbE', 'col-12-12']}},  # Flipkart
        {'tag': 'li', 'attrs': {'class': ['s-item']}},  # eBay
        {'tag': 'div', 'attrs': {'class': ['product-item']}},  # Generic
        {'tag': 'div', 'attrs': {'class': ['product-container']}},  # Generic
    ]
    
    # Try each pattern to find product containers
    product_containers = []
    for pattern in container_patterns:
        containers = soup.find_all(pattern['tag'], pattern['attrs'])
        if containers:
            product_containers.extend(containers)
    
    # If no containers found with specific patterns, try generic approach
    if not product_containers:
        product_containers = soup.find_all('div', class_=lambda x: x and any(term in str(x).lower() 
                           for term in ['product', 'item', 'result']))
    
    for container in product_containers:
        try:
            product = {}
            
            # Product Name
            name_elements = container.find_all(['h2', 'h3', 'h4', 'a'], 
                class_=lambda x: x and any(term in str(x).lower() for term in ['title', 'name', 'product']))
            for elem in name_elements:
                text = elem.get_text().strip()
                if text and len(text) > 5:  # Avoid empty or too short names
                    product['name'] = text
                    break
            
            # Price
            price_patterns = [
                {'class': lambda x: x and 'price' in str(x).lower()},
                {'class': ['a-price', 'price', '_30jeq3']},  # Common price classes
            ]
            
            for pattern in price_patterns:
                price_elem = container.find(['span', 'div'], pattern)
                if price_elem:
                    price_text = price_elem.get_text().strip()
                    # Clean price text
                    price_text = ''.join(c for c in price_text if c.isdigit() or c in ',.').strip()
                    if price_text:
                        product['price'] = f"${price_text}"
                        break
            
            # Rating
            rating_patterns = [
                {'class': lambda x: x and any(term in str(x).lower() for term in ['rating', 'stars'])},
                {'class': ['a-icon-alt', '_3LWZlK']},  # Common rating classes
            ]
            
            for pattern in rating_patterns:
                rating_elem = container.find(['span', 'div'], pattern)
                if rating_elem:
                    rating_text = rating_elem.get_text().strip()
                    if rating_text:
                        product['rating'] = rating_text
                        break
            
            # Reviews
            review_patterns = [
                {'class': lambda x: x and 'review' in str(x).lower()},
                {'class': ['a-size-base', '_2_R_DZ']},  # Common review classes
            ]
            
            for pattern in review_patterns:
                review_elem = container.find(['span', 'div'], pattern)
                if review_elem:
                    review_text = review_elem.get_text().strip()
                    if review_text:
                        product['reviews'] = review_text
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
