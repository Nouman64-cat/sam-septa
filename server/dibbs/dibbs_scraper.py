import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import logging
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DibbsScraper:
    def __init__(self, headless=False):
        self.headless = headless
        self.data = []
        self.output_file = "dibbs_bids.csv"
        # Today's date for filtering/selection
        self.target_date_str = datetime.now().strftime("%m-%d-%Y") 
        # For testing purposes matching the prompt's date if needed, but user said "recent todays date".
        # If the user context is strictly 2025-12-22, datetime.now() should return that if system time is mocked or correct.
        # The prompt metadata says: "The current local time is: 2025-12-22..."
        # So datetime.now() is safe.

        self.setup_driver()

    def setup_driver(self):
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        # Random User Agent
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        
        try:
            driver_path = ChromeDriverManager().install()
            # Win fix for driver path if needed
            if not driver_path.endswith(".exe"):
                 driver_dir = os.path.dirname(driver_path)
                 for root, dirs, files in os.walk(driver_dir):
                     if "chromedriver.exe" in files:
                         driver_path = os.path.join(root, "chromedriver.exe")
                         break
            service = Service(driver_path)
        except:
            service = Service()

        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.maximize_window()

    def run(self):
        try:
            # 1. Navigate to RFQ
            url = "https://www.dibbs.bsm.dla.mil/RFQ/"
            logger.info(f"Navigating to {url}")
            self.driver.get(url)

            # 1.1 Handle DoD Consent Banner (Popup)
            try:
                # Wait briefly for the OK button to appear
                # id="butAgree"
                wait = WebDriverWait(self.driver, 10)
                ok_button = wait.until(EC.element_to_be_clickable((By.ID, "butAgree")))
                if ok_button:
                    logger.info("Consent banner found. Clicking 'OK'.")
                    ok_button.click()
                    # Wait for redirect or page load after clicking OK
                    time.sleep(2) 
            except Exception as banner_e:
                # If not found, perhaps we are already past it or it didn't load. 
                # Proceeding anyway as it might not always appear.
                logger.info("Consent banner not found or already accepted. Proceeding.")
            
            # 2. Click "Issue Date"
            # id="ctl00_cph1_lnkRfqDatesIssue"
            wait = WebDriverWait(self.driver, 20)
            issue_date_link = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_cph1_lnkRfqDatesIssue")))
            logger.info("Clicking " "Issue Date" "")
            issue_date_link.click()
            
            # 3. Select Recent Date (Today)
            # We are now on RfqDates.aspx?category=issue
            # Should look for the link with text == self.target_date_str
            logger.info(f"Looking for date link: {self.target_date_str}")
            
            try:
                date_link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, self.target_date_str)))
                date_link.click()
            except:
                logger.error(f"Could not find link for date {self.target_date_str}. Trying to find the first recent date available.")
                # Fallback: click the first date in the table
                # Table id might be implicitly found by class or just first link in dates area
                # User said: <td headers="H0" class="BgGold"> is relevant, but that might be header.
                # Let's try finding any date link format MM-DD-YYYY
                links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'Value=')]")
                if links:
                    logger.info(f"Clicking fallback date: {links[0].text}")
                    links[0].click()
                else:
                    raise Exception("No date links found.")

            # 4. Scrape Pages (1 to 10)
            self.scrape_bids_loop(max_pages=10)

        except Exception as e:
            logger.error(f"Error during execution: {e}")
        finally:
            self.save_csv()
            self.driver.quit()
            return self.output_file

    def scrape_bids_loop(self, max_pages=44):
        wait = WebDriverWait(self.driver, 20)
        
        for page_num in range(1, max_pages + 1):
            logger.info(f"Scraping Page {page_num}...")
            
            # Wait for grid to load
            try:
                table = wait.until(EC.presence_of_element_located((By.ID, "ctl00_cph1_grdRfqSearch")))
            except:
                logger.warning("Bid table not found on this page.")
                break

            # Parse Rows
            # Usually rows are tr class="GridItem" or "GridAltItem" or just tr in tbody
            # Skipping header row (th)
            rows = table.find_elements(By.TAG_NAME, "tr")
            
            # Map headers to verify columns? 
            # The user listed columns: NSN/Part Number, Nomenclature, Solicitation, RFQ/Quote Status, Purchase Request, Issued, Return By
            # Let's assume standard order or reliable text in cells. 
            # Given the dynamic nature, I'll grab all text from cells and map by index if consistent.
            
            # Based on inspection or typical ASP.NET grids:
            # Row 0 is header.
            # Row 1+ are data.
            
            for row in rows[1:]: # Skip header
                cols = row.find_elements(By.TAG_NAME, "td")
                if not cols: continue
                
                # Check for "There are no records..." row
                if "no records" in row.text.lower():
                    logger.info("No records found.")
                    return

                # Column mapping assumption (User listed 7 columns, but table might have more)
                # Let's try to identify by contents or just grab first 7 visible.
                # Validating "RFQ/Quote Status" for cancel/removed.
                
                # Let's clean the text
                row_texts = [c.text.strip() for c in cols]
                
                if len(row_texts) < 7:
                    # Maybe not a data row
                    continue
                
                # Identify "RFQ/Quote Status" column. User said it's one of them.
                # "Open", "Canceled", "Removed".
                # Let's look for these keywords in the row to find the index dynamically or just check known index.
                # Usually: 
                # 0: Row Num? 
                # 1: NSN
                # 2: Nomenclature
                # 3: Tech Docs
                # 4: Solicitation
                # 5: Status (RFQ/Quote Status)
                # 6: Purchase Request
                # 7: Issued
                # 8: Return By
                
                # I will verify this by looking at correct indices based on standard layout
                # If "Status" is index 5 (0-based)
                
                # Let's dump all relevant data to dict
                # Indices might vary. Let's start with basic extraction.
                
                try:
                    # Guessing indices based on user provided list order:
                    # NSN, Nomenclature, Solicitation, Status, PR, Issued, Return By.
                    # But often there's "Tech Data" column too.
                    # Let's try to map by creating a robust check.
                    
                    # Finding 'Status'
                    status = ""
                    status_idx = -1
                    
                    # Typical value for status: "Open", "Canceled", "Awarded"
                    for i, txt in enumerate(row_texts):
                        if "Open" in txt or "Canceled" in txt or "Removed" in txt or "Quote" in txt:
                             status = txt
                             status_idx = i
                             # We might hit multiple matches, but usually Status is distinct.
                    
                    if "canceled" in status.lower() or "removed" in status.lower():
                        continue 

                    # Extract other fields relative to Status or just by fixed index if Status detection fails
                    # Let's blindly grab columns as per user order if we assume the user listed them in order appearance
                    # NSN (1), Nomenclature (2), Solicitation (4?), Status (5?), PR (6?), Issued (7?), Return (8?)
                    # Column 0 is usually line number.
                    
                    # Safer approach: Get all text, clean it, save it.
                    # AND specific columns for CSV.
                    
                    # Let's try:
                    # c[1] -> NSN
                    # c[2] -> Nomenclature
                    # c[4] -> Solicitation
                    # c[5] -> Status
                    # c[6] -> PR
                    # c[7] -> Issued
                    # c[8] -> Return By
                    
                    # I will assume this mapping.
                    if len(row_texts) >= 9:
                        item = {
                            "NSN/Part Number": row_texts[1],
                            "Nomenclature": row_texts[2],
                            "Solicitation": row_texts[4],
                            "RFQ/Quote Status": row_texts[5],
                            "Purchase Request": row_texts[6],
                            "Issued": row_texts[7],
                            "Return By": row_texts[8]
                        }
                        
                        # Apply filter again just in case
                        st = item["RFQ/Quote Status"].lower()
                        if "canceled" in st or "removed" in st:
                            continue
                            
                        self.data.append(item)
                except Exception as row_e:
                    logger.warning(f"Error parsing row: {row_e}")
            
            # Pagination
            if page_num < max_pages:
                # Click "Next" or specific page number
                # Usually <tr class="Paging"> ... <a>...
                try:
                    # Look for the pager row, which is usually the last row or in a footer
                    # Or look for text "page_num + 1" in a link
                    next_page_text = str(page_num + 1)
                    
                    # Be specific to avoid other links
                    # The pager links often invoke __doPostBack
                    # Find link with exact text '2', '3', etc.
                    
                    # Also there might be "..." for next chunk.
                    # If 'next_page_text' is not visible, check for "..."
                    
                    next_link = self.driver.find_elements(By.LINK_TEXT, next_page_text)
                    if next_link:
                        logger.info(f"Navigating to page {next_page_text}")
                        next_link[0].click()
                    else:
                        # Try "..." if we are at page 10 and want 11? 
                        # But prompt says "at least 10 pages". 
                        # If we can't find '2' when on '1', we break.
                        
                        # Wait, sometimes the next pages are in a 'Next' button if numbered links aren't all shown.
                        # But standard GridView shows 1 2 3 ... 10
                        logger.info(f"Could not find link for page {next_page_text}. Checking for '...'")
                        ellipses = self.driver.find_elements(By.LINK_TEXT, "...")
                        if ellipses:
                             ellipses[-1].click() # Click the last one (usually next set)
                        else:
                             logger.info("No next page link found. Stopping.")
                             break
                    
                    # Wait for reload
                    time.sleep(3) 
                    WebDriverWait(self.driver, 20).until(EC.staleness_of(table))
                    
                except Exception as nav_e:
                    logger.warning(f"Pagination error: {nav_e}")
                    break

    def save_csv(self):
        if not self.data:
            return
        df = pd.DataFrame(self.data)
        df.to_csv(self.output_file, index=False)
        logger.info(f"Saved {len(self.data)} bids to {self.output_file}")


if __name__ == "__main__":
    s = DibbsScraper(headless=False)
    s.run()
