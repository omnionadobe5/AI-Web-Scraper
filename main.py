#cat main.py
import streamlit as st
import pandas as pd
from scrape import (
    scrape_website,
    clean_body_content,
    split_dom_content
)
from parse import parse_with_ollama
import re

# Streamlit UI
st.title("Universal E-commerce Scraper")
url = st.text_input("Enter E-commerce Website URL")

def process_parsed_data(parsed_result):
    """Process and clean the parsed data for table display"""
    rows = []
    lines = parsed_result.split('\n')
    
    for line in lines:
        if '|' in line:
            parts = [part.strip() for part in line.split('|')]
            if len(parts) == 4:
                # Clean and standardize the data
                name = parts[0].strip()
                
                # Clean price
                price = parts[1].strip()
                if not price.startswith('$'):
                    price = f"${price}" if price != 'N/A' else price
                
                # Clean rating
                rating = parts[2].strip()
                if rating != 'N/A':
                    rating_match = re.search(r'\d+\.?\d*', rating)
                    if rating_match:
                        rating = f"{float(rating_match.group())} out of 5"
                
                # Clean reviews
                reviews = parts[3].strip()
                if reviews != 'N/A':
                    reviews_match = re.search(r'\d+', reviews)
                    if reviews_match:
                        reviews = reviews_match.group()
                
                rows.append({
                    'Product Name': name,
                    'Price': price,
                    'Rating': rating,
                    'Reviews': reviews
                })
    
    return rows

# Step 1: Scrape the Website
if st.button("Scrape Website"):
    if url:
        try:
            with st.spinner('Scraping website...'):
                st.info("Starting scraping process... This may take a few moments.")
                
                # Scrape the website
                dom_content = scrape_website(url)
                
                if dom_content:
                    # Clean and extract product information
                    cleaned_content = clean_body_content(dom_content)
                    
                    if cleaned_content:
                        st.session_state.dom_content = cleaned_content
                        st.success("Website scraped successfully!")
                        st.info(f"Found product information. Ready for parsing.")
                    else:
                        st.warning("No product information could be extracted. This might be due to:")
                        st.write("1. The website's structure is not recognized")
                        st.write("2. The content is loaded dynamically and requires different handling")
                        st.write("3. The website might be blocking automated access")
                else:
                    st.error("Failed to retrieve content from the website")
        except Exception as e:
            st.error(f"Error scraping website: {str(e)}")
            st.write("Please check if:")
            st.write("1. The URL is correct and accessible")
            st.write("2. The website allows automated access")
            st.write("3. Your internet connection is stable")

# Step 2: Parse Content
if "dom_content" in st.session_state:
    parse_description = st.text_area(
        "Describe what to extract (e.g., 'Extract all product names, prices, ratings, and reviews')"
    )

    if st.button("Parse Content"):
        if parse_description:
            with st.spinner('Parsing content...'):
                dom_chunks = split_dom_content(st.session_state.dom_content)
                parsed_result = parse_with_ollama(dom_chunks, parse_description)
                
                if parsed_result:
                    rows = process_parsed_data(parsed_result)
                    
                    if rows:
                        df = pd.DataFrame(rows)
                        
                        st.write("### Scraped Products")
                        st.dataframe(df)
                        
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label="Download as CSV",
                            data=csv,
                            file_name="scraped_products.csv",
                            mime="text/csv"
                        )
                    else:
                        st.error("Could not format the data into a table")
                else:
                    st.error("No valid data was parsed from the content")
