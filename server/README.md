# Server Setup

FastAPI backend — runs scrapers, saves to PostgreSQL, streams Excel exports.

## Requirements

Python 3.12+, PostgreSQL 14+, Google Chrome, Git

## Install

### Windows
- Python: https://www.python.org — ✅ check **Add to PATH**
- PostgreSQL: https://www.postgresql.org/download/windows — note the `postgres` password you set
- Chrome: https://www.google.com/chrome

### Linux (Ubuntu/Debian)
```bash
sudo apt install -y python3.12 python3.12-venv postgresql postgresql-contrib
sudo systemctl enable --now postgresql

# Chrome
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" \
  | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update && sudo apt install -y google-chrome-stable
```

> Ubuntu 22.04 or older needs the deadsnakes PPA for Python 3.12:
> `sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt update`

## Database

```bash
# Windows
psql -U postgres -c "CREATE DATABASE \"sam-septa-db\";"

# Linux
sudo -u postgres psql -c 'CREATE DATABASE "sam-septa-db";'
```

## Environment Variables

```bash
cp .env.example .env      # Windows: copy .env.example .env
```

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/sam-septa-db
SEPTA_USERNAME=your_septa_username    # required for SEPTA scraper
SEPTA_PASSWORD=your_septa_password
UNISON_EMAIL=your_email               # optional
UNISON_PASSWORD=your_password         # optional
```

## Virtual Environment & Dependencies

```bash
python -m venv .venv                  # Linux: python3.12 -m venv .venv
.venv\Scripts\activate                # Windows
source .venv/bin/activate             # Linux

pip install -r requiremnets.txt       # note: typo in filename is intentional
```

## Start

```bash
uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

Verify: http://127.0.0.1:8001/ → `{"message":"SAM-SEPTA Scraper API"}`
Swagger UI: http://127.0.0.1:8001/docs

> ⚠️ Always use `--workers 1` in production — the job registry is not shared across workers.

## Run as a Service

### Windows (NSSM — https://nssm.cc)
```cmd
nssm install BidScraperServer
# Path:      C:\projects\sam-septa\server\.venv\Scripts\python.exe
# Arguments: -m uvicorn main:app --host 127.0.0.1 --port 8001
# Start in:  C:\projects\sam-septa\server
nssm start BidScraperServer
```

### Linux (systemd)
```bash
sudo nano /etc/systemd/system/bidscraper.service
```
```ini
[Unit]
Description=BidScraper Pro
After=network.target postgresql.service

[Service]
User=your_username
WorkingDirectory=/home/your_username/sam-septa/server
Environment="PATH=/home/your_username/sam-septa/server/.venv/bin"
ExecStart=/home/your_username/sam-septa/server/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8001
Restart=on-failure

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now bidscraper
sudo journalctl -u bidscraper -f      # logs
```

## Reset Database ⚠️ deletes all data

```bash
python migrate.py
```
Drops and recreates `sam_bids`, `septa_quotes`, `scrape_jobs`. Run after changing `models.py`.

## Stop

```bash
Ctrl + C                              # dev terminal
nssm stop BidScraperServer            # Windows service
sudo systemctl stop bidscraper        # Linux service
```

## Troubleshooting

| Error | Fix |
|-------|-----|
| `No module named 'fastapi'` | Activate venv |
| `Connection refused` (PostgreSQL) | Start PostgreSQL service |
| `password authentication failed` | Update password in `.env`; reset with `ALTER USER postgres PASSWORD 'new';` |
| `database does not exist` | Run the `CREATE DATABASE` command above |
| `Address already in use :8001` | `netstat -ano \| findstr :8001` → `taskkill /PID n /F` (Win) / `lsof -i :8001` → `kill -9 n` (Linux) |
| `Chrome failed to start` | Update Chrome; headless Linux: `sudo apt install xvfb` + `Xvfb :99 &` + `export DISPLAY=:99` |
| SEPTA `Login failed` | Check credentials in `.env`; see `septa_scraper.log` |
| Column not found / schema error | `python migrate.py` |

---
*FastAPI · SQLModel · PostgreSQL · Selenium · Python 3.12+*
