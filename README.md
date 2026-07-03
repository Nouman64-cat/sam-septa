# SAM-SEPTA Bid Scraper & Evaluation Platform

An intelligent, full-stack procurement automation platform designed to scrape, clean, and filter government opportunities from multiple source portals (SAM.gov, SEPTA, Unison, and DIBBS). Equipped with a deterministic NAICS-first 5-step classification pipeline and integrated with local LLMs (Ollama/Llama 3) for advanced service vs. hardware context extraction.

---

## 🏗️ System Architecture

The application is structured as a decoupled full-stack platform:

```mermaid
graph TD
    A[Next.js Client] <-->|REST API / Live Status / Screenshots| B[FastAPI Server]
    B <-->|ORM / SQLModel| C[(PostgreSQL DB)]
    B -->|Selenium WebDriver| D[SAM.gov Portal]
    B -->|Selenium WebDriver| E[SEPTA Vendor Portal]
    B -->|PyMuPDF & python-docx| F[Attachment Extraction]
    B <-->|HTTP API :11434| G[Ollama / Llama 3]
```

*   **Frontend (`client/`)**: Built with **Next.js**, **TypeScript**, and **Tailwind CSS**. It supports live background job progress tracking, real-time Selenium browser screenshot streaming, interactive evaluation rule configuration, and structured spreadsheet downloads.
*   **Backend (`server/`)**: Built with **FastAPI** (Python 3.12+). It uses **SQLModel** / **SQLAlchemy** to connect to **PostgreSQL**. Scrapers run asynchronously in concurrent background threads, and document text (PDF, DOCX, TXT) is processed locally using **PyMuPDF** and **python-docx**.
*   **Intelligent Sieve**: A local **Ollama** instance runs **Llama 3** to perform natural language context validation on ambiguous bids, ensuring minimal GPU overhead through a progressive filtering funnel.

---

## 🧠 Smart Bid Evaluation Funnel (SAM.gov)

When a bid is scraped, its details and attachments (sometimes totaling over 120,000 tokens) are evaluated using a 5-step, high-performance hybrid evaluation funnel. This avoids passing massive documents to the LLM and keeps inference fast and cost-effective.

```mermaid
graph TD
    Start([New Scraped Bid]) --> Step0{Step 0: Kill-Word?}
    Step0 -->|Yes| Reject[REJECT]
    Step0 -->|No| Step1{Step 1: Classify Req}
    Step1 -->|Hardware| Step2[Step 2: Rule A - Pursue]
    Step1 -->|Service| Step3{Step 3: Rule B - Excluded?}
    Step3 -->|Yes| Reject
    Step3 -->|No| Step4{Step 4: Rule C - Allowed?}
    Step4 -->|Yes| Step5{Step 5: Location Gate}
    Step4 -->|No| Step5
    Step5 -->|US Mainland| Pursue[PURSUE]
    Step5 -->|Outside US Mainland / Foreign| Reject
    Step5 -->|No Rule Match & US Mainland| Review[MANUAL REVIEW]
```

### Funnel Steps & Rules

1.  **Step 0: Kill-Word Sieve**
    *   *Action*: Fast Python substring lookup (`in`) on full text and title.
    *   *Triggers*: Instantly rejects bids containing user-defined dealbreakers (e.g., `"idiq"`, `"market research"`, `"rfi"`, `"sources sought"`).
2.  **Step 1: Requirement Type Classification**
    *   *Action*: Determines if the requirement is **HARDWARE** (physical product/material) or **SERVICE**.
    *   *Logic*: NAICS prefix classification (311–339 manufacturing/wholesale defaults to Hardware unless overridden by service keywords; 236–238 construction always maps to Service).
3.  **Step 2: Hardware Sieve (Rule A)**
    *   *Action*: If classified as **HARDWARE**, the bid is instantly set to **PURSUE** (Rule A).
    *   *Exception*: Food/poultry consumables are evaluated under Rule B #15. Location checks are entirely bypassed for hardware.
4.  **Step 3: Excluded Services Sieve (Rule B)**
    *   *Action*: Evaluates services against 20 excluded categories (e.g., R&D, marine vessel refits, general maintenance, lease of equipment).
    *   *Result*: If matched, the bid is instantly **REJECTED** regardless of performance location.
5.  **Step 4 & 5: Allowed Services (Rule C) & Location Gate**
    *   *Action*: Services on the Allowed list (Rule C, e.g., fence, HVAC, door/window, cable installation) are set to **PURSUE** *only* if performed in the **US Mainland** (contiguous 48 states + DC).
    *   *Logic*: Services outside the Mainland (Alaska, Hawaii, Guam, Puerto Rico, foreign bases) or not matching either list are **REJECTED** or flagged for **MANUAL REVIEW**.

### Local LLM (Ollama) Integration
When a service place of performance is ambiguous (e.g., Guam mentioned in a local slice), a regex window extracts a ~250-word context window and submits it to a local Llama 3 instance to classify the scope as Hardware supply (Pass) or Service contract (Reject).

---

## ⚡ Key Features

*   **Multi-Portal Scraping**: Scrape from SAM.gov, SEPTA, Unison, and DIBBS.
*   **Live Browser Streaming**: View real-time base64 screenshots of Selenium's active Chrome instance directly in the web UI.
*   **Interactive Config Panel**: Add or remove Kill Words, Allowed Services (Rule C), or Excluded Services (Rule B) on the fly.
*   **NAICS Code Database**: Built-in reference parser containing searchable 6-digit NAICS codes.
*   **Styled Exports**: Streams customized Excel workbooks (`.xlsx`) using `openpyxl` with consistent styling.
*   **Comprehensive Test Suite**: Evaluation engine validated against 50+ real-world edge cases.

---

## 📂 Repository Layout

```
.
├── client/                     # Next.js Frontend
│   ├── app/
│   │   ├── components/         # UI Components (Forms, Config, Tabs)
│   │   ├── naics/              # NAICS reference tool routing
│   │   ├── sam/                # SAM.gov scraper dashboard routing
│   │   ├── septa/              # SEPTA scraper dashboard routing
│   │   └── page.tsx            # Landing Dashboard
│   ├── package.json
│   └── tsconfig.json
├── server/                     # FastAPI Backend
│   ├── config/                 # Default YAML configurations
│   ├── db/                     # DB session & initialization scripts
│   ├── models/                 # SQLModel / SQLAlchemy schemas
│   ├── routes/                 # API controllers
│   ├── scrappers/              # Scraper packages
│   │   ├── sam/                # SAM.gov crawler & PyMuPDF extractor
│   │   ├── septa/              # Selenium-based SEPTA crawler
│   │   ├── unison/             # Unison crawler
│   │   └── dibbs/              # DIBBS crawler
│   ├── services/               # Background tasks & notifications
│   ├── utils/                  # Styled Excel workbook stream builders
│   ├── main.py                 # FastAPI Gateway entrypoint
│   ├── migrate.py              # Schema reset script
│   ├── migrate_to_new_eval.py  # Rule B / C evaluation seeding script
│   ├── test_evaluator_spec.py  # Validation test harness
│   └── requirements.txt        # Python dependency manifest
└── README.md                   # Project Documentation
```

---

## 🚀 Setup & Installation

### Prerequisites

*   **Python**: Version 3.12+
*   **Node.js**: Version 18+ (with npm)
*   **PostgreSQL**: Version 14+
*   **Google Chrome**: Installed on host (needed for Selenium WebDriver)
*   **Ollama**: Installed and running locally (`ollama pull llama3`)

### 1. Database Setup
Create the target database inside PostgreSQL:
```bash
# Linux
sudo -u postgres psql -c 'CREATE DATABASE "sam-septa-db";'

# Windows
psql -U postgres -c "CREATE DATABASE \"sam-septa-db\";"
```

### 2. Backend Setup
1. Navigate to the server folder:
   ```bash
   cd server
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment template and edit `.env`:
   ```bash
   cp .env.example .env
   ```
   Provide your database URL and credentials:
   ```env
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/sam-septa-db
   SEPTA_USERNAME=your_septa_username
   SEPTA_PASSWORD=your_septa_password
   ```
5. Initialize the database schema and seed evaluation data:
   ```bash
   python migrate.py
   python migrate_to_new_eval.py
   ```

### 3. Frontend Setup
1. Navigate to the client folder:
   ```bash
   cd ../client
   ```
2. Copy the environment template and install dependencies:
   ```bash
   cp .env.example .env
   npm install
   ```
3. Ensure `.env` is pointing to your active backend (usually `http://localhost:8001`).

---

## 🏃 Running the Application

Start both servers concurrently.

**Start Backend Server:**
```bash
cd server
source .venv/bin/activate
uvicorn main:app --port 8001 --reload
```
*   API root: [http://localhost:8001](http://localhost:8001)
*   Interactive Swagger Docs: [http://localhost:8001/docs](http://localhost:8001/docs)

**Start Frontend Client:**
```bash
cd client
npm run dev
```
*   Web Interface: [http://localhost:3000](http://localhost:3000)

---

## 🧪 Testing the Evaluator

The deterministic decision logic is validated via an automated test harness covering the 28 Section 8 spec cases, plus 35 additional bug pattern regression cases.

Run the test suite from the `server` directory:
```bash
python test_evaluator_spec.py
```

All 63 test cases must return `ALL TESTS PASSED ✓`.

---

## 🛠️ Troubleshooting

| Issue | Cause | Resolution |
| :--- | :--- | :--- |
| `Address already in use` | Another process is using port 8001 or 3000 | Find and terminate process: `lsof -i :8001` -> `kill -9 <PID>` |
| `No module named 'fastapi'` | Virtual environment not active | Activate using `source .venv/bin/activate` or `.venv\Scripts\activate` |
| `Chrome failed to start` | Missing Chrome binary / headless Linux issues | Ensure Google Chrome is installed. On headless servers run: `sudo apt install xvfb` + `Xvfb :99 &` + `export DISPLAY=:99` |
| `Login failed` (SEPTA) | Bad credentials | Verify `SEPTA_USERNAME` and `SEPTA_PASSWORD` in `server/.env` |
| Database relation error | Tables missing or out of sync | Run `python migrate.py` and `python migrate_to_new_eval.py` to rebuild database structures |
| `ollama` connection error | Ollama service not running | Run `ollama serve` and make sure you pulled Llama 3 via `ollama pull llama3` |
