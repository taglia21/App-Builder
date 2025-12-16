import React from 'react';
import { motion } from 'framer-motion';

const Dashboard: React.FC = () => {
    return (
        <div style={{
            height: '100%',
            width: '100%',
            padding: '3rem',
            boxSizing: 'border-box',
            display: 'flex',
            flexDirection: 'column',
        }}>
            <header style={{ marginBottom: '3rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h1 style={{ fontSize: '3rem', margin: 0, textShadow: '0 0 10px rgba(255,255,255,0.3)' }}>MISSION CONTROL</h1>
                    <p style={{ color: '#00f3ff', letterSpacing: '0.2em' }}>SYSTEMS NOMINAL</p>
                </div>
                <div className="glass-panel" style={{ padding: '0.5rem 1.5rem', color: '#00f3ff' }}>
                    USER: ADMIN
                </div>
            </header>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '2rem', flex: 1 }}>
                {/* Market Signals */}
                <motion.div
                    className="glass-panel"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 }}
                    style={{ padding: '2rem', display: 'flex', flexDirection: 'column' }}
                >
                    <h3 style={{ borderBottom: '1px solid rgba(0, 243, 255, 0.3)', paddingBottom: '1rem', marginTop: 0 }}>
                        <span style={{ marginRight: '10px' }}>📡</span>
                        MARKET SIGNALS
                    </h3>
                    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                        <h2 style={{ fontSize: '4rem', margin: 0, color: '#00f3ff' }}>142</h2>
                        <p style={{ opacity: 0.7 }}>ACTIVE STREAMS</p>
                    </div>
                </motion.div>

                {/* Idea Generator */}
                <motion.div
                    className="glass-panel"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.7 }}
                    style={{ padding: '2rem', display: 'flex', flexDirection: 'column' }}
                >
                    <h3 style={{ borderBottom: '1px solid rgba(0, 243, 255, 0.3)', paddingBottom: '1rem', marginTop: 0 }}>
                        <span style={{ marginRight: '10px' }}>💡</span>
                        IDEATION ENGINE
                    </h3>
                    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                        <h2 style={{ fontSize: '4rem', margin: 0, color: '#ff00cc' }}>24</h2>
                        <p style={{ opacity: 0.7 }}>CONCEPTS GENERATED</p>
                    </div>
                </motion.div>

                {/* Code Factory */}
                <motion.div
                    className="glass-panel"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.9 }}
                    style={{ padding: '2rem', display: 'flex', flexDirection: 'column' }}
                >
                    <h3 style={{ borderBottom: '1px solid rgba(0, 243, 255, 0.3)', paddingBottom: '1rem', marginTop: 0 }}>
                        <span style={{ marginRight: '10px' }}>⚡</span>
                        FABRICATION
                    </h3>
                    <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                        <button style={{
                            width: '100%',
                            padding: '1.5rem',
                            background: 'linear-gradient(45deg, #00f3ff 0%, #0066ff 100%)',
                            border: 'none',
                            borderRadius: '8px',
                            color: 'black',
                            fontWeight: 'bold',
                            fontSize: '1.2rem',
                            fontFamily: '"Orbitron", sans-serif',
                            cursor: 'pointer'
                        }}>
                            INITIALIZE BUILD
                        </button>
                    </div>
                </motion.div>
            </div>
        </div>
    );
};

export default Dashboard;
