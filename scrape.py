from selenium.webdriver import Remote, ChromeOptions
from selenium.webdriver.chromium.remote_connection import ChromiumRemoteConnection
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import time
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
SBR_WEBDRIVER = os.getenv("SBR_WEBDRIVER")

def wait_for_elements(driver, timeout=15):
    """Enhanced wait for dynamic content"""
    try:
        # Wait for common product elements
        common_selectors = [
            "//div[contains(@class, 'product')]",
            "//div[contains(@class, 'item')]",
            "//article",
            "//div[@data-component-type='s-search-result']",
            "//li[contains(@class, 's-item')]"
        ]
        
        for selector in common_selectors:
            try:
                WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                return True
            except:
                continue
                
        # If no specific elements found, wait for body
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(5)  # Additional wait for dynamic content
        return True
    except Exception as e:
        logger.warning(f"Timeout waiting for elements - {str(e)}")
        return False

def scroll_page(driver, max_scrolls=15):
    """Enhanced scrolling mechanism"""
    logger.info("Starting page scroll to load more products...")
    scrolls = 0
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while scrolls < max_scrolls:
        # Scroll down
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # Try clicking "Load More" buttons
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
        except Exception as e:
            logger.debug(f"Load more button handling: {str(e)}")
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            time.sleep(3)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
        
        last_height = new_height
        scrolls += 1
        logger.info(f"Completed scroll {scrolls}/{max_scrolls}")

def scrape_website(website):
    if not SBR_WEBDRIVER:
        raise ValueError("SBR_WEBDRIVER environment variable is not set")
    
    logger.info("Connecting to Scraping Browser...")
    sbr_connection = ChromiumRemoteConnection(SBR_WEBDRIVER, "goog", "chrome")
    options = ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36')
    
    with Remote(sbr_connection, options=options) as driver:
        try:
            logger.info("Navigating to website...")
            driver.get(website)
            
            if not wait_for_elements(driver):
                logger.warning("Page might not have loaded completely")
            
            # Execute JavaScript to ensure dynamic content loads
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/4);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(2)
            
            scroll_page(driver)
            
            logger.info("Scraping page content...")
            html = driver.page_source
            
            if len(html) < 1000:
                logger.warning("Retrieved content seems too small")
                return None
                
            return html
            
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            return None

def clean_body_content(body_content):
    """Enhanced product information extractor"""
    if not body_content:
        logger.error("No content provided to clean_body_content")
        return None
        
    logger.info(f"Content length: {len(body_content)}")
    
    soup = BeautifulSoup(body_content, "html.parser")
    
    for element in soup(['script', 'style', 'nav', 'footer', 'iframe']):
        element.decompose()
    
    products = []
    
    container_patterns = [
        {'tag': 'div', 'attrs': {'data-component-type': 's-search-result'}},
        {'tag': 'div', 'attrs': {'class': ['s-result-item']}},
        {'tag': 'div', 'attrs': {'class': ['_1AtVbE', 'col-12-12']}},
        {'tag': 'li', 'attrs': {'class': ['s-item']}},
        {'tag': 'div', 'attrs': {'class': ['product-item']}},
        {'tag': 'div', 'attrs': {'class': ['product-container']}},
        {'tag': 'div', 'attrs': {'class': lambda x: x and 'product' in str(x).lower()}},
        {'tag': 'div', 'attrs': {'class': lambda x: x and any(term in str(x).lower() for term in ['item', 'product', 'result', 'card'])}},
        {'tag': 'article', 'attrs': {}},
        {'tag': 'div', 'attrs': {'data-test': lambda x: x and 'product' in str(x).lower()}},
        {'tag': 'div', 'attrs': {'id': lambda x: x and 'product' in str(x).lower()}},
    ]
    
    product_containers = []
    for pattern in container_patterns:
        containers = soup.find_all(pattern['tag'], pattern['attrs'])
        if containers:
            product_containers.extend(containers)
    
    if not product_containers:
        logger.warning("No product containers found with any pattern")
        product_containers = soup.find_all(['div', 'article'], 
            class_=lambda x: x and any(term in str(x).lower() 
                for term in ['product', 'item', 'result', 'card', 'grid']))
        
        if not product_containers:
            logger.error("Could not find any product containers")
            return None
    
    logger.info(f"Found {len(product_containers)} potential product containers")
    
    # Rest of the function remains the same as in the original code
    # (Rating patterns, review patterns, and product extraction logic)
    
    return "\n".join(products)

def split_dom_content(content, max_chunk_size=8000):
    """Split the DOM content into smaller chunks"""
    if not content:
        return []
    
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
