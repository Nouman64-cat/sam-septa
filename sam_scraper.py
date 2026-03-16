import os
import time
import random
import pandas as pd
import re
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager
from config import SCRAPER_CONFIG
# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from urllib.parse import quote

class SAMGovScraper:
    def __init__(self, headless=False, search_query="", date_filter=None):
        """Initialize the scraper with Chrome driver"""
        self.headless = headless
        self.search_query = search_query
        self.date_filter = date_filter
        self.filter_date_obj = None
        
        if self.date_filter:
            try:
                self.filter_date_obj = datetime.strptime(self.date_filter, "%Y-%m-%d")
                logger.info(f"Date filter active: >= {self.filter_date_obj.strftime('%Y-%m-%d')}")
            except Exception as e:
                logger.warning(f"Invalid date format provided: {self.date_filter}. Ignoring filter. Error: {e}")

        self.data = []
        self.setup_driver()
        
        # Filtering configuration
        self.forbidden_titles = ["rfi", "market research", "foods", "meal", "survey"]
        self.forbidden_subtiers = ["defense logistics agency", "defences logistic agency"] # Handling user's spelling + correct spelling
        
        # Base URL from requirements (Updated without NAICS 541714)
        encoded_query = quote(search_query) if search_query else ""
        self.base_url = f"https://sam.gov/search/?page={{page}}&pageSize=100&sort=-modifiedDate&index=opp&sfm%5BsimpleSearch%5D%5BkeywordRadio%5D=ALL&sfm%5BsimpleSearch%5D%5BkeywordEditorTextarea%5D={encoded_query}&sfm%5Bstatus%5D%5Bis_active%5D=true&sfm%5BsetAside%5D%5B0%5D%5Bkey%5D=NONE&sfm%5BsetAside%5D%5B0%5D%5Bvalue%5D=No%20Set%20aside%20used&sfm%5BsetAside%5D%5B1%5D%5Bkey%5D=SBA&sfm%5BsetAside%5D%5B1%5D%5Bvalue%5D=Total%20Small%20Business%20Set-Aside%20(FAR%2019.5)&sfm%5BsetAside%5D%5B2%5D%5Bkey%5D=8A&sfm%5BsetAside%5D%5B2%5D%5Bvalue%5D=8(a)%20Set-Aside%20(FAR%2019.8)&sfm%5BsetAside%5D%5B3%5D%5Bkey%5D=SDVOSBC&sfm%5BsetAside%5D%5B3%5D%5Bvalue%5D=Service-Disabled%20Veteran-Owned%20Small%20Business%20(SDVOSB)%20Set-Aside%20(FAR%2019.14)&sfm%5BsetAside%5D%5B4%5D%5Bkey%5D=WOSB&sfm%5BsetAside%5D%5B4%5D%5Bvalue%5D=SBA%20Certified%20Women-Owned%20Small%20Business%20(WOSB)%20Program%20Set-Aside%20(FAR%2019.15)&sfm%5BtypeOfNotice%5D%5B0%5D%5Bkey%5D=o&sfm%5BtypeOfNotice%5D%5B0%5D%5Bvalue%5D=Solicitation&sfm%5BtypeOfNotice%5D%5B1%5D%5Bkey%5D=k&sfm%5BtypeOfNotice%5D%5B1%5D%5Bvalue%5D=Combined%20Synopsis%2FSolicitation"

    def setup_driver(self):
        """Setup Chrome driver with options"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        
        # Standard anti-detection options
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Suppress SSL/Handshake errors
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument('--log-level=3')

        try:
            driver_path = ChromeDriverManager().install()
            
            # Fix: webdriver-manager might return a path to a LICENSE file or similar if the structure changed
            # Verify if it returns an executable
            if not driver_path.endswith(".exe"):
                # Try to find chromedriver.exe in the same directory or parent
                driver_dir = os.path.dirname(driver_path)
                found_exe = False
                for root, dirs, files in os.walk(driver_dir):
                    if "chromedriver.exe" in files:
                        driver_path = os.path.join(root, "chromedriver.exe")
                        found_exe = True
                        break
                if not found_exe:
                    # Try looking in the parent directory just in case
                    parent_dir = os.path.dirname(driver_dir)
                    for root, dirs, files in os.walk(parent_dir):
                        if "chromedriver.exe" in files:
                            driver_path = os.path.join(root, "chromedriver.exe")
                            found_exe = True
                            break

            service = Service(driver_path)
        except Exception as e:
            logger.warning(f"Could not automatically setup driver via manager: {e}")
            # Fallback for some repetitive usage limits or network issues
            service = Service()
            
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.maximize_window()
        logger.info("Chrome driver initialized successfully")

    def random_delay(self, min_sec=2, max_sec=4):
        time.sleep(random.uniform(min_sec, max_sec))

    def wait_for_page_load(self):
        try:
            WebDriverWait(self.driver, 20).until(
                lambda driver: driver.execute_script('return document.readyState') == 'complete'
            )
            time.sleep(2) # Extra buffer
        except:
            pass

    def check_updated_date_rule(self, date_str):
        """
        Check rule: 
        - If (3) or higher is present -> SKIP
        - If (2) is present -> KEEP
        - If no (X) is present -> KEEP
        - If date_filter is set -> Check if date >= filter_date
        """
        if not date_str:
            return True
            
        # 1. Check Version Count (Original Logic)
        match = re.search(r'\((\d+)\)', date_str)
        if match:
            count = int(match.group(1))
            # User specified "more than 3"
            if count > 3:
                return False # Filter out

        # 2. Check Date Range (New Logic)
        if self.filter_date_obj:
            # Extract date string like "Dec 18, 2025" or "Jan 05, 2024"
            # Regex for "Mmm DD, YYYY"
            date_match = re.search(r'([A-Z][a-z]{2}\s\d{1,2},\s\d{4})', date_str)
            if date_match:
                extracted_date_str = date_match.group(1)
                try:
                    item_date = datetime.strptime(extracted_date_str, "%b %d, %Y")
                    # Compare: Item Date must be >= Filter Date
                    # Using date() for comparison to ignore time if any (though we used strptime with YMD only)
                    if item_date.date() < self.filter_date_obj.date():
                        return False # Too old
                except Exception as e:
                    # If date parsing fails, strictly we might keep it or drop it.
                    # Safest is to log and keep or drop? 
                    # If we can't read the date, we can't filter it. Let's keep it to be safe, 
                    # OR drop if strict. Let's keep.
                    # logger.warning(f"Could not parse date {extracted_date_str}: {e}")
                    pass
            # If no date found in string but string exists... assume valid?
        
        return True # Keep

    def is_valid_title(self, title):
        """Check forbidden keywords in title"""
        if not title:
            return True
        title_lower = title.lower()
        for kw in self.forbidden_titles:
            if kw in title_lower:
                return False
        return True

    def get_links_from_current_page(self):
        """
        Extract links from search results page with preliminary filtering.
        Returns a list of dicts: {'url': url, 'updated_date': date_str, 'title': title}
        """
        candidates = []
        try:
            self.wait_for_page_load()
            
            # Wait for results to be visible - try multiple potential containers
            try:
                WebDriverWait(self.driver, 30).until(
                    lambda d: d.find_elements(By.CSS_SELECTOR, "sds-search-result-list, .sds-card, sds-card, .usa-card, [role='listitem']")
                )
            except Exception as e:
                logger.warning("Timeout waiting for result list. Saving debug page.")
                with open("debug_search_timeout.html", "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
                return []
            
            # Find all result cards using strategies
            cards = []
            selectors = [
                "sds-search-result-list > div", 
                ".sds-card", 
                "sds-card", 
                "div[class*='sds-card']",
                ".usa-card",
                "[role='listitem']"
            ]
            
            for sel in selectors:
                cards = self.driver.find_elements(By.CSS_SELECTOR, sel)
                if cards:
                    logger.info(f"Found {len(cards)} cards using selector: {sel}")
                    break
            
            if not cards:
                logger.info("No cards found. Saving debug page.")
                with open("debug_no_cards.html", "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
                return []
            
            for card in cards:
                try:
                    # Extract Title (try multiple selectors)
                    title_elem = None
                    title_selectors = ["a.word-break-all", "a.usa-link", "h3 a", ".sds-card__title a"]
                    
                    for ts in title_selectors:
                        try:
                            el = card.find_element(By.CSS_SELECTOR, ts)
                            if el and el.is_displayed():
                                title_elem = el
                                break
                        except:
                            continue
                            
                    if not title_elem:
                        # Fallback: look for any link with reasonable text length
                        links = card.find_elements(By.TAG_NAME, "a")
                        for l in links:
                            if len(l.text) > 10 and "opp" in l.get_attribute("href"):
                                title_elem = l
                                break
                    
                    if not title_elem:
                        continue
                        
                    title = title_elem.text.strip()
                    url = title_elem.get_attribute("href")
                        
                    # 1. Title Filter
                    if not self.is_valid_title(title):
                        logger.info(f"Skipping Title: {title}")
                        continue

                    # Extract Updated Date
                    updated_date = ""
                    try:
                        card_text = card.text
                        if "Updated Date" in card_text:
                            parts = card_text.split("Updated Date")
                            if len(parts) > 1:
                                remainder = parts[1].strip().split('\n')[0]
                                updated_date = remainder.strip()
                    except:
                        pass
                        
                    # 2. Updated Date Filter
                    if not self.check_updated_date_rule(updated_date):
                        logger.info(f"Skipping Updated Date: {updated_date} for {title}")
                        continue
                        
                    candidates.append({
                        'url': url,
                        'title': title, 
                        'pre_extracted_updated_date': updated_date
                    })
                    
                except Exception as e:
                    # logger.warning(f"Error parsing card: {str(e)}") 
                    continue
                    
        except Exception as e:
            logger.error(f"Error getting links from page: {str(e)}")
            with open("debug_error.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            
        return candidates

    def extract_details(self, url):
        """Visit detail page and extract required fields"""
        data = {
            'Notice ID': '',
            'Title': '',
            'Date Offers Due': '',
            'Published Date': '',
            'Updated Date': '',
            'Inactive Dates': ''
        }
        
        try:
            self.driver.get(url)
            self.wait_for_page_load()
            self.random_delay(2, 4)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # 1. Subtier Filter Check
            page_text = soup.get_text(separator=' ', strip=True).lower()
            
            if "defense logistics agency" in page_text or "defences logistic agency" in page_text:
                # Double check specific headers if possible to avoid false positives in random text
                # But for now, stick to the safety check
                logger.info(f"Skipping due to Subtier filter: {url}")
                return None 

            # 2. Extract Fields using ID-based strategy
            
            # Title (usually h1)
            title_elem = soup.select_one("h1")
            if title_elem:
                data['Title'] = title_elem.get_text(strip=True)
            
            # Helper for the specific SAM.gov structure provided
            def get_value_by_id_reference(label_id):
                # 1. Try to find value pointing to this label via aria-describedby
                value_elem = soup.find(attrs={"aria-describedby": label_id})
                if value_elem:
                    return value_elem.get_text(strip=True)
                
                # 2. Try simple sibling check if the aria-link is missing
                label_elem = soup.find(id=label_id)
                if label_elem:
                    # Check next sibling
                    sib = label_elem.find_next_sibling()
                    if sib:
                        return sib.get_text(strip=True)
                    # Check parent's next sibling (if label is wrapped)
                    parent = label_elem.parent
                    if parent:
                        sib_parent = parent.find_next_sibling()
                        if sib_parent:
                            return sib_parent.get_text(strip=True)
                return ""

            # Notice ID: id="notice-id"
            data['Notice ID'] = get_value_by_id_reference("notice-id")
            
            # Date Offers Due: id="date-offers-date"
            # Note: User specified "date-offers-date", sometimes it might be "date-offers-due". 
            # I will try the user's specific ID first, then fallback.
            data['Date Offers Due'] = get_value_by_id_reference("date-offers-date") 
            if not data['Date Offers Due']:
                 data['Date Offers Due'] = get_value_by_id_reference("offers-due-date")

            # Published Date: id="published-date"
            data['Published Date'] = get_value_by_id_reference("published-date")
            
            # Inactive Dates: id="inactive-dates"
            data['Inactive Dates'] = get_value_by_id_reference("inactive-dates")

            # Updated Date
            # User didn't provide ID for this, but following the pattern:
            data['Updated Date'] = get_value_by_id_reference("updated-date")
            if not data['Updated Date']:
                # Fallback to text search for Updated Date if ID fails
                 data['Updated Date'] = self._find_field(soup, "Updated Date")
            
            # Re-verify Updated Date Rule
            if not self.check_updated_date_rule(data['Updated Date']):
                 logger.info(f"Skipping due to Updated Date found on page: {data['Updated Date']}")
                 return None

            return data

        except Exception as e:
            logger.error(f"Error details extraction {url}: {e}")
            return None

    def _find_field(self, soup, label_candidates):
        if isinstance(label_candidates, str):
            label_candidates = [label_candidates]
            
        for label in label_candidates:
            # 1. Search for a generic Label tag
            # <label ...>Text</label> <div ...>Value</div>
            label_tag = soup.find("label", string=lambda x: x and label.lower() in x.lower())
            if label_tag:
                 # Check next sibling
                 sib = label_tag.find_next_sibling()
                 if sib: return sib.get_text(strip=True)
                 # Check next input
                 inp = label_tag.find_next("input")
                 if inp: return inp.get('value', '')
            
            # 2. Search for common grid structure: <div>Label</div> <div>Value</div>
            # Or <div id="...description...">Label</div> <div id="...value...">Value</div>
            element = soup.find(string=lambda x: x and x.strip().lower() == label.lower())
            if element:
                 parent = element.parent
                 # look for the "value" container. Usually the next div in the flex/grid.
                 # or look for a sibling with class containing 'content' or 'value'
                 
                 # Try next sibling element
                 next_el = parent.find_next_sibling()
                 if next_el:
                     text = next_el.get_text(strip=True)
                     if text: return text
                     
                 # Try finding field value by ID based on label?
                 # Too complex to guess IDs.
                 
                 # Fallback: parent's parent query
                 grand = parent.parent
                 if grand:
                     # Get all text from grandparent, split by label?
                     full_text = grand.get_text(" ", strip=True)
                     if label in full_text:
                         parts = full_text.split(label)
                         if len(parts) > 1:
                             # take the chunk after label
                             # Usually it's short, so we can take first few words or lines
                             val = parts[1].strip()
                             # Cleanup if it grabbed too much
                             # e.g. "Dec 18, 2025 1:00 PM EST Details..."
                             # Simple heuristic: take until newline or reasonable length?
                             # For dates, it's usually short.
                             return val[:50].strip() # Truncate safety

        return ""

    def run(self, max_records=1000):
        extracted_count = 0
        page = 1
        scraped_urls = set()
        scraped_titles = set()
        
        while extracted_count < max_records:
            logger.info(f"Scanning Page {page}...")
            # 1. Update URL and navigate
            url = self.base_url.format(page=page)
            self.driver.get(url)
            
            # 2. Check if we have results
            try:
                # Wait for spinner or results
                WebDriverWait(self.driver, 15).until(
                    lambda d: d.find_elements(By.CSS_SELECTOR, "sds-search-result-list, .sds-card")
                )
            except:
                logger.info("No more results found or timeout.")
                break
                
            # 3. Get Candidates
            candidates = self.get_links_from_current_page()
            if not candidates:
                logger.info("No candidates found on this page.")
                break
                
            # 4. Process Candidates
            new_items_on_page = 0
            for item in candidates:
                if extracted_count >= max_records:
                    break
                    
                bid_url = item['url']
                bid_title = item['title']
                
                # De-duplication checks
                if bid_url in scraped_urls:
                    logger.info(f"Duplicate URL found, skipping: {bid_url}")
                    continue
                    
                if bid_title in scraped_titles:
                    logger.info(f"Duplicate Title found, skipping: {bid_title}")
                    # Capture URL too just in case
                    scraped_urls.add(bid_url)
                    continue
                
                logger.info(f"Scraping bid: {bid_title}")
                
                details = self.extract_details(bid_url)
                if details:
                    self.data.append(details)
                    scraped_urls.add(bid_url)
                    scraped_titles.add(bid_title)
                    extracted_count += 1
                    new_items_on_page += 1
                    logger.info(f"Success! Total extracted: {extracted_count}")
                    
                    # Periodic Save
                    if extracted_count % 10 == 0:
                        self.save_csv()
            
            # Check progress
            if new_items_on_page == 0 and len(candidates) > 0:
                logger.warning("No new items found on this page (all duplicates or filtered). Stopping to prevent infinite loop.")
                break
                        
            page += 1
            
        saved_file = self.save_csv()
        self.close()
        return saved_file

    def save_csv(self):
        if not self.data:
            return
        df = pd.DataFrame(self.data)
        # Reorder columns preference
        cols = ['Notice ID', 'Title', 'Date Offers Due', 'Published Date', 'Updated Date']
        # Add any other cols that might be there
        for c in df.columns:
            if c not in cols:
                cols.append(c)
        
        # Filter extracting only available columns
        final_cols = [c for c in cols if c in df.columns]
        df = df[final_cols]
        
        saved_file = "sam_gov_bids.csv"
        try:
            df.to_csv(saved_file, index=False)
            logger.info(f"CSV saved successfully to {saved_file}")
            return saved_file
        except PermissionError:
            logger.warning("Could not save to 'sam_gov_bids.csv' because it is open. Saving to backup file.")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            saved_file = f"sam_gov_bids_backup_{timestamp}.csv"
            df.to_csv(saved_file, index=False)
            logger.info(f"CSV saved to {saved_file}")
            return saved_file
        except Exception as e:
            logger.error(f"Error saving CSV: {e}")
            return None

    def close(self):
        if self.driver:
            self.driver.quit()

if __name__ == "__main__":
    scraper = SAMGovScraper(headless=False)
    try:
        scraper.run(max_records=1500)
    except KeyboardInterrupt:
        logger.info("Interrupted!")
        scraper.save_csv()
        scraper.close()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        scraper.save_csv()
        scraper.close()
