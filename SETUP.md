# Setup

## Windows CMD

```cmd
cd C:\path\to\letmesee
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
npm install
copy .env.example .env
notepad .env
```

Add the real `TINYFISH_API_KEY` to `.env`.

Terminal 1:

```cmd
python -m uvicorn api.index:app --reload
```

Terminal 2:

```cmd
npm run dev
```

Open `http://localhost:5173`.

## Tests

```cmd
python -m py_compile api\index.py src\config.py src\scraper.py src\matcher.py
python -c "from src.config import UserPreferences; print(UserPreferences(role='Backend Engineer', location='Remote'))"
npm run build
```

Health endpoint: `http://127.0.0.1:8000/api/health`.

## ⚠️ Deployment note

Vercel routing for a Vite static build and FastAPI Python function must be verified in a preview deployment. If the combined deployment does not route `/api/search` to FastAPI correctly, deploy the Python API separately (e.g. a Python-capable host) and set `VITE_API_BASE_URL` to that API origin before building the frontend.
