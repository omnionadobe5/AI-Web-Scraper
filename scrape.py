from selenium.webdriver import Remote, ChromeOptions
from selenium.webdriver.chromium.remote_connection import ChromiumRemoteConnection
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os

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
        # Add a small delay to allow dynamic content to load
        driver.implicitly_wait(5)
        print("Scraping page content...")
        html = driver.page_source
        return html

def extract_body_content(html_content):
    """Extract content from the body tag of HTML"""
    soup = BeautifulSoup(html_content, "html.parser")
    body_content = soup.body
    if body_content:
        return str(body_content)
    return ""

def clean_body_content(body_content):
    """Clean the HTML content by removing scripts, styles, and extra whitespace"""
    soup = BeautifulSoup(body_content, "html.parser")
    
    # Remove script and style elements
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()
    
    # Specifically look for price elements in Amazon's structure
    price_elements = soup.find_all(class_=lambda x: x and ('price' in x.lower() or 'a-price' in x.lower()))
    
    # Get text and clean it
    cleaned_content = ""
    for element in price_elements:
        cleaned_content += element.get_text() + "\n"
    
    if not cleaned_content:
        cleaned_content = soup.get_text(separator="\n")
    
    cleaned_content = "\n".join(
        line.strip() for line in cleaned_content.splitlines() if line.strip()
    )
    
    return cleaned_content

def split_dom_content(dom_content, max_length=6000):
    """Split content into chunks of specified maximum length"""
    return [
        dom_content[i : i + max_length] 
        for i in range(0, len(dom_content), max_length)
    ]
