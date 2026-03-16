"""
SEPTA Procurement Portal Scraper
Author: Automated Solution
Date: 2024
Description: Scrapes quote requests from SEPTA portal
"""

import os
import sys
import time
import csv
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Third-party imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (TimeoutException, NoSuchElementException, 
                                       ElementClickInterceptedException, 
                                       StaleElementReferenceException)
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

# Try to import dotenv, provide clear error if missing
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    print("ERROR: python-dotenv not installed. Run: pip install python-dotenv")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('septa_scraper.log')
    ]
)
logger = logging.getLogger(__name__)

class Config:
    """Configuration manager for the scraper"""
    
    def __init__(self):
        """Initialize configuration with environment variables"""
        self.base_url = "https://epsadmin.septa.org/vendor/login/"
        self.excluded_keywords = ['new flyer', 'nf', 'cummins', 'nova']
        
        # Load environment variables
        self._load_environment()
        
        # Create output directory
        self.output_dir = Path.cwd()
        self.ensure_output_dir()
    
    def _load_environment(self):
        """Load environment variables from .env file"""
        env_file = Path.cwd() / '.env'
        
        if not DOTENV_AVAILABLE:
            raise ImportError("python-dotenv package is not installed")
        
        if not env_file.exists():
            logger.error(f".env file not found at: {env_file}")
            logger.info("Creating a template .env file...")
            self._create_template_env(env_file)
            raise FileNotFoundError(f".env file not found. Template created at {env_file}")
        
        # Load the .env file
        load_dotenv(dotenv_path=env_file)
        
        # Get credentials
        self.username = os.getenv('SEPTA_USERNAME')
        self.password = os.getenv('SEPTA_PASSWORD')
        
        # Validate credentials
        if not self.username or not self.password:
            logger.error("Credentials not found in .env file")
            logger.info(f"SEPTA_USERNAME: {'SET' if self.username else 'MISSING'}")
            logger.info(f"SEPTA_PASSWORD: {'SET' if self.password else 'MISSING'}")
            raise ValueError("SEPTA_USERNAME and/or SEPTA_PASSWORD not set in .env file")
        
        logger.info("Environment variables loaded successfully")
    
    def _create_template_env(self, env_path: Path):
        """Create a template .env file if it doesn't exist"""
        template = """# SEPTA Portal Credentials
SEPTA_USERNAME=your_username_here
SEPTA_PASSWORD=your_password_here

# Optional settings
# TIMEOUT=30
# HEADLESS=False
"""
        with open(env_path, 'w') as f:
            f.write(template)
        logger.info(f"Template .env file created at {env_path}")
    
    def ensure_output_dir(self):
        """Ensure output directory exists"""
        self.output_dir.mkdir(exist_ok=True)
    
    def get_csv_filename(self) -> str:
        """Generate CSV filename with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"septa_quotes_{timestamp}.csv"
    
    def get_csv_path(self) -> Path:
        """Get full path for CSV file"""
        return self.output_dir / self.get_csv_filename()

class BrowserManager:
    """Manages browser setup and teardown"""
    
    def __init__(self, config: Config):
        self.config = config
        self.driver: Optional[WebDriver] = None
        self.wait: Optional[WebDriverWait] = None
    
    def setup_driver(self, headless: bool = False) -> bool:
        """Setup Chrome driver with appropriate options"""
        try:
            chrome_options = Options()
            
            # Common options for stability
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Headless mode if specified
            if headless:
                chrome_options.add_argument('--headless=new')
            
            # Set window size
            chrome_options.add_argument('--window-size=1920,1080')
            
            # Disable images for faster loading
            prefs = {"profile.managed_default_content_settings.images": 2}
            chrome_options.add_experimental_option("prefs", prefs)
            
            # Setup service
            # Setup service
            from webdriver_manager.chrome import ChromeDriverManager
            import glob
            
            driver_path = None
            try:
                driver_path = ChromeDriverManager().install()
            except Exception as e:
                logger.warning(f"Failed to download/install driver: {e}")
                logger.info("Attempting to find existing driver in cache...")
                
                # Try to find in standard WDM cache location
                try:
                    user_home = Path.home()
                    wdm_pattern = str(user_home / ".wdm" / "drivers" / "chromedriver" / "**" / "chromedriver.exe")
                    found_drivers = glob.glob(wdm_pattern, recursive=True)
                    
                    if found_drivers:
                        # Sort by modification time to get the latest used one
                        found_drivers.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                        driver_path = found_drivers[0]
                        logger.info(f"Found cached driver at: {driver_path}")
                    else:
                        logger.warning("No drivers found in WDM cache")
                except Exception as cache_err:
                    logger.error(f"Error searching cache: {cache_err}")
            
            if not driver_path:
                logger.warning("Could not determine driver path, letting Selenium find it on PATH")
                service = Service() # Expects chromedriver on PATH
            else:
                service = Service(driver_path)
            
            # Create driver
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Set wait
            self.wait = WebDriverWait(self.driver, 30)
            
            # Execute CDP commands to avoid detection
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            logger.info("Browser setup completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup browser: {str(e)}")
            return False
    
    def close_driver(self):
        """Close browser driver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.error(f"Error closing browser: {str(e)}")
    
    def wait_for_element(self, by: By, selector: str, timeout: int = 30) -> Optional[WebElement]:
        """Wait for element with retry logic"""
        try:
            wait = WebDriverWait(self.driver, timeout)
            return wait.until(EC.presence_of_element_located((by, selector)))
        except TimeoutException:
            logger.warning(f"Element not found: {selector} (timeout: {timeout}s)")
            return None
    
    def wait_for_element_clickable(self, by: By, selector: str, timeout: int = 30) -> Optional[WebElement]:
        """Wait for element to be clickable"""
        try:
            wait = WebDriverWait(self.driver, timeout)
            return wait.until(EC.element_to_be_clickable((by, selector)))
        except TimeoutException:
            logger.warning(f"Element not clickable: {selector}")
            return None
    
    def safe_click(self, element: WebElement, description: str = "element") -> bool:
        """Safely click an element with error handling"""
        try:
            element.click()
            logger.debug(f"Clicked {description}")
            # time.sleep(1)  # Removed for speed
            return True
        except ElementClickInterceptedException:
            logger.warning(f"Element {description} click intercepted, trying JavaScript click")
            try:
                self.driver.execute_script("arguments[0].click();", element)
                # time.sleep(1) # Removed for speed
                return True
            except Exception as e:
                logger.error(f"JavaScript click failed: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"Failed to click {description}: {str(e)}")
            return False

class SeptaPortal:
    """Handles interactions with SEPTA portal"""
    
    def __init__(self, browser_manager: BrowserManager, config: Config):
        self.browser = browser_manager
        self.config = config
        self.driver = browser_manager.driver
        self.wait = browser_manager.wait
    
    def login(self) -> bool:
        """Login to SEPTA portal"""
        try:
            logger.info(f"Navigating to {self.config.base_url}")
            self.driver.get(self.config.base_url)
            
            # Use combined selector with 'contains' to handle ASP.NET dynamic IDs (e.g. ctl00$...)
            username_xpath = (
                "//input[contains(@id, 'Username') or contains(@name, 'Username') or "
                "contains(@id, 'User') or contains(@name, 'User') or "
                "contains(@id, 'email') or contains(@name, 'email') or "
                "@type='email']"
            )
            
            username_field = self.browser.wait_for_element(By.XPATH, username_xpath, 10)
            
            if not username_field:
                # Fallback: Find by label if ID/Name fails
                logger.debug("Username field by ID not found, trying by Label")
                try:
                    username_field = self.driver.find_element(By.XPATH, "//label[contains(text(), 'Login ID') or contains(text(), 'User')]/following::input[1]")
                except:
                    # Final fallback to generic input
                    username_field = self.browser.wait_for_element(By.CSS_SELECTOR, "input[type='text']", 5)

            if not username_field:
                logger.error("Could not find username field")
                return False
            
            # Password field - combined selector with 'contains'
            password_xpath = (
                "//input[contains(@id, 'Password') or contains(@name, 'Password') or "
                "contains(@id, 'Pass') or contains(@name, 'Pass') or "
                "@type='password']"
            )
            
            password_field = self.driver.find_elements(By.XPATH, password_xpath)
            if not password_field:
                # Fallback by label
                try:
                    password_element = self.driver.find_element(By.XPATH, "//label[contains(text(), 'Password')]/following::input[1]")
                    password_field = [password_element]
                except:
                    logger.error("Could not find password field")
                    return False
            
            password_field = password_field[0]
            
            # Enter credentials
            logger.info("Entering credentials...")
            username_field.clear()
            username_field.send_keys(self.config.username)
            
            password_field.clear()
            password_field.send_keys(self.config.password)
            
            # Find login button - Updated for ASP.NET Anchor Tags
            # Looks for:
            # 1. <a> tag with 'Submit' text
            # 2. <a> tag with 'doPostBack' in href AND 'Submit' text
            # 3. Standard buttons/inputs
            login_btn_xpath = (
                "//a[contains(text(), 'Submit')] | "
                "//a[contains(@href, 'doPostBack') and contains(text(), 'Submit')] | "
                "//a[contains(@id, 'Submit')] | "
                "//button[contains(text(), 'SUBMIT') or contains(text(), 'Submit')] | "
                "//input[@value='SUBMIT' or @value='Submit' or @type='submit']"
            )
            
            login_button = self.browser.wait_for_element(By.XPATH, login_btn_xpath, 5)
            
            if not login_button:
                logger.error("Could not find login button")
                return False
            
            # Click login button
            logger.info(f"Clicking login button: {login_button.tag_name} {login_button.text}")
            self.browser.safe_click(login_button, "login button")
            
            # Efficient wait for login completion
            try:
                WebDriverWait(self.driver, 15).until(
                    lambda d: "login" not in d.current_url.lower() or 
                              d.find_elements(By.XPATH, "//a[contains(@href, 'logout')]")
                )
            except TimeoutException:
                logger.warning("Timeout waiting for login redirect, checking URL...")
            
            # Check if login was successful
            if "login" in self.driver.current_url.lower():
                # Double check for logout button
                if not self.driver.find_elements(By.XPATH, "//a[contains(@href, 'logout')]"):
                    logger.error("Login failed - still on login page")
                    # Try to see if there is an error message
                    error_msg = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Invalid') or contains(text(), 'Failed')]")
                    if error_msg:
                        logger.error(f"Login error message: {error_msg[0].text}")
                    return False
            
            logger.info("Login successful!")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False
    
    def navigate_to_open_quotes(self) -> bool:
        """Navigate to Open Quotes section"""
        try:
            logger.info("Navigating to Open Quotes...")
            
            # Common navigation patterns for procurement portals
            navigation_attempts = [
                # Specific "View Open Quotes" link based on user screenshot
                lambda: self._try_click_by_xpath("//a[contains(text(), 'View Open Quotes')]"),
                lambda: self._try_click_by_text("View Open Quotes"),
                
                # Fallbacks
                lambda: self._try_click_by_text("eProcurement"),
                lambda: self._try_click_by_text("Quotations"),
                lambda: self._try_click_by_text("Quote Module"),
                lambda: self._try_click_by_text("Direct Quote Requests"),
                
                # Try direct link or button
                lambda: self._try_click_by_xpath("//a[contains(@href, 'openquote') or contains(@href, 'OpenQuote')]"),
                lambda: self._try_click_by_xpath("//button[contains(text(), 'Open Quotes')]"),
                
                # Try finding in menus
                lambda: self._explore_menu_structure()
            ]
            
            for attempt in navigation_attempts:
                try:
                    if attempt():
                        time.sleep(3)
                        # Check if we're on the right page
                        if self._is_on_open_quotes_page():
                            logger.info("Successfully navigated to Open Quotes")
                            return True
                except Exception as e:
                    logger.debug(f"Navigation attempt failed: {str(e)}")
                    continue
            
            logger.error("Could not navigate to Open Quotes")
            return False
            
        except Exception as e:
            logger.error(f"Navigation error: {str(e)}")
            return False
    
    def apply_date_filter(self, date_filter: Optional[str] = None) -> bool:
        """Apply date filter. Default: Today. Input date_filter format: YYYY-MM-DD"""
        try:
            target_date_str = ""
            if date_filter:
                try:
                    # Parse YYYY-MM-DD from HTML input
                    dt = datetime.strptime(date_filter, "%Y-%m-%d")
                    target_date_str = dt.strftime("%m/%d/%Y")
                    logger.info(f"Applying specific date filter: {target_date_str}")
                except ValueError:
                    logger.warning(f"Could not parse provided date {date_filter}, defaulting to today.")
                    target_date_str = datetime.now().strftime("%m/%d/%Y")
            else:
                target_date_str = datetime.now().strftime("%m/%d/%Y")
                logger.info(f"Applying default date filter (Today): {target_date_str}")
            
            # 1. Set Date Field
            # Combined selector for date input (Start/Open Date)
            date_input_xpath = (
                "//*[@id='ctl00_ctl00_masterMain_cntMain_ctl00_txtOpensStartDate'] | "
                "//input[contains(@name, 'txtOpensStartDate')] | "
                "//input[contains(@id, 'OpenDate') or contains(@name, 'OpenDate') or "
                "contains(@id, 'FromDate') or contains(@name, 'FromDate') or "
                "contains(@id, 'StartDate') or contains(@name, 'StartDate')] | "
                "//input[contains(@class, 'date') and not(contains(@id, 'Close')) and not(contains(@id, 'End'))]"
            )
            
            # Try to find specific date field first
            date_fields = self.driver.find_elements(By.XPATH, date_input_xpath)
            
            date_set = False
            if date_fields:
                try:
                    # Target the first one (usually Open/Start date)
                    date_field = date_fields[0]
                    if date_field.is_displayed():
                        date_field.clear()
                        date_field.send_keys(target_date_str)
                        # time.sleep(0.5) # Removed for speed
                        date_set = True
                except Exception as e:
                    logger.debug(f"Failed to set specific date field: {e}")

            if not date_set:
                logger.warning("Specific date field not found, trying generic first date input")
                # Fallback: Find first visible input that looks like a date field
                all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
                for inp in all_inputs:
                    try:
                        if inp.is_displayed() and (inp.get_attribute("type") == "text" or inp.get_attribute("type") == "date"):
                            # Check ID/Name for "date" keyword to be safer
                            if "date" in (inp.get_attribute("id") or "").lower() or "date" in (inp.get_attribute("name") or "").lower():
                                inp.clear()
                                inp.send_keys(target_date_str)
                                date_set = True
                                break
                    except:
                        continue
            
            # 2. Click Search Button
            # Updated selectors to handle ASP.NET Anchor Tags and Buttons for "SEARCH"
            search_btn_xpath = (
                "//a[contains(text(), 'Search') or contains(text(), 'SEARCH')] | "
                "//a[contains(@id, 'Search') or contains(@id, 'btnSearch')] | "
                "//button[contains(text(), 'Search') or contains(text(), 'SEARCH')] | "
                "//input[@value='Search' or @value='SEARCH' or @type='submit'] | "
                "//*[@id='searchButton'] | //*[contains(@class, 'search-btn')]"
            )
            
            search_btn = self.browser.wait_for_element(By.XPATH, search_btn_xpath, 5)
            
            if search_btn:
                logger.info(f"Clicking search button: {search_btn.tag_name}")
                self.browser.safe_click(search_btn, "search button")
                
                # 3. Wait for Results
                logger.info("Search executed, waiting for results...")
                try:
                    # Wait for the table to appear OR for the loading usage to finish
                    # We wait for the data table specifically
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, "//table[contains(@class, 'data') or contains(@class, 'table') or @id]"))
                    )
                    # Give a small buffer for rows to render if table structure appears first
                    # time.sleep(1) 
                    return True
                except TimeoutException:
                    logger.warning("Timeout waiting for data table after search.")
                    # Return True anyway to allow scraper to try extracting whatever is there (or empty)
                    return True
            else:
                logger.error("Could not find search button")
                return False
            
        except Exception as e:
            logger.error(f"Error applying date filter: {str(e)}")
            return False
    
    def scrape_quotes(self) -> List[Dict[str, str]]:
        """Scrape quote data from the page"""
        quotes = []
        
        try:
            logger.info("Starting to scrape quotes...")
            
            # Look for data table
            table = self._find_data_table()
            if not table:
                logger.warning("No data table found")
                return quotes
            
            # Get all rows
            rows = table.find_elements(By.TAG_NAME, "tr")
            
            if len(rows) <= 1:
                logger.info("No data rows found in table")
                return quotes
            
            logger.info(f"Found {len(rows) - 1} rows to process")
            
            # Process each row
            for i, row in enumerate(rows[1:], 1):  # Skip header
                try:
                    row_data = self._extract_row_data(row)
                    if row_data:
                        # Check for excluded keywords
                        if not self._contains_excluded_keywords(row_data['summary']):
                            quotes.append(row_data)
                            logger.debug(f"Added quote: {row_data['requisition_number']}")
                        else:
                            logger.debug(f"Skipped (excluded keyword): {row_data['requisition_number']}")
                except Exception as e:
                    logger.warning(f"Error processing row {i}: {str(e)}")
                    continue
            
            logger.info(f"Successfully extracted {len(quotes)} quotes from current page")
            
        except Exception as e:
            logger.error(f"Error scraping quotes: {str(e)}")
        
        return quotes

    def scrape_all_pages(self) -> List[Dict[str, str]]:
        """Scrape quotes from all available pages"""
        all_quotes = []
        page_num = 1
        max_pages = 50 # Safety limit to prevent infinite loops
        last_page_signature = None
        
        while page_num <= max_pages:
            logger.info(f"Processing Page {page_num}...")
            
            # Scrape current page
            quotes = self.scrape_quotes()
            
            if not quotes:
                logger.warning(f"No quotes found on page {page_num}")
                break
                
            # Create a signature for the current page to check for duplicates
            # Use a list of unique identifiers (e.g. quote number/description)
            current_signature = sorted([str(q.get('quote_number', '')) + str(q.get('description', '')) for q in quotes])
            
            if not current_signature:
                logger.warning("Empty page signature, stopping.")
                break
                
            # Check if this page is identical to the last one (infinite loop detection)
            if last_page_signature and current_signature == last_page_signature:
                logger.info("Duplicate page detected (content identical to previous page). End of pagination reached.")
                break
            
            last_page_signature = current_signature
            all_quotes.extend(quotes)
            logger.info(f"Collected {len(quotes)} quotes from page {page_num}. Total: {len(all_quotes)}")
            
            # Try to go to next page
            if not self._click_next_page():
                logger.info("No more pages found or last page reached")
                break
                
            page_num += 1
            time.sleep(2) # Wait for table refresh
            
        if page_num > max_pages:
            logger.warning(f"Reached maximum page limit of {max_pages}. Stopping.")
            
        return all_quotes

    def _click_next_page(self) -> bool:
        """Click the Next page button if available"""
        try:
            # Common ASP.NET pagination selectors
            next_selectors = [
                "//a[contains(text(), 'Next')]",
                "//a[contains(text(), 'next')]",
                "//a[text()='>']",
                "//a[contains(text(), ' > ')]",
                "//input[@class='next']",
                "//a[contains(@id, 'btnNext')]",
                "//a[contains(@id, 'Next')]"
            ]
            
            for selector in next_selectors:
                try:
                    next_btn = self.driver.find_element(By.XPATH, selector)
                    if next_btn.is_displayed() and next_btn.is_enabled():
                        # Check if it's disabled (often class contains 'Disabled')
                        if 'disabled' in next_btn.get_attribute("class").lower():
                            continue
                            
                        self.browser.safe_click(next_btn, "Next Page button")
                        
                        # Wait for table to reload
                        try:
                            WebDriverWait(self.driver, 10).until(
                                EC.staleness_of(next_btn)
                            )
                        except:
                            pass # Element might not effectively go stale in some ASP.NET grids, but we wait anyway
                            
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking next page: {e}")
            return False
    
    def _try_click_by_text(self, text: str) -> bool:
        """Try to click element by text content"""
        try:
            element = self.driver.find_element(By.XPATH, f"//*[contains(text(), '{text}')]")
            if element.is_displayed() and element.is_enabled():
                self.browser.safe_click(element, f"'{text}' link")
                return True
        except:
            return False
        return False
    
    def _try_click_by_xpath(self, xpath: str) -> bool:
        """Try to click element by XPath"""
        try:
            element = self.driver.find_element(By.XPATH, xpath)
            if element.is_displayed() and element.is_enabled():
                self.browser.safe_click(element, f"element at {xpath}")
                return True
        except:
            return False
        return False
    
    def _explore_menu_structure(self) -> bool:
        """Explore menu structure to find navigation"""
        try:
            # Look for common menu structures
            menus = self.driver.find_elements(By.CSS_SELECTOR, "nav, .navbar, .menu, .sidebar, ul.menu")
            
            for menu in menus:
                try:
                    # Look for procurement-related links
                    links = menu.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        link_text = link.text.lower()
                        if any(keyword in link_text for keyword in ['procurement', 'quote', 'bid', 'tender']):
                            if link.is_displayed() and link.is_enabled():
                                self.browser.safe_click(link, "procurement menu")
                                time.sleep(2)
                                return True
                except:
                    continue
        except:
            pass
        
        return False
    
    def _is_on_open_quotes_page(self) -> bool:
        """Check if we're on the Open Quotes page"""
        try:
            # Check page title or heading
            page_text = self.driver.page_source.lower()
            if 'open quote' in page_text or 'open quotes' in page_text:
                return True
            
            # Check for search button
            if self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Search')]"):
                return True
            
            # Check for date filters
            if self.driver.find_elements(By.XPATH, "//input[contains(@placeholder, 'Date')]"):
                return True
            
            return False
        except:
            return False
    
    def _set_date_field(self, label: str, date_str: str, field_type: str, suffix: str) -> bool:
        """Set date field value"""
        try:
            # Try different selectors for date field
            selectors = [
                f"//input[contains(@placeholder, '{label}')]",
                f"//input[contains(@name, '{field_type}') and contains(@name, '{suffix}')]" if suffix else f"//input[contains(@name, '{field_type}')]",
                f"//input[@id='{field_type}{suffix}']" if suffix else f"//input[@id='{field_type}']",
                f"//label[contains(text(), '{label}')]/following::input[1]"
            ]
            
            for selector in selectors:
                try:
                    date_field = self.driver.find_element(By.XPATH, selector)
                    if date_field.is_displayed():
                        date_field.clear()
                        date_field.send_keys(date_str)
                        time.sleep(0.5)
                        return True
                except:
                    continue
            
            return False
        except Exception as e:
            logger.debug(f"Error setting date field: {str(e)}")
            return False
    
    def _find_data_table(self) -> Optional[WebElement]:
        """Find the main data table on the page"""
        try:
            # Common table selectors
            table_selectors = [
                "//table[contains(@class, 'data') or contains(@class, 'table')]",
                "//table[@id]",
                "//table[.//th]",
                "//div[contains(@class, 'table')]//table",
                "//*[@role='table' or @role='grid']"
            ]
            
            for selector in table_selectors:
                try:
                    table = self.driver.find_element(By.XPATH, selector)
                    if table.is_displayed():
                        return table
                except:
                    continue
            
            # If no table found, check if there's data in divs or other structures
            logger.debug("No table found with standard selectors")
            return None
            
        except Exception as e:
            logger.error(f"Error finding table: {str(e)}")
            return None
    
    def _extract_row_data(self, row: WebElement) -> Optional[Dict[str, str]]:
        """Extract data from a table row"""
        try:
            cells = row.find_elements(By.TAG_NAME, "td")
            
            if len(cells) < 4:
                # Try to find data in other structures
                return self._extract_alternative_row_data(row)
            
            requisition_number = cells[0].text.strip() if cells[0].text else "N/A"
            summary = cells[1].text.strip() if len(cells) > 1 and cells[1].text else "N/A"
            open_date = cells[2].text.strip() if len(cells) > 2 and cells[2].text else "N/A"
            close_date = cells[3].text.strip() if len(cells) > 3 and cells[3].text else "N/A"
            
            return {
                'requisition_number': requisition_number,
                'summary': summary,
                'open_date': open_date,
                'close_date': close_date
            }
            
        except Exception as e:
            logger.debug(f"Error extracting row data: {str(e)}")
            return None
    
    def _extract_alternative_row_data(self, row: WebElement) -> Optional[Dict[str, str]]:
        """Try alternative methods to extract row data"""
        try:
            # Get all text from row
            row_text = row.text.strip()
            if not row_text:
                return None
            
            # Try to parse by splitting (this is a fallback)
            parts = [p.strip() for p in row_text.split('\n') if p.strip()]
            
            if len(parts) >= 4:
                return {
                    'requisition_number': parts[0],
                    'summary': parts[1],
                    'open_date': parts[2],
                    'close_date': parts[3]
                }
            elif len(parts) >= 1:
                return {
                    'requisition_number': parts[0],
                    'summary': parts[1] if len(parts) > 1 else "N/A",
                    'open_date': parts[2] if len(parts) > 2 else "N/A",
                    'close_date': parts[3] if len(parts) > 3 else "N/A"
                }
            
            return None
        except:
            return None
    
    def _contains_excluded_keywords(self, summary: str) -> bool:
        """Check if summary contains excluded keywords"""
        if not summary or summary == "N/A":
            return False
        
        summary_lower = summary.lower()
        for keyword in self.config.excluded_keywords:
            if keyword in summary_lower:
                return True
        return False

class DataExporter:
    """Handles data export functionality"""
    
    @staticmethod
    def export_to_csv(quotes: List[Dict[str, str]], filepath: Path) -> bool:
        """Export quotes data to CSV file"""
        try:
            if not quotes:
                logger.warning("No data to export")
                return False
            
            # Prepare data for CSV
            fieldnames = ['Requisition Number', 'Summary', 'Open Date', 'Close Date']
            rows = []
            
            for quote in quotes:
                rows.append({
                    'Requisition Number': quote.get('requisition_number', 'N/A'),
                    'Summary': quote.get('summary', 'N/A'),
                    'Open Date': quote.get('open_date', 'N/A'),
                    'Close Date': quote.get('close_date', 'N/A')
                })
            
            # Write to CSV
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            
            logger.info(f"Data exported to {filepath}")
            logger.info(f"Total records exported: {len(quotes)}")
            
            # Print sample of exported data
            if quotes:
                logger.info("Sample of exported data:")
                for i, quote in enumerate(quotes[:3], 1):
                    logger.info(f"  {i}. {quote.get('requisition_number')}: {quote.get('summary')[:50]}...")
            
            return True
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {str(e)}")
            return False
    

class SeptaScraper:
    """Main scraper orchestrator"""
    
    def __init__(self, headless: bool = False):
        """Initialize the scraper"""
        self.config = Config()
        self.browser_manager = BrowserManager(self.config)
        self.portal = None
        self.quotes = []
        self.headless = headless
    
    def run(self) -> bool:
        """Main execution method"""
        try:
            logger.info("=" * 60)
            logger.info("SEPTA PROCUREMENT PORTAL SCRAPER")
            logger.info("=" * 60)
            
            # Setup browser
            if not self.browser_manager.setup_driver(self.headless):
                return False
            
            try:
                # Initialize portal
                self.portal = SeptaPortal(self.browser_manager, self.config)
                
                # Step 1: Login
                if not self.portal.login():
                    logger.error("Login failed. Exiting.")
                    return False
                
                # Step 2: Navigate to Open Quotes
                if not self.portal.navigate_to_open_quotes():
                    logger.error("Navigation to Open Quotes failed.")
                    return False
                
                # Step 3: Apply date filter
                if not self.portal.apply_date_filter():
                    logger.warning("Date filter may not have been applied correctly")
                
                # Step 4: Scrape data (All Pages)
                self.quotes = self.portal.scrape_all_pages()
                
                if not self.quotes:
                    logger.warning("No quotes found. The page structure may have changed.")
                    
                    # Check if we're on the right page
                    page_text = self.portal.driver.page_source[:1000]
                    logger.debug(f"Page snippet: {page_text[:500]}...")
                    
                    return False
                
                # Step 5: Export data
                csv_path = self.config.get_csv_path()
                if DataExporter.export_to_csv(self.quotes, csv_path):
                    
                    logger.info("=" * 60)
                    logger.info("SCRAPING COMPLETED SUCCESSFULLY!")
                    logger.info("=" * 60)
                    return True
                else:
                    logger.error("Failed to export data")
                    return False
                
            except KeyboardInterrupt:
                logger.info("Scraping interrupted by user")
                return False
                
            except Exception as e:
                logger.error(f"Unexpected error during scraping: {str(e)}")
                return False
                
            finally:
                # Close browser
                self.browser_manager.close_driver()
                
        except Exception as e:
            logger.error(f"Critical error in scraper: {str(e)}")
            return False

def main():
    """Main function to run the scraper"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SEPTA Procurement Portal Scraper')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('selenium').setLevel(logging.WARNING)
    
    # Run scraper
    scraper = SeptaScraper(headless=args.headless)
    success = scraper.run()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()