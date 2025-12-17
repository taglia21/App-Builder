"""
AI Startup Generator - Red/Purple Professional Edition
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime
import json
import asyncio
import os

st.set_page_config(
    page_title="AI Startup Generator",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if 'launched' not in st.session_state:
    st.session_state.launched = False

# =============================================================================
# SVG ICONS (PROFESSIONAL ASSETS)
# =============================================================================

ICONS = {
    "live_data": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v20M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path><path d="M2 12h20"></path></svg>""",
    "neural": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/><path d="M12 16a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-2a2 2 0 0 1 2-2z"/><path d="M5 9a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-2a2 2 0 0 1 2-2z"/><path d="M19 9a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-2a2 2 0 0 1 2-2z"/><circle cx="12" cy="12" r="3"/><path d="M12 6v3"/><path d="M12 15v3"/><path d="M19.07 10.93l-2.5 2.5"/><path d="M7.43 13.43l-2.5-2.5"/></svg>""",
    "ranking": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="20" x2="12" y2="10"></line><line x1="18" y1="20" x2="18" y2="4"></line><line x1="6" y1="20" x2="6" y2="16"></line></svg>""",
    "code": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>""",
    "search": """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>""",
    "lock": """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>""",
    "settings": """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>"""
}

def get_icon(name):
    return ICONS.get(name, "")

# =============================================================================
# HYPER-REALISTIC INTRO (RED/PURPLE EDITION)
# =============================================================================

if not st.session_state.launched:
    intro_html = '''
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&family=Rajdhani:wght@300;400;600;700&display=swap');
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            background-color: #050005;
            color: #fff;
            font-family: 'Rajdhani', sans-serif;
            overflow: hidden;
            height: 100vh;
            width: 100vw;
        }

        #starfield {
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 100%;
            z-index: 1;
        }

        .hud-overlay {
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            z-index: 10;
            text-align: center;
            width: 100%;
            pointer-events: none;
        }

        .content-container {
            pointer-events: auto;
            background: rgba(20, 0, 10, 0.4);
            backdrop-filter: blur(10px);
            padding: 50px 90px;
            border: 1px solid rgba(255, 0, 60, 0.3);
            border-radius: 0;
            display: inline-block;
            box-shadow: 0 0 40px rgba(255, 0, 60, 0.1);
        }
        
        /* Decorative Corners */
        .content-container::before {
            content: ''; position: absolute; top: -1px; left: -1px; width: 30px; height: 30px;
            border-top: 3px solid #ff003c; border-left: 3px solid #ff003c;
        }
        .content-container::after {
            content: ''; position: absolute; bottom: -1px; right: -1px; width: 30px; height: 30px;
            border-bottom: 3px solid #ff003c; border-right: 3px solid #ff003c;
        }

        h1 {
            font-family: 'Orbitron', sans-serif;
            font-size: 72px;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 8px;
            color: #fff;
            text-shadow: 0 0 30px rgba(255, 0, 60, 0.8);
            margin-bottom: 20px;
            opacity: 0;
            animation: fadeInDown 1s ease-out forwards 0.5s;
        }
        
        .subtitle {
            font-size: 24px;
            text-transform: uppercase;
            letter-spacing: 6px;
            color: #ff003c;
            margin-bottom: 60px;
            opacity: 0;
            animation: fadeInUp 1s ease-out forwards 1s;
        }

        .init-btn {
            background: transparent;
            border: 2px solid #ff003c;
            color: #ff003c;
            padding: 24px 64px;
            font-family: 'Orbitron', sans-serif;
            font-size: 20px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 4px;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
            opacity: 0;
            animation: pulseRed 2s infinite, fadeIn 1s ease-out forwards 1.5s;
        }
        
        @keyframes pulseRed {
            0% { box-shadow: 0 0 0 0 rgba(255, 0, 60, 0.4); }
            70% { box-shadow: 0 0 0 15px rgba(255, 0, 60, 0); }
            100% { box-shadow: 0 0 0 0 rgba(255, 0, 60, 0); }
        }
        
        .init-btn:hover {
            background: rgba(255, 0, 60, 0.2);
            box-shadow: 0 0 50px rgba(255, 0, 60, 0.8);
            transform: scale(1.05);
            border-color: #fff;
            color: #fff;
        }
        
        /* Animations */
        @keyframes fadeInDown {
            from { opacity: 0; transform: translateY(-30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        .warp-active .content-container {
            opacity: 0;
            transform: scale(1.5);
            transition: all 0.5s ease-in;
        }

        .flash-overlay {
            position: absolute;
            top: 0; left: 0; width: 100%; height: 100%;
            background: #ff003c; /* Red flash */
            opacity: 0;
            pointer-events: none;
            z-index: 100;
            transition: opacity 0.2s ease-in;
        }

    </style>
    </head>
    <body>
        <canvas id="starfield"></canvas>
        <div class="flash-overlay" id="flash"></div>
        
        <div class="hud-overlay">
            <div class="content-container">
                <h1>Startup Generator</h1>
                <div class="subtitle">Neural Ideation Core</div>
                <button class="init-btn" onclick="engageWarp()" id="engageBtn">Initialize</button>
            </div>
        </div>

        <script>
            // Starfield Logic
            const canvas = document.getElementById('starfield');
            const ctx = canvas.getContext('2d');
            
            let width, height;
            
            const stars = [];
            let speed = 0.5;
            const numStars = 1500;
            let warpActive = false;
            
            function resize() {
                width = window.innerWidth;
                height = window.innerHeight;
                canvas.width = width;
                canvas.height = height;
            }
            
            window.addEventListener('resize', resize);
            resize();
            
            class Star {
                constructor() {
                    this.init();
                }
                
                init() {
                    this.x = (Math.random() - 0.5) * width * 2;
                    this.y = (Math.random() - 0.5) * height * 2;
                    this.z = Math.random() * width;
                }
                
                update() {
                    this.z -= speed;
                    if (this.z <= 0) {
                        this.init();
                        this.z = width;
                    }
                }
                
                draw() {
                    let x = (this.x / this.z) * width/2 + width/2;
                    let y = (this.y / this.z) * height/2 + height/2;
                    
                    let pz = this.z + speed * (warpActive ? 3 : 0.5); 
                    
                    let px = (this.x / pz) * width/2 + width/2;
                    let py = (this.y / pz) * height/2 + height/2;
                    
                    let r = Math.max(0.1, (1 - this.z / width) * 2.5);
                    
                    if (x < 0 || x > width || y < 0 || y > height) return;
                    
                    ctx.beginPath();
                    if (warpActive) {
                        ctx.moveTo(x, y);
                        ctx.lineTo(px, py);
                        // Red/Purple trails
                        ctx.strokeStyle = Math.random() > 0.5 ? 
                            `rgba(255, 0, 60, ${1 - this.z/width})` : 
                            `rgba(112, 0, 255, ${1 - this.z/width})`;
                        ctx.lineWidth = r * 1.5;
                        ctx.stroke();
                    } else {
                        ctx.arc(x, y, r, 0, Math.PI * 2);
                        // Subtle red tint on stars
                        ctx.fillStyle = `rgba(255, 200, 200, ${1 - this.z/width})`;
                        ctx.fill();
                    }
                }
            }
            
            for(let i=0; i<numStars; i++) stars.push(new Star());
            
            function animate() {
                // Red/Black fade
                ctx.fillStyle = warpActive ? 'rgba(5, 0, 5, 0.2)' : 'rgba(5, 0, 5, 0.8)';
                ctx.fillRect(0, 0, width, height);
                stars.forEach(star => { star.update(); star.draw(); });
                requestAnimationFrame(animate);
            }
            
            animate();
            
            function engageWarp() {
                const btn = document.getElementById('engageBtn');
                btn.innerHTML = "SYSTEM ENGAGED";
                document.body.classList.add('warp-active');
                
                let acceleration = setInterval(() => {
                    speed *= 1.1;
                    if (speed > 100) {
                        clearInterval(acceleration);
                        warpActive = true;
                        setTimeout(() => {
                            document.getElementById('flash').style.opacity = '1';
                            setTimeout(() => {
                                const buttons = window.parent.document.getElementsByTagName('button');
                                let clicked = false;
                                for (let b of buttons) {
                                    if (b.innerText === "Continue") { b.click(); clicked = true; break; }
                                }
                                if (!clicked && buttons.length > 0) buttons[buttons.length-1].click();
                            }, 400);
                        }, 1800);
                    }
                }, 80);
            }
        </script>
    </body>
    </html>
    '''
    
    st.markdown("""
    <style>
    #MainMenu, footer, header, [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
    .stApp { background: #050005 !important; }
    .main .block-container { padding: 0 !important; max-width: 100% !important; }
    div[data-testid="stButton"] { display: none; }
    div.row-widget.stButton { position: fixed; top: -9999px; }
    </style>
    """, unsafe_allow_html=True)
    
    components.html(intro_html, height=900, scrolling=False)
    
    if st.button("Continue", key="continue_btn"):
        st.session_state.launched = True
        st.rerun()
    
    st.stop()


# =============================================================================
# MAIN APP CSS (RED/PURPLE PROFESSIONAL THEME)
# =============================================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&family=Rajdhani:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600&display=swap');

:root {
    --bg-dark: #050005;
    --bg-panel: rgba(20, 10, 15, 0.7);
    --border-color: rgba(255, 0, 60, 0.2);
    --primary: #ff003c;      /* Neon Red */
    --secondary: #7000ff;    /* Deep Purple */
    --text-main: #ffffff;
    --text-dim: #e2e8f0; /* Brighter for readability */
    --shadow-glow: 0 0 20px rgba(255, 0, 60, 0.2);
}

/* Global Reset & Fonts */
* { font-family: 'Rajdhani', sans-serif !important; }
h1, h2, h3, .hero-title, .stat-value, .section-title { font-family: 'Orbitron', sans-serif !important; }

#MainMenu, footer, header, [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }

/* Dynamic Background */
.stApp {
    background-color: var(--bg-dark);
    background-image: 
        radial-gradient(circle at 80% 0%, rgba(255, 0, 60, 0.08) 0%, transparent 50%),
        radial-gradient(circle at 20% 100%, rgba(112, 0, 255, 0.08) 0%, transparent 50%);
    background-attachment: fixed;
}

.main .block-container { padding: 2rem 3rem !important; max-width: 1600px; }

/* Components */
.glass {
    background: var(--bg-panel);
    backdrop-filter: blur(12px);
    border: 1px solid var(--border-color);
    box-shadow: 0 4px 20px -1px rgba(0, 0, 0, 0.3);
}

/* Hero Section */
.hero { 
    text-align: center; 
    padding: 1rem 1rem 2rem; 
    position: relative;
    border-bottom: 1px solid rgba(255, 0, 60, 0.1);
    margin-bottom: 1.5rem;
}

.badge { 
    display: inline-flex; align-items: center; gap: 8px; 
    border: 1px solid rgba(255, 0, 60, 0.5); 
    padding: 4px 12px; 
    font-size: 10px; 
    color: var(--primary); 
    text-transform: uppercase;
    letter-spacing: 3px;
    margin-bottom: 16px;
    background: rgba(255, 0, 60, 0.05);
}

.hero-title { 
    font-size: 48px; 
    font-weight: 900; 
    color: var(--text-main); 
    margin: 0 0 16px; 
    line-height: 1.1; 
    text-transform: uppercase;
    letter-spacing: 2px;
    text-shadow: 0 0 40px rgba(255, 0, 60, 0.3);
}

.gradient-text { 
    background: linear-gradient(180deg, #fff 0%, #ff003c 100%); 
    -webkit-background-clip: text; 
    -webkit-text-fill-color: transparent; 
}

.stats { 
    display: flex; justify-content: center; gap: 60px; margin-top: 30px; 
    display: inline-flex;
}
.stat { text-align: center; }
.stat-value { font-size: 28px; font-weight: 700; color: var(--text-main); margin-bottom: 4px; }
.stat-label { font-size: 10px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 3px; opacity: 0.9; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { 
    background: transparent; 
    border-bottom: 1px solid var(--border-color);
    padding: 0; gap: 20px;
}
.stTabs [data-baseweb="tab"] { 
    background: transparent; border: none; color: var(--text-dim); 
    font-family: 'Orbitron', sans-serif !important;
    font-size: 13px; text-transform: uppercase; letter-spacing: 2px;
    padding: 12px 0;
}
.stTabs [aria-selected="true"] { 
    color: var(--primary) !important; 
    border-bottom: 2px solid var(--primary) !important;
    text-shadow: 0 0 10px rgba(255, 0, 60, 0.5);
}

/* Interactive Elements */
.feature { 
    background: rgba(255,255,255,0.02);
    border: 1px solid var(--border-color); 
    padding: 20px 15px; text-align: center; 
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    height: 100%;
}
.feature:hover { 
    border-color: var(--primary); 
    background: rgba(255, 0, 60, 0.05);
    transform: translateY(-5px);
    box-shadow: 0 10px 40px -10px rgba(255, 0, 60, 0.2);
}
.feature-icon-wrapper {
    color: var(--primary);
    margin-bottom: 15px;
    display: inline-flex;
    padding: 10px;
    background: rgba(255, 0, 60, 0.1);
    border-radius: 4px;
}
.feature-title { font-weight: 700; color: var(--text-main); font-size: 13px; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 6px; }
.feature-desc { font-size: 12px; color: var(--text-dim); line-height: 1.4; }

/* Dashboard Config */
.config { 
    background: rgba(20, 10, 15, 0.5); 
    border: 1px solid var(--border-color); 
    padding: 20px; 
}
.config-title { 
    font-family: 'Orbitron', sans-serif !important;
    font-weight: 600; color: var(--primary); font-size: 13px; text-transform: uppercase; letter-spacing: 2px;
    margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid var(--border-color); 
    display: flex; align-items: center; gap: 10px;
}
.config-label { font-size: 10px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 1px; margin: 15px 0 8px; font-weight: 700; }

/* Ideas */
.idea { 
    background: linear-gradient(90deg, rgba(255, 0, 60, 0.02), transparent);
    border: 1px solid var(--border-color);
    border-left: 3px solid var(--primary);
    padding: 24px; margin-bottom: 16px; 
    transition: all 0.3s; 
}
.idea:hover { 
    border-color: var(--primary);
    background: linear-gradient(90deg, rgba(255, 0, 60, 0.08), transparent); 
}

.idea-score { color: var(--primary); font-family: 'Orbitron', sans-serif !important; font-size: 18px; font-weight: 700; letter-spacing: 1px; }

/* Metrics */
.metric { 
    background: rgba(20, 10, 15, 0.6); border: 1px solid var(--border-color); 
    padding: 24px; text-align: center; 
}
.metric-value { font-family: 'Orbitron', sans-serif !important; font-size: 32px; font-weight: 700; color: var(--text-main); }
.metric-value.red { color: var(--primary); text-shadow: 0 0 20px rgba(255, 0, 60, 0.4); }
.metric-value.purple { color: var(--secondary); text-shadow: 0 0 20px rgba(112, 0, 255, 0.4); }

/* Buttons */
.stButton > button { 
    background: transparent !important; 
    border: 1px solid var(--primary) !important; 
    color: var(--primary) !important; 
    font-family: 'Orbitron', sans-serif !important;
    text-transform: uppercase;
    letter-spacing: 3px;
    padding: 16px 32px !important; 
    transition: all 0.3s !important;
    box-shadow: 0 0 15px rgba(255, 0, 60, 0.1) !important;
    border-radius: 0 !important;
}
.stButton > button:hover { 
    background: rgba(255, 0, 60, 0.1) !important; 
    box-shadow: 0 0 40px rgba(255, 0, 60, 0.6) !important;
    text-shadow: 0 0 5px rgba(255, 0, 60, 1) !important;
    border-color: #fff !important;
    color: #fff !important;
}

/* Status */
.status { 
    border-left: 2px solid var(--primary); 
    background: linear-gradient(90deg, rgba(255, 0, 60, 0.1), transparent);
    padding: 16px 20px; margin: 16px 0; color: var(--text-main); font-size: 14px; 
    font-family: 'Orbitron', sans-serif !important; letter-spacing: 2px;
}
.status-done { 
    border-color: #fff; 
    background: linear-gradient(90deg, rgba(255, 255, 255, 0.1), transparent); 
    color: #fff;
    text-shadow: 0 0 10px rgba(255,255,255,0.5);
}

.section-title { font-size: 22px; font-weight: 700; color: var(--text-main); margin-bottom: 8px; text-transform: uppercase; border-left: 3px solid var(--primary); padding-left: 16px; letter-spacing: 1px; }

</style>
""", unsafe_allow_html=True)

# =============================================================================
# MAIN APP LAYOUT
# =============================================================================

st.markdown("""
<div class="hero">
    <div class="badge">System Online</div>
    <h1 class="hero-title">Startup Idea<br><span class="gradient-text">Generator Core</span></h1>
    <div class="stats">
        <div class="stat"><div class="stat-value">4</div><div class="stat-label">Streams</div></div>
        <div class="stat"><div class="stat-value">150+</div><div class="stat-label">Signals</div></div>
        <div class="stat"><div class="stat-value">T-60s</div><div class="stat-label">Compute</div></div>
    </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["⚡ GENERATE", "📊 DATA", "📁 EXPORT", "📖 SYSTEM"])

with tab1:
    c1, c2 = st.columns([2.5, 1])
    
    with c2:
        st.markdown(f'<div class="config"><div class="config-title">{get_icon("settings")} PARAMETERS</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="config-label">Data Sources</div>', unsafe_allow_html=True)
        g = st.checkbox("GitHub Trending", value=True)
        n = st.checkbox("News Feed", value=True)
        s = st.checkbox("Search Index", value=True)
        r = st.checkbox("Social Signals", value=False)
        st.markdown('<div class="config-label">Model Settings</div>', unsafe_allow_html=True)
        llm = st.checkbox("AI Inference", value=True)
        num = st.slider("Output Count", 5, 25, 10)
        pp = st.slider("Signal Density", 20, 100, 40)
        
        st.markdown('<div class="config-label">Advanced Modules</div>', unsafe_allow_html=True)
        use_council = st.checkbox("Consensus Protocol", value=False, help="Use multiple AI models that review each other's work")
        
        if use_council:
            st.markdown(f'<div class="config-label">{get_icon("lock")} Access Keys</div>', unsafe_allow_html=True)
            openrouter_key = st.text_input("OpenRouter Key", type="password", key="openrouter_key")
            if openrouter_key: os.environ["OPENROUTER_API_KEY"] = openrouter_key
        
        if llm and not use_council:
            st.markdown(f'<div class="config-label">{get_icon("lock")} Access Keys</div>', unsafe_allow_html=True)
            groq_key = st.text_input("Groq Key (Optional)", type="password", key="groq_key")
            if groq_key: os.environ["GROQ_API_KEY"] = groq_key
    
    with c1:
        st.markdown("""
        <div class="section-title">Initialize Generation Sequence</div>
        <div style="margin-left: 20px; color: #e2e8f0; font-size: 14px; margin-bottom: 20px; opacity: 0.9;">Scanning global data streams for high-value opportunities via neural interpretation layers.</div>
        """, unsafe_allow_html=True)
        
        # Features Grid with SVGs
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            st.markdown(f'<div class="feature"><div class="feature-icon-wrapper">{get_icon("live_data")}</div><div class="feature-title">Live Data</div><div class="feature-desc">Real-time ingestion</div></div>', unsafe_allow_html=True)
        with col_f2:
            st.markdown(f'<div class="feature"><div class="feature-icon-wrapper">{get_icon("neural")}</div><div class="feature-title">Neural Net</div><div class="feature-desc">Deep pattern matching</div></div>', unsafe_allow_html=True)
        with col_f3:
            st.markdown(f'<div class="feature"><div class="feature-icon-wrapper">{get_icon("ranking")}</div><div class="feature-title">Ranking</div><div class="feature-desc">Multi-variable score</div></div>', unsafe_allow_html=True)
        with col_f4:
            st.markdown(f'<div class="feature"><div class="feature-icon-wrapper">{get_icon("code")}</div><div class="feature-title">Architecture</div><div class="feature-desc">Stack generation</div></div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        if st.button("INITIATE SEQUENCE", use_container_width=True):
            prog = st.progress(0)
            stat = st.empty()
            pps = []
            
            stat.markdown('<div class="status"> ESTABLISHING DOWNLINK...</div>', unsafe_allow_html=True)
            
            # (Logic remains same)
            if g:
                try:
                    prog.progress(10)
                    from src.intelligence.collectors.github_collector import GitHubCollector
                    pps.extend(GitHubCollector().collect())
                except Exception as e: st.warning(f"GitHub: {e}")
            
            if n:
                try:
                    prog.progress(25)
                    from src.intelligence.collectors.news_collector import NewsCollector
                    pps.extend(NewsCollector().collect())
                except Exception as e: st.warning(f"News: {e}")
            
            if s:
                try:
                    prog.progress(40)
                    from src.intelligence.collectors.search_collector import SearchCollector
                    pps.extend(SearchCollector().collect())
                except Exception as e: st.warning(f"Search: {e}")
            
            if r:
                try:
                    prog.progress(50)
                    from src.intelligence.sources.reddit import RedditSource
                    reddit_source = RedditSource()
                    reddit_data = reddit_source.collect()
                    if reddit_data: pps.extend(reddit_data)
                except Exception as e: st.warning(f"Reddit: {e}")
            
            if not pps:
                st.error("No signals detected. Verify connection.")
            else:
                st.session_state['pain_points'] = pps
                prog.progress(60)
                
                if use_council:
                    stat.markdown('<div class="status"> CONVENING CONSENSUS PROTOCOL...</div>', unsafe_allow_html=True)
                    try:
                        from src.llm_council import LLMCouncil
                        council = LLMCouncil()
                        def update_status(msg): stat.markdown(f'<div class="status"> {msg}</div>', unsafe_allow_html=True)
                        
                        pain_point_strs = []
                        for p in pps[:pp]:
                            if hasattr(p, 'description'): pain_point_strs.append(p.description)
                            elif hasattr(p, 'text'): pain_point_strs.append(p.text)
                            else: pain_point_strs.append(str(p))
                        
                        council_result = asyncio.run(council.generate_ideas(pain_point_strs, num_ideas=num, on_stage_complete=update_status))
                        st.session_state['council_result'] = council_result
                        if 'ideas' in st.session_state: del st.session_state['ideas']
                        if 'evaluations' in st.session_state: del st.session_state['evaluations']
                        prog.progress(100)
                        stat.markdown('<div class="status status-done"> PROTOCOL COMPLETE. DATA READY.</div>', unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Council error: {e}")
                else:
                    stat.markdown('<div class="status"> NEURAL PROCESSING ACTIVE...</div>', unsafe_allow_html=True)
                    from src.config import load_config
                    from src.models import IntelligenceData
                    cfg = load_config('config.yml')
                    intel = IntelligenceData(pain_points=pps[:pp], emerging_industries=[], competitors=[], opportunity_categories=[])
                    
                    try:
                        if llm:
                            from src.idea_generation import LLMIdeaGenerationEngine
                            idea_catalog = asyncio.run(LLMIdeaGenerationEngine(cfg, 'groq').generate_async(intel))
                        else:
                            from src.idea_generation import IdeaGenerationEngine
                            idea_catalog = asyncio.run(IdeaGenerationEngine(cfg).generate(intel))
                        
                        ideas = idea_catalog.ideas if hasattr(idea_catalog, 'ideas') else idea_catalog
                        st.session_state['ideas'] = ideas
                        
                        prog.progress(80)
                        stat.markdown('<div class="status"> CALCULATING VIABILITY SCORES...</div>', unsafe_allow_html=True)
                        
                        from src.scoring import ScoringEngine
                        eval_report = asyncio.run(ScoringEngine(cfg).evaluate(idea_catalog, intel))
                        evals = eval_report.evaluated_ideas if hasattr(eval_report, 'evaluated_ideas') else []
                        st.session_state['evaluations'] = evals
                        
                        prog.progress(90)
                        try:
                            out = Path(f"./output/run_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                            out.mkdir(parents=True, exist_ok=True)
                            if evals:
                                data = []
                                for e in evals:
                                    idea = next((i for i in ideas if i.id == e.idea_id), None)
                                    if idea:
                                        idea_dict = idea.model_dump() if hasattr(idea, 'model_dump') else vars(idea)
                                        idea_dict['score'] = e.total_score
                                        data.append(idea_dict)
                                with open(out/'ideas.json','w') as f: json.dump(data, f, indent=2, default=str)
                        except: pass
                        
                        prog.progress(100)
                        stat.markdown('<div class="status status-done"> PROCESSING COMPLETE. RESULTS AVAILABLE.</div>', unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Processing Error: {e}")

with tab2:
    if 'council_result' in st.session_state and st.session_state['council_result']:
        council = st.session_state['council_result']
        st.markdown('<div class="section-title">Consensus Results</div>', unsafe_allow_html=True)
        members = council.get('council_members', [])
        st.markdown(f'<div class="section-sub"><span class="badge">COUNCIL</span> {" • ".join(members)}</div>', unsafe_allow_html=True)
        st.markdown(council.get('final_ideas', 'No ideas generated'))
    
    elif 'ideas' in st.session_state and st.session_state.get('ideas'):
        ideas = st.session_state['ideas']
        evals = st.session_state.get('evaluations', [])
        pps = st.session_state.get('pain_points', [])
        if not isinstance(evals, list): evals = []
        
        top = evals[0].total_score if evals else 0
        avg = sum(e.total_score for e in evals)/len(evals) if evals else 0
        
        st.markdown(f'<div class="metrics"><div class="metric"><div class="metric-value red">{len(ideas)}</div><div class="metric-label">Objects</div></div><div class="metric"><div class="metric-value red">{top:.0f}</div><div class="metric-label">Max Score</div></div><div class="metric"><div class="metric-value purple">{avg:.0f}</div><div class="metric-label">Mean Score</div></div><div class="metric"><div class="metric-value">{len(pps)}</div><div class="metric-label">Inputs</div></div></div>', unsafe_allow_html=True)
        
        displayed_count = 0
        st.markdown('<div class="section-title">High Priority Targets</div>', unsafe_allow_html=True)
        
        for i, e in enumerate(evals[:10]):
            idea = next((x for x in ideas if x.id==e.idea_id), None)
            if not idea: continue
            
            displayed_count += 1
            problem = getattr(idea, "problem_statement", "N/A")
            solution = getattr(idea, "solution_description", "N/A")
            revenue = getattr(idea, "revenue_model", "N/A")
            tam = getattr(idea, "tam_estimate", "N/A")
            
            problem_preview = problem[:150] + "..." if len(problem) > 150 else problem
            solution_preview = solution[:150] + "..." if len(solution) > 150 else solution
            
            st.markdown(f'<div class="idea"><div class="idea-header"><div class="idea-rank">0{displayed_count}</div><div class="idea-score">:// {e.total_score:.0f}</div></div><div class="idea-name">{idea.name}</div><div class="idea-text"><strong style="color:var(--primary)">PROBLEM:</strong> {problem_preview}</div><div class="idea-text"><strong style="color:var(--primary)">SOLUTION:</strong> {solution_preview}</div><div class="idea-footer"><div><div class="idea-meta-label">Revenue Model</div><div class="idea-meta-value">{revenue[:50]}</div></div><div><div class="idea-meta-label">Est. Market</div><div class="idea-meta-value">{tam[:50]}</div></div></div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="empty"><div class="empty-icon">⚠️</div><div>No Data. Initiate Generation Sequence.</div></div>', unsafe_allow_html=True)

with tab3:
    st.markdown('<div class="section-title">Data Export</div>', unsafe_allow_html=True)
    output_dir = Path('./output')
    runs = sorted([r for r in output_dir.glob('run_*') if r.is_dir()], reverse=True) if output_dir.exists() else []
    if runs:
        sel = st.selectbox("Select Dataset:", [r.name for r in runs], label_visibility="collapsed")
        for f in (Path('./output')/sel).glob('*'):
            if f.is_file():
                c1, c2 = st.columns([5,1])
                with c1: st.write(f"📄 **{f.name}**")
                with c2:
                    with open(f,'rb') as fp: st.download_button("⬇", fp, f.name)
    else:
        st.write("No archives found.")

with tab4:
    st.markdown('<div class="section-title">System Manual</div>', unsafe_allow_html=True)
    st.markdown('<div class="glass"><h3>Pipeline Architecture</h3><p>Ingestion → NLP Analysis → Scoring Heuristics → Stack Assembly</p></div>', unsafe_allow_html=True)

st.markdown('<div style="text-align: center; margin-top: 50px; color: #52525b; font-size: 10px; text-transform: uppercase;">System Ready • v2.1.0 • Redacted</div>', unsafe_allow_html=True)
