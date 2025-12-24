# BI Agent System

Text-to-BI assistant with a FastAPI backend and a dashboard UI. The backend routes
natural-language questions to SQL/insight/report generators and serves a static
dashboard if frontend assets are present.

## Project Layout

- `text-bi-llm-backend/` - FastAPI API server, services, schemas, and tests.
- `text-bi-llm-backend/frontend/` - dashboard assets and React sources.
- `app/` - standalone scripts (not used by the FastAPI app by default).

## Quick Start (Backend)

```bash
cd text-bi-llm-backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Create `text-bi-llm-backend/.env`:

```bash
OPENAI_API_KEY=your_key
SQLALCHEMY_DATABASE_URI=mysql+pymysql://user:pass@host:3306/dbname
OPENAI_BASE_URL=https://api.openai.com/v1
```

Run the API server:

```bash
uvicorn app.main:app --reload
```

If `text-bi-llm-backend/frontend/index.html` exists, it will be served at
`http://localhost:8000/`.

## Quick Start (Frontend)

```bash
cd text-bi-llm-backend/frontend
npm install
npm start
```

This starts the dev server at `http://localhost:3000`.

## API Endpoints

- `POST /api/v1/ask` - main text-to-BI endpoint.
- `POST /api/v1/po/generate_po` - generate PO PDFs.
- `GET /api/v1/po/download_po?file_name=...` - download generated PDFs.

Example request:

```bash
curl -X POST http://localhost:8000/api/v1/ask ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"Show open PO status\"}"
```

## Notes

- PO PDFs are written to `C:/po_gen` (see `text-bi-llm-backend/app/api/v1/endpoints/po.py`).
- Configure DB access via `SQLALCHEMY_DATABASE_URI` in `.env`.
