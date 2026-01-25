# Deployment Troubleshooting Guide

Common deployment issues and their solutions.

## Railway Issues

### 1. Build Timeout

**Symptom:**
```
Build failed: Timeout exceeded
```

**Causes:**
- Too many dependencies
- Large ML packages (torch, transformers)
- Slow package resolution

**Solutions:**
1. Use `requirements-railway.txt` (minimal dependencies)
2. Remove ML/AI packages from dashboard deployment
3. Increase build timeout in railway.toml (if available)

```bash
# Test locally first
pip install -r requirements-railway.txt
```

---

### 2. Memory Limit Exceeded

**Symptom:**
```
OOM killed
Container exceeded memory limit
```

**Causes:**
- ML models loading into memory
- Large pandas DataFrames
- Memory leaks in long-running processes

**Solutions:**
1. Use Railway's higher memory plans
2. Remove ML dependencies for dashboard
3. Implement lazy loading for heavy modules

```python
# Instead of top-level import
# import transformers

# Use lazy import
def get_model():
    import transformers
    return transformers.pipeline("...")
```

---

### 3. Port Configuration Error

**Symptom:**
```
Connection refused
Health check failed
```

**Causes:**
- App not listening on $PORT
- Hardcoded port number
- Wrong host binding

**Solutions:**
1. Always use `--port $PORT` (Railway sets this automatically)
2. Bind to `0.0.0.0`, not `127.0.0.1`

```python
# Correct
uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

# Wrong
uvicorn.run(app, host="127.0.0.1", port=8000)
```

---

### 4. Dependency Conflict

**Symptom:**
```
ERROR: Cannot install package-a and package-b
ResolutionImpossible
```

**Solutions:**
1. Check conflicting version requirements
2. Use flexible version specs (`>=` instead of `==`)
3. Test resolution locally:

```bash
pip install -r requirements-railway.txt --dry-run
```

4. Use pip-tools for dependency resolution:
```bash
pip install pip-tools
pip-compile requirements-railway.txt
```

---

### 5. Database Connection Error

**Symptom:**
```
Connection refused
psycopg2.OperationalError
```

**Causes:**
- DATABASE_URL not set
- Wrong connection string format
- Database not provisioned

**Solutions:**
1. Verify DATABASE_URL is set:
```bash
railway variables
```

2. Check connection string format:
```
postgresql://user:password@host:port/database
```

3. Test connection:
```python
import psycopg2
conn = psycopg2.connect(os.environ["DATABASE_URL"])
print("Connected!")
conn.close()
```

---

### 6. Import Error on Deploy

**Symptom:**
```
ModuleNotFoundError: No module named 'xyz'
```

**Solutions:**
1. Add missing package to requirements-railway.txt
2. Use try/except for optional imports:

```python
try:
    import optional_package
    HAS_OPTIONAL = True
except ImportError:
    HAS_OPTIONAL = False
    optional_package = None
```

---

## Render Issues

### 1. Build Command Fails

**Solutions:**
1. Use explicit Python version in render.yaml
2. Check build logs for specific error
3. Simplify requirements

---

### 2. Start Command Fails

**Solutions:**
1. Verify module path: `src.dashboard.app:app`
2. Check for import errors in startup
3. Test locally with same command

---

## General Issues

### 1. Migrations Not Running

**Solutions:**
1. Add migration command to start script:
```bash
alembic upgrade head && uvicorn src.dashboard.app:app ...
```

2. Or use release phase (Heroku/Render):
```yaml
releaseCommand: alembic upgrade head
```

---

### 2. Static Files Not Found

**Solutions:**
1. Ensure static directory is included in build
2. Check path resolution:
```python
static_path = Path(__file__).parent / "static"
```

3. Verify files are committed to git

---

### 3. HTTPS/SSL Issues

**Solutions:**
1. Most platforms handle SSL automatically
2. Ensure `Strict-Transport-Security` header is set
3. Use platform's built-in SSL

---

### 4. Cold Start Timeouts

**Solutions:**
1. Implement health check endpoint
2. Keep app warm with external pinger
3. Use platform's "always on" feature if available

---

## Debugging Checklist

1. **Test locally first:**
   ```bash
   pip install -r requirements-railway.txt
   uvicorn src.dashboard.app:app --host 0.0.0.0 --port 8000
   curl http://localhost:8000/health
   ```

2. **Check environment variables:**
   - DATABASE_URL
   - REDIS_URL
   - STRIPE_SECRET_KEY
   - RESEND_API_KEY
   - SECRET_KEY

3. **Review build logs:**
   - Look for pip install errors
   - Check for missing system dependencies

4. **Review runtime logs:**
   - Import errors
   - Connection errors
   - Port binding issues

5. **Verify health endpoint:**
   ```bash
   curl https://your-app.railway.app/health
   ```

---

## Quick Fixes

### Remove Problematic Packages

These packages often cause issues and are not needed for dashboard:

```bash
# Remove from requirements:
torch              # ~2GB, not needed for dashboard
transformers       # Requires torch
sentence-transformers
scikit-learn       # Usually not needed
spacy              # Large models
pygooglenews       # Deprecated, often fails
feedparser         # Can cause conflicts
```

### Minimal Working Setup

```requirements.txt
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
redis>=5.0.0
stripe>=7.0.0
resend>=0.8.0
jinja2>=3.1.0
python-dotenv>=1.0.0
```

---

## Getting Help

1. **Railway Discord:** https://discord.gg/railway
2. **Render Community:** https://community.render.com
3. **Stack Overflow:** Tag with platform name
4. **GitHub Issues:** Check platform's status page

---

## Emergency Rollback

If deployment fails:

1. **Railway:**
   ```bash
   railway rollback
   ```

2. **Render:** Use dashboard to revert to previous deploy

3. **Heroku:**
   ```bash
   heroku rollback
   ```

4. **Docker/VPS:**
   ```bash
   docker compose down
   git checkout <previous-commit>
   docker compose up -d
   ```
