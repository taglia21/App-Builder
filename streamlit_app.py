"""
AI Startup Generator - Epic Rocket Launch Experience
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
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if 'launched' not in st.session_state:
    st.session_state.launched = False

# =============================================================================
# EPIC ROCKET INTRO
# =============================================================================

if not st.session_state.launched:
    
    intro_html = '''
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', sans-serif;
        }
        
        body {
            background: linear-gradient(180deg, #000000 0%, #0a0a1a 30%, #0f0f2a 60%, #1a1a3a 100%);
            min-height: 100vh;
            overflow: hidden;
            position: relative;
        }
        
        .space-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
        }
        
        /* Stars */
        .stars {
            position: absolute;
            width: 100%;
            height: 100%;
        }
        
        .star {
            position: absolute;
            background: white;
            border-radius: 50%;
            animation: twinkle 2s ease-in-out infinite;
        }
        
        @keyframes twinkle {
            0%, 100% { opacity: 0.3; transform: scale(1); }
            50% { opacity: 1; transform: scale(1.2); }
        }
        
        /* Shooting stars */
        .shooting-star {
            position: absolute;
            width: 80px;
            height: 2px;
            background: linear-gradient(90deg, white, transparent);
            animation: shoot 4s linear infinite;
            opacity: 0;
        }
        
        @keyframes shoot {
            0% { transform: translateX(0) translateY(0); opacity: 0; }
            5% { opacity: 1; }
            100% { transform: translateX(500px) translateY(300px); opacity: 0; }
        }
        
        /* Sun */
        .sun {
            position: absolute;
            top: 8%;
            right: 10%;
            width: 80px;
            height: 80px;
            background: radial-gradient(circle, #ffdd00 0%, #ff8800 50%, #ff4400 100%);
            border-radius: 50%;
            box-shadow: 0 0 60px #ff8800, 0 0 100px #ff6600, 0 0 140px #ff4400;
            animation: sunPulse 4s ease-in-out infinite;
        }
        
        @keyframes sunPulse {
            0%, 100% { transform: scale(1); box-shadow: 0 0 60px #ff8800, 0 0 100px #ff6600; }
            50% { transform: scale(1.1); box-shadow: 0 0 80px #ff8800, 0 0 120px #ff6600; }
        }
        
        /* Earth */
        .earth {
            position: absolute;
            top: 20%;
            left: 8%;
            width: 100px;
            height: 100px;
            background: radial-gradient(circle at 30% 30%, #4a9fff 0%, #1e5aa8 40%, #0c3d6e 100%);
            border-radius: 50%;
            box-shadow: inset -10px -10px 20px rgba(0,0,0,0.5), 0 0 20px rgba(74, 159, 255, 0.3);
            animation: planetFloat 8s ease-in-out infinite;
            overflow: hidden;
        }
        
        .earth::before {
            content: '';
            position: absolute;
            top: 20%;
            left: 10%;
            width: 30px;
            height: 20px;
            background: #2d8f2d;
            border-radius: 50%;
        }
        
        .earth::after {
            content: '';
            position: absolute;
            top: 50%;
            left: 40%;
            width: 25px;
            height: 15px;
            background: #2d8f2d;
            border-radius: 50%;
        }
        
        @keyframes planetFloat {
            0%, 100% { transform: translateY(0) rotate(0deg); }
            50% { transform: translateY(-15px) rotate(5deg); }
        }
        
        /* Mars */
        .mars {
            position: absolute;
            bottom: 25%;
            left: 12%;
            width: 50px;
            height: 50px;
            background: radial-gradient(circle at 30% 30%, #ff6b4a 0%, #cc4422 60%, #8b2500 100%);
            border-radius: 50%;
            box-shadow: inset -5px -5px 15px rgba(0,0,0,0.5);
            animation: planetFloat 10s ease-in-out infinite;
            animation-delay: -3s;
        }
        
        /* Saturn */
        .saturn {
            position: absolute;
            top: 35%;
            right: 15%;
            width: 70px;
            height: 70px;
            background: radial-gradient(circle at 30% 30%, #f4d59e 0%, #c9a227 60%, #8b7355 100%);
            border-radius: 50%;
            box-shadow: inset -5px -5px 15px rgba(0,0,0,0.4);
            animation: planetFloat 12s ease-in-out infinite;
            animation-delay: -5s;
        }
        
        .saturn::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) rotateX(75deg);
            width: 120px;
            height: 120px;
            border: 8px solid rgba(200, 180, 150, 0.5);
            border-radius: 50%;
        }
        
        /* Moon */
        .moon {
            position: absolute;
            bottom: 35%;
            right: 8%;
            width: 40px;
            height: 40px;
            background: radial-gradient(circle at 30% 30%, #f5f5f5 0%, #c9c9c9 50%, #888 100%);
            border-radius: 50%;
            box-shadow: inset -3px -3px 10px rgba(0,0,0,0.3);
            animation: planetFloat 6s ease-in-out infinite;
            animation-delay: -2s;
        }
        
        /* Asteroids */
        .asteroid {
            position: absolute;
            background: linear-gradient(135deg, #666 0%, #333 100%);
            border-radius: 40% 60% 70% 30% / 40% 50% 60% 50%;
            animation: asteroidTumble 8s linear infinite;
        }
        
        @keyframes asteroidTumble {
            0% { transform: rotate(0deg) translateX(0); }
            100% { transform: rotate(360deg) translateX(20px); }
        }
        
        /* UFOs */
        .ufo {
            position: absolute;
            animation: ufoFly 15s linear infinite;
        }
        
        .ufo-body {
            width: 60px;
            height: 20px;
            background: linear-gradient(180deg, #888 0%, #444 100%);
            border-radius: 50%;
            position: relative;
        }
        
        .ufo-dome {
            position: absolute;
            top: -15px;
            left: 50%;
            transform: translateX(-50%);
            width: 30px;
            height: 20px;
            background: linear-gradient(180deg, rgba(0, 255, 200, 0.6) 0%, rgba(0, 200, 150, 0.8) 100%);
            border-radius: 50% 50% 0 0;
        }
        
        .ufo-lights {
            position: absolute;
            bottom: -5px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 8px;
        }
        
        .ufo-light {
            width: 6px;
            height: 6px;
            background: #0ff;
            border-radius: 50%;
            animation: ufoLight 0.5s ease-in-out infinite alternate;
        }
        
        @keyframes ufoLight {
            0% { opacity: 0.3; }
            100% { opacity: 1; box-shadow: 0 0 10px #0ff; }
        }
        
        @keyframes ufoFly {
            0% { left: -100px; top: 30%; }
            50% { top: 25%; }
            100% { left: calc(100% + 100px); top: 35%; }
        }
        
        /* Aliens */
        .alien {
            position: absolute;
            font-size: 35px;
            animation: alienFloat 5s ease-in-out infinite;
        }
        
        @keyframes alienFloat {
            0%, 100% { transform: translateY(0) rotate(-5deg); }
            50% { transform: translateY(-20px) rotate(5deg); }
        }
        
        /* Main content */
        .content {
            position: relative;
            z-index: 10;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            text-align: center;
            padding: 20px;
        }
        
        /* Rocket */
        .rocket-container {
            cursor: pointer;
            transition: transform 0.3s ease;
            position: relative;
        }
        
        .rocket-container:hover {
            transform: scale(1.05);
        }
        
        .rocket-container.launching {
            animation: rocketShake 0.1s ease-in-out infinite;
        }
        
        .rocket-container.blastoff {
            animation: blastOff 1.5s ease-in forwards;
        }
        
        @keyframes rocketShake {
            0%, 100% { transform: translateX(0) rotate(0); }
            25% { transform: translateX(-4px) rotate(-1deg); }
            75% { transform: translateX(4px) rotate(1deg); }
        }
        
        @keyframes blastOff {
            0% { transform: translateY(0); }
            100% { transform: translateY(-120vh); }
        }
        
        .rocket-svg {
            width: 140px;
            height: 200px;
            filter: drop-shadow(0 0 20px rgba(0, 200, 255, 0.4));
        }
        
        .flames {
            transform-origin: top center;
            animation: flameFlicker 0.1s ease-in-out infinite alternate;
        }
        
        .rocket-container.launching .flames {
            animation: flameGrow 0.3s ease-out forwards, flameFlicker 0.05s ease-in-out infinite alternate;
        }
        
        @keyframes flameFlicker {
            0% { opacity: 0.8; transform: scaleY(0.95); }
            100% { opacity: 1; transform: scaleY(1.05); }
        }
        
        @keyframes flameGrow {
            0% { transform: scaleY(1); }
            100% { transform: scaleY(2); }
        }
        
        /* Smoke */
        .smoke-container {
            position: absolute;
            bottom: -20px;
            left: 50%;
            transform: translateX(-50%);
            display: none;
        }
        
        .rocket-container.launching .smoke-container {
            display: block;
        }
        
        .smoke {
            position: absolute;
            background: radial-gradient(circle, rgba(200,200,200,0.8) 0%, rgba(150,150,150,0.4) 50%, transparent 70%);
            border-radius: 50%;
            animation: smokePuff 1s ease-out forwards;
        }
        
        @keyframes smokePuff {
            0% { transform: scale(0.3); opacity: 0.8; }
            100% { transform: scale(4); opacity: 0; }
        }
        
        /* Text */
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(139, 92, 246, 0.15);
            border: 1px solid rgba(139, 92, 246, 0.3);
            border-radius: 50px;
            padding: 10px 20px;
            font-size: 14px;
            color: #a78bfa;
            margin: 30px 0 20px;
        }
        
        .badge-dot {
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
            box-shadow: 0 0 10px #10b981;
            animation: pulse 2s ease infinite;
        }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.3); }
        }
        
        .title {
            font-size: 48px;
            font-weight: 800;
            color: white;
            margin-bottom: 10px;
            line-height: 1.2;
        }
        
        .gradient-text {
            background: linear-gradient(135deg, #06b6d4, #8b5cf6, #ec4899);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-size: 200% 200%;
            animation: gradientMove 4s ease infinite;
        }
        
        @keyframes gradientMove {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
        }
        
        .subtitle {
            font-size: 18px;
            color: rgba(255,255,255,0.7);
            margin-top: 20px;
            text-align: center;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
        }
        
        .click-hint {
            font-size: 16px;
            color: rgba(255,255,255,0.8);
            margin-top: 15px;
            animation: bounce 2s ease infinite;
        }
        
        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-5px); }
        }
        
        /* Page transition */
        .intro-wrapper {
            transition: transform 1s ease-in;
        }
        
        .intro-wrapper.slide-up {
            transform: translateY(-100vh);
        }
        
        /* Enter button (appears after animation) */
        .enter-btn {
            display: none;
            background: linear-gradient(135deg, #06b6d4, #8b5cf6);
            border: none;
            border-radius: 14px;
            padding: 16px 48px;
            font-size: 18px;
            font-weight: 700;
            color: white;
            cursor: pointer;
            margin-top: 30px;
            box-shadow: 0 4px 30px rgba(139, 92, 246, 0.4);
            animation: fadeIn 0.5s ease forwards;
        }
        
        .enter-btn.show {
            display: inline-block;
        }
        
        @keyframes fadeIn {
            0% { opacity: 0; transform: translateY(20px); }
            100% { opacity: 1; transform: translateY(0); }
        }
        
        .enter-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 6px 40px rgba(139, 92, 246, 0.5);
        }
    </style>
    </head>
    <body>
        <div class="intro-wrapper" id="introWrapper">
            <div class="space-container">
                <!-- Stars generated by JS -->
                <div class="stars" id="stars"></div>
                
                <!-- Shooting stars -->
                <div class="shooting-star" style="top: 10%; left: 5%; animation-delay: 0s;"></div>
                <div class="shooting-star" style="top: 30%; left: 20%; animation-delay: 2s;"></div>
                <div class="shooting-star" style="top: 50%; left: 40%; animation-delay: 4s;"></div>
                
                <!-- Sun -->
                <div class="sun"></div>
                
                <!-- Planets -->
                <div class="earth"></div>
                <div class="mars"></div>
                <div class="saturn"></div>
                <div class="moon"></div>
                
                <!-- Asteroids -->
                <div class="asteroid" style="top: 15%; left: 30%; width: 15px; height: 12px; animation-delay: 0s;"></div>
                <div class="asteroid" style="top: 60%; left: 75%; width: 20px; height: 16px; animation-delay: -2s;"></div>
                <div class="asteroid" style="top: 75%; left: 20%; width: 12px; height: 10px; animation-delay: -4s;"></div>
                <div class="asteroid" style="top: 40%; left: 85%; width: 18px; height: 14px; animation-delay: -6s;"></div>
                <div class="asteroid" style="top: 80%; left: 60%; width: 14px; height: 11px; animation-delay: -3s;"></div>
                
                <!-- UFOs -->
                <div class="ufo" style="animation-delay: 0s;">
                    <div class="ufo-dome"></div>
                    <div class="ufo-body"></div>
                    <div class="ufo-lights">
                        <div class="ufo-light"></div>
                        <div class="ufo-light" style="animation-delay: 0.2s;"></div>
                        <div class="ufo-light" style="animation-delay: 0.4s;"></div>
                    </div>
                </div>
                <div class="ufo" style="animation-delay: -8s; animation-duration: 20s;">
                    <div class="ufo-dome"></div>
                    <div class="ufo-body"></div>
                    <div class="ufo-lights">
                        <div class="ufo-light"></div>
                        <div class="ufo-light" style="animation-delay: 0.2s;"></div>
                        <div class="ufo-light" style="animation-delay: 0.4s;"></div>
                    </div>
                </div>
                
                <!-- Aliens -->
                <div class="alien" style="top: 25%; right: 25%; animation-delay: 0s;">👽</div>
                <div class="alien" style="bottom: 20%; left: 25%; animation-delay: -2s;">👾</div>
                <div class="alien" style="top: 55%; right: 5%; animation-delay: -1s; font-size: 28px;">🛸</div>
            </div>
            
            <div class="content">
                <!-- Rocket -->
                <div class="rocket-container" id="rocket" onclick="launchRocket()">
                    <svg class="rocket-svg" viewBox="0 0 100 180" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <defs>
                            <linearGradient id="bodyGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                                <stop offset="0%" stop-color="#e8e8e8"/>
                                <stop offset="50%" stop-color="#ffffff"/>
                                <stop offset="100%" stop-color="#c8c8c8"/>
                            </linearGradient>
                            <linearGradient id="windowGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                                <stop offset="0%" stop-color="#00d4ff"/>
                                <stop offset="100%" stop-color="#0088cc"/>
                            </linearGradient>
                            <linearGradient id="finGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                                <stop offset="0%" stop-color="#ff5555"/>
                                <stop offset="100%" stop-color="#cc2222"/>
                            </linearGradient>
                            <linearGradient id="flameGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                                <stop offset="0%" stop-color="#00ccff"/>
                                <stop offset="25%" stop-color="#ffcc00"/>
                                <stop offset="50%" stop-color="#ff8800"/>
                                <stop offset="100%" stop-color="#ff2200"/>
                            </linearGradient>
                        </defs>
                        
                        <!-- Body -->
                        <path d="M50 8 C50 8 78 35 78 75 L78 115 L22 115 L22 75 C22 35 50 8 50 8Z" fill="url(#bodyGrad)" stroke="#aaa" stroke-width="1"/>
                        
                        <!-- Window -->
                        <circle cx="50" cy="55" r="14" fill="url(#windowGrad)" stroke="#0099dd" stroke-width="2"/>
                        <circle cx="45" cy="50" r="4" fill="white" opacity="0.6"/>
                        
                        <!-- Stripes -->
                        <rect x="27" y="82" width="46" height="6" rx="2" fill="#ff4444"/>
                        <rect x="27" y="93" width="46" height="6" rx="2" fill="#ff4444"/>
                        
                        <!-- Fins -->
                        <path d="M22 90 L5 125 L22 115Z" fill="url(#finGrad)"/>
                        <path d="M78 90 L95 125 L78 115Z" fill="url(#finGrad)"/>
                        <path d="M38 115 L50 138 L62 115Z" fill="url(#finGrad)"/>
                        
                        <!-- Engine -->
                        <ellipse cx="50" cy="117" rx="14" ry="5" fill="#555"/>
                        
                        <!-- Flames -->
                        <g class="flames">
                            <path d="M50 120 Q38 145 50 175 Q62 145 50 120Z" fill="url(#flameGrad)" opacity="0.9"/>
                            <path d="M38 120 Q28 140 36 160 Q44 140 38 120Z" fill="url(#flameGrad)" opacity="0.7"/>
                            <path d="M62 120 Q72 140 64 160 Q56 140 62 120Z" fill="url(#flameGrad)" opacity="0.7"/>
                        </g>
                    </svg>
                    
                    <div class="smoke-container" id="smokeContainer"></div>
                </div>
                
                <div class="badge">
                    <span class="badge-dot"></span>
                    AI-Powered Platform
                </div>
                
                <h1 class="title">
                    Ready to discover your<br>
                    <span class="gradient-text">Billion Dollar Idea?</span>
                </h1>
                
                <p class="subtitle">Transform real-time market data into startup opportunities</p>
                
                <p class="click-hint" id="clickHint">👆 Click the rocket to blast off!</p>
            </div>
        </div>
        
        <script>
            // Generate stars
            const starsContainer = document.getElementById('stars');
            for (let i = 0; i < 200; i++) {
                const star = document.createElement('div');
                star.className = 'star';
                star.style.left = Math.random() * 100 + '%';
                star.style.top = Math.random() * 100 + '%';
                star.style.width = (Math.random() * 2.5 + 0.5) + 'px';
                star.style.height = star.style.width;
                star.style.animationDelay = Math.random() * 2 + 's';
                starsContainer.appendChild(star);
            }
            
            let launched = false;
            
            function launchRocket() {
                if (launched) return;
                launched = true;
                
                const rocket = document.getElementById('rocket');
                const smokeContainer = document.getElementById('smokeContainer');
                const clickHint = document.getElementById('clickHint');
                const enterBtn = document.getElementById('enterBtn');
                const introWrapper = document.getElementById('introWrapper');
                
                // Hide click hint
                clickHint.style.display = 'none';
                
                // Phase 1: Shake and smoke (2 seconds)
                rocket.classList.add('launching');
                
                // Add smoke particles
                for (let i = 0; i < 8; i++) {
                    setTimeout(() => {
                        const smoke = document.createElement('div');
                        smoke.className = 'smoke';
                        smoke.style.width = (30 + Math.random() * 40) + 'px';
                        smoke.style.height = smoke.style.width;
                        smoke.style.left = (-20 + Math.random() * 40) + 'px';
                        smoke.style.animationDelay = (Math.random() * 0.3) + 's';
                        smokeContainer.appendChild(smoke);
                    }, i * 200);
                }
                
                // Phase 2: Blast off (after 2 seconds)
                setTimeout(() => {
                    rocket.classList.remove('launching');
                    rocket.classList.add('blastoff');
                }, 2000);
                
                // Phase 3: Slide page up (after 3.5 seconds)
                setTimeout(() => {
                    introWrapper.classList.add('slide-up');
                }, 3500);
                
                // Automatically trigger Streamlit transition (after 4.5 seconds)
                setTimeout(() => {
                    const btn = window.parent.document.querySelector('button[key="continue_btn"]');
                    if (btn) {
                        btn.click();
                    } else {
                        // Fallback: try any button
                        const allBtns = window.parent.document.querySelectorAll('button');
                        if (allBtns.length > 0) allBtns[allBtns.length - 1].click();
                    }
                }, 4500);
            }
            

        </script>
    </body>
    </html>
    '''
    
    # Hide streamlit elements for intro
    st.markdown("""
    <style>
    #MainMenu, footer, header, [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
    .stApp { background: #0a0a1a !important; }
    .main .block-container { padding: 0 !important; max-width: 100% !important; }
    </style>
    """, unsafe_allow_html=True)
    
    components.html(intro_html, height=750, scrolling=False)
    
    # Hidden button for state change
    if st.button("Continue", key="continue_btn"):
        st.session_state.launched = True
        st.rerun()
    
    st.stop()


# =============================================================================
# MAIN APP CSS
# =============================================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --bg: #0a0a1a;
    --card: rgba(255,255,255,0.03);
    --border: rgba(255,255,255,0.08);
    --text: #ffffff;
    --dim: #ffffff;
    --muted: #ffffff;
    --cyan: #06b6d4;
    --purple: #8b5cf6;
    --pink: #ec4899;
    --green: #10b981;
}

* { font-family: 'Inter', sans-serif; }
#MainMenu, footer, header, [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
.stApp { background: var(--bg); }
.main .block-container { padding: 2rem 3rem; max-width: 1300px; }

.hero { text-align: center; padding: 2rem 1rem; }
.badge { display: inline-flex; align-items: center; gap: 8px; background: rgba(139,92,246,0.1); border: 1px solid rgba(139,92,246,0.3); border-radius: 50px; padding: 6px 14px; font-size: 12px; color: #a78bfa; margin-bottom: 16px; }
.hero-title { font-size: 40px; font-weight: 800; color: var(--text); margin: 0 0 12px; line-height: 1.15; }
.gradient-text { background: linear-gradient(135deg, #06b6d4, #8b5cf6, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.hero-sub { font-size: 16px; color: #ffffff; max-width: 450px; margin: 0 auto 20px; text-align: center !important; display: block !important; }
.stats { display: flex; justify-content: center; gap: 40px; }
.stat { text-align: center; }
.stat-value { font-size: 28px; font-weight: 700; color: var(--cyan); }
.stat-label { font-size: 10px; color: #ffffff; text-transform: uppercase; letter-spacing: 1px; }

.stTabs [data-baseweb="tab-list"] { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 4px; justify-content: center; }
.stTabs [data-baseweb="tab"] { background: transparent; border-radius: 8px; color: #ffffff; font-weight: 500; font-size: 13px; padding: 8px 16px; }
.stTabs [aria-selected="true"] { background: linear-gradient(135deg, var(--cyan), var(--purple)) !important; color: white !important; }

.features { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 20px 0; }
.feature { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px; text-align: center; transition: all 0.2s; }
.feature:hover { transform: translateY(-3px); border-color: var(--cyan); }
.feature-icon { font-size: 20px; margin-bottom: 8px; }
.feature-title { font-weight: 600; color: var(--text); font-size: 13px; margin-bottom: 4px; }
.feature-desc { font-size: 11px; color: #ffffff; }

.config { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px; }
.config-title { font-weight: 600; color: var(--text); font-size: 13px; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid var(--border); }
.config-label { font-size: 9px; color: #ffffff; text-transform: uppercase; letter-spacing: 1px; margin: 12px 0 6px; }

.stCheckbox { background: rgba(255,255,255,0.02); border: 1px solid var(--border); border-radius: 6px; padding: 6px 10px; margin-bottom: 4px; }
.stCheckbox:hover { border-color: var(--purple); }
.stCheckbox label, .stCheckbox p, [data-testid="stCheckbox"] label p { color: var(--text) !important; font-size: 12px !important; }

.stButton > button { background: linear-gradient(135deg, var(--cyan), var(--purple)) !important; color: white !important; border: none !important; padding: 10px 20px !important; font-weight: 600 !important; font-size: 13px !important; border-radius: 8px !important; box-shadow: 0 4px 15px rgba(139,92,246,0.3) !important; }
.stButton > button:hover { transform: translateY(-2px) !important; }

.metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
.metric { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 14px; text-align: center; }
.metric-value { font-size: 28px; font-weight: 700; }
.metric-value.cyan { color: var(--cyan); }
.metric-value.green { color: var(--green); }
.metric-value.purple { color: var(--purple); }
.metric-value.pink { color: var(--pink); }
.metric-label { font-size: 9px; color: #ffffff; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }

.idea { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px; margin-bottom: 10px; transition: all 0.2s; }
.idea:hover { transform: translateX(4px); border-color: var(--cyan); }
.idea-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.idea-rank { width: 28px; height: 28px; background: linear-gradient(135deg, var(--cyan), var(--purple)); border-radius: 6px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 12px; color: white; }
.idea-score { background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.2); color: var(--green); padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; }
.idea-name { font-size: 16px; font-weight: 600; color: var(--text); margin-bottom: 10px; }
.idea-label { font-size: 10px; color: var(--cyan); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 3px; font-weight: 600; }
.idea-text { color: #ffffff; font-size: 13px; line-height: 1.6; margin-bottom: 10px; }
.idea-footer { display: flex; gap: 20px; padding-top: 10px; border-top: 1px solid var(--border); }
.idea-meta-label { font-size: 10px; color: #ffffff; text-transform: uppercase; font-weight: 600; }
.idea-meta-value { color: #ffffff; font-size: 13px; font-weight: 500; }

.section-title { font-size: 20px; font-weight: 700; color: var(--text); margin-bottom: 6px; }
.section-sub { color: #ffffff; font-size: 13px; margin-bottom: 16px; }
.empty { text-align: center; padding: 40px; color: #ffffff; }
.empty-icon { font-size: 40px; opacity: 0.3; margin-bottom: 12px; }
.status { background: rgba(6,182,212,0.05); border: 1px solid rgba(6,182,212,0.2); border-radius: 8px; padding: 10px 14px; margin: 10px 0; color: var(--text); font-size: 13px; }
.status-done { background: rgba(16,185,129,0.05); border-color: rgba(16,185,129,0.2); }
.stProgress > div > div { background: linear-gradient(90deg, var(--cyan), var(--purple)) !important; }
.stProgress > div { background: rgba(255,255,255,0.1) !important; }
.glass { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px; margin-bottom: 10px; }
.glass h3 { color: var(--text); font-size: 14px; margin-bottom: 6px; }
.glass p { color: #ffffff; font-size: 13px; line-height: 1.5; }
.footer { text-align: center; padding: 24px; margin-top: 40px; border-top: 1px solid var(--border); color: #ffffff; font-size: 12px; }

.council-badge { background: linear-gradient(135deg, #f59e0b, #ef4444); color: white; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 600; display: inline-block; margin-bottom: 10px; }
.council-member { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 12px; margin-bottom: 8px; }
.council-member-name { font-weight: 600; color: var(--cyan); margin-bottom: 4px; }
.council-score { background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); color: #f59e0b; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }


@media (max-width: 900px) { .features, .metrics { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px) { .features, .metrics { grid-template-columns: 1fr; } }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# MAIN APP
# =============================================================================

st.markdown("""
<div class="hero">
    <div class="badge">● AI-Powered Platform</div>
    <h1 class="hero-title">Discover Your Next<br><span class="gradient-text">Billion Dollar Idea</span></h1>
    <div class="stats">
        <div class="stat"><div class="stat-value">4</div><div class="stat-label">Data Sources</div></div>
        <div class="stat"><div class="stat-value">150+</div><div class="stat-label">Pain Points</div></div>
        <div class="stat"><div class="stat-value">37</div><div class="stat-label">Files Gen</div></div>
        <div class="stat"><div class="stat-value">&lt;60s</div><div class="stat-label">Analysis</div></div>
    </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["⚡ Generate", "📊 Results", "📁 Export", "📖 Docs"])

with tab1:
    c1, c2 = st.columns([2.5, 1])
    
    with c2:
        st.markdown('<div class="config"><div class="config-title">⚙️ Configuration</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="config-label">Data Sources</div>', unsafe_allow_html=True)
        g = st.checkbox("GitHub Trending", value=True)
        n = st.checkbox("News APIs", value=True)
        s = st.checkbox("Search APIs", value=True)
        r = st.checkbox("Reddit", value=False)
        st.markdown('<div class="config-label">Settings</div>', unsafe_allow_html=True)
        llm = st.checkbox("AI Mode", value=True)
        num = st.slider("Ideas", 5, 25, 10)
        pp = st.slider("Pain Points", 20, 100, 40)
        
        st.markdown('<div class="config-label">Advanced</div>', unsafe_allow_html=True)
        use_council = st.checkbox("🏛️ LLM Council Mode", value=False, help="Use multiple AI models that review each other's work")
        
        # API Keys section - only show if Council Mode is enabled
        if use_council:
            st.markdown('<div class="config-label">🔑 API Keys (Required for Council Mode)</div>', unsafe_allow_html=True)
            openrouter_key = st.text_input(
                "OpenRouter API Key",
                type="password",
                value=os.getenv("OPENROUTER_API_KEY", ""),
                help="Get your free key at openrouter.ai",
                key="openrouter_key"
            )
            if openrouter_key:
                os.environ["OPENROUTER_API_KEY"] = openrouter_key
        
        if llm and not use_council:
            st.markdown('<div class="config-label">🔑 API Key (Optional)</div>', unsafe_allow_html=True)
            groq_key = st.text_input(
                "Groq API Key",
                type="password", 
                value=os.getenv("GROQ_API_KEY", ""),
                help="Optional: Get your free key at console.groq.com",
                key="groq_key"
            )
            if groq_key:
                os.environ["GROQ_API_KEY"] = groq_key
    
    with c1:
        st.markdown("""
        <div class="section-title">Generate Startup Ideas</div>
        <div class="section-sub">Our AI scans real-time data to find problems worth solving</div>
        <div class="features">
            <div class="feature"><div class="feature-icon">📡</div><div class="feature-title">Real-Time Data</div><div class="feature-desc">GitHub, News, Reddit, Search</div></div>
            <div class="feature"><div class="feature-icon">🧠</div><div class="feature-title">AI Analysis</div><div class="feature-desc">LLM-powered ideation</div></div>
            <div class="feature"><div class="feature-icon">📊</div><div class="feature-title">Smart Scoring</div><div class="feature-desc">Multi-factor ranking</div></div>
            <div class="feature"><div class="feature-icon">💻</div><div class="feature-title">Code Gen</div><div class="feature-desc">Full-stack apps</div></div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚀 Generate Ideas", use_container_width=True):
            prog = st.progress(0)
            stat = st.empty()
            pps = []
            
            stat.markdown('<div class="status">📡 Scanning data sources...</div>', unsafe_allow_html=True)
            
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
                    if reddit_data:
                        pps.extend(reddit_data)
                except Exception as e: 
                    st.warning(f"Reddit: {e}")
            
            if not pps:
                st.error("No data. Check API keys.")
            else:
                st.session_state['pain_points'] = pps
                prog.progress(60)
                
                if use_council:
                    # LLM Council Mode
                    stat.markdown('<div class="status">🏛️ Convening LLM Council...</div>', unsafe_allow_html=True)
                    
                    try:
                        from src.llm_council import LLMCouncil
                        council = LLMCouncil()
                        
                        def update_status(msg):
                            stat.markdown(f'<div class="status">🏛️ {msg}</div>', unsafe_allow_html=True)
                        
                        # Extract pain point descriptions
                        pain_point_strs = []
                        for p in pps[:pp]:
                            if hasattr(p, 'description'):
                                pain_point_strs.append(p.description)
                            elif hasattr(p, 'text'):
                                pain_point_strs.append(p.text)
                            else:
                                pain_point_strs.append(str(p))
                        
                        council_result = asyncio.run(council.generate_ideas(
                            pain_point_strs,
                            num_ideas=num,
                            on_stage_complete=update_status
                        ))
                        
                        st.session_state['council_result'] = council_result
                        # Clear standard mode results
                        if 'ideas' in st.session_state:
                            del st.session_state['ideas']
                        if 'evaluations' in st.session_state:
                            del st.session_state['evaluations']
                        
                        prog.progress(100)
                        stat.markdown('<div class="status status-done">✅ Council complete! Check Results tab.</div>', unsafe_allow_html=True)
                        
                    except Exception as e:
                        st.error(f"Council error: {e}")
                        import traceback
                        st.code(traceback.format_exc())
                else:
                    # Standard single-LLM mode
                    stat.markdown('<div class="status">🧠 AI generating ideas...</div>', unsafe_allow_html=True)
                    
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
                        
                        # Extract ideas list for display
                        ideas = idea_catalog.ideas if hasattr(idea_catalog, 'ideas') else idea_catalog
                        st.session_state['ideas'] = ideas
                        
                        prog.progress(80)
                        stat.markdown('<div class="status">📊 Scoring ideas...</div>', unsafe_allow_html=True)
                        
                        from src.scoring import ScoringEngine
                        # Pass the full catalog to scoring, not just the ideas list
                        eval_report = asyncio.run(ScoringEngine(cfg).evaluate(idea_catalog, intel))
                        # Extract the evaluated_ideas list from the report
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
                        stat.markdown('<div class="status status-done">✅ Done! Check Results tab.</div>', unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Error: {e}")

with tab2:
    # Check for council results first
    if 'council_result' in st.session_state and st.session_state['council_result']:
        council = st.session_state['council_result']
        
        st.markdown('<div class="section-title">🏛️ LLM Council Results</div>', unsafe_allow_html=True)
        
        # Show council members
        members = council.get('council_members', [])
        st.markdown(f'<div class="section-sub"><span class="council-badge">Council</span> {" • ".join(members)}</div>', unsafe_allow_html=True)
        
        # Show scores
        if council.get('stage2_scores'):
            st.markdown("**📊 Peer Review Scores:**")
            score_data = council['stage2_scores']
            if score_data:
                cols = st.columns(len(score_data))
                for idx, (member, scores) in enumerate(score_data):
                    if scores:
                        score = scores.get('average', 0)
                        with cols[idx]:
                            st.markdown(f'<div class="council-member"><div class="council-member-name">{member}</div><span class="council-score">{score:.1f}/10</span></div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Show final synthesized ideas
        st.markdown("### 🏆 Chairman's Final Selection")
        st.markdown(council.get('final_ideas', 'No ideas generated'))
        
        # Expandable: Show individual responses
        with st.expander("🔍 View Individual Council Member Responses"):
            for member, response in council.get('stage1_responses', []):
                st.markdown(f"**{member}:**")
                st.markdown(response)
                st.markdown("---")
    
    elif 'ideas' in st.session_state and st.session_state.get('ideas'):
        ideas = st.session_state['ideas']
        evals = st.session_state.get('evaluations', [])
        pps = st.session_state.get('pain_points', [])
        # Ensure evals is a list
        if not isinstance(evals, list):
            evals = []
        top = evals[0].total_score if evals and len(evals) > 0 else 0
        avg = sum(e.total_score for e in evals)/len(evals) if evals and len(evals) > 0 else 0
        
        st.markdown(f'<div class="metrics"><div class="metric"><div class="metric-value cyan">{len(ideas)}</div><div class="metric-label">Ideas</div></div><div class="metric"><div class="metric-value green">{top:.0f}</div><div class="metric-label">Top Score</div></div><div class="metric"><div class="metric-value purple">{avg:.0f}</div><div class="metric-label">Average</div></div><div class="metric"><div class="metric-value pink">{len(pps)}</div><div class="metric-label">Pain Points</div></div></div>', unsafe_allow_html=True)
        
        if evals:
            data = [{'Idea': (next((i for i in ideas if i.id==e.idea_id),None).name[:18]+'...' if len(next((i for i in ideas if i.id==e.idea_id),None).name)>18 else next((i for i in ideas if i.id==e.idea_id),None).name), 'Score': e.total_score} for e in evals[:10] if next((i for i in ideas if i.id==e.idea_id),None)]
            fig = go.Figure(go.Bar(x=[d['Score'] for d in data], y=[d['Idea'] for d in data], orientation='h', marker=dict(color=[d['Score'] for d in data], colorscale=[[0,'#8b5cf6'],[0.5,'#06b6d4'],[1,'#10b981']])))
            fig.update_layout(height=280, margin=dict(l=0,r=10,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(categoryorder='total ascending', tickfont=dict(color='rgba(255,255,255,0.7)',size=10)), xaxis=dict(tickfont=dict(color='rgba(255,255,255,0.5)'), gridcolor='rgba(255,255,255,0.03)', range=[0,100]), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown('<div class="section-title">Top Ideas</div>', unsafe_allow_html=True)
        if st.session_state.get('used_council'):
            st.markdown('<p style="color: rgba(255,255,255,0.8); font-size: 13px; margin-bottom: 16px; text-align: center;">💎 Scores based on peer review by multiple AI models (Innovation, Feasibility, Market Fit, Revenue Potential)</p>', unsafe_allow_html=True)
        
        displayed_count = 0
        for i, e in enumerate(evals[:10]):
            idea = next((x for x in ideas if x.id==e.idea_id), None)
            if not idea:
                st.warning(f"Idea #{i+1} not found (ID: {e.idea_id})")
                continue
            
            try:
                displayed_count += 1
                problem = getattr(idea, "problem_statement", "N/A")
                solution = getattr(idea, "solution_description", "N/A")
                revenue = getattr(idea, "revenue_model", "N/A")
                tam = getattr(idea, "tam_estimate", "N/A")
                
                # Show preview with truncation
                problem_preview = problem[:150] + "..." if len(problem) > 150 else problem
                solution_preview = solution[:150] + "..." if len(solution) > 150 else solution
                
                st.markdown(f'<div class="idea"><div class="idea-header"><div class="idea-rank">{displayed_count}</div><div class="idea-score">⭐ {e.total_score:.0f}/100</div></div><div class="idea-name">{idea.name}</div><div class="idea-label">Problem</div><div class="idea-text">{problem_preview}</div><div class="idea-label">Solution</div><div class="idea-text">{solution_preview}</div><div class="idea-footer"><div><div class="idea-meta-label">Revenue</div><div class="idea-meta-value">{revenue[:50]}</div></div><div><div class="idea-meta-label">TAM</div><div class="idea-meta-value">{tam[:50]}</div></div></div></div>', unsafe_allow_html=True)
                
                # Add expandable section for full details
                with st.expander(f"📋 View Full Details", expanded=False):
                    st.markdown(f"### {idea.name}\n")
                    st.markdown(f"**💡 Problem Statement**\n\n{problem}\n")
                    st.markdown(f"**✨ Solution Description**\n\n{solution}\n")
                    st.markdown(f"**💰 Revenue Model**\n\n{revenue}\n")
                    st.markdown(f"**📊 TAM Estimate**\n\n{tam}\n")
                    if hasattr(idea, 'target_market'):
                        st.markdown(f"**🎯 Target Market**\n\n{idea.target_market}\n")
                    if hasattr(idea, 'competitive_advantage'):
                        st.markdown(f"**🏆 Competitive Advantage**\n\n{idea.competitive_advantage}")
            except Exception as ex:
                st.error(f"Error displaying idea #{i+1}: {str(ex)}")
    else:
        st.markdown('<div class="empty"><div class="empty-icon">🚀</div><div>No ideas yet. Generate some!</div></div>', unsafe_allow_html=True)

with tab3:
    st.markdown('<div class="section-title">Export</div>', unsafe_allow_html=True)
    output_dir = Path('./output')
    runs = sorted([r for r in output_dir.glob('run_*') if r.is_dir()], reverse=True) if output_dir.exists() else []
    if runs:
        sel = st.selectbox("Run:", [r.name for r in runs], label_visibility="collapsed")
        for f in (Path('./output')/sel).glob('*'):
            if f.is_file():
                c1, c2 = st.columns([5,1])
                with c1: st.write(f"📄 **{f.name}**")
                with c2:
                    with open(f,'rb') as fp: st.download_button("⬇️", fp, f.name)
    else:
        st.markdown('<div class="empty"><div class="empty-icon">📁</div><div>No exports yet</div></div>', unsafe_allow_html=True)

with tab4:
    st.markdown('<div class="section-title">Documentation</div>', unsafe_allow_html=True)
    st.markdown('<div class="glass"><h3>🔄 Pipeline</h3><p>Data Collection → Pain Point Extraction → AI Ideation → Scoring → Code Generation</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="glass"><h3>📡 Data Sources</h3><p>GitHub Trending • News APIs • Search APIs • Reddit</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="glass"><h3>💻 Code Generation</h3><p>37-file production app: FastAPI + Next.js + PostgreSQL + Docker + CI/CD</p></div>', unsafe_allow_html=True)

st.markdown('<div class="footer">AI Startup Generator • Built for founders who move fast</div>', unsafe_allow_html=True)
