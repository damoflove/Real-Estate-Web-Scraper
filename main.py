import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

def fetch_page_data(driver, fields):
    data = []
    
    try:
        # Wait for listings to load on the page
        listings = WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[id^="zpid_"]'))
        )
        
        for listing in listings:
            record = {}
            # Attempt to fetch each field, setting 'N/A' if not found
            try:
                if 'price' in fields:
                    record['price'] = listing.find_element(By.CSS_SELECTOR, 'span[data-test="property-card-price"]').text
            except Exception:
                record['price'] = 'N/A'
                
            try:
                if 'beds' in fields:
                    record['beds'] = listing.find_element(By.CSS_SELECTOR, 'li[data-test="bed"]').text
            except Exception:
                record['beds'] = 'N/A'
                
            try:
                if 'baths' in fields:
                    record['baths'] = listing.find_element(By.CSS_SELECTOR, 'li[data-test="bath"]').text
            except Exception:
                record['baths'] = 'N/A'
                
            try:
                if 'link' in fields:
                    record['link'] = listing.find_element(By.TAG_NAME, 'a').get_attribute('href')
            except Exception:
                record['link'] = 'N/A'
                
            try:
                if 'address' in fields:
                    record['address'] = listing.find_element(By.CSS_SELECTOR, 'address').text
            except Exception:
                record['address'] = 'N/A'
                
            try:
                if 'hoa_fee' in fields:
                    record['hoa_fee'] = listing.find_element(By.CSS_SELECTOR, 'span[data-test="property-card-hoa"]').text
            except Exception:
                record['hoa_fee'] = 'N/A'
                
            try:
                if 'home_type' in fields:
                    record['home_type'] = listing.find_element(By.CSS_SELECTOR, 'span[data-test="property-card-home-type"]').text
            except Exception:
                record['home_type'] = 'N/A'
                
            try:
                if 'lot_size' in fields:
                    record['lot_size'] = listing.find_element(By.CSS_SELECTOR, 'span[data-test="property-card-lot-size"]').text
            except Exception:
                record['lot_size'] = 'N/A'
            
            data.append(record)

    except Exception as e:
        st.write("Error loading listings:", e)
    
    return data

def scrape_data(url, fields):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36")
    
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
    driver.get(url)

    all_data = []
    page_num = 1

    while True:
        st.write(f"Scraping page {page_num}...")
        page_data = fetch_page_data(driver, fields)
        if not page_data:
            break

        all_data.extend(page_data)

        try:
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[title="Next page"]'))
            )
            next_button.click()
            time.sleep(3)
            page_num += 1
        except Exception:
            st.write("No more pages found or failed to load the next page.")
            break

    driver.quit()
    return all_data

# Streamlit UI
st.title("Real Estate Web Scraper")
st.write("Enter the URL and fields to scrape from Zillow-like real estate sites.")

url = st.text_input("Enter the URL of the main page:")
fields = st.multiselect(
    "Select fields to extract",
    ["price", "beds", "baths", "link", "address", "hoa_fee", "home_type", "lot_size"],
    default=["price", "beds", "baths", "link", "address"]
)

if st.button("Scrape and Download Data"):
    if url:
        with st.spinner("Scraping data... Please wait"):
            scraped_data = scrape_data(url, fields)
            if scraped_data:
                df = pd.DataFrame(scraped_data)
                st.write(df)
                
                # Download button for CSV
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download data as CSV",
                    data=csv,
                    file_name="real_estate_data.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No data found. Please check the URL and try again.")
    else:
        st.error("Please enter a valid URL.")
