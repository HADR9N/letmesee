# letmesee

Job discovery across Naukri, LinkedIn, Indeed, Foundit, Glassdoor, Instahyre, Hirist, Cutshort, and Wellfound. The frontend is React, Vite, and TypeScript; the API is FastAPI and TinyFish.

## Run locally

Requirements: Node.js 20+ and Python 3.11+.

1. Install frontend packages with `npm install`.
2. Install backend packages with `python -m pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and add your `TINYFISH_API_KEY`.
4. Start FastAPI in one terminal: `python -m uvicorn api.index:app --reload`.
5. Start Vite in another terminal: `npm run dev`.
6. Open `http://localhost:5173`.

Local accounts use SQLite at `data/letmesee.sqlite3`, created automatically by the API. Passwords are stored as salted PBKDF2 hashes; sessions use HttpOnly cookies. The database directory and `.env` are excluded from Git.

## Deploy to Vercel

Import the GitHub repository as a Vercel project. Vercel builds the Vite frontend and serves the FastAPI app from `api/index.py`.

Before deploying, add `TINYFISH_API_KEY` to the Vercel project environment variables. Add a Postgres database through the Vercel Marketplace (for example, Neon) and provide its connection string as `DATABASE_URL`. The app uses Postgres when that variable is present; Vercel's function filesystem is not used for persistent account data.

Vercel's Python runtime supports FastAPI applications: [Python Runtime](https://vercel.com/docs/functions/runtimes/python). Marketplace storage provides managed Postgres integrations: [Vercel Marketplace Storage](https://vercel.com/docs/marketplace-storage).
