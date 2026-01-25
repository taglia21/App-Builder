# Beta Launch Checklist

## Pre-Deployment (Complete before deploying)

### External Services Setup
- [ ] Sign up for Resend.com and get API key
- [ ] Sign up for Plausible.io and add domain
- [ ] Sign up for Railway.app (or your preferred hosting platform)
- [ ] Set up Stripe account for payments (optional for beta)
- [ ] Configure Sentry.io for error tracking (optional)

### Environment Configuration
- [ ] Configure all environment variables (see `.env.example`)
- [ ] Set `RESEND_API_KEY` for email service
- [ ] Set `FROM_EMAIL` and `SUPPORT_EMAIL`
- [ ] Set `PLAUSIBLE_DOMAIN` and enable analytics
- [ ] Set `ADMIN_EMAIL` for admin notifications
- [ ] Generate secure `SECRET_KEY` with `openssl rand -hex 32`
- [ ] Configure `DATABASE_URL` for production PostgreSQL
- [ ] Configure `REDIS_URL` for production Redis

### Database & Migrations
- [ ] Run database migrations: `alembic upgrade head`
- [ ] Verify all tables created correctly
- [ ] Test database connectivity from application

### Email Setup
- [ ] Configure Resend domain and verify DNS
- [ ] Test email sending locally with Mailhog
- [ ] Verify all 5 email templates render correctly:
  - [ ] Verification email
  - [ ] Welcome email
  - [ ] Password reset email
  - [ ] Payment confirmation email
  - [ ] App generation complete email
- [ ] Test email delivery to real inbox

### Legal & Compliance
- [ ] Review Privacy Policy and update for your jurisdiction
- [ ] Review Terms of Service
- [ ] Review Acceptable Use Policy
- [ ] Add cookie consent banner if required
- [ ] Configure data retention policies

## Deployment Steps

### 1. Create Railway Project
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize project
railway init
```

### 2. Add PostgreSQL and Redis
```bash
# Add PostgreSQL database
railway add postgresql

# Add Redis cache
railway add redis
```

### 3. Deploy from GitHub
```bash
# Link to GitHub repository
railway link

# Deploy
railway up
```

### 4. Run Migrations
```bash
# Run migrations on production
railway run alembic upgrade head
```

### 5. Configure Domain
- [ ] Add custom domain in Railway settings
- [ ] Configure DNS CNAME record
- [ ] Wait for SSL certificate provisioning
- [ ] Verify HTTPS works correctly

### 6. Test Health Checks
```bash
# Test main health endpoint
curl https://your-domain.com/health

# Test database connectivity
curl https://your-domain.com/health/database

# Test email service
curl https://your-domain.com/health/email

# Test all dependencies
curl https://your-domain.com/health/dependencies
```

## Post-Deployment Verification

### Core Functionality
- [ ] Dashboard loads correctly
- [ ] User signup works and creates account
- [ ] Email verification sends and verifies
- [ ] Login/logout works correctly
- [ ] Password reset flow works

### Onboarding Flow
- [ ] Onboarding checklist displays for new users
- [ ] Email verification step completes
- [ ] API key setup step completes
- [ ] First app generation step completes
- [ ] First deploy step completes

### Features
- [ ] Project creation works
- [ ] App generation starts and completes
- [ ] Deployment to providers works
- [ ] Analytics tracking works (check Plausible)

### User Engagement
- [ ] Feedback submission works
- [ ] Contact form works
- [ ] Admin dashboard shows submissions

### Admin Functions
- [ ] Admin dashboard accessible at `/admin`
- [ ] Can view and filter feedback
- [ ] Can view and filter contacts
- [ ] Can mark items as resolved
- [ ] Can reply to contacts

### Performance & Monitoring
- [ ] Response times are acceptable (<500ms)
- [ ] No errors in logs
- [ ] Sentry receiving errors (if configured)
- [ ] Health checks all pass

## Beta User Onboarding

### Step 1: Send Invite Email
```python
# Example invite email content
subject = "You're invited to LaunchForge Beta! 🚀"
# Include:
# - What LaunchForge does
# - Beta expectations
# - Signup link
# - Support contact
```

### Step 2: Monitor First Session
- [ ] Check user completed signup
- [ ] Check email verification completed
- [ ] Check onboarding progress
- [ ] Check for any errors in their session

### Step 3: Collect Initial Feedback
- [ ] Send feedback request after first app generation
- [ ] Encourage use of in-app feedback widget
- [ ] Schedule call for detailed feedback (optional)

### Step 4: Follow Up After 3 Days
- [ ] Send check-in email
- [ ] Ask about experience so far
- [ ] Offer help with any issues
- [ ] Collect feature requests

## Rollback Procedures

### If deployment fails:
```bash
# Rollback to previous deployment
railway rollback

# Or redeploy specific commit
git revert HEAD
railway up
```

### If migrations fail:
```bash
# Downgrade to previous migration
railway run alembic downgrade -1
```

### If email service fails:
- Check Resend.com dashboard for errors
- Verify API key is correct
- Check DNS configuration
- Temporarily disable email-required features

## Support Escalation

### For beta users:
1. Check in-app feedback first
2. Review Sentry for errors
3. Check application logs
4. Reach out directly via email

### For critical issues:
1. Post in #incidents channel (if applicable)
2. Check Railway status page
3. Check external service status pages
4. Initiate rollback if necessary

---

**Last Updated:** January 25, 2026  
**Checklist Version:** 1.0.0
