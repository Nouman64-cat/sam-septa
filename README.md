# BidScraper Pro

Scrapes federal solicitations from **SAM.gov** and vendor quotes from **SEPTA**, saves to PostgreSQL, exports Excel.

## Prerequisites

- Node.js 18+, Python 3.12+, PostgreSQL 14+, Google Chrome, Git
- ChromeDriver is auto-downloaded — no manual install needed

## Setup

```bash
git clone <your-repo-url> sam-septa

# Backend env
cd sam-septa/server
cp .env.example .env        # Windows: copy .env.example .env

# Frontend env
cd ../client
cp .env.example .env
```

**`server/.env`**
```env
DATABASE_URL=postgresql://username:password@localhost:5432/sam-septa-db
SEPTA_USERNAME=your_septa_username
SEPTA_PASSWORD=your_septa_password
```

**`client/.env`**
```env
NEXT_PUBLIC_SERVER_URL=http://127.0.0.1:8001
```

## Database

```bash
psql -U postgres -c 'CREATE DATABASE "sam-septa-db";'
```
Tables are created automatically on first server start.

## Run Backend

```bash
cd server
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/macOS
pip install -r requiremnets.txt
uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

## Run Frontend

```bash
cd client
npm install
npm run dev
```

Open **http://localhost:3000**

## Reset Database (schema changes only ⚠️ deletes all data)

```bash
cd server && python migrate.py
```

## Troubleshooting

| Error | Fix |
|-------|-----|
| `No module named 'fastapi'` | Activate venv |
| PostgreSQL connection refused | Start PostgreSQL service |
| `password authentication failed` | Fix password in `.env` |
| `database does not exist` | Run the `CREATE DATABASE` command above |
| `Chrome failed to start` | Install/update Chrome |
| SEPTA `Login failed` | Check credentials in `.env` |
| Column not found / schema mismatch | `python migrate.py` |

---
*FastAPI · Next.js 16 · PostgreSQL · Selenium*
