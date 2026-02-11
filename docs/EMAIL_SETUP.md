# Email Setup Guide

Valeric uses transactional email for user communications. This guide covers setting up email with Resend.com (recommended) or SMTP fallback.

## 📧 Email Types

Valeric sends the following transactional emails:

| Email Type | Trigger | Template |
|------------|---------|----------|
| **Verification** | User signup | `verification.html` |
| **Welcome** | Email verified | `welcome.html` |
| **Password Reset** | Forgot password | `password_reset.html` |
| **Payment Confirmation** | Subscription started | `payment_confirmation.html` |
| **App Complete** | Generation finished | `app_complete.html` |

---

## 🚀 Resend.com Setup (Recommended)

[Resend](https://resend.com) is the recommended email provider due to:
- Free tier: 100 emails/day, 3,000/month
- Simple API integration
- Great deliverability
- Easy domain verification

### Step 1: Create Resend Account

1. Go to [resend.com](https://resend.com)
2. Sign up (GitHub login available)
3. Verify your email

### Step 2: Verify Your Domain

For production, you must verify your sending domain:

1. Go to **Settings** → **Domains**
2. Click **"Add Domain"**
3. Enter your domain (e.g., `valeric.dev`)
4. Add the DNS records Resend provides:

```
# Example DNS records (your values will differ)
Type: MX
Name: send
Value: feedback-smtp.us-east-1.amazonses.com
Priority: 10

Type: TXT
Name: resend._domainkey
Value: "p=MIGfMA0GCSqGSIb3DQEB..."
```

5. Click **"Verify"** after adding records
6. Wait for verification (usually 5-30 minutes)

### Step 3: Get API Key

1. Go to **API Keys**
2. Click **"Create API Key"**
3. Name it (e.g., "Valeric Production")
4. Select permissions: **"Full Access"** or **"Sending access"**
5. Copy the key (starts with `re_`)

### Step 4: Configure Valeric

Add to your `.env` file:

```env
RESEND_API_KEY=re_your_api_key_here
EMAIL_FROM=noreply@yourdomain.com
```

### Step 5: Test Email Sending

```python
# Test script
from src.emails import send_verification_email
import asyncio

async def test():
    result = await send_verification_email(
        email="test@example.com",
        name="Test User",
        verification_url="https://valeric.dev/verify/abc123"
    )
    print(f"Success: {result.success}, ID: {result.message_id}")

asyncio.run(test())
```

---

## 📮 SMTP Fallback

If you prefer SMTP (e.g., Gmail, SendGrid SMTP, Mailgun SMTP):

### Gmail SMTP

1. Enable 2-Factor Authentication on your Google account
2. Generate an App Password:
   - Go to [Google Account Security](https://myaccount.google.com/security)
   - Click **"App passwords"**
   - Select "Mail" and your device
   - Copy the 16-character password

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
EMAIL_FROM=your-email@gmail.com
```

### SendGrid SMTP

```env
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your_sendgrid_api_key
EMAIL_FROM=noreply@yourdomain.com
```

### Mailgun SMTP

```env
SMTP_HOST=smtp.mailgun.org
SMTP_PORT=587
SMTP_USER=postmaster@your-domain.mailgun.org
SMTP_PASSWORD=your-mailgun-smtp-password
EMAIL_FROM=noreply@yourdomain.com
```

---

## 🎨 Template Customization

Email templates are located in `src/emails/templates/`. They use Jinja2 templating.

### Template Variables

All templates receive:
- `year`: Current year (for copyright)
- Template-specific variables (see below)

| Template | Variables |
|----------|-----------|
| `verification.html` | `name`, `verification_url` |
| `welcome.html` | `name`, `dashboard_url` |
| `password_reset.html` | `name`, `reset_url` |
| `payment_confirmation.html` | `name`, `plan_name`, `amount`, `receipt_url` |
| `app_complete.html` | `name`, `app_name`, `project_url` |

### Customizing Templates

1. Edit the HTML file in `src/emails/templates/`
2. Test locally using the test script below
3. Deploy

### Example: Change Logo

```html
<!-- In any template, replace the logo section -->
<div class="logo">
    <img src="https://yourdomain.com/logo.png" alt="Your Logo" height="50">
</div>
```

### Example: Add Custom Footer

```html
<div class="footer">
    <p>© {{ year }} Your Company. All rights reserved.</p>
    <p>123 Main Street, City, State 12345</p>
    <p>
        <a href="https://yourdomain.com/unsubscribe">Unsubscribe</a>
    </p>
</div>
```

---

## 🧪 Testing Emails Locally

### Option 1: Mailhog (Recommended for Development)

Mailhog catches all outgoing emails and displays them in a web UI.

```bash
# Install with Docker
docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog

# Configure in .env
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USER=
SMTP_PASSWORD=

# View emails at http://localhost:8025
```

### Option 2: Resend Test Mode

Resend has a test mode that doesn't send real emails:

```python
# The Resend API accepts emails to *.resend.dev addresses without sending
# Use: test@resend.dev for testing
```

### Option 3: Console Output

For quick testing, enable console email output:

```python
# In src/emails/client.py, add logging
import logging
logging.getLogger('src.emails').setLevel(logging.DEBUG)
```

---

## 🔧 Troubleshooting

### "Email not configured" Warning

**Cause**: `RESEND_API_KEY` is not set or empty.

**Fix**: 
1. Check your `.env` file has `RESEND_API_KEY=re_...`
2. Ensure the environment variable is loaded
3. Restart the application

### Emails Going to Spam

**Causes & Fixes**:
1. **Domain not verified**: Complete Resend domain verification
2. **Missing SPF/DKIM**: Add required DNS records
3. **No DMARC policy**: Add a DMARC DNS record:
   ```
   Type: TXT
   Name: _dmarc
   Value: "v=DMARC1; p=none; rua=mailto:dmarc@yourdomain.com"
   ```

### Rate Limiting

**Free Tier Limits**:
- Resend: 100/day, 3,000/month
- Gmail SMTP: 500/day
- SendGrid Free: 100/day

**Solutions**:
1. Upgrade to paid tier
2. Implement email queuing with Redis
3. Use background tasks for bulk emails

### Connection Timeout

**Cause**: Network/firewall blocking SMTP port.

**Fix**:
1. Check if port 587 is open
2. Try port 465 (SSL) or 25 (unencrypted)
3. Use API-based provider (Resend) instead

---

## 📊 Email Analytics

### Resend Dashboard

Resend provides built-in analytics:
- Delivery status
- Open rates
- Click rates
- Bounce reports

Access at: https://resend.com/emails

### Custom Tracking

Add tracking parameters to links:

```html
<a href="{{ dashboard_url }}?utm_source=email&utm_medium=welcome&utm_campaign=onboarding">
    Go to Dashboard
</a>
```

---

## 🔒 Security Best Practices

1. **Never commit API keys** - Use environment variables
2. **Verify sender domain** - Prevents spoofing
3. **Use TLS** - Always use port 587 with STARTTLS
4. **Rate limit** - Implement sending limits
5. **Validate recipients** - Check email format before sending
6. **Handle bounces** - Remove invalid emails from lists

---

## 📚 Related Documentation

- [Resend Documentation](https://resend.com/docs)
- [Email Deliverability Best Practices](https://resend.com/blog/email-deliverability-best-practices)
- [DMARC, SPF, DKIM Explained](https://resend.com/blog/dmarc-spf-dkim-explained)
