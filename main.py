import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import time
import random
from fake_useragent import UserAgent
import pyautogui  # To simulate mouse movements and clicks
import pickle

# Helper function for gradual scrolling
def scroll_to_bottom(driver, pause_time=5, scrolls=3):
    """Scrolls down the page multiple times to load dynamic content."""
    try:
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(scrolls):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(pause_time, pause_time + 2))  # Add randomness to delay
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
    except Exception as e:
        st.error(f"Error during scrolling: {e}")
        raise

# Simulate human-like mouse movements and clicks to avoid detection
def simulate_mouse_movements(driver):
    """Simulate human-like mouse movements and clicks."""
    x = random.randint(500, 1500)
    y = random.randint(200, 1000)
    pyautogui.moveTo(x, y, duration=random.uniform(0.5, 1.5))  # Move mouse to a random position
    pyautogui.click()  # Click to simulate user interaction

# Fetch all main page data (including multiple pages)
def fetch_all_main_pages(driver):
    """Fetch all property listings across multiple pages."""
    all_listings = []
    page_number = 1  # Track the current page number for debugging
    
    try:
        while True:
            st.write(f"Scraping page {page_number}...")  # Log page number
            scroll_to_bottom(driver, pause_time=5, scrolls=5)  # Scroll multiple times to load more content
            
            # Wait for listings to load with a longer timeout
            try:
                st.write("Waiting for listings to load...")
                listings = WebDriverWait(driver, 120).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[id^="zpid_"]'))
                )
                st.write(f"Found {len(listings)} listings on page {page_number}.")
            except TimeoutException as e:
                st.error(f"Timeout waiting for listings on page {page_number}: {str(e)}")
                st.write("Checking the page source for debug: ")
                st.text(driver.page_source)  # Log the page source for debugging
                break  # Exit the loop if listings fail to load

            # Extract data from each listing
            for listing in listings:
                try:
                    price = listing.find_element(By.CSS_SELECTOR, 'span[data-test="property-card-price"]').text
                except NoSuchElementException:
                    price = "N/A"

                try:
                    address = listing.find_element(By.CSS_SELECTOR, 'address').text
                except NoSuchElementException:
                    address = "N/A"

                try:
                    link = listing.find_element(By.TAG_NAME, 'a').get_attribute('href')
                except NoSuchElementException:
                    link = "N/A"

                try:
                    details_list = listing.find_elements(By.CSS_SELECTOR, 'ul li')
                    beds = details_list[0].text if len(details_list) > 0 else "N/A"
                    baths = details_list[1].text if len(details_list) > 1 else "N/A"
                except Exception:
                    beds = "N/A"
                    baths = "N/A"

                all_listings.append({
                    "price": price,
                    "address": address,
                    "link": link,
                    "beds": beds,
                    "baths": baths,
                })

            # Check for next page button
            try:
                next_button = driver.find_element(By.XPATH, '//a[contains(@aria-label, "Next page")]')
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(random.uniform(3, 5))  # Random delay to simulate human browsing
                page_number += 1  # Increment page counter
            except NoSuchElementException:
                st.write("No more pages found.")
                break  # Exit the loop if no next page button is found
    except Exception as e:
        st.error(f"Unexpected error while fetching listings: {str(e)}")
        raise  # Re-raise the exception to let the caller handle it

    return all_listings

# Fetch individual listing details
def fetch_listing_details(driver, link, retry_attempts=2):
    details = {
        "hoa_fee": "N/A",
        "home_type": "N/A",
        "lot_size": "N/A",
    }
    attempts = 0

    while attempts < retry_attempts:
        try:
            st.write(f"Visiting {link}... (Attempt {attempts + 1}/{retry_attempts})")
            time.sleep(random.uniform(5, 10))  # Random delay

            driver.get(link)

            # Simulate mouse movements and clicks to mimic human-like behavior
            simulate_mouse_movements(driver)

            # Detect CAPTCHA
            if "captcha" in driver.current_url.lower():
                st.warning(f"CAPTCHA detected at {link}. Skipping.")
                return details

            scroll_to_bottom(driver, pause_time=5)

            # Extract details
            try:
                details["hoa_fee"] = driver.find_element(By.XPATH, '//span[contains(text(),"HOA fee")]/following-sibling::span').text
            except NoSuchElementException:
                pass

            try:
                details["home_type"] = driver.find_element(By.XPATH, '//span[contains(text(),"Property type")]/following-sibling::span').text
            except NoSuchElementException:
                pass

            try:
                details["lot_size"] = driver.find_element(By.XPATH, '//span[contains(text(),"Lot size")]/following-sibling::span').text
            except NoSuchElementException:
                pass

            return details

        except TimeoutException:
            st.error(f"Timeout while loading {link}")
            attempts += 1
        except WebDriverException as e:
            st.error(f"WebDriverException encountered: {e}. Retrying...")
            driver.quit()
            driver = initialize_driver()  # Reinitialize the driver if an error occurs

    st.warning(f"Failed to fetch details for {link} after {retry_attempts} attempts.")
    return details

# Initialize WebDriver with random user-agent, headless mode, human-like behavior, and session management (cookies)
def initialize_driver():
    chrome_options = Options()
    ua = UserAgent()
    random_user_agent = ua.random
    chrome_options.add_argument(f"user-agent={random_user_agent}")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # Start in headless mode (can be toggled for testing)
    chrome_options.add_argument("--headless")

    # Initialize WebDriver
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
    
    # Load cookies if available
    try:
        with open("cookies.pkl", "rb") as file:
            cookies = pickle.load(file)
            driver.get("https://www.zillow.com/")
            for cookie in cookies:
                driver.add_cookie(cookie)
    except FileNotFoundError:
        pass

    return driver

# Main scraping function
def scrape_data(main_url):
    driver = initialize_driver()
    all_data = []

    try:
        driver.get(main_url)
        st.write("Fetching data from the main page...")
        main_page_data = fetch_all_main_pages(driver)
        if not main_page_data:
            st.warning("No listings found on the main page.")
            return []

        st.write(f"Found {len(main_page_data)} listings on the main page.")
        for item in main_page_data:  # Process all listings
            link = item.get("link", "N/A")
            if link and link != "N/A":
                details = fetch_listing_details(driver, link)
                item.update(details)
            all_data.append(item)
    except WebDriverException as e:
        st.error(f"WebDriver encountered an error: {e}")
    finally:
        # Save cookies for session persistence
        with open("cookies.pkl", "wb") as file:
            pickle.dump(driver.get_cookies(), file)
        driver.quit()

    return all_data

# Streamlit UI
st.title("Real Estate Web Scraper")
url = st.text_input("Enter the URL of the main page:")
if st.button("Start Scraping"):
    if url:
        with st.spinner("Scraping data... Please wait"):
            scraped_data = scrape_data(url)
            if scraped_data:
                df = pd.DataFrame(scraped_data)
                st.write(df)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="real_estate_data.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No data scraped. Please check the URL or try again.")
    else:
        st.error("Please provide a valid URL.")
