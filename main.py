import streamlit as st
import pandas as pd
from scrape import (
    scrape_website,
    extract_body_content,
    clean_body_content,
    split_dom_content,
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
                dom_content = scrape_website(url)
                body_content = extract_body_content(dom_content)
                cleaned_content = clean_body_content(body_content)
                
                if cleaned_content:
                    st.session_state.dom_content = cleaned_content
                    st.success("Website scraped successfully!")
                else:
                    st.warning("No product data found on this page")
        except Exception as e:
            st.error(f"Error scraping website: {str(e)}")

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
