# SAM-SEPTA Scraper

This is a full-stack tool for scraping government bids (SAM.gov, SEPTA, Unison, DIBBS), equipped with a smart 4-layer evaluation pipeline that automatically rejects/passes bids.

## Requirements
To run the automated bid evaluation (Layer 4), you must have **Ollama** installed on your system with the **Llama 3** model pulled:
```bash
ollama pull llama3
```

## Running the Application

Once you have completed the initial setup, you can start the application by running the client and server concurrently in two separate terminal windows:

**1. Start the Server (Backend)**
```bash
cd server
.venv\Scripts\activate  # On Windows
uvicorn main:app --reload
```

**2. Start the Client (Frontend)**
```bash
cd client
npm run dev
```
The application will be available at [http://localhost:3000](http://localhost:3000).

---

### Setup Instructions
If you have not set up the project yet, please refer to the respective setup guides:
- **Server setup:** See [`server/README.md`](server/README.md)
- **Client setup:** See [`client/README.md`](client/README.md)
