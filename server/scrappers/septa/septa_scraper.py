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
import glob
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Third-party imports
import yaml
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from scrappers.exceptions import StopScraping, check_stop, smart_sleep
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
)
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


# ---------------------------------------------------------------------------
# Bootstrap logging – read log filename from config.yml before anything else
# ---------------------------------------------------------------------------
def _get_log_file_from_config() -> str:
    """Read septa.logging.log_file from config/config.yml; fall back to a safe default."""
    config_file = Path.cwd() / "config" / "config.yml"
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            return (
                cfg.get("septa", {})
                   .get("logging", {})
                   .get("log_file", "logs/septa_scraper.log")
            )
        except Exception:
            pass
    return "logs/septa_scraper.log"


LOG_FILE = _get_log_file_from_config()
os.makedirs(os.path.dirname(LOG_FILE) or ".", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE),
    ],
)
logger = logging.getLogger(__name__)


# ===========================================================================
# Config
# ===========================================================================
class Config:
    """Configuration manager – all tuneable values come from config.yml;
    credentials come from the .env file."""

    # Default values (used when a key is absent from config.yml)
    _DEFAULTS = {
        "browser": {
            "window_size": "1920,1080",
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "disable_images": True,
        },
        "timeouts": {
            "element_wait": 30,
            "clickable_wait": 30,
            "login_redirect_wait": 15,
            "navigation_sleep": 3,
            "search_result_wait": 20,
            "date_field_wait": 5,
            "next_page_wait": 10,
            "page_change_sleep": 2,
        },
        "scraping": {
            "max_pages": 50,
        },
        "csv": {
            "prefix": "septa_quotes_",
            "timestamp_format": "%Y%m%d_%H%M%S",
        },
        "wdm": {
            "cache_pattern": ".wdm/drivers/chromedriver/**/chromedriver.exe",
        },
        "navigation": {
            "open_quotes_link_texts": [
                "View Open Quotes", "eProcurement", "Quotations",
                "Quote Module", "Direct Quote Requests",
            ],
            "open_quotes_href_patterns": ["openquote", "OpenQuote"],
            "open_quotes_page_keywords": ["open quote", "open quotes"],
            "menu_procurement_keywords": ["procurement", "quote", "bid", "tender"],
        },
        "selectors": {
            "username_xpath": (
                "//input[contains(@id, 'Username') or contains(@name, 'Username') or "
                "contains(@id, 'User') or contains(@name, 'User') or "
                "contains(@id, 'email') or contains(@name, 'email') or @type='email']"
            ),
            "username_label_xpath": (
                "//label[contains(text(), 'Login ID') or contains(text(), 'User')]"
                "/following::input[1]"
            ),
            "username_fallback_css": "input[type='text']",
            "password_xpath": (
                "//input[contains(@id, 'Password') or contains(@name, 'Password') or "
                "contains(@id, 'Pass') or contains(@name, 'Pass') or @type='password']"
            ),
            "password_label_xpath": (
                "//label[contains(text(), 'Password')]/following::input[1]"
            ),
            "login_btn_xpath": (
                "//a[contains(text(), 'Submit')] | "
                "//a[contains(@href, 'doPostBack') and contains(text(), 'Submit')] | "
                "//a[contains(@id, 'Submit')] | "
                "//button[contains(text(), 'SUBMIT') or contains(text(), 'Submit')] | "
                "//input[@value='SUBMIT' or @value='Submit' or @type='submit']"
            ),
            "logout_xpath": "//a[contains(@href, 'logout')]",
            "login_error_xpath": "//*[contains(text(), 'Invalid') or contains(text(), 'Failed')]",
            "date_input_xpath": (
                "//*[@id='ctl00_ctl00_masterMain_cntMain_ctl00_txtOpensStartDate'] | "
                "//input[contains(@name, 'txtOpensStartDate')] | "
                "//input[contains(@id, 'OpenDate') or contains(@name, 'OpenDate') or "
                "contains(@id, 'FromDate') or contains(@name, 'FromDate') or "
                "contains(@id, 'StartDate') or contains(@name, 'StartDate')] | "
                "//input[contains(@class, 'date') and not(contains(@id, 'Close')) "
                "and not(contains(@id, 'End'))]"
            ),
            "search_btn_xpath": (
                "//a[contains(text(), 'Search') or contains(text(), 'SEARCH')] | "
                "//a[contains(@id, 'Search') or contains(@id, 'btnSearch')] | "
                "//button[contains(text(), 'Search') or contains(text(), 'SEARCH')] | "
                "//input[@value='Search' or @value='SEARCH' or @type='submit'] | "
                "//*[@id='searchButton'] | //*[contains(@class, 'search-btn')]"
            ),
            "data_table_wait_xpath": (
                "//table[contains(@class, 'data') or contains(@class, 'table') or @id]"
            ),
            "table_selectors": [
                "//table[contains(@class, 'data') or contains(@class, 'table')]",
                "//table[@id]",
                "//table[.//th]",
                "//div[contains(@class, 'table')]//table",
                "//*[@role='table' or @role='grid']",
            ],
            "next_page_selectors": [
                "//a[contains(text(), 'Next')]",
                "//a[contains(text(), 'next')]",
                "//a[text()='>']",
                "//a[contains(text(), ' > ')]",
                "//input[@class='next']",
                "//a[contains(@id, 'btnNext')]",
                "//a[contains(@id, 'Next')]",
            ],
            "open_quotes_search_xpath": "//button[contains(text(), 'Search')]",
            "open_quotes_date_placeholder_xpath": "//input[contains(@placeholder, 'Date')]",
        },
    }

    def __init__(self):
        self._load_config_yaml()
        self._load_environment()
        self.output_dir = Path.cwd()
        self.ensure_output_dir()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_config_yaml(self):
        """Load all SEPTA configuration from config/config.yml."""
        config_file = Path.cwd() / "config" / "config.yml"
        yaml_septa: dict = {}

        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    raw = yaml.safe_load(f)
                if raw:
                    # base_url lives under urls.septa
                    self.base_url = (
                        raw.get("urls", {})
                           .get("septa", {})
                           .get("base_url", "")
                    )
                    yaml_septa = raw.get("septa", {})
                else:
                    self.base_url = ""
            except Exception as e:
                logger.error(f"Failed to load config.yml: {e}")
                self.base_url = ""
        else:
            logger.error(f"config.yml not found at: {config_file}")
            self.base_url = ""

        def _merge(section: str) -> dict:
            """Merge defaults with yaml values (yaml wins)."""
            merged = dict(self._DEFAULTS.get(section, {}))
            merged.update(yaml_septa.get(section, {}))
            return merged

        # Expose every section as a plain attribute dict
        self.browser_cfg     = _merge("browser")
        self.timeouts        = _merge("timeouts")
        self.scraping_cfg    = _merge("scraping")
        self.csv_cfg         = _merge("csv")
        self.wdm_cfg         = _merge("wdm")
        self.navigation_cfg  = _merge("navigation")
        self.selectors       = _merge("selectors")

    def _load_environment(self):
        """Load SEPTA credentials from .env file."""
        if not DOTENV_AVAILABLE:
            raise ImportError("python-dotenv is not installed")

        env_file = Path.cwd() / ".env"
        if not env_file.exists():
            logger.error(f".env file not found at: {env_file}")
            logger.info("Creating a template .env file…")
            self._create_template_env(env_file)
            raise FileNotFoundError(
                f".env file not found. Template created at {env_file}"
            )

        load_dotenv(dotenv_path=env_file)
        self.username = os.getenv("SEPTA_USERNAME")
        self.password = os.getenv("SEPTA_PASSWORD")

        if not self.username or not self.password:
            logger.error("Credentials not found in .env file")
            logger.info(f"SEPTA_USERNAME: {'SET' if self.username else 'MISSING'}")
            logger.info(f"SEPTA_PASSWORD: {'SET' if self.password else 'MISSING'}")
            raise ValueError(
                "SEPTA_USERNAME and/or SEPTA_PASSWORD not set in .env file"
            )

        logger.info("Environment variables loaded successfully")

    @staticmethod
    def _create_template_env(env_path: Path):
        template = (
            "# SEPTA Portal Credentials\n"
            "SEPTA_USERNAME=your_username_here\n"
            "SEPTA_PASSWORD=your_password_here\n\n"
            "# Optional settings\n"
            "# TIMEOUT=30\n"
            "# HEADLESS=False\n"
        )
        with open(env_path, "w") as f:
            f.write(template)
        logger.info(f"Template .env file created at {env_path}")

    def ensure_output_dir(self):
        self.output_dir.mkdir(exist_ok=True)

    def get_excel_filename(self) -> str:
        now = datetime.now()
        date_part = now.strftime("%Y-%m-%d")
        # Format time to integer hour to remove leading zero, plus minute/ampm
        hour = int(now.strftime("%I"))
        minute = now.strftime("%M")
        ampm = now.strftime("%p").lower()
        
        # Windows does not allow colons (:) in filenames, using '-' instead
        # Example format: septa-2026-03-13 & 1-12am.xlsx
        return f"septa-{date_part} & {hour}-{minute}{ampm}.xlsx"

    def get_excel_path(self) -> Path:
        return self.output_dir / self.get_excel_filename()


# ===========================================================================
# BrowserManager
# ===========================================================================
class BrowserManager:
    """Manages browser setup and teardown."""

    def __init__(self, config: Config):
        self.config = config
        self.driver: Optional[WebDriver] = None
        self.wait: Optional[WebDriverWait] = None

    def setup_driver(self, headless: bool = False) -> bool:
        """Setup Chrome driver using options from config.yml."""
        try:
            b_cfg = self.config.browser_cfg
            t_cfg = self.config.timeouts

            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)
            chrome_options.add_argument(f"--window-size={b_cfg['window_size']}")

            if headless:
                chrome_options.add_argument("--headless=new")

            if b_cfg.get("disable_images", True):
                chrome_options.add_experimental_option(
                    "prefs",
                    {"profile.managed_default_content_settings.images": 2},
                )

            # -- Locate chromedriver ------------------------------------------
            driver_path = None
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                driver_path = ChromeDriverManager().install()
            except Exception as e:
                logger.warning(f"Failed to install chromedriver via WDM: {e}")
                logger.info("Searching local WDM cache…")
                try:
                    pattern = str(
                        Path.home()
                        / self.config.wdm_cfg["cache_pattern"]
                    )
                    found = sorted(
                        glob.glob(pattern, recursive=True),
                        key=os.path.getmtime,
                        reverse=True,
                    )
                    if found:
                        driver_path = found[0]
                        logger.info(f"Found cached driver: {driver_path}")
                    else:
                        logger.warning("No drivers found in WDM cache")
                except Exception as cache_err:
                    logger.error(f"Error searching cache: {cache_err}")

            service = Service(driver_path) if driver_path else Service()
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, t_cfg["element_wait"])

            self.driver.execute_cdp_cmd(
                "Network.setUserAgentOverride",
                {"userAgent": b_cfg["user_agent"]},
            )

            logger.info("Browser setup completed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to setup browser: {e}")
            return False

    def close_driver(self):
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")

    def wait_for_element(
        self, by: By, selector: str, timeout: Optional[int] = None
    ) -> Optional[WebElement]:
        t = timeout if timeout is not None else self.config.timeouts["element_wait"]
        try:
            return WebDriverWait(self.driver, t).until(
                EC.presence_of_element_located((by, selector))
            )
        except TimeoutException:
            logger.warning(f"Element not found: {selector} (timeout: {t}s)")
            return None

    def wait_for_element_clickable(
        self, by: By, selector: str, timeout: Optional[int] = None
    ) -> Optional[WebElement]:
        t = timeout if timeout is not None else self.config.timeouts["clickable_wait"]
        try:
            return WebDriverWait(self.driver, t).until(
                EC.element_to_be_clickable((by, selector))
            )
        except TimeoutException:
            logger.warning(f"Element not clickable: {selector}")
            return None

    def safe_click(self, element: WebElement, description: str = "element") -> bool:
        try:
            element.click()
            logger.debug(f"Clicked {description}")
            return True
        except ElementClickInterceptedException:
            logger.warning(f"Click intercepted on {description}, trying JS click")
            try:
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except Exception as e:
                logger.error(f"JS click failed: {e}")
                return False
        except Exception as e:
            logger.error(f"Failed to click {description}: {e}")
            return False


# ===========================================================================
# SeptaPortal
# ===========================================================================
class SeptaPortal:
    """Handles all interactions with the SEPTA procurement portal."""

    def __init__(self, browser_manager: BrowserManager, config: Config, stop_event=None):
        self.browser = browser_manager
        self.config  = config
        self.driver  = browser_manager.driver
        self.wait    = browser_manager.wait
        self.stop_event = stop_event
        self._sel    = config.selectors       # shorthand
        self._t      = config.timeouts        # shorthand
        self._nav    = config.navigation_cfg  # shorthand

    def _check(self):
        check_stop(self.stop_event)

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------
    def login(self) -> bool:
        try:
            logger.info(f"Navigating to {self.config.base_url}")
            self.driver.get(self.config.base_url)

            # Username field
            username_field = self.browser.wait_for_element(
                By.XPATH, self._sel["username_xpath"], 10
            )
            if not username_field:
                logger.debug("Username by ID not found, trying label XPath")
                try:
                    username_field = self.driver.find_element(
                        By.XPATH, self._sel["username_label_xpath"]
                    )
                except Exception:
                    username_field = self.browser.wait_for_element(
                        By.CSS_SELECTOR, self._sel["username_fallback_css"], 5
                    )

            if not username_field:
                logger.error("Could not find username field")
                return False

            # Password field
            password_fields = self.driver.find_elements(
                By.XPATH, self._sel["password_xpath"]
            )
            if not password_fields:
                try:
                    pw = self.driver.find_element(
                        By.XPATH, self._sel["password_label_xpath"]
                    )
                    password_fields = [pw]
                except Exception:
                    logger.error("Could not find password field")
                    return False
            password_field = password_fields[0]

            # Enter credentials
            logger.info("Entering credentials…")
            username_field.clear()
            username_field.send_keys(self.config.username)
            password_field.clear()
            password_field.send_keys(self.config.password)

            # Login button
            login_button = self.browser.wait_for_element(
                By.XPATH, self._sel["login_btn_xpath"], 5
            )
            if not login_button:
                logger.error("Could not find login button")
                return False

            logger.info(f"Clicking login button: {login_button.tag_name} '{login_button.text}'")
            self.browser.safe_click(login_button, "login button")

            # Wait for redirect away from login page
            try:
                WebDriverWait(self.driver, self._t["login_redirect_wait"]).until(
                    lambda d: (
                        "login" not in d.current_url.lower()
                        or d.find_elements(By.XPATH, self._sel["logout_xpath"])
                    )
                )
            except TimeoutException:
                logger.warning("Timeout waiting for login redirect, checking URL…")

            if "login" in self.driver.current_url.lower():
                if not self.driver.find_elements(
                    By.XPATH, self._sel["logout_xpath"]
                ):
                    logger.error("Login failed – still on login page")
                    errors = self.driver.find_elements(
                        By.XPATH, self._sel["login_error_xpath"]
                    )
                    if errors:
                        logger.error(f"Login error message: {errors[0].text}")
                    return False

            logger.info("Login successful!")
            return True

        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def navigate_to_open_quotes(self) -> bool:
        try:
            logger.info("Navigating to Open Quotes…")

            nav_attempts = []

            # Link text attempts (from config)
            for text in self._nav["open_quotes_link_texts"]:
                nav_attempts.append(
                    lambda t=text: self._try_click_by_xpath(
                        f"//a[contains(text(), '{t}')]"
                    )
                )
                nav_attempts.append(
                    lambda t=text: self._try_click_by_text(t)
                )

            # href pattern attempts (from config)
            for pattern in self._nav["open_quotes_href_patterns"]:
                nav_attempts.append(
                    lambda p=pattern: self._try_click_by_xpath(
                        f"//a[contains(@href, '{p}')]"
                    )
                )

            # Generic button fallback
            nav_attempts.append(
                lambda: self._try_click_by_xpath(
                    "//button[contains(text(), 'Open Quotes')]"
                )
            )
            nav_attempts.append(lambda: self._explore_menu_structure())

            for attempt in nav_attempts:
                self._check()
                try:
                    if attempt():
                        smart_sleep(self._t["navigation_sleep"], self.stop_event)
                        if self._is_on_open_quotes_page():
                            logger.info("Successfully navigated to Open Quotes")
                            return True
                except StopScraping:
                    raise
                except Exception as e:
                    logger.debug(f"Navigation attempt failed: {e}")
                    continue

            logger.error("Could not navigate to Open Quotes")
            return False

        except Exception as e:
            logger.error(f"Navigation error: {e}")
            return False

    # ------------------------------------------------------------------
    # Date filter
    # ------------------------------------------------------------------
    def apply_date_filter(self, date_filter: Optional[str] = None) -> bool:
        """Apply date filter. date_filter format: YYYY-MM-DD. Defaults to today."""
        try:
            if date_filter:
                try:
                    dt = datetime.strptime(date_filter, "%Y-%m-%d")
                    target_date_str = dt.strftime("%m/%d/%Y")
                    logger.info(f"Applying date filter: {target_date_str}")
                except ValueError:
                    logger.warning(
                        f"Could not parse date '{date_filter}', defaulting to today."
                    )
                    target_date_str = datetime.now().strftime("%m/%d/%Y")
            else:
                target_date_str = datetime.now().strftime("%m/%d/%Y")
                logger.info(f"Applying default date filter (today): {target_date_str}")

            # Set date field
            date_set = False
            date_fields = self.driver.find_elements(
                By.XPATH, self._sel["date_input_xpath"]
            )
            if date_fields:
                try:
                    field = date_fields[0]
                    if field.is_displayed():
                        field.clear()
                        field.send_keys(target_date_str)
                        date_set = True
                except Exception as e:
                    logger.debug(f"Failed to set specific date field: {e}")

            if not date_set:
                logger.warning("Specific date field not found, trying generic input")
                for inp in self.driver.find_elements(By.TAG_NAME, "input"):
                    try:
                        if inp.is_displayed() and inp.get_attribute("type") in ("text", "date"):
                            id_ = (inp.get_attribute("id") or "").lower()
                            name_ = (inp.get_attribute("name") or "").lower()
                            if "date" in id_ or "date" in name_:
                                inp.clear()
                                inp.send_keys(target_date_str)
                                date_set = True
                                break
                    except Exception:
                        continue

            # Click search button
            search_btn = self.browser.wait_for_element(
                By.XPATH,
                self._sel["search_btn_xpath"],
                self._t["date_field_wait"],
            )
            if not search_btn:
                logger.error("Could not find search button")
                return False

            logger.info(f"Clicking search button: {search_btn.tag_name}")
            self.browser.safe_click(search_btn, "search button")

            # Wait for results table
            try:
                WebDriverWait(self.driver, self._t["search_result_wait"]).until(
                    EC.presence_of_element_located(
                        (By.XPATH, self._sel["data_table_wait_xpath"])
                    )
                )
            except TimeoutException:
                logger.warning("Timeout waiting for data table after search.")

            return True

        except Exception as e:
            logger.error(f"Error applying date filter: {e}")
            return False

    # ------------------------------------------------------------------
    # Scraping
    # ------------------------------------------------------------------
    def scrape_quotes(self) -> List[Dict[str, str]]:
        quotes: List[Dict[str, str]] = []
        try:
            logger.info("Scraping quotes from current page…")
            table = self._find_data_table()
            if not table:
                logger.warning("No data table found")
                return quotes

            rows = table.find_elements(By.TAG_NAME, "tr")
            if len(rows) <= 1:
                logger.info("No data rows found in table")
                return quotes

            logger.info(f"Found {len(rows) - 1} data rows")
            for i, row in enumerate(rows[1:], 1):
                self._check()
                try:
                    row_data = self._extract_row_data(row)
                    if row_data:
                        quotes.append(row_data)
                        logger.debug(f"Row {i}: {row_data.get('requisition_number')}")
                except Exception as e:
                    logger.warning(f"Error processing row {i}: {e}")

            logger.info(f"Extracted {len(quotes)} quotes from current page")
        except Exception as e:
            logger.error(f"Error scraping quotes: {e}")
        return quotes

    def scrape_all_pages(self, stop_event=None, on_quote=None) -> List[Dict[str, str]]:
        if stop_event: self.stop_event = stop_event
        all_quotes: List[Dict[str, str]] = []
        max_pages = self.config.scraping_cfg["max_pages"]
        page_sleep = self._t["page_change_sleep"]
        page_num = 1
        last_signature = None

        try:
            while page_num <= max_pages:
                self._check()

                logger.info(f"Processing page {page_num}…")
                quotes = self.scrape_quotes()

                if not quotes:
                    logger.warning(f"No quotes on page {page_num}, stopping.")
                    break

                signature = sorted(
                    str(q.get("requisition_number", "")) + str(q.get("summary", ""))
                    for q in quotes
                )

                if not signature:
                    logger.warning("Empty page signature, stopping.")
                    break

                if last_signature and signature == last_signature:
                    logger.info("Duplicate page detected – end of pagination.")
                    break

                last_signature = signature
                all_quotes.extend(quotes)
                # Fire per-quote callback so callers can update a live counter
                if on_quote:
                    for q in quotes:
                        try:
                            on_quote(q)
                        except Exception as _cb_err:
                            logger.warning(f"on_quote callback failed: {_cb_err}")
                logger.info(
                    f"Page {page_num}: {len(quotes)} quotes | total: {len(all_quotes)}"
                )

                if not self._click_next_page():
                    logger.info("No more pages.")
                    break

                page_num += 1
                smart_sleep(page_sleep, self.stop_event)
        except StopScraping:
            logger.info(f"Stop signal received - returning {len(all_quotes)} partial quotes.")
            return all_quotes

        if page_num > max_pages:
            logger.warning(f"Reached max page limit ({max_pages}).")

        return all_quotes

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------
    def _click_next_page(self) -> bool:
        try:
            for selector in self._sel["next_page_selectors"]:
                try:
                    btn = self.driver.find_element(By.XPATH, selector)
                    if btn.is_displayed() and btn.is_enabled():
                        cls = (btn.get_attribute("class") or "").lower()
                        if "disabled" in cls:
                            continue
                        self.browser.safe_click(btn, "Next Page button")
                        try:
                            WebDriverWait(self.driver, self._t["next_page_wait"]).until(
                                EC.staleness_of(btn)
                            )
                        except Exception:
                            pass
                        return True
                except Exception:
                    continue
            return False
        except Exception as e:
            logger.debug(f"Error checking next page: {e}")
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _try_click_by_text(self, text: str) -> bool:
        try:
            el = self.driver.find_element(
                By.XPATH, f"//*[contains(text(), '{text}')]"
            )
            if el.is_displayed() and el.is_enabled():
                self.browser.safe_click(el, f"'{text}' link")
                return True
        except Exception:
            pass
        return False

    def _try_click_by_xpath(self, xpath: str) -> bool:
        try:
            el = self.driver.find_element(By.XPATH, xpath)
            if el.is_displayed() and el.is_enabled():
                self.browser.safe_click(el, f"element at {xpath}")
                return True
        except Exception:
            pass
        return False

    def _explore_menu_structure(self) -> bool:
        keywords = self._nav["menu_procurement_keywords"]
        try:
            menus = self.driver.find_elements(
                By.CSS_SELECTOR, "nav, .navbar, .menu, .sidebar, ul.menu"
            )
            for menu in menus:
                try:
                    for link in menu.find_elements(By.TAG_NAME, "a"):
                        if any(kw in link.text.lower() for kw in keywords):
                            if link.is_displayed() and link.is_enabled():
                                self.browser.safe_click(link, "procurement menu")
                                smart_sleep(self._t["navigation_sleep"], self.stop_event)
                                return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    def _is_on_open_quotes_page(self) -> bool:
        try:
            page_text = self.driver.page_source.lower()
            if any(kw in page_text for kw in self._nav["open_quotes_page_keywords"]):
                return True
            if self.driver.find_elements(
                By.XPATH, self._sel["open_quotes_search_xpath"]
            ):
                return True
            if self.driver.find_elements(
                By.XPATH, self._sel["open_quotes_date_placeholder_xpath"]
            ):
                return True
            return False
        except Exception:
            return False

    def _find_data_table(self) -> Optional[WebElement]:
        try:
            for selector in self._sel["table_selectors"]:
                try:
                    table = self.driver.find_element(By.XPATH, selector)
                    if table.is_displayed():
                        return table
                except Exception:
                    continue
            logger.debug("No data table found with configured selectors")
            return None
        except Exception as e:
            logger.error(f"Error finding table: {e}")
            return None

    def _extract_row_data(self, row: WebElement) -> Optional[Dict[str, str]]:
        try:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 4:
                return self._extract_alternative_row_data(row)

            return {
                "requisition_number": cells[0].text.strip() or "N/A",
                "summary":            cells[1].text.strip() if len(cells) > 1 else "N/A",
                "open_date":          cells[2].text.strip() if len(cells) > 2 else "N/A",
                "close_date":         cells[3].text.strip() if len(cells) > 3 else "N/A",
            }
        except Exception as e:
            logger.debug(f"Error extracting row data: {e}")
            return None

    def _extract_alternative_row_data(
        self, row: WebElement
    ) -> Optional[Dict[str, str]]:
        try:
            row_text = row.text.strip()
            if not row_text:
                return None
            parts = [p.strip() for p in row_text.split("\n") if p.strip()]
            if not parts:
                return None
            return {
                "requisition_number": parts[0],
                "summary":            parts[1] if len(parts) > 1 else "N/A",
                "open_date":          parts[2] if len(parts) > 2 else "N/A",
                "close_date":         parts[3] if len(parts) > 3 else "N/A",
            }
        except Exception:
            return None


# ===========================================================================
# DataExporter
# ===========================================================================
class DataExporter:
    """Handles CSV export."""

    @staticmethod
    def export_to_excel(quotes: List[Dict[str, str]], filepath: Path) -> bool:
        try:
            if not quotes:
                logger.warning("No data to export")
                return False

            import pandas as pd

            # Rename keys for the final Excel headers
            rows = [
                {
                    "Requisition Number": q.get("requisition_number", "N/A"),
                    "Summary":            q.get("summary", "N/A"),
                    "Open Date":          q.get("open_date", "N/A"),
                    "Close Date":         q.get("close_date", "N/A"),
                }
                for q in quotes
            ]

            df = pd.DataFrame(rows)
            df.to_excel(filepath, index=False)

            logger.info(f"Exported {len(quotes)} records → {filepath}")
            for i, q in enumerate(quotes[:3], 1):
                logger.info(
                    f"  {i}. {q.get('requisition_number')}: "
                    f"{str(q.get('summary', ''))[:50]}…"
                )
            return True

        except Exception as e:
            logger.error(f"Error exporting Excel: {e}")
            return False


# ===========================================================================
# SeptaScraper  (main orchestrator – used when running the file directly)
# ===========================================================================
class SeptaScraper:
    """Orchestrates the full scrape lifecycle."""

    def __init__(self, headless: bool = False):
        self.config = Config()
        self.browser_manager = BrowserManager(self.config)
        self.portal = None
        self.quotes: List[Dict[str, str]] = []
        self.headless = headless

    def run(self) -> bool:
        logger.info("=" * 60)
        logger.info("SEPTA PROCUREMENT PORTAL SCRAPER")
        logger.info("=" * 60)

        if not self.browser_manager.setup_driver(self.headless):
            return False

        try:
            self.portal = SeptaPortal(self.browser_manager, self.config, stop_event=stop_event)

            if not self.portal.login():
                logger.error("Login failed. Exiting.")
                return False

            if not self.portal.navigate_to_open_quotes():
                logger.error("Navigation to Open Quotes failed.")
                return False

            if not self.portal.apply_date_filter():
                logger.warning("Date filter may not have been applied correctly")

            self.quotes = self.portal.scrape_all_pages()

            if not self.quotes:
                logger.warning("No quotes found. The page structure may have changed.")
                return False

            excel_path = self.config.get_excel_path()
            if DataExporter.export_to_excel(self.quotes, excel_path):
                logger.info("=" * 60)
                logger.info("SCRAPING COMPLETED SUCCESSFULLY!")
                logger.info("=" * 60)
                return True

            logger.error("Failed to export data")
            return False

        except KeyboardInterrupt:
            logger.info("Scraping interrupted by user")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False
        finally:
            self.browser_manager.close_driver()


# ===========================================================================
# CLI entry point
# ===========================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="SEPTA Procurement Portal Scraper")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--debug",    action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("selenium").setLevel(logging.WARNING)

    scraper = SeptaScraper(headless=args.headless)
    sys.exit(0 if scraper.run() else 1)


if __name__ == "__main__":
    main()
