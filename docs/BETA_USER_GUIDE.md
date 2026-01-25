# LaunchForge Beta User Guide

Welcome to the LaunchForge beta! This guide will help you get started and make the most of your beta access.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Setting Up API Keys](#setting-up-api-keys)
3. [Generating Your First App](#generating-your-first-app)
4. [Deploying Your App](#deploying-your-app)
5. [Providing Feedback](#providing-feedback)
6. [FAQ](#faq)

---

## Getting Started

### Step 1: Sign Up

1. Visit [LaunchForge](https://launchforge.app)
2. Click "Get Started" or "Sign Up"
3. Enter your email address and create a password
4. Click "Create Account"

### Step 2: Verify Your Email

1. Check your inbox for a verification email from `noreply@launchforge.app`
2. Click the verification link in the email
3. You'll be redirected to the dashboard with a success message

> **Tip:** If you don't see the email, check your spam folder. You can also request a new verification email from the login page.

### Step 3: Complete Your Profile

1. Navigate to **Settings** from the dashboard
2. Add your name and any optional profile information
3. Review your notification preferences

---

## Setting Up API Keys

LaunchForge uses AI to generate your applications. You'll need to provide API keys for the AI services.

### Required API Keys

| Service | Purpose | Get Key |
|---------|---------|---------|
| OpenAI | Code generation | [platform.openai.com](https://platform.openai.com/api-keys) |
| **OR** Anthropic | Code generation | [console.anthropic.com](https://console.anthropic.com/) |

### Optional API Keys

| Service | Purpose | Get Key |
|---------|---------|---------|
| Groq | Fast inference (optional) | [console.groq.com](https://console.groq.com/keys) |
| Perplexity | Market research | [perplexity.ai](https://www.perplexity.ai/) |

### Adding Your API Keys

1. Go to **Settings** → **API Keys**
2. Click "Add API Key" for each service
3. Paste your API key
4. Click "Save"

> **Security Note:** Your API keys are encrypted and stored securely. We never share them with third parties.

---

## Generating Your First App

### Step 1: Start a New Project

1. From the dashboard, click **"New Project"**
2. You'll enter the project wizard

### Step 2: Describe Your Idea

1. Enter a name for your project
2. Describe your app idea in detail:
   - What problem does it solve?
   - Who is it for?
   - What are the main features?

**Example:**
```
A project management tool for remote teams that includes:
- Task boards with drag-and-drop
- Team chat and messaging
- Time tracking
- Client invoicing
```

### Step 3: Choose Features

Select from available features:
- ✅ User authentication
- ✅ Database integration
- ✅ REST API
- ✅ Admin dashboard
- ✅ Payment processing
- ✅ Email notifications

### Step 4: Review and Generate

1. Review your project configuration
2. Click **"Generate App"**
3. Wait for generation to complete (typically 2-5 minutes)

### Step 5: Review Generated Code

Once complete:
1. Preview the generated code in the browser
2. Download as a ZIP file
3. Or push directly to GitHub

---

## Deploying Your App

LaunchForge supports one-click deployment to multiple platforms.

### Supported Platforms

| Platform | Best For | Free Tier |
|----------|----------|-----------|
| Vercel | Frontend/Full-stack | ✅ Generous |
| Render | Backend/Full-stack | ✅ Limited |
| Railway | Full-stack | ✅ $5 credit |
| Netlify | Frontend/Static | ✅ Generous |

### One-Click Deploy

1. From your project page, click **"Deploy"**
2. Select your preferred platform
3. Connect your account (first time only)
4. Click **"Deploy Now"**

### Manual Deployment

If you prefer to deploy manually:

1. Download your project code
2. Push to your own GitHub repository
3. Connect the repo to your hosting platform
4. Configure environment variables as needed

### Environment Variables

Most generated apps need these environment variables:

```env
DATABASE_URL=your_database_connection_string
REDIS_URL=your_redis_connection_string  # if using caching
SECRET_KEY=your_secure_secret_key
```

---

## Providing Feedback

Your feedback is invaluable during the beta! Here's how to share it:

### In-App Feedback Widget

1. Click the **feedback button** (💬) in the bottom-right corner
2. Select a category:
   - 🐛 Bug Report
   - 💡 Feature Request
   - 🔧 Improvement
   - 💬 General Feedback
3. Describe your feedback
4. Click "Submit"

### Contact Form

For detailed questions or issues:
1. Visit the **Contact** page
2. Fill out the form with:
   - Your name
   - Email address
   - Subject
   - Detailed message
3. We'll respond within 24-48 hours

### What We Want to Know

- 🎯 What's working well?
- 🐛 What bugs did you encounter?
- 🔧 What could be improved?
- ✨ What features are missing?
- 📊 How does it compare to alternatives?

---

## FAQ

### Account & Access

**Q: How long does the beta last?**
A: The beta period runs until we reach full launch. Beta users will receive special benefits at launch.

**Q: Can I invite others to the beta?**
A: Currently, beta access is limited. Contact us if you'd like to refer someone.

**Q: Will my projects be saved after beta?**
A: Yes! All your projects and data will be preserved when we launch.

### Generation

**Q: How long does app generation take?**
A: Typically 2-5 minutes, depending on complexity.

**Q: Can I regenerate parts of my app?**
A: Yes! You can regenerate individual components or the entire app.

**Q: What programming languages are supported?**
A: We currently generate:
- **Frontend:** Next.js (React), HTML/CSS/JS
- **Backend:** FastAPI (Python), Node.js (Express)
- **Database:** PostgreSQL, SQLite

**Q: Can I customize the generated code?**
A: Absolutely! The generated code is yours to modify. It's clean, well-documented, and follows best practices.

### Deployment

**Q: Do I need a hosting account?**
A: Yes, you'll need an account on one of our supported platforms (Vercel, Render, Railway, or Netlify). All have free tiers.

**Q: Can I deploy to my own server?**
A: Yes! Download the code and deploy it anywhere. We provide Docker support for easy self-hosting.

**Q: Are there any usage limits?**
A: Beta users have generous limits. Check your dashboard for your current usage.

### Billing & Pricing

**Q: Is the beta free?**
A: Yes, the beta is free for all invited users.

**Q: What will pricing be at launch?**
A: We'll share pricing details before launch. Beta users will receive special discounts.

### Getting Help

**Q: I'm stuck. How do I get help?**
A: 
1. Check this guide and our [documentation](/docs)
2. Submit feedback through the in-app widget
3. Contact us via the contact form
4. Email us directly at support@launchforge.app

**Q: I found a bug. What should I do?**
A: Report it immediately using the feedback widget! Include:
- What you were trying to do
- What happened instead
- Any error messages
- Your browser and OS

---

## Tips for Beta Users

### Get the Most Out of LaunchForge

1. **Be Specific:** The more detailed your app description, the better the results
2. **Iterate:** Don't be afraid to regenerate and try different approaches
3. **Explore Features:** Try different feature combinations
4. **Read the Code:** Learn from the generated code to improve your skills
5. **Give Feedback:** Your input shapes the product!

### Common Gotchas

- ⚠️ Make sure to set up API keys before generating
- ⚠️ Email verification is required to access all features
- ⚠️ Large apps may take longer to generate
- ⚠️ Check deployment logs if something doesn't work

---

## Contact Us

- **Email:** support@launchforge.app
- **Twitter:** [@LaunchForgeApp](https://twitter.com/LaunchForgeApp)
- **Documentation:** [docs.launchforge.app](https://docs.launchforge.app)

---

Thank you for being a beta tester! Your feedback helps us build a better product. 🚀

**Last Updated:** January 25, 2026  
**Guide Version:** 1.0.0
