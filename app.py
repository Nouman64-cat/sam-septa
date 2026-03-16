from flask import Flask, render_template, request, jsonify, send_file
import os
import time
import importlib.util
from sam_scraper import SAMGovScraper

# Import Septa Scraper
# septa_scrapper.py is in the same directory
try:
    from septa_scrapper import Config as SeptaConfig, BrowserManager as SeptaBrowser, SeptaPortal, DataExporter
except ImportError:
    print("Error importing Septa scraper modules. Make sure septa_scrapper.py works.")

# Import Unison Scraper (handling hyphen in filename)
try:
    spec = importlib.util.spec_from_file_location("unison_module", "unison-scraper.py")
    unison_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(unison_module)
    UnisonMarketplaceScraper = unison_module.UnisonMarketplaceScraper
except Exception as e:
    print(f"Error importing Unison scraper: {e}")

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.json
    search_query = data.get('search_query', '')
    date_filter = data.get('date_filter', None)
    
    # Run Sam.gov Scraper
    try:
        scraper = SAMGovScraper(headless=False, search_query=search_query, date_filter=date_filter)
        csv_file = scraper.run(max_records=1000)
        
        if csv_file and os.path.exists(csv_file):
            return jsonify({'success': True, 'filename': csv_file})
        else:
            return jsonify({'success': False, 'error': 'No data extracted or file not created.'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/scrape_septa', methods=['POST'])
def scrape_septa():
    try:
        data = request.json
        date_filter = data.get('date_filter')
        
        # Initialize Septa Scraper components
        config = SeptaConfig()
        browser_manager = SeptaBrowser(config)
        
        # Use headless=True for server environment, or False if user wants to see it
        # User requirement: "works smoothly". Headless is usually smoother/less intrusive.
        if not browser_manager.setup_driver(headless=True):
             return jsonify({'success': False, 'error': 'Failed to setup browser for Septa Scraper'})
             
        portal = SeptaPortal(browser_manager, config)
        
        # Run execution flow
        if not portal.login():
            browser_manager.close_driver()
            return jsonify({'success': False, 'error': 'Septa Login Failed'})
            
        if not portal.navigate_to_open_quotes():
            browser_manager.close_driver()
            return jsonify({'success': False, 'error': 'Septa Navigation Failed'})
            
        portal.apply_date_filter(date_filter) # Attempt date filter, continue even if fails potentially
        
        quotes = portal.scrape_all_pages()
        
        # Save to CSV using DataExporter for consistent formatting
        csv_filename = config.get_csv_filename()
        csv_path = config.get_csv_path()
        
        if DataExporter.export_to_csv(quotes, csv_path):
             pass # Success
        else:
             # If export failed (e.g. no quotes), we still want to handle it
             pass 
        
        browser_manager.close_driver()
        
        if os.path.exists(csv_path):
             return jsonify({'success': True, 'filename': csv_filename})
        else:
             return jsonify({'success': False, 'error': 'No quotes imported or CSV creation failed.'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/scrape_unison', methods=['POST'])
def scrape_unison():
    try:
        data = request.json
        filter_by = data.get('filter_by')
        
        scraper = UnisonMarketplaceScraper()
        
        # The Unison scraper prints to stdout and doesn't return data nicely in run_scraper
        # But it saves to a known csv filename format inside the class instance: self.csv_file
        
        # We need to run it.
        # Note: scraper.run_scraper() calls driver.quit() at the end.
        scraper.run_scraper(filter_by=filter_by)
        
        if os.path.exists(scraper.csv_file):
            return jsonify({'success': True, 'filename': scraper.csv_file})
        else:
            return jsonify({'success': False, 'error': 'Unison scraper finished but CSV file not found (maybe no data).'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Import Dibbs Scraper
try:
    spec_dibbs = importlib.util.spec_from_file_location("dibbs_module", "dibbs-scrapper.py")
    dibbs_module = importlib.util.module_from_spec(spec_dibbs)
    spec_dibbs.loader.exec_module(dibbs_module)
    DibbsScraper = dibbs_module.DibbsScraper
except Exception as e:
    print(f"Error importing Dibbs scraper: {e}")

@app.route('/scrape_dibbs', methods=['POST'])
def scrape_dibbs():
    try:
        # Initialize and run Dibbs Scraper
        scraper = DibbsScraper(headless=False) # Or True if preferred, user seems to like seeing it or server mode
        csv_file = scraper.run()
        
        if csv_file and os.path.exists(csv_file):
            return jsonify({'success': True, 'filename': csv_file})
        else:
            return jsonify({'success': False, 'error': 'Dibbs scraper finished but CSV file not found.'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return str(e)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
