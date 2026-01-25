# Pre-Deployment Checklist

Complete this checklist before deploying to any cloud platform.

## Local Testing

- [ ] **Test minimal requirements install**
  ```bash
  python -m venv .venv-test
  source .venv-test/bin/activate
  pip install -r requirements-railway.txt
  ```

- [ ] **Verify dashboard starts without AI libraries**
  ```bash
  uvicorn src.dashboard.app:app --host 0.0.0.0 --port 8000
  ```

- [ ] **Test health endpoint**
  ```bash
  curl http://localhost:8000/health
  # Expected: {"status":"ok","service":"launchforge-dashboard",...}
  ```

- [ ] **Test root endpoint**
  ```bash
  curl http://localhost:8000/
  # Expected: {"status":"healthy","service":"LaunchForge Dashboard"}
  ```

---

## Database

- [ ] **Run database migrations locally**
  ```bash
  alembic upgrade head
  ```

- [ ] **Verify migrations are committed**
  ```bash
  git status alembic/versions/
  ```

- [ ] **Check DATABASE_URL format**
  ```
  postgresql://user:password@host:port/database
  ```

---

## Environment Variables

Ensure all required variables are set:

- [ ] `DATABASE_URL` - PostgreSQL connection string
- [ ] `REDIS_URL` - Redis connection string (optional)
- [ ] `STRIPE_SECRET_KEY` - Stripe API key (sk_test_... or sk_live_...)
- [ ] `STRIPE_WEBHOOK_SECRET` - Stripe webhook signing secret
- [ ] `RESEND_API_KEY` - Resend email API key
- [ ] `SECRET_KEY` - JWT signing key (generate with `openssl rand -hex 32`)
- [ ] `ENVIRONMENT` - `production` for prod

---

## Configuration Files

- [ ] **Procfile exists** (for Heroku, some platforms)
- [ ] **railway.toml configured** (for Railway)
- [ ] **nixpacks.toml configured** (for Railway/Nixpacks)
- [ ] **render.yaml configured** (for Render)

---

## Code Quality

- [ ] **No hardcoded secrets**
  ```bash
  grep -r "sk_live_\|sk_test_\|password=" src/
  ```

- [ ] **All imports are protected**
  - Optional imports use try/except
  - No crashes on missing packages

- [ ] **Tests pass**
  ```bash
  pytest tests/ -v
  ```

---

## Git

- [ ] **All changes committed**
  ```bash
  git status
  ```

- [ ] **On correct branch**
  ```bash
  git branch --show-current
  # Should be: main or production
  ```

- [ ] **Pushed to remote**
  ```bash
  git push origin main
  ```

---

## Platform-Specific

### Railway
- [ ] Project linked: `railway link`
- [ ] Variables set: `railway variables`
- [ ] PostgreSQL addon created

### Render
- [ ] render.yaml in repo root
- [ ] Service connected to GitHub
- [ ] Environment groups configured

### Heroku
- [ ] App created: `heroku apps:info`
- [ ] Addons provisioned (postgres, redis)
- [ ] Config vars set: `heroku config`

---

## Post-Deployment Verification

After deploying, verify:

- [ ] **Health check responds**
  ```bash
  curl https://your-app.com/health
  ```

- [ ] **Homepage loads**
  ```bash
  curl https://your-app.com/
  ```

- [ ] **Database connected**
  - Check logs for connection errors
  - Try accessing a database-dependent route

- [ ] **No error logs**
  - Check platform's log viewer
  - Look for import errors or crashes

- [ ] **SSL/HTTPS working**
  ```bash
  curl -I https://your-app.com/
  # Should show 200 and security headers
  ```

---

## Rollback Plan

If deployment fails:

1. Identify the issue in logs
2. Rollback to previous version:
   - Railway: `railway rollback`
   - Render: Use dashboard
   - Heroku: `heroku rollback`
3. Fix the issue locally
4. Re-test with this checklist
5. Redeploy

---

## Quick Commands

```bash
# Full local test
./scripts/deploy-railway.sh

# Test requirements
pip install -r requirements-railway.txt --dry-run

# Check for import errors
python -c "from src.dashboard.app import app; print('OK')"

# Generate SECRET_KEY
openssl rand -hex 32
```
