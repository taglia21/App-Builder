# Deployment Guide for AI-PoweredCrmAutomation

## 🚀 Quick Start (Automated)

You can deploy this application using the App-Builder CLI:

```bash
python main.py deploy ./generated_app_v2 --frontend vercel --backend render
```

## 🛠 Manual Deployment

### Frontend (Vercel)
1. Install CLI: `npm i -g vercel`
2. Login: `vercel login`
3. Deploy: `cd frontend && vercel`

### Backend (Render)
1. Create a Web Service for `backend/` (Python/FastAPI).
2. Create a PostgreSQL database.
3. Set `DATABASE_URL` environment variable.

### Infrastructure (Terraform)
Templates are available in `terraform/` directory for AWS provisioning.
