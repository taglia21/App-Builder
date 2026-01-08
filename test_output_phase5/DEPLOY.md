# Deployment Guide for Phase5App

## Frontend (Vercel)
1. Push this repo to GitHub.
2. Go to [Vercel](https://vercel.com/new).
3. Import the repository.
4. Set "Root Directory" to `frontend`.
5. Click **Deploy**.

## Backend (Render)
1. Go to [Render](https://dashboard.render.com/).
2. Click **New +** -> **Blueprint**.
3. Connect your GitHub repo.
4. Render will detect `render.yaml` and auto-configure the Backend + Postgres.
5. Click **Apply**.

## Environment Variables
- Copy the `SECRET_KEY` from Render to Vercel environment variables.
- Copy the `API_URL` (Render URL) to Vercel as `NEXT_PUBLIC_API_URL`.
