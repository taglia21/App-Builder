# Deployment Alternatives Guide

When Railway deployment becomes problematic due to dependency issues or build timeouts, consider these alternatives:

## 1. Render.com (Recommended) - $7/month

**Pros:**
- Simple GitHub integration
- Automatic deploys on push
- Free PostgreSQL (90-day limit on free tier)
- Better error messages than Railway

**Setup:**
1. Connect GitHub repo
2. Use `requirements-railway.txt` for minimal dependencies
3. Set environment variables in dashboard
4. Deploy!

**Configuration:**
Already configured in `render.yaml`

---

## 2. Heroku - $7/month (Eco Dyno)

**Pros:**
- Battle-tested platform
- Excellent documentation
- Good addon ecosystem

**Setup:**
```bash
# Install Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# Login and create app
heroku login
heroku create launchforge-dashboard

# Add PostgreSQL
heroku addons:create heroku-postgresql:mini

# Add Redis
heroku addons:create heroku-redis:mini

# Set config vars
heroku config:set STRIPE_SECRET_KEY=sk_test_...
heroku config:set RESEND_API_KEY=re_...
heroku config:set SECRET_KEY=$(openssl rand -hex 32)

# Deploy
git push heroku main
```

**Procfile:**
Already configured in repo root.

---

## 3. DigitalOcean App Platform - $5/month

**Pros:**
- Predictable pricing
- Good container support
- Managed databases

**Setup:**
1. Go to DigitalOcean App Platform
2. Connect GitHub repo
3. Set build command: `pip install -r requirements-railway.txt`
4. Set run command: `uvicorn src.dashboard.app:app --host 0.0.0.0 --port $PORT`
5. Add environment variables
6. Deploy

**App Spec (app.yaml):**
```yaml
name: launchforge
services:
  - name: dashboard
    github:
      repo: your-username/App-Builder
      branch: main
    build_command: pip install -r requirements-railway.txt
    run_command: uvicorn src.dashboard.app:app --host 0.0.0.0 --port $PORT
    envs:
      - key: DATABASE_URL
        scope: RUN_TIME
        value: ${db.DATABASE_URL}
databases:
  - name: db
    engine: PG
    size: db-s-dev-database
```

---

## 4. Vercel (Frontend) + Supabase (Backend) - FREE

**Best for:** Separating frontend/backend, maximizing free tier

**Frontend on Vercel:**
- Host static dashboard or Next.js frontend
- Free unlimited deployments
- Global CDN

**Backend on Supabase:**
- Free PostgreSQL with 500MB storage
- Built-in Auth
- Edge Functions for API endpoints

**Setup:**
This requires refactoring the app into:
1. Static frontend (React/HTMX) → Vercel
2. Database + Auth → Supabase
3. API endpoints → Supabase Edge Functions

---

## 5. Docker on VPS - $5/month

**Pros:**
- Full control
- No platform restrictions
- Can run anything

**Providers:**
- DigitalOcean Droplet ($4-6/mo)
- Vultr ($5/mo)
- Linode ($5/mo)
- Hetzner (€3.49/mo - cheapest)

**Setup:**
```bash
# SSH into VPS
ssh root@your-server-ip

# Install Docker
curl -fsSL https://get.docker.com | sh

# Clone repo
git clone https://github.com/your-username/App-Builder.git
cd App-Builder

# Create .env file
cp .env.railway.template .env
nano .env  # Fill in values

# Run with Docker Compose
docker compose -f docker-compose.simple.yml up -d

# Setup nginx/caddy for SSL (optional)
# ...
```

---

## 6. Fly.io - $0-5/month

**Pros:**
- Generous free tier
- Global edge deployment
- Good Docker support

**Setup:**
```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login and launch
fly auth login
fly launch

# Set secrets
fly secrets set STRIPE_SECRET_KEY=sk_test_...
fly secrets set RESEND_API_KEY=re_...
fly secrets set SECRET_KEY=$(openssl rand -hex 32)

# Deploy
fly deploy
```

**fly.toml:**
```toml
app = "launchforge-dashboard"
primary_region = "iad"

[build]
  dockerfile = "Dockerfile"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0

[env]
  PORT = "8000"
```

---

## Comparison Table

| Platform | Cost/Month | Ease | Free DB | Cold Start |
|----------|------------|------|---------|------------|
| Render | $7 | ⭐⭐⭐⭐ | ✅ (90 days) | Yes |
| Heroku | $7 | ⭐⭐⭐⭐⭐ | ❌ ($5+) | Yes |
| DO App | $5 | ⭐⭐⭐ | ❌ ($7+) | No |
| Fly.io | $0-5 | ⭐⭐⭐ | ✅ (limited) | Yes |
| VPS+Docker | $5 | ⭐⭐ | Self-host | No |
| Vercel+Supabase | $0 | ⭐⭐ | ✅ | Yes |

---

## Quick Migration Steps

1. **Export environment variables** from current platform
2. **Copy `requirements-railway.txt`** to new platform
3. **Set DATABASE_URL** (or create new database)
4. **Run migrations**: `alembic upgrade head`
5. **Test health endpoint**: `curl https://your-app.com/health`
6. **Update DNS** if using custom domain

---

## Need Help?

- Check `docs/DEPLOYMENT_TROUBLESHOOTING.md` for common issues
- Test locally first: `./scripts/deploy-railway.sh`
- Verify requirements: `pip install -r requirements-railway.txt`
