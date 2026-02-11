#!/usr/bin/env python3
"""
⚡ Valeric - AI-Powered Startup Builder

Generate validated startup ideas and production-ready applications
using AI with real-time market intelligence.

Usage:
    python main.py generate --demo          # Try with sample data
    python main.py generate                 # Use real AI providers
    python main.py providers                # List available providers

For more: python main.py --help
"""

from src.cli import cli

if __name__ == "__main__":
    cli()
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        flash('Thank you for your message! We\'ll get back to you soon.', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

