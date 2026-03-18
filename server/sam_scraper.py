"""
SAM.gov Procurement Scraper
Description:
  Scrapes active solicitations from SAM.gov filtered by a user-supplied date.
  Applies Response Date + Updated Date URL filters, plus a new Partial Small
  Business Set-Aside (SBP / FAR 19.5).

Extraction fields (9):
  1. Notice Title
  2. Notice ID
  3. Department/Ind. Agency   → skip if contains "Department of Defense"
  4. Description
  5. Subtier                  → skip if contains "Department of Defense"
  6. Updated Date             → skip if version count > 1  (keep 0 or 1 only)
  7. Date Offers Due
  8. Published Date
  9. Office                   → skip if contains "DLA" / "Defense Logistics Agency"

Card-level pre-filters:
  • Forbidden titles  (rfi, market research, foods, meal, survey)
  • Version count > 1
  • Updated Date < user date_filter
"""

import os
import csv
import re
import time
import random
import logging
from datetime import datetime
from pathlib import Path

import yaml
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager


# ---------------------------------------------------------------------------
# Bootstrap logging from config.yml before basicConfig is called
# ---------------------------------------------------------------------------
def _get_sam_log_config() -> dict:
    cfg_file = Path.cwd() / "config.yml"
    if cfg_file.exists():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)
            return raw.get("sam", {}).get("logging", {})
        except Exception:
            pass
    return {}


_log_cfg = _get_sam_log_config()

logging.basicConfig(
    level=logging.INFO,
    format=_log_cfg.get("format", "%(asctime)s - %(levelname)s - %(message)s"),
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(_log_cfg.get("log_file", "sam_scraper.log")),
    ],
)
logger = logging.getLogger(__name__)


# ===========================================================================
# SAMGovScraper
# ===========================================================================
class SAMGovScraper:
    """
    Scrapes SAM.gov solicitations filtered by date.
    All tuneable values come from config.yml under the 'sam:' key.
    """

    def __init__(
        self,
        headless: bool = False,
        date_filter: str = None,   # kept for backward-compat; treated as date_from
        date_to: str = None,
    ):
        self._load_config()

        self.headless    = headless
        self.date_filter = date_filter      # YYYY-MM-DD  (from / start of range)
        self.date_to     = date_to          # YYYY-MM-DD  (to   / end   of range)

        # Parsed datetime objects
        self.filter_date_from = None        # start of range
        self.filter_date_to   = None        # end   of range (defaults to today)
        self.filter_date_obj  = None        # backward-compat alias = filter_date_from

        self.data = []
        self._output_filename = None
        self._csv_filepath    = None
        self._stop_event      = None   # optional threading.Event for graceful stop
        self.skip_csv         = False  # set True to skip all file I/O (DB-only mode)
        self._on_bid_extracted = None  # optional callback(dict) — called per saved bid

        fmt = self._date_cfg.get("filter_date_format", "%Y-%m-%d")

        # ── Parse from-date ──────────────────────────────────────────────
        if self.date_filter:
            try:
                self.filter_date_from = datetime.strptime(self.date_filter, fmt)
                self.filter_date_obj  = self.filter_date_from   # backward-compat alias
            except Exception as e:
                logger.warning(f"Invalid date_filter '{self.date_filter}'. Filter disabled. {e}")

        # ── Parse to-date; default to today if from-date is set ──────────
        if self.date_to:
            try:
                self.filter_date_to = datetime.strptime(self.date_to, fmt)
            except Exception as e:
                logger.warning(f"Invalid date_to '{self.date_to}'. Defaulting to today. {e}")

        if self.filter_date_from and self.filter_date_to is None:
            # No to-date → treat today as the upper bound
            self.filter_date_to = datetime.now().replace(
                hour=23, minute=59, second=59, microsecond=0
            )

        # ── Log the active filter ────────────────────────────────────────
        if self.filter_date_from:
            from_str = self.filter_date_from.strftime("%Y-%m-%d")
            to_str   = self.filter_date_to.strftime("%Y-%m-%d") if self.filter_date_to else "today"
            if from_str == to_str or (
                self.filter_date_to and
                self.filter_date_from.date() == self.filter_date_to.date()
            ):
                logger.info(f"Date filter active: Published Date = {from_str} (exact match)")
            else:
                logger.info(f"Date range filter active: Published Date {from_str} to {to_str}")

        self.setup_driver()

    # ------------------------------------------------------------------
    # Config loading
    # ------------------------------------------------------------------
    def _load_config(self):
        cfg_file = Path.cwd() / "config.yml"
        if not cfg_file.exists():
            raise FileNotFoundError(f"config.yml not found at {cfg_file}")

        with open(cfg_file, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        self._cfg = raw.get("sam", {})
        self.base_url = raw.get("urls", {}).get("sam", {}).get("base_url", "")

        if not self.base_url:
            raise ValueError("urls.sam.base_url is missing from config.yml")

        # Convenience shortcuts
        self._timeouts       = self._cfg.get("timeouts", {})
        self._selectors      = self._cfg.get("selectors", {})
        self._filtering      = self._cfg.get("filtering", {})
        self._skip_cond      = self._cfg.get("skip_conditions", {})
        self._date_cfg       = self._cfg.get("date_parsing", {})
        self._scraping       = self._cfg.get("scraping", {})
        self._csv_cfg        = self._cfg.get("csv", {})
        self._field_ids      = self._cfg.get("detail_field_ids", {})
        self._desc_selectors = self._cfg.get("description_selectors", [])
        self._desc_label     = self._cfg.get("description_heading_label", "Description")
        self._debug_cfg           = self._cfg.get("debug", {})
        self._url_date_params     = self._cfg.get("url_date_params", {})
        self._date_filter_ui_cfg  = self._cfg.get("date_filter_ui", {})

    # ------------------------------------------------------------------
    # Chrome driver
    # ------------------------------------------------------------------
    def setup_driver(self):
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument(
            f"user-agent={self._cfg.get('browser', {}).get('user_agent', '')}"
        )
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--ignore-ssl-errors")
        chrome_options.add_argument("--log-level=3")

        try:
            driver_path = ChromeDriverManager().install()
            if not driver_path.endswith(".exe"):
                driver_dir = os.path.dirname(driver_path)
                found = False
                for root, _dirs, files in os.walk(driver_dir):
                    if "chromedriver.exe" in files:
                        driver_path = os.path.join(root, "chromedriver.exe")
                        found = True
                        break
                if not found:
                    parent = os.path.dirname(driver_dir)
                    for root, _dirs, files in os.walk(parent):
                        if "chromedriver.exe" in files:
                            driver_path = os.path.join(root, "chromedriver.exe")
                            break
            service = Service(driver_path)
        except Exception as e:
            logger.warning(f"ChromeDriverManager failed: {e}. Falling back to PATH.")
            service = Service()

        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.maximize_window()
        logger.info("Chrome driver initialised successfully")

    # ------------------------------------------------------------------
    # URL builder – appends date params when date_filter is provided
    # ------------------------------------------------------------------
    def _build_page_url(self, page: int) -> str:
        """
        Builds the full search URL for a given page number.

        When a date range is active, appends SAM.gov's updatedDate range
        URL parameters so the server pre-filters results before the browser
        renders them.  This dramatically reduces the number of pages the
        scraper needs to click through.

        URL params injected (URL-encoded):
          sfm[dates][updatedDate][updatedDateFrom] = YYYY-MM-DD   (from)
          sfm[dates][updatedDate][updatedDateTo]   = YYYY-MM-DD   (to)
        """
        url = self.base_url.format(page=page)

        if self.filter_date_from:
            from_iso = self.filter_date_from.strftime("%Y-%m-%d")
            to_iso   = (
                self.filter_date_to.strftime("%Y-%m-%d")
                if self.filter_date_to
                else datetime.now().strftime("%Y-%m-%d")
            )
            # SAM.gov range URL params (URL-encoded bracket notation)
            url += (
                f"&sfm%5Bdates%5D%5BupdatedDate%5D%5BupdatedDateFrom%5D={from_iso}"
                f"&sfm%5Bdates%5D%5BupdatedDate%5D%5BupdatedDateTo%5D={to_iso}"
                f"&sfm%5Bdates%5D%5BresponseDue%5D%5BresponseDueFrom%5D={from_iso}"
                f"&sfm%5Bdates%5D%5BresponseDue%5D%5BresponseDueTo%5D={to_iso}"
            )
            logger.debug(f"URL date range params appended: {from_iso} -> {to_iso} (page {page})")

        # Legacy single-date extra params (from config url_date_params, if any)
        elif self.filter_date_obj and self._url_date_params:
            date_iso = self.filter_date_obj.strftime("%Y-%m-%d")
            for param_template in self._url_date_params.values():
                url += "&" + param_template.format(date=date_iso)

        return url

    # ------------------------------------------------------------------
    # Page-number verifier
    # ------------------------------------------------------------------
    def _verify_on_correct_page(self, expected_page: int) -> bool:
        """
        After driver.get("?page=N"), confirm SAM.gov is actually displaying
        page N and hasn't silently redirected back to page 1.

        SAM.gov (Angular SPA) redirects to page 1 when the requested page
        is beyond the result set.

        Strategy order (most reliable → least):
          1. Python URL check  – driver.current_url always reflects the
             address bar instantly; if Angular redirected us the URL will
             show page=1 not page=N.  This check is instantaneous and
             doesn't depend on Angular rendering anything.
          2. Pagination widget – retry up to 5 times with 2-second gaps
             (total 10 s) so Angular has plenty of time to update the
             "N of Total" input box after routing completes.

        Returns True  when we are confirmed to be on expected_page, OR
                       when neither check can make a determination (give
                       benefit of the doubt and continue).
        Returns False when both checks consistently show a different page
                       (genuine end of results / SAM.gov redirect detected).
        """
        # ── Step 1: URL check (instant – no Angular wait needed) ────────
        # Angular updates window.location immediately on routing.  If
        # SAM.gov redirected ?page=N → ?page=1, the URL already shows it.
        try:
            current_url = self.driver.current_url
            url_m = re.search(r"[?&]page=(\d+)", current_url)
            if url_m:
                url_page = int(url_m.group(1))
                if url_page == expected_page:
                    return True   # URL confirms correct page
                # URL shows wrong page — but Angular might still be mid-
                # route (rare).  Fall through to widget check with retries
                # before declaring end-of-results.
                logger.debug(
                    f"URL shows page={url_page}, expected {expected_page}; "
                    f"checking widget before deciding."
                )
        except Exception:
            pass   # can't read URL → continue to widget check

        # ── Step 2: Pagination widget with retries ───────────────────────
        # Read the "current page" input inside SAM.gov's sds-pagination
        # component.  Angular can lag several seconds after navigation, so
        # we retry up to 5 times with 2-second gaps (max 10 s total).
        _JS_PAGE = """
            var selectors = [
                'sds-pagination input[type="number"]',
                'sds-pagination input',
                'nav[aria-label*="pagination"] input',
                '.sds-pagination input'
            ];
            for (var s = 0; s < selectors.length; s++) {
                var els = document.querySelectorAll(selectors[s]);
                for (var i = 0; i < els.length; i++) {
                    var v = parseInt(els[i].value, 10);
                    if (!isNaN(v) && v > 0) return v;
                }
            }
            // Fallback: read page number from the URL inside the browser
            var m = window.location.search.match(/[?&]page=(\\d+)/);
            if (m) return parseInt(m[1], 10);
            return -1;
        """
        for attempt in range(5):
            try:
                result = self.driver.execute_script(_JS_PAGE)
                if result is None or int(result) == -1:
                    # Widget not found – can't verify, give benefit of doubt
                    return True
                current = int(result)
                if current == expected_page:
                    return True
                # Mismatch – wait before the next retry
                if attempt < 4:
                    time.sleep(2)
                    continue
                # All 5 attempts show the wrong page → genuine redirect
                logger.info(
                    f"SAM.gov shows page {current} after {attempt + 1} checks, "
                    f"expected {expected_page} — end of results."
                )
                return False
            except Exception:
                return True   # can't read widget → assume still on correct page

        return True

    # ------------------------------------------------------------------
    # Next-page navigation via UI button (SAM.gov SPA requirement)
    # ------------------------------------------------------------------
    def _click_next_page(self, current_page: int) -> bool:
        """
        Navigate to the next search results page by clicking SAM.gov's own
        pagination "Next" button (#bottomPagination-nextPage).

        WHY THIS IS REQUIRED
        ────────────────────
        SAM.gov is an Angular SPA that uses session-state / cursor-based
        pagination internally.  Navigating directly to ?page=N (N > 1) via
        driver.get() always redirects back to page 1 because the browser has
        no active search session.  Clicking the Next button inside the same
        browser session preserves that state and correctly loads the next page.

        Returns True  → next page loaded (cards present on the new page)
        Returns False → button absent, disabled, or no cards rendered
                        (= genuine end of results, stop the loop)
        """
        NEXT_BTN_ID = "bottomPagination-nextPage"
        results_wait = self._timeouts.get("results_wait", 20)

        # ── Locate the Next button ───────────────────────────────────────
        try:
            btn = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, NEXT_BTN_ID))
            )
        except Exception:
            logger.info(
                f"Next-page button '{NEXT_BTN_ID}' not found after page "
                f"{current_page} — end of results."
            )
            return False

        # ── Check whether the button is disabled ─────────────────────────
        disabled = (
            btn.get_attribute("disabled") is not None
            or btn.get_attribute("aria-disabled") == "true"
            or "disabled" in (btn.get_attribute("class") or "")
        )
        if disabled:
            logger.info(
                f"Next-page button is disabled after page {current_page} "
                f"— end of results."
            )
            return False

        # ── Scroll into view and click ───────────────────────────────────
        self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
        time.sleep(0.5)
        try:
            btn.click()
        except Exception:
            # Fallback to JS click in case element is obscured
            self.driver.execute_script("arguments[0].click();", btn)

        time.sleep(2)   # give Angular router time to start the transition

        # ── Wait for result cards to appear on the new page ──────────────
        try:
            WebDriverWait(self.driver, results_wait).until(
                lambda d: d.find_elements(
                    By.CSS_SELECTOR,
                    self._selectors.get(
                        "results_container_css",
                        "sds-search-result-list, .sds-card",
                    ),
                )
            )
            return True
        except Exception:
            logger.info(
                f"No cards rendered after clicking Next from page {current_page} "
                f"— end of results."
            )
            return False

    # ------------------------------------------------------------------
    # UI date-range filter
    # ------------------------------------------------------------------
    def _apply_ui_date_filters(self) -> bool:
        """
        Fill SAM.gov's "Updated Date" and "Response/Date Offers Due" range
        pickers after page 1 has loaded, using the same from/to date range.

        Two strategies are tried for each input field:
          1. Exact element ID from config  (formly_31_datepicker_updatedDateFrom_1)
          2. Partial-ID XPath fallback     (any input whose @id contains the key)

        After both fields are filled the method dispatches 'input', 'change',
        and 'blur' events so Angular's change-detection picks up the new values,
        then waits for the results list to re-render.

        Returns True if at least the Updated Date from-date field was filled.
        """
        if not self.filter_date_from:
            return False

        ui_cfg   = self._date_filter_ui_cfg
        from_id  = ui_cfg.get("from_input_id", "formly_31_datepicker_updatedDateFrom_1")
        to_id    = ui_cfg.get("to_input_id",   "formly_31_datepicker_updatedDateTo_2")
        date_fmt = ui_cfg.get("input_date_format", "%m/%d/%Y")
        wait_sec = ui_cfg.get("apply_wait", 3)

        from_str = self.filter_date_from.strftime(date_fmt)
        to_str   = (
            self.filter_date_to.strftime(date_fmt)
            if self.filter_date_to
            else datetime.now().strftime(date_fmt)
        )

        def _fill(input_id: str, date_str: str, key_fragment: str) -> bool:
            """Locate an input by ID (exact then partial) and type the date."""
            el = None
            # Strategy 1: exact ID
            try:
                el = WebDriverWait(self.driver, 6).until(
                    EC.presence_of_element_located((By.ID, input_id))
                )
            except Exception:
                pass

            # Strategy 2: partial-ID XPath (handles dynamic Formly numbering)
            if el is None:
                try:
                    els = self.driver.find_elements(
                        By.XPATH, f"//input[contains(@id, '{key_fragment}')]"
                    )
                    if els:
                        el = els[0]
                except Exception:
                    pass

            if el is None:
                logger.warning(f"Date filter input not found: id='{input_id}'")
                return False

            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", el
                )
                time.sleep(0.3)
                el.click()
                time.sleep(0.2)

                # Clear existing value then type new date
                el.send_keys(Keys.CONTROL + "a")
                el.send_keys(Keys.DELETE)
                el.send_keys(date_str)
                el.send_keys(Keys.TAB)   # tab out to trigger Angular blur
                time.sleep(0.3)

                # Dispatch events so Angular's change-detection runs
                self.driver.execute_script(
                    """
                    var e = arguments[0];
                    ['input','change','blur'].forEach(function(t){
                        e.dispatchEvent(new Event(t, {bubbles:true}));
                    });
                    """,
                    el,
                )
                return True
            except Exception as exc:
                logger.debug(f"Error filling date input '{input_id}': {exc}")
                return False

        # --- Updated Date pickers ---
        from_ok = _fill(from_id, from_str, "updatedDateFrom")
        to_ok   = _fill(to_id,   to_str,   "updatedDateTo")

        # --- Response / Date Offers Due pickers (same date range) ---
        resp_from_id = ui_cfg.get(
            "resp_due_from_input_id", "formly_25_datepicker_responseDueFrom_1"
        )
        resp_to_id = ui_cfg.get(
            "resp_due_to_input_id", "formly_25_datepicker_responseDueTo_2"
        )
        resp_from_ok = _fill(resp_from_id, from_str, "responseDueFrom")
        resp_to_ok   = _fill(resp_to_id,   to_str,   "responseDueTo")

        if from_ok:
            time.sleep(wait_sec)   # wait for Angular to re-render results
            logger.info(
                f"UI date filters applied: {from_str} → {to_str} | "
                f"updatedDate(from={'OK' if from_ok else 'FAIL'}, to={'OK' if to_ok else 'FAIL'}) | "
                f"responseDue(from={'OK' if resp_from_ok else 'FAIL'}, to={'OK' if resp_to_ok else 'FAIL'})"
            )
        else:
            logger.warning(
                "Could not fill UI date filter inputs — "
                "URL params will still apply the server-side range."
            )

        return from_ok

    # ------------------------------------------------------------------
    # Timing helpers
    # ------------------------------------------------------------------
    def _random_delay(self):
        lo = self._timeouts.get("delay_min", 2)
        hi = self._timeouts.get("delay_max", 4)
        time.sleep(random.uniform(lo, hi))

    # ------------------------------------------------------------------
    # Date-window boundary detector
    # ------------------------------------------------------------------
    def _is_past_date_window(self) -> bool:
        """
        Returns True when ALL cards currently visible on the search results
        page have an Updated Date (= SAM.gov's modifiedDate, the sort key)
        strictly BEFORE the user's filter date.

        WHY THIS IS THE CORRECT STOP SIGNAL
        ─────────────────────────────────────
        SAM.gov sorts results by -modifiedDate (newest first).  A bid
        published on March 17 has modifiedDate >= March 17 by definition
        (it was at minimum modified on the day it was published).  Once
        every card on a page shows an Updated Date < March 17, all
        remaining pages are guaranteed to also be before March 17 — the
        sort order ensures no later date can appear after this point.

        Returns False when:
          • No date filter is active                (never stop early)
          • No Updated Date is parseable on the page (can't determine → keep going)
          • At least one card has Updated Date >= filter date  (still in window)
        """
        if not self.filter_date_from:
            return False

        # Stop boundary = start of the range (from-date).
        # SAM.gov sorts by -modifiedDate. Once every card's Updated Date is
        # strictly before the from-date, no bid in [from, to] can appear
        # on any later page — safe to stop.
        filter_date   = self.filter_date_from.date()
        updated_label = self._date_cfg.get("updated_date_card_label", "Updated Date")

        try:
            # Re-use the same card selector logic as get_links_from_current_page()
            cards = []
            for sel in self._selectors.get("card_selectors", [".sds-card"]):
                cards = self.driver.find_elements(By.CSS_SELECTOR, sel)
                if cards:
                    break

            if not cards:
                return False   # no cards to read → can't determine

            dates_found: list = []
            for card in cards:
                try:
                    card_text = card.text
                    if updated_label not in card_text:
                        continue
                    raw = (
                        card_text.split(updated_label)[1]
                        .strip().split("\n")[0].strip()
                    )
                    # Strip version count  "(1)" etc.
                    raw = re.sub(r"\s*\(\d+\)\s*", "", raw).strip()
                    m = self._DATE_PATTERN.search(raw)
                    if not m:
                        continue
                    date_str = re.sub(r"\s+", " ", m.group()).strip()
                    for fmt in ("%b %d, %Y", "%b %d,%Y"):
                        try:
                            dates_found.append(
                                datetime.strptime(date_str, fmt).date()
                            )
                            break
                        except ValueError:
                            continue
                except Exception:
                    continue

            if not dates_found:
                return False   # couldn't parse any dates → give benefit of doubt

            # Stop only when EVERY parseable date is strictly before the filter
            past = all(d < filter_date for d in dates_found)
            if past:
                logger.info(
                    f"Date window passed: all {len(dates_found)} card(s) on this "
                    f"page have Updated Date < {filter_date} — stopping."
                )
            return past

        except Exception:
            return False   # safety net: never stop due to an unexpected error

    def _wait_for_page_load(self):
        try:
            WebDriverWait(
                self.driver, self._timeouts.get("page_load_wait", 20)
            ).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            time.sleep(self._timeouts.get("page_load_sleep", 2))
        except Exception:
            pass

    def _wait_for_angular(self):
        """
        Extra wait for Angular to finish rendering detail-page content.
        Waits up to 15 s for at least one field-like element to appear.
        """
        try:
            WebDriverWait(self.driver, 15).until(
                lambda d: d.find_elements(
                    By.CSS_SELECTOR,
                    "h1, [id*='notice'], [id*='department'], [id*='agency']"
                )
            )
        except Exception:
            pass
        # Extra buffer for Angular change detection to complete
        time.sleep(1.5)

    # ------------------------------------------------------------------
    # Card-level filters
    # ------------------------------------------------------------------
    def _check_updated_date_rule(self, date_str: str) -> bool:
        """
        Returns True (keep) / False (skip).

        Only checks the version/amendment count.
        Threshold = 1 → keep bids with no count (version 0) or count = 1.
        Any higher count → skip.

        The date-range comparison that previously rejected bids whose
        Updated Date was before the user's filter date has been removed.
        It was correct for current-date searches but silently dropped
        all past-date bids (bids from weeks ago have an older Updated Date
        than today's filter date → everything was filtered out).
        """
        if not date_str:
            return True

        threshold = self._filtering.get("version_count_threshold", 1)
        version_match = re.search(r"\((\d+)\)", date_str)
        if version_match and int(version_match.group(1)) > threshold:
            return False

        return True

    def _matches_published_date(self, date_str: str) -> bool:
        """
        Returns True if the extracted Published Date falls within the active
        date range [filter_date_from, filter_date_to] (both ends inclusive).

        Scenarios:
          • from == to (exact day)   → same as old exact-match behaviour
          • from < to  (range)       → any date in the range is accepted
          • Only from set, no to     → from <= date <= today
          • No filter active         → always True (keep all bids)

        Robustness rules:
          • No filter active OR date_str is empty  → True (keep the bid)
          • Date string in unrecognised format      → True (keep to avoid silent drops)
          • Date parsed successfully                → range comparison
        """
        if not self.filter_date_from or not date_str:
            return True     # no filter active, or no date on page → always keep

        # _parse_any_date handles all formats and returns "Mon D, YYYY" or ""
        normalised = self._parse_any_date(date_str)
        if not normalised:
            logger.debug(f"_matches_published_date: unrecognised format '{date_str}' - keeping")
            return True

        raw = re.sub(r"\s+", " ", normalised).strip()
        for fmt in ("%b %d, %Y", "%b %d,%Y", "%b %d, %Y"):
            try:
                extracted = datetime.strptime(raw, fmt).date()
                from_date = self.filter_date_from.date()
                to_date   = self.filter_date_to.date() if self.filter_date_to else datetime.now().date()
                in_range  = from_date <= extracted <= to_date
                if not in_range:
                    logger.debug(
                        f"Published Date {extracted} not in range [{from_date}, {to_date}]"
                    )
                return in_range
            except ValueError:
                continue

        logger.debug(f"_matches_published_date: could not parse '{raw}' - keeping")
        return True

    def _clean_updated_date(self, date_str: str) -> str:
        """
        Strip the version count suffix from an Updated Date string so only the
        bare date is stored in the CSV column.

        Examples:
          "Mar 17, 2026 (1)"  →  "Mar 17, 2026"
          "Mar 17, 2026"      →  "Mar 17, 2026"   (unchanged)
        """
        if not date_str:
            return date_str
        # Remove  (N)  anywhere in the string, then trim whitespace
        return re.sub(r"\s*\(\d+\)\s*", "", date_str).strip()

    # Date pattern used to validate date fields (e.g. "Mar 17, 2026" or
    # "Mar 17, 2026 (1)").  If a field value doesn't match this it's treated
    # as garbage and discarded before falling back to a cleaner extractor.
    _DATE_PATTERN = re.compile(r"[A-Z][a-z]{2}\s+\d{1,2},\s*\d{4}")

    # Additional patterns for alternative date formats that SAM.gov (or
    # the user's browser timezone conversion) may produce:
    #   ISO 8601 : "2026-03-31T17:00:00+05:30"
    #   Slash    : "03/31/2026"
    #   Full name: "March 31, 2026"
    _ISO_DATE_RE   = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
    _SLASH_DATE_RE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")
    _FULL_MONTH_RE = re.compile(
        r"(January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+(\d{1,2}),?\s*(\d{4})"
    )

    def _looks_like_date(self, s: str) -> bool:
        """
        Return True when s contains a recognisable date token (Mon DD, YYYY).
        Used to guard date fields against being contaminated with URLs or
        other non-date text that fallback strategies sometimes return.
        """
        return bool(self._DATE_PATTERN.search(s)) if s else False

    def _parse_any_date(self, s: str) -> str:
        """
        Extract a date from ANY format and normalise it to "Mon D, YYYY".

        Handles all formats SAM.gov (or the user's browser timezone
        conversion) may produce, including but not limited to:
          "Mar 17, 2026 2:26 PM GMT+7"   -> "Mar 17, 2026"
          "2026-03-31T17:00:00+05:30"    -> "Mar 31, 2026"
          "2026-03-31"                   -> "Mar 31, 2026"
          "03/31/2026"                   -> "Mar 31, 2026"
          "March 31, 2026"               -> "Mar 31, 2026"
          "Mar 31, 2026"                 -> "Mar 31, 2026"  (unchanged)

        Returns "" if no date pattern can be found in s.
        """
        if not s:
            return ""

        # 1: Already in "Mon DD, YYYY" form (with optional time/tz suffix)
        m = self._DATE_PATTERN.search(s)
        if m:
            return m.group().strip()

        # 2: ISO 8601  "2026-03-31T17:00:00+05:30"  or bare "2026-03-31"
        m = self._ISO_DATE_RE.search(s)
        if m:
            try:
                d = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                return f"{d.strftime('%b')} {d.day}, {d.year}"
            except ValueError:
                pass

        # 3: MM/DD/YYYY  "03/31/2026"
        m = self._SLASH_DATE_RE.search(s)
        if m:
            try:
                d = datetime(int(m.group(3)), int(m.group(1)), int(m.group(2)))
                return f"{d.strftime('%b')} {d.day}, {d.year}"
            except ValueError:
                pass

        # 4: Full month name  "March 31, 2026"
        m = self._FULL_MONTH_RE.search(s)
        if m:
            try:
                d = datetime.strptime(
                    f"{m.group(1)} {int(m.group(2))} {m.group(3)}", "%B %d %Y"
                )
                return f"{d.strftime('%b')} {d.day}, {d.year}"
            except ValueError:
                pass

        return ""

    def _is_valid_title(self, title: str) -> bool:
        """Returns False if the title contains any forbidden keyword."""
        if not title:
            return True
        lower = title.lower()
        for kw in self._filtering.get("forbidden_titles", []):
            if kw in lower:
                return False
        return True

    # ------------------------------------------------------------------
    # Detail-page skip conditions
    # ------------------------------------------------------------------
    def _should_skip_bid(self, data: dict) -> tuple[bool, str]:
        """
        Returns (True, reason) if the bid should be discarded.
        Applied AFTER all 9 fields have been extracted.

        Conditions:
          • Department/Ind. Agency contains DoD term  → skip
          • Subtier contains DoD term                 → skip
          • Office contains DLA term                  → skip
        """
        dept = data.get("Department/Ind. Agency", "").lower()
        for term in self._skip_cond.get("department_skip_terms", []):
            if term in dept:
                return True, f"Dept=DoD ({dept})"

        subtier = data.get("Subtier", "").lower()
        for term in self._skip_cond.get("subtier_skip_terms", []):
            if term in subtier:
                return True, f"Subtier=DoD ({subtier})"

        office = data.get("Office", "").lower()
        for term in self._skip_cond.get("office_skip_terms", []):
            if term in office:
                return True, f"Office=DLA ({office})"

        return False, ""

    # ------------------------------------------------------------------
    # Search-results page – candidate link extraction
    # ------------------------------------------------------------------
    def get_links_from_current_page(self) -> list:
        # NOTE: run() already waits for cards before calling this method.
        # We skip _wait_for_page_load() here to avoid re-triggering Angular
        # and to prevent reading stale DOM content from a previous page.
        candidates = []
        try:

            # Find card elements
            cards = []
            for sel in self._selectors.get("card_selectors", [".sds-card"]):
                cards = self.driver.find_elements(By.CSS_SELECTOR, sel)
                if cards:
                    logger.info(f"Found {len(cards)} cards via selector: {sel}")
                    break

            if not cards:
                logger.info("No cards found on page.")
                self._save_debug(self._debug_cfg.get("no_cards_file", "debug_no_cards.html"))
                return []

            title_min_len  = self._selectors.get("title_min_length", 10)
            href_contains  = self._selectors.get("title_href_contains", "opp")
            updated_label  = self._date_cfg.get("updated_date_card_label", "Updated Date")

            for card in cards:
                try:
                    # ── Find title element ──────────────────────────────
                    title_elem = None
                    for ts in self._selectors.get("title_selectors", []):
                        try:
                            el = card.find_element(By.CSS_SELECTOR, ts)
                            if el and el.is_displayed():
                                title_elem = el
                                break
                        except Exception:
                            continue

                    if not title_elem:
                        for lnk in card.find_elements(By.TAG_NAME, "a"):
                            href = lnk.get_attribute("href") or ""
                            if len(lnk.text) > title_min_len and href_contains in href:
                                title_elem = lnk
                                break

                    if not title_elem:
                        continue

                    title = title_elem.text.strip()
                    url   = title_elem.get_attribute("href")

                    # ── Filter 1: forbidden title ───────────────────────
                    if not self._is_valid_title(title):
                        logger.info(f"[SKIP] Forbidden title: {title}")
                        continue

                    # ── Extract Updated Date + Published Date from card ──
                    card_text     = ""
                    updated_date  = ""
                    card_pub_date = ""
                    try:
                        card_text = card.text

                        # Updated Date – prefer DOM element with sds-field__value
                        # so we get the exact text SAM.gov renders for that field
                        # rather than a raw text-split that can bleed into the
                        # next label.
                        updated_date = ""
                        try:
                            lbl_els = card.find_elements(
                                By.XPATH,
                                f".//*[contains(@class,'sds-field__label') and "
                                f"normalize-space(text())='{updated_label}']",
                            )
                            for lbl in lbl_els:
                                # Strategy A: following-sibling sds-field__value
                                try:
                                    val_el = lbl.find_element(
                                        By.XPATH,
                                        "following-sibling::*[contains(@class,'sds-field__value')]",
                                    )
                                    t = val_el.text.strip()
                                    if t:
                                        updated_date = t
                                        break
                                except Exception:
                                    pass
                                # Strategy B: parent → sds-field__value sibling
                                if not updated_date:
                                    try:
                                        val_el = lbl.find_element(
                                            By.XPATH,
                                            "../*[contains(@class,'sds-field__value')]",
                                        )
                                        t = val_el.text.strip()
                                        if t:
                                            updated_date = t
                                            break
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                        # Fallback: plain text-split if DOM strategies failed
                        if not updated_date and updated_label in card_text:
                            updated_date = (
                                card_text.split(updated_label)[1]
                                .strip().split("\n")[0].strip()
                            )

                        # ── Bid Repeat Count ──────────────────────────────
                        # SAM.gov shows a repeat/amendment count as an <a>
                        # element with class "ng-star-inserted" and text
                        # matching "(N)" (e.g. "(2)").  Default is 0.
                        bid_repeat_count = 0
                        try:
                            count_els = card.find_elements(
                                By.CSS_SELECTOR, "a.ng-star-inserted"
                            )
                            for ce in count_els:
                                m = re.match(r"^\((\d+)\)$", ce.text.strip())
                                if m:
                                    bid_repeat_count = int(m.group(1))
                                    break
                        except Exception:
                            pass

                        # ── Published Date: CSS class extraction ──────────
                        # SAM.gov uses class "sds-field__value0" (and the un-
                        # suffixed "sds-field__value") for card field values.
                        # XPath contains(@class,'sds-field__value') matches
                        # both variants without hard-coding the suffix.
                        pub_label = self._selectors.get(
                            "card_pub_date_label",
                            self._date_cfg.get(
                                "published_date_card_label", "Published Date"
                            ),
                        )
                        # Strategy A: find the value element that immediately
                        # follows a label whose text is "Published Date".
                        # Works for both sds-field__value and sds-field__value0.
                        try:
                            val_el = card.find_element(
                                By.XPATH,
                                f".//*[contains(@class,'{self._selectors.get('card_field_label_class','sds-field__label')}') "
                                f"and normalize-space(text())='{pub_label}']"
                                f"/following-sibling::*[contains(@class,'{self._selectors.get('card_field_value_class','sds-field__value')}')]",
                            )
                            card_pub_date = val_el.text.strip()
                        except Exception:
                            pass

                        # Strategy B: parent-then-child (some DOM layouts put
                        # label + value as siblings inside the same container)
                        if not card_pub_date:
                            try:
                                val_el = card.find_element(
                                    By.XPATH,
                                    f".//*[contains(@class,'{self._selectors.get('card_field_label_class','sds-field__label')}') "
                                    f"and normalize-space(text())='{pub_label}']"
                                    f"/../*[contains(@class,'{self._selectors.get('card_field_value_class','sds-field__value')}')]",
                                )
                                card_pub_date = val_el.text.strip()
                            except Exception:
                                pass

                        # Strategy C: text-split fallback (original approach)
                        if not card_pub_date and pub_label in card_text:
                            card_pub_date = (
                                card_text.split(pub_label)[1]
                                .strip().split("\n")[0].strip()
                            )

                    except Exception:
                        pass

                    # ── Filter 2: version count ──────────────────────────
                    if not self._check_updated_date_rule(updated_date):
                        logger.info(f"[SKIP] Date/version rule: {updated_date} | {title}")
                        continue

                    # ── Filter 3: Published Date exact-day match (CARD) ──
                    # This is the PRIMARY date gate.  With the filter active,
                    # a detail page is NEVER opened unless the card's own
                    # Published Date field confirms a match.  This prevents
                    # off-date bids (e.g. March 16 when user asked for March
                    # 17) from ever wasting a network round-trip.
                    #
                    # Strict rules (filter active):
                    #   • Date found + matches filter  → proceed
                    #   • Date found + does NOT match  → skip card entirely
                    #   • Date NOT found on card        → skip card (cannot confirm)
                    if self.filter_date_obj:
                        if not card_pub_date:
                            logger.info(
                                f"[SKIP-CARD] Published Date not found on card "
                                f"(filter active – cannot confirm date) | {title}"
                            )
                            continue
                        if not self._matches_published_date(card_pub_date):
                            logger.info(
                                f"[SKIP-CARD] Published {card_pub_date} "
                                f"!= {self.filter_date_obj.date()} | {title}"
                            )
                            continue

                    # ── Filter 4: DoD / DLA check at CARD level ─────────
                    # SAM.gov cards display the Department, Sub-tier and
                    # Office directly on the search result — no need to open
                    # the detail page just to discard the bid.
                    # We reuse the same skip-term lists from config so the
                    # logic stays in one place.
                    if card_text:
                        card_lower = card_text.lower()
                        _dod_skip   = False
                        _dod_reason = ""

                        for term in self._skip_cond.get("department_skip_terms", []):
                            if term in card_lower:
                                _dod_skip   = True
                                _dod_reason = f"Dept contains '{term}'"
                                break

                        if not _dod_skip:
                            for term in self._skip_cond.get("subtier_skip_terms", []):
                                if term in card_lower:
                                    _dod_skip   = True
                                    _dod_reason = f"Subtier contains '{term}'"
                                    break

                        if not _dod_skip:
                            for term in self._skip_cond.get("office_skip_terms", []):
                                if term in card_lower:
                                    _dod_skip   = True
                                    _dod_reason = f"Office contains '{term}'"
                                    break

                        if _dod_skip:
                            logger.info(
                                f"[SKIP-CARD] DoD/DLA ({_dod_reason}) – "
                                f"detail page NOT opened | {title}"
                            )
                            continue

                    candidates.append({
                        "url":                        url,
                        "title":                      title,
                        "pre_extracted_updated_date": updated_date,
                        "card_pub_date":              card_pub_date,
                        "bid_repeat_count":           bid_repeat_count,
                    })

                except Exception:
                    continue

        except Exception as e:
            logger.error(f"Error collecting page links: {e}")
            self._save_debug(self._debug_cfg.get("error_file", "debug_error.html"))

        return candidates

    # ------------------------------------------------------------------
    # Detail page – full field extraction
    # ------------------------------------------------------------------
    def extract_details(self, url: str, pre_updated_date: str = "") -> dict | None:
        """
        Visit an opportunity detail page and extract all 9 required fields.
        Returns None if any skip condition is triggered.

        pre_updated_date: Updated Date already extracted from the search-results
        card (sds-field__value).  When provided the method skips the detail-page
        extraction for that field; the version check was already applied at the
        card-filter stage.
        """
        data = {
            "Notice Title":           "",
            "Notice ID":              "",
            "Department/Ind. Agency": "",
            "Description":            "",
            "Subtier":                "",
            "Updated Date":           "",
            "Date Offers Due":        "",
            "Published Date":         "",
            "Office":                 "",
        }

        try:
            self.driver.get(url)
            self._wait_for_page_load()
            # Wait for Angular to finish rendering field elements
            self._wait_for_angular()

            # Scroll halfway down to trigger lazy-loaded content, then back up
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)

            self._random_delay()

            # Re-parse after Angular has fully rendered
            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            ids = self._field_ids

            # ── Field 1: Notice Title ────────────────────────────────────
            h1 = soup.select_one("h1")
            data["Notice Title"] = h1.get_text(strip=True) if h1 else ""
            if not data["Notice Title"]:
                try:
                    el = self.driver.find_element(By.TAG_NAME, "h1")
                    data["Notice Title"] = el.text.strip()
                except Exception:
                    pass

            # ── Field 2: Notice ID ───────────────────────────────────────
            data["Notice ID"] = self._get_field(
                soup, ids.get("notice_id", "notice-id"), "Notice ID"
            )

            # ── Field 3: Department/Ind. Agency ─────────────────────────
            data["Department/Ind. Agency"] = self._get_field(
                soup, ids.get("department_agency", "department-ind-agency"),
                "Department/Ind. Agency"
            )

            # ── Field 4: Description ─────────────────────────────────────
            # Extracted BEFORE skip check so we can log full info; filtered out below if DoD
            data["Description"] = self._extract_description(soup)

            # ── Field 5: Subtier ─────────────────────────────────────────
            data["Subtier"] = self._get_field(
                soup, ids.get("sub_tier", "sub-tier"), "Sub-Tier"
            )

            # ── Field 6: Updated Date ────────────────────────────────────
            # Use the value already pulled from the search-results card when
            # available — it comes from the sds-field__value element and is
            # more reliable than re-extracting it from the detail page.
            if pre_updated_date:
                data["Updated Date"] = self._clean_updated_date(pre_updated_date)
                logger.debug(
                    f"Updated Date taken from card: {data['Updated Date']}"
                )
            else:
                # Fall back to detail-page extraction (no card value provided)
                _raw_updated = self._get_field(
                    soup, ids.get("updated_date", "updated-date"),
                    self._date_cfg.get("updated_date_card_label", "Updated Date")
                )
                # Guard: discard URL/garbage values returned by fallback strategies
                if _raw_updated and not self._looks_like_date(_raw_updated):
                    logger.debug(
                        f"Updated Date fallback returned non-date value "
                        f"'{_raw_updated[:60]}' – discarding and using regex."
                    )
                    _raw_updated = ""
                if not _raw_updated:
                    _raw_updated = self._regex_date_from_page("Updated Date")
                data["Updated Date"] = _raw_updated

            # ── Field 7: Date Offers Due ─────────────────────────────────
            # SAM.gov can show this in many formats depending on the user's
            # browser locale / timezone, e.g.:
            #   "Mar 31, 2026 5:00 PM GMT+7"
            #   "2026-03-31T17:00:00+05:30"
            #   "03/31/2026"
            # _parse_any_date() normalises all of these to "Mon D, YYYY".
            # If the primary element lookup fails we try an alternate ID and
            # then a full page-body regex scan so the field is never left
            # blank when the date IS present on the page.
            _raw_due = self._get_field(
                soup, ids.get("date_offers_due", "date-offers-date"), "Date Offers Due"
            )
            if not _raw_due:
                _raw_due = self._get_field(
                    soup, ids.get("date_offers_due_alt", "offers-due-date"), ""
                )

            # Normalise: extract just the date regardless of time/tz suffix
            _raw_due = self._parse_any_date(_raw_due)

            # Fallback: scan the full rendered page body for the date
            if not _raw_due:
                _fallback_due = self._regex_date_from_page("Date Offers Due")
                if not _fallback_due:
                    # Some pages label it "Response Date" instead
                    _fallback_due = self._regex_date_from_page("Response Date")
                if _fallback_due:
                    _raw_due = self._parse_any_date(_fallback_due)
                    if _raw_due:
                        logger.debug(f"Date Offers Due recovered via page-text fallback: {_raw_due}")

            data["Date Offers Due"] = _raw_due

            # ── Field 8: Published Date ──────────────────────────────────
            # Uses the same normalise + fallback pipeline as Date Offers Due.
            # Handles any format SAM.gov may show:
            #   "Mar 17, 2026 2:26 PM GMT+7"
            #   "2026-03-17T00:00:00+05:30"
            #   "03/17/2026"  etc.
            _raw_pub = self._get_field(
                soup, ids.get("published_date", "published-date"), "Published Date"
            )

            # Normalise to "Mon D, YYYY"
            _raw_pub = self._parse_any_date(_raw_pub)

            # Fallback: scan the full rendered page body for the date
            if not _raw_pub:
                _fallback_pub = self._regex_date_from_page("Published Date")
                if _fallback_pub:
                    _raw_pub = self._parse_any_date(_fallback_pub)
                    if _raw_pub:
                        logger.debug(f"Published Date recovered via page-text fallback: {_raw_pub}")

            data["Published Date"] = _raw_pub

            # ── Field 9: Office ──────────────────────────────────────────
            data["Office"] = self._get_field(
                soup, ids.get("office", "office"), "Office"
            )

            # ── Re-verify version/date rule against detail-page Updated Date
            #    (uses raw string that still contains the version count)
            if not self._check_updated_date_rule(data["Updated Date"]):
                logger.info(
                    f"[SKIP] Version count > 1: {data['Updated Date']}"
                )
                return None

            # ── Store ONLY the bare date in Updated Date column ──────────
            #    Strip "(N)" so the CSV shows e.g. "Mar 17, 2026" only.
            data["Updated Date"] = self._clean_updated_date(data["Updated Date"])

            # ── Published Date (extracted from detail page) ───────────────
            # We no longer apply a strict exact-match or empty-date rule here.
            # SAM.gov sometimes shows different dates on the card vs the
            # detail page (e.g., Mar 17 on card, Mar 16 on detail). The user
            # wants to trust the CARD's published date, which we already verified
            # in get_links_from_current_page(). We just extract what's here for
            # the CSV without throwing the bid away.
            # ── Apply DoD / DLA skip conditions ─────────────────────────
            skip, reason = self._should_skip_bid(data)
            if skip:
                logger.info(f"[SKIP] {reason} | {data['Notice Title']}")
                return None

            return data

        except Exception as e:
            logger.error(f"Error extracting details from {url}: {e}")
            return None

    # ------------------------------------------------------------------
    # Multi-strategy field extractor (BS4 + Selenium fallbacks)
    # ------------------------------------------------------------------
    def _get_field(self, soup: BeautifulSoup, field_id: str, label: str) -> str:
        """
        Try every known strategy to extract the value for a named field.

        Strategy order:
          1. aria-describedby attribute (BS4)
          2. Direct ID → inner text (BS4)
          3. Direct ID → next sibling (BS4)
          4. Direct ID → parent sibling (BS4)
          5. Selenium: CSS [aria-describedby=field_id]
          6. Selenium: CSS [id=field_id] inner text
          7. XPath label-value pairs (Selenium) using the human label
          8. Definition list dt/dd pairs (BS4)
          9. _find_field label-text search (BS4)
         10. Regex on full page text
        """
        # ── BS4 strategies ──────────────────────────────────────────────
        # 1: aria-describedby
        val = soup.find(attrs={"aria-describedby": field_id})
        if val:
            t = val.get_text(strip=True)
            if t:
                return t

        # 2: element with that ID – use its own text content
        el_id = soup.find(id=field_id)
        if el_id:
            t = el_id.get_text(strip=True)
            if t and t.lower() != label.lower():
                return t

        # 3: ID → next sibling
        if el_id:
            sib = el_id.find_next_sibling()
            if sib:
                t = sib.get_text(strip=True)
                if t:
                    return t
            # 4: ID → parent → next sibling
            parent = el_id.parent
            if parent:
                ps = parent.find_next_sibling()
                if ps:
                    t = ps.get_text(strip=True)
                    if t:
                        return t

        # 8: definition list <dt>/<dd>
        if label:
            for dt in soup.find_all("dt"):
                if label.lower() in dt.get_text(strip=True).lower():
                    dd = dt.find_next_sibling("dd")
                    if dd:
                        t = dd.get_text(strip=True)
                        if t:
                            return t

        # 9: generic label text search (BS4)
        if label:
            found = self._find_field(soup, label)
            if found:
                return found

        # ── Selenium strategies ─────────────────────────────────────────
        # 5: aria-describedby via CSS
        try:
            els = self.driver.find_elements(
                By.CSS_SELECTOR, f'[aria-describedby="{field_id}"]'
            )
            for e in els:
                t = e.text.strip()
                if t:
                    return t
        except Exception:
            pass

        # 6: element ID via CSS
        try:
            els = self.driver.find_elements(By.CSS_SELECTOR, f'[id="{field_id}"]')
            for e in els:
                t = e.text.strip()
                if t and t.lower() != label.lower():
                    return t
        except Exception:
            pass

        # 7: XPath label→value patterns
        if label:
            label_escaped = label.replace("'", "\\'")
            xpaths = [
                f"//span[normalize-space(text())='{label_escaped}']/following-sibling::span[1]",
                f"//span[normalize-space(text())='{label_escaped}']/parent::*/following-sibling::*[1]",
                f"//dt[contains(normalize-space(text()),'{label_escaped}')]/following-sibling::dd[1]",
                f"//*[contains(@class,'label') and contains(normalize-space(text()),'{label_escaped}')]/following-sibling::*[1]",
                f"//*[contains(@class,'key') and contains(normalize-space(text()),'{label_escaped}')]/following-sibling::*[1]",
                f"//*[normalize-space(text())='{label_escaped}']/parent::*//*[contains(@class,'value')]",
            ]
            for xp in xpaths:
                try:
                    els = self.driver.find_elements(By.XPATH, xp)
                    for e in els:
                        t = e.text.strip()
                        if t and t.lower() not in (label.lower(), ""):
                            return t
                except Exception:
                    continue

        # 10: regex on full page body text
        if label:
            found = self._regex_from_page_text(label)
            if found:
                return found

        return ""

    # ------------------------------------------------------------------
    # Regex helpers for full-page text fallback
    # ------------------------------------------------------------------
    def _regex_from_page_text(self, label: str) -> str:
        """
        Scan the rendered page body text for 'LabelValue' proximity patterns.
        Returns the text immediately after the label on the same logical line.
        """
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            escaped = re.escape(label)
            # Match label followed by optional whitespace then value on same or next line
            m = re.search(
                escaped + r"[:\s]*([^\n]{2,120})",
                body_text,
                re.IGNORECASE,
            )
            if m:
                candidate = m.group(1).strip()
                # Exclude values that look like another label (all caps / very short)
                if candidate and len(candidate) > 1:
                    return candidate
        except Exception:
            pass
        return ""

    def _regex_date_from_page(self, label: str) -> str:
        """
        Look for a date pattern (e.g. 'Mar 15, 2026') following the given label
        in the full rendered page text.
        """
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            pattern = self._date_cfg.get(
                "card_date_regex", r"([A-Z][a-z]{2}\s\d{1,2},\s\d{4})"
            )
            escaped_label = re.escape(label)
            m = re.search(
                escaped_label + r".*?" + pattern,
                body_text,
                re.IGNORECASE | re.DOTALL,
            )
            if m:
                return m.group(1).strip()
        except Exception:
            pass
        return ""

    # ------------------------------------------------------------------
    # Description extractor
    # ------------------------------------------------------------------
    # Compiled regex used as the PRIMARY description strategy.
    # Matches everything between "\nDescription\n" and the next known
    # section heading, capturing the full paragraph text of the description.
    # Stops at: Contact Information, Contracting Office, Attachments/Links,
    #           Place of Performance, History, Award Notices.
    _DESC_RE = re.compile(
        r'\nDescription\s*\n([\s\S]+?)(?=\n(?:'
        r'Contact Information|Contracting Office|Attachments[\s/\-]*Links|'
        r'Place of Performance|History|Award Notices'
        r')|\Z)',
        re.IGNORECASE,
    )

    # JavaScript injected into the page to collect ONLY the plain-text
    # paragraph content that appears beneath the "Description" heading.
    # It walks nextElementSibling nodes and STOPS the instant it hits any
    # heading tag (h1-h6), so "Contact Information" and every other section
    # header that follows Description are never included.
    # Within each sibling div/section it prefers <p> and <li> tags; if none
    # exist it falls back to direct text nodes (skipping heading children).
    _JS_DESC_COLLECT = """
        return (function(heading) {
            var HEADING_TAGS = ['H1','H2','H3','H4','H5','H6'];
            var parts = [];

            function collectText(el) {
                // Collect visible text from el while skipping heading children
                var out = [];
                el.childNodes.forEach(function(node) {
                    if (node.nodeType === 3) {                   // text node
                        var t = node.textContent.trim();
                        if (t) out.push(t);
                    } else if (node.nodeType === 1) {            // element node
                        if (HEADING_TAGS.indexOf(node.tagName) !== -1) return; // skip sub-heading
                        var t = (node.innerText || node.textContent || '').trim();
                        if (t) out.push(t);
                    }
                });
                return out.join(' ').trim();
            }

            var sib = heading.nextElementSibling;
            while (sib) {
                // Stop if we've hit the next section heading
                if (HEADING_TAGS.indexOf(sib.tagName) !== -1) break;

                // Prefer <p> / <li> descendants (pure paragraph content)
                var pEls = sib.querySelectorAll('p, li');
                if (pEls.length) {
                    pEls.forEach(function(p) {
                        var t = (p.innerText || p.textContent || '').trim();
                        if (t) parts.push(t);
                    });
                } else {
                    var t = collectText(sib);
                    if (t) parts.push(t);
                }
                sib = sib.nextElementSibling;
            }

            // Fallback: dive one level into the first sibling if nothing found yet
            if (!parts.length && heading.nextElementSibling) {
                var container = heading.nextElementSibling;
                var pEls = container.querySelectorAll('p, li');
                if (pEls.length) {
                    pEls.forEach(function(p) {
                        var t = (p.innerText || p.textContent || '').trim();
                        if (t) parts.push(t);
                    });
                } else {
                    var t = collectText(container);
                    if (t) parts.push(t);
                }
            }

            return parts.join(' ').trim();
        })(arguments[0]);
    """

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """
        Extracts the Description section text from a SAM.gov detail page.

        Strategy order (first result with len > 5 wins):

          1. CSS containers — scroll element into view first so Angular renders
             it, then read Selenium's .text (already filters invisible nodes).
             Known containers: sam-display-description .usa-prose, #description…
             Heading prefix ("Description") stripped; text cut at next section.

          2. Body-text regex (_DESC_RE) — scroll to 40% of page height, get the
             full rendered body text, run the compiled regex that captures
             everything between "\nDescription\n" and the next section heading.

          3. Scroll to the Description heading, wait 1.5 s for Angular to render
             the lazy content, then repeat Strategy 2 on freshly fetched text.

          4. JS sibling-walk — traverse nextElementSibling from the heading,
             stop at any h1-h6, prefer <p>/<li> text inside each sibling.

          5. BS4 heading walk — same logic as 4 but on static HTML from
             driver.page_source (no JavaScript needed).
        """
        label       = self._desc_label   # "Description"
        label_upper = label.upper()

        _BREAK_WORDS = [
            "\ncontact information",
            "\ncontracting office",
            "\nattachments/links",
            "\nattachments",
            "\nplace of performance",
            "\nhistory",
            "\naward notices",
        ]

        def _cut_at_next_section(text: str) -> str:
            """Remove everything from the next section heading onward."""
            low = text.lower()
            cutoff = len(text)
            for bw in _BREAK_WORDS:
                idx = low.find(bw)
                if 0 < idx < cutoff:
                    cutoff = idx
            return text[:cutoff].strip()

        def _strip_heading_prefix(text: str) -> str:
            """Remove a leading 'Description' label from the top of the text."""
            if text.lower().startswith(label.lower()):
                text = text[len(label):].lstrip(" :\n\r\t-")
            return text.strip()

        # ── Strategy 1: CSS containers – scroll into view then read .text ─
        # This is the most targeted approach: it hits exactly the element
        # SAM.gov uses for description content and uses Selenium's rendered
        # text (no hidden / off-screen nodes included).
        for sel in self._desc_selectors:
            try:
                els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                for e in els:
                    try:
                        # Scroll the element into the viewport so Angular
                        # finishes rendering its lazy content.
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block:'center'});", e
                        )
                        time.sleep(1.0)
                        text = e.text.strip()
                        if not text:
                            continue
                        text = _strip_heading_prefix(text)
                        text = _cut_at_next_section(text)
                        if len(text) > 5:
                            return text[:5000]
                    except Exception:
                        continue
            except Exception:
                continue

        # ── Strategy 2: Body-text regex after scrolling to 40% height ────
        # Scrolling ensures the description section has been rendered by
        # Angular before we read the page's full visible text.
        try:
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight * 0.4);"
            )
            time.sleep(1.0)
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            m = self._DESC_RE.search(body_text)
            if m:
                candidate = m.group(1).strip()
                if len(candidate) > 5:
                    return candidate[:5000]
        except Exception:
            pass

        # ── Strategy 3: Scroll TO the Description heading, then re-regex ─
        # For pages where the description is below the fold and lazy-loaded.
        try:
            h_el = self.driver.find_element(
                By.XPATH,
                f"//*[normalize-space(text())='{label}' or "
                f"normalize-space(text())='{label_upper}']",
            )
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior:'smooth', block:'center'});",
                h_el,
            )
            time.sleep(1.5)
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            m = self._DESC_RE.search(body_text)
            if m:
                candidate = m.group(1).strip()
                if len(candidate) > 5:
                    return candidate[:5000]
        except Exception:
            pass

        # ── Strategy 4: JS sibling-walk from heading element ─────────────
        heading_xpaths = [
            f"//h2[normalize-space(text())='{label}']",
            f"//h3[normalize-space(text())='{label}']",
            f"//h4[normalize-space(text())='{label}']",
            f"//h2[normalize-space(text())='{label_upper}']",
            f"//h3[normalize-space(text())='{label_upper}']",
            f"//*[contains(@class,'section-title') and normalize-space(text())='{label}']",
        ]
        for xp in heading_xpaths:
            try:
                for h_el in self.driver.find_elements(By.XPATH, xp):
                    try:
                        result = self.driver.execute_script(
                            self._JS_DESC_COLLECT, h_el
                        )
                        text = (result or "").strip()
                        if len(text) > 5:
                            return text[:5000]
                    except Exception:
                        continue
            except Exception:
                continue

        # ── Strategy 5: BS4 heading walk ─────────────────────────────────
        fresh_soup = BeautifulSoup(self.driver.page_source, "html.parser")
        h_tags = ["h1", "h2", "h3", "h4", "h5"]
        for tag in h_tags:
            for h_el in fresh_soup.find_all(tag):
                if h_el.get_text(strip=True).lower() == label.lower():
                    parts: list[str] = []
                    sib = h_el.find_next_sibling()
                    while sib:
                        if sib.name in h_tags:
                            break
                        for p in sib.find_all(["p", "li"]) or [sib]:
                            t = p.get_text(separator=" ", strip=True)
                            if t:
                                parts.append(t)
                        sib = sib.find_next_sibling()
                    result = " ".join(parts).strip()
                    if len(result) > 5:
                        return result[:5000]

        return ""

    # ------------------------------------------------------------------
    # Generic field fallback – text-search in soup
    # ------------------------------------------------------------------
    def _find_field(self, soup: BeautifulSoup, label: str) -> str:
        label_tag = soup.find(
            "label", string=lambda x: x and label.lower() in x.lower()
        )
        if label_tag:
            sib = label_tag.find_next_sibling()
            if sib:
                return sib.get_text(strip=True)
            inp = label_tag.find_next("input")
            if inp:
                return inp.get("value", "")

        element = soup.find(
            string=lambda x: x and x.strip().lower() == label.lower()
        )
        if element:
            parent = element.parent
            next_el = parent.find_next_sibling()
            if next_el:
                text = next_el.get_text(strip=True)
                if text:
                    return text
            grand = parent.parent
            if grand:
                full_text = grand.get_text(" ", strip=True)
                if label in full_text:
                    val = full_text.split(label)[1].strip()
                    return val[:50].strip()

        return ""

    # ------------------------------------------------------------------
    # Debug helper
    # ------------------------------------------------------------------
    def _save_debug(self, filename: str):
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Instant CSV helpers  – file created immediately, rows written live
    # ------------------------------------------------------------------
    def _resolve_output_dir(self) -> Path:
        """Return the absolute output directory, creating it if needed."""
        cfg_dir    = self._csv_cfg.get("output_dir", "sam_output")
        output_dir = Path(cfg_dir)
        if not output_dir.is_absolute():
            output_dir = Path.cwd() / output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _init_csv(self) -> Path:
        """
        Create the CSV file RIGHT NOW with the header row.
        Called once at the very start of run() so the file exists on disk
        immediately – even before a single bid is scraped.

        Uses the SAME directory-resolution logic as save_csv() so both
        methods always write to the same folder regardless of cwd() timing.
        Returns the absolute Path stored in self._csv_filepath.
        """
        columns = self._csv_cfg.get("columns", [
            "Notice Title", "Notice ID", "Department/Ind. Agency",
            "Description", "Subtier", "Updated Date",
            "Date Offers Due", "Published Date", "Office",
        ])

        # ── Resolve output directory (identical to save_csv logic) ───────
        cfg_dir    = self._csv_cfg.get("output_dir", "sam_output")
        output_dir = Path(cfg_dir)
        if not output_dir.is_absolute():
            output_dir = Path.cwd() / output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        filepath = output_dir / self._output_filename

        # Write header row (overwrites any leftover file from a previous run)
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()

        abs_path = filepath.resolve()
        logger.info(f"CSV created (headers written): {abs_path}")
        print(f"\n[SAM] CSV file created - rows are written instantly as they are scraped:\n"
              f"      {abs_path}\n")
        return filepath

    def _append_row(self, row: dict) -> None:
        """
        Append a single extracted row to the CSV file instantly.
        Because this opens the file in append mode on every call the data
        is flushed to disk immediately – a Ctrl-C at any point will still
        leave all previously scraped rows intact in the file.
        """
        if not self._csv_filepath:
            return
        columns = self._csv_cfg.get("columns", list(row.keys()))
        with open(self._csv_filepath, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
            writer.writerow(row)

    # ------------------------------------------------------------------
    # Dynamic CSV filename  →  sam-2026-03-16 & 1-12am.csv
    # ------------------------------------------------------------------
    def get_csv_filename(self) -> str:
        now = datetime.now()
        date_part = now.strftime("%Y-%m-%d")
        hour      = int(now.strftime("%I"))   # 1-12, no leading zero
        minute    = now.strftime("%M")
        ampm      = now.strftime("%p").lower()
        prefix    = self._csv_cfg.get("filename_prefix", "sam-")
        return f"{prefix}{date_part} & {hour}-{minute}{ampm}.csv"

    # ------------------------------------------------------------------
    # Main run loop
    # ------------------------------------------------------------------
    def run(self, max_records: int = None) -> str | None:
        if max_records is None:
            max_records = self._scraping.get("max_records", 1000)

        # ── Generate filename / init CSV (skipped in DB-only mode) ───────────
        self._output_filename = self.get_csv_filename()
        if self.skip_csv:
            self._csv_filepath = None   # no file I/O — data goes to DB via callback
        else:
            self._csv_filepath = self._init_csv()   # file exists on disk from this point

        extracted_count     = 0
        page                = 1
        scraped_urls: set   = set()
        scraped_titles: set = set()

        # ── Stopping rule ───────────────────────────────────────────────
        # We ONLY stop when SAM.gov itself has no more cards to show
        # (WebDriverWait times out = genuine end of results).
        # We NEVER stop because our client-side filters (version count,
        # DoD/DLA, Published Date) eliminated all cards on a page –
        # matching bids may exist on any later page.
        # ────────────────────────────────────────────────────────────────

        while extracted_count < max_records:
            # ── Stop check ───────────────────────────────────────────────────
            if self._stop_event and self._stop_event.is_set():
                logger.info(
                    f"Stop signal received - saving {extracted_count} partial "
                    f"rows and exiting."
                )
                break

            logger.info(f"-- Page {page} ------------------------------------------")

            if page == 1:
                # ── Page 1: navigate directly via URL ────────────────────
                # Only page 1 can be reached via driver.get().  SAM.gov's
                # Angular SPA redirects any direct ?page=N (N>1) back to
                # page 1 because there is no active search session yet.
                page_url = self._build_page_url(1)
                self.driver.get(page_url)
                time.sleep(2)   # Angular routing startup

                # Wait for result cards
                has_cards = False
                try:
                    WebDriverWait(
                        self.driver, self._timeouts.get("results_wait", 20)
                    ).until(
                        lambda d: d.find_elements(
                            By.CSS_SELECTOR,
                            self._selectors.get(
                                "results_container_css",
                                "sds-search-result-list, .sds-card",
                            ),
                        )
                    )
                    has_cards = True
                except Exception:
                    pass

                if not has_cards:
                    logger.info("Page 1: no cards rendered - end of results.")
                    break

                # ── Apply UI date-range filter on the first page load ─────
                # The URL params already told SAM.gov the date range server-
                # side; filling the date-picker inputs confirms the filter
                # in the Angular state so it persists across page clicks.
                self._apply_ui_date_filters()

            else:
                # ── Page 2+: click the Next button to stay in-session ────
                # We must use the UI button so that SAM.gov's Angular router
                # knows about the existing session / cursor state.
                # _click_next_page() blocks until cards appear on the new
                # page (or returns False when the button is disabled /
                # missing = genuine end of results).
                if not self._click_next_page(page - 1):
                    break

                # Sanity-check: confirm the page indicator matches expectation
                if not self._verify_on_correct_page(page):
                    break

            # ── Card-level filtering (version / title / Published Date) ─
            candidates = self.get_links_from_current_page()
            logger.info(
                f"Page {page}: {len(candidates)} candidate(s) after card filters."
            )
            # If every card was filtered client-side, check whether we have
            # moved past the date window before deciding to continue.
            # Since SAM.gov sorts by -modifiedDate, once every card on a page
            # has Updated Date < filter date no later page can contain
            # matching bids — stop immediately instead of paging forever.
            if not candidates:
                if self._is_past_date_window():
                    break
                page += 1
                continue

            # ── Visit each candidate's detail page ──────────────────────
            for item in candidates:
                if extracted_count >= max_records:
                    break

                # ── Per-bid stop check ───────────────────────────────────
                # Checked here so Stop responds within ~1 bid (~10 s)
                # instead of waiting for all candidates on the page.
                if self._stop_event and self._stop_event.is_set():
                    logger.info(
                        f"Stop signal received during bid extraction - "
                        f"saving {extracted_count} partial rows and exiting."
                    )
                    break

                bid_url   = item["url"]
                bid_title = item["title"]

                if bid_url in scraped_urls or bid_title in scraped_titles:
                    logger.info(f"[DUP] {bid_title}")
                    scraped_urls.add(bid_url)
                    continue

                logger.info(f"Scraping -> {bid_title}")

                # Open in new tab to preserve the search page's internal state
                self.driver.execute_script("window.open('');")
                self.driver.switch_to.window(self.driver.window_handles[1])

                details = None
                try:
                    details = self.extract_details(
                        bid_url,
                        pre_updated_date=item.get("pre_extracted_updated_date", ""),
                    )
                except Exception as _detail_err:
                    _emsg = str(_detail_err).lower()
                    # Browser was closed (manually or due to stop) — exit cleanly
                    if any(k in _emsg for k in (
                        "invalid session", "disconnected",
                        "not connected", "no such window",
                        "browser has closed",
                    )):
                        logger.warning(
                            f"Browser session lost - saving {extracted_count} "
                            f"partial rows and exiting."
                        )
                        if self._stop_event:
                            self._stop_event.set()
                        break
                    logger.warning(f"Error extracting details from {bid_url}: {_detail_err}")
                finally:
                    # Close the tab and switch back; ignore errors if session is gone
                    try:
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
                    except Exception:
                        pass

                if details:
                    # Attach the card-level repeat count to the detail dict
                    # so it flows through to the DB callback and CSV row.
                    details["bid_repeat_count"] = item.get("bid_repeat_count", 0)
                    self.data.append(details)
                    if not self.skip_csv:
                        self._append_row(details)
                    if self._on_bid_extracted:
                        try:
                            self._on_bid_extracted(details)
                        except Exception as _cb_err:
                            logger.warning(f"on_bid_extracted callback failed: {_cb_err}")
                    scraped_urls.add(bid_url)
                    scraped_titles.add(bid_title)
                    extracted_count += 1
                    _dest = self._csv_filepath.name if self._csv_filepath else "database"
                    logger.info(f"[OK] {extracted_count} rows saved -> {_dest}")

            page += 1

        # All rows already written live via _append_row().
        # Log the final summary and return the absolute file path.
        abs_path = self._csv_filepath.resolve() if self._csv_filepath else None
        if abs_path:
            print(f"\n[SAM] Scraping complete - {extracted_count} rows saved to:\n"
                  f"      {abs_path}\n")
            logger.info(f"Scraping complete - {extracted_count} rows -> {abs_path}")
        self.close()
        return str(abs_path) if abs_path else None

    # ------------------------------------------------------------------
    # CSV save  →  fixed filename set in run(), 9-column order
    # ------------------------------------------------------------------
    def save_csv(self) -> str | None:
        """
        Writes self.data to a CSV file and returns the absolute path.

        Key guarantees:
          • The output directory (sam.csv.output_dir in config.yml) is created
            automatically if it does not yet exist.
          • A FILE IS ALWAYS WRITTEN even when self.data is empty – an empty
            CSV with the correct headers is created so the file is always
            visible in the filesystem.
          • The absolute path is both logged AND printed to stdout so you can
            always see exactly where the file was saved.
        """
        # ── Resolve output directory and ensure it exists ────────────────
        cfg_dir     = self._csv_cfg.get("output_dir", "sam_output")
        output_dir  = Path(cfg_dir)
        if not output_dir.is_absolute():
            # Make it relative to the project root (where config.yml lives)
            output_dir = Path.cwd() / output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # ── Use the filename fixed at run() start (prevents multiple files)
        filename = self._output_filename or self.get_csv_filename()
        filepath = output_dir / filename

        # ── Build the DataFrame (headers only when there is no data) ─────
        preferred  = self._csv_cfg.get("columns", [])
        if not self.data:
            # Always create the file with correct headers even if empty
            df = pd.DataFrame(columns=preferred)
            try:
                df.to_csv(filepath, index=False, encoding="utf-8-sig")
                abs_path = filepath.resolve()
                logger.warning(
                    f"No rows passed all filters - empty CSV created -> {abs_path}"
                )
                print(f"\n[SAM] [!] No bids matched all filters. "
                      f"Empty CSV created:\n      {abs_path}\n")
            except Exception as e:
                logger.error(f"Error creating empty CSV: {e}")
            return str(filepath)

        df    = pd.DataFrame(self.data)
        extra = [c for c in df.columns if c not in preferred]
        df    = df[[c for c in preferred + extra if c in df.columns]]

        # ── Write CSV ────────────────────────────────────────────────────
        try:
            df.to_csv(filepath, index=False, encoding="utf-8-sig")
            abs_path = filepath.resolve()
            logger.info(f"CSV saved -> {abs_path}  ({len(df)} rows)")
            print(f"\n[SAM] CSV saved ({len(df)} rows):\n      {abs_path}\n")
            return str(abs_path)

        except PermissionError:
            # File is open in Excel – write a timestamped backup instead
            ts       = datetime.now().strftime(
                self._csv_cfg.get("timestamp_format", "%Y%m%d_%H%M%S")
            )
            backup   = output_dir / f"{self._csv_cfg.get('backup_prefix', 'sam-backup-')}{ts}.csv"
            df.to_csv(backup, index=False, encoding="utf-8-sig")
            abs_path = backup.resolve()
            logger.warning(f"Original file open - backup saved -> {abs_path}")
            print(f"\n[SAM] [!] Original file was open. Backup saved:\n      {abs_path}\n")
            return str(abs_path)

        except Exception as e:
            logger.error(f"Error saving CSV: {e}")
            print(f"\n[SAM] [ERR] Failed to save CSV: {e}\n")
            return None

    def close(self):
        if self.driver:
            self.driver.quit()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SAM.gov Scraper – date-filter only")
    parser.add_argument("--headless",    action="store_true", help="Run headless Chrome")
    parser.add_argument("--date-filter", default=None,        help="Start date YYYY-MM-DD")
    parser.add_argument("--max-records", type=int, default=None)
    args = parser.parse_args()

    scraper = SAMGovScraper(headless=args.headless, date_filter=args.date_filter)
    try:
        scraper.run(max_records=args.max_records)
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
        # Rows were already written to disk live via _append_row(), so the
        # CSV contains everything scraped up to this point. No extra save needed.
        if scraper._csv_filepath:
            abs_path = scraper._csv_filepath.resolve()
            print(f"\n[SAM] [!] Stopped by user. Data saved to:\n      {abs_path}\n")
        scraper.close()
        scraper.close()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        scraper.save_csv()
        scraper.close()
