// Tab Switching Logic
document.querySelectorAll('.tab-btn').forEach(button => {
    button.addEventListener('click', () => {
        // Remove active class from all buttons and content
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

        // Add active class to clicked button
        button.classList.add('active');

        // Show corresponding content
        const tabId = button.getAttribute('data-tab');
        document.getElementById(`${tabId}-content`).classList.add('active');

        // Reset status message when switching tabs
        const status = document.getElementById('status');
        const downloadSection = document.getElementById('downloadSection');
        status.textContent = '';
        downloadSection.classList.add('hidden');
    });
});

// Generic Scrape Function
async function handleScrape(url, body, buttonId, loaderId, buttonTextOriginal) {
    const btn = document.getElementById(buttonId);
    const btnText = btn.querySelector('.btn-text');
    const loader = document.getElementById(loaderId);
    const status = document.getElementById('status');
    const downloadSection = document.getElementById('downloadSection');
    const downloadLink = document.getElementById('downloadLink');

    // Reset State
    downloadSection.classList.add('hidden');
    status.textContent = 'Initializing scraper... (This may take a minute)';
    status.style.color = '#94a3b8';

    // UI Loading State
    btn.disabled = true;
    btnText.textContent = 'Processing...';
    loader.style.display = 'block';

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(body)
        });

        const data = await response.json();

        if (data.success) {
            status.textContent = 'Scraping Completed Successfully!';
            status.style.color = '#4ade80'; // Success green

            // Setup download link
            downloadLink.href = `/download/${data.filename}`;
            downloadSection.classList.remove('hidden');
        } else {
            status.textContent = `Error: ${data.error}`;
            status.style.color = '#f87171'; // Error red
        }

    } catch (error) {
        status.textContent = `Network Error: ${error.message}`;
        status.style.color = '#f87171';
    } finally {
        // Reset Button
        btn.disabled = false;
        btnText.textContent = buttonTextOriginal;
        loader.style.display = 'none';
    }
}

// SAM Scraper Listener
document.getElementById('scrapeSamBtn').addEventListener('click', () => {
    const naicsCode = document.getElementById('naics_code').value.trim();
    const dateFilter = document.getElementById('date_filter').value;
    handleScrape('/scrape', { search_query: naicsCode, date_filter: dateFilter }, 'scrapeSamBtn', 'samLoader', 'Scrape SAM Data');
});

// SEPTA Scraper Listener
document.getElementById('scrapeSeptaBtn').addEventListener('click', () => {
    const dateFilter = document.getElementById('septa_date_filter').value;
    handleScrape('/scrape_septa', { date_filter: dateFilter }, 'scrapeSeptaBtn', 'septaLoader', 'Scrape SEPTA Quotes');
});

// UNISON Scraper Listener
document.getElementById('scrapeUnisonBtn').addEventListener('click', () => {
    const filterBy = document.getElementById('unison_filter').value;
    handleScrape('/scrape_unison', { filter_by: filterBy }, 'scrapeUnisonBtn', 'unisonLoader', 'Scrape Unison Market');
});

// DIBBS Scraper Listener
document.getElementById('scrapeDibbsBtn').addEventListener('click', () => {
    // No params needed, just run it
    handleScrape('/scrape_dibbs', {}, 'scrapeDibbsBtn', 'dibbsLoader', 'Scrape DIBBS');
});
