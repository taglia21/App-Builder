import React, { useEffect, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import Scene from './Scene';

interface LandingProps {
    onLaunch: () => void;
}

const Landing: React.FC<LandingProps> = ({ onLaunch }) => {
    const [coordinates, setCoordinates] = useState('000.000');

    useEffect(() => {
        const interval = setInterval(() => {
            setCoordinates((Math.random() * 1000).toFixed(3));
        }, 100);
        return () => clearInterval(interval);
    }, []);

    return (
        <div style={{ width: '100%', height: '100%', position: 'relative' }}>
            {/* 3D Scene Background */}
            <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', zIndex: 0 }}>
                <Canvas>
                    <Scene />
                </Canvas>
            </div>

            {/* Tech Junk - Corners */}
            <div style={{ position: 'absolute', top: '2rem', left: '2rem', zIndex: 1, color: 'rgba(0, 243, 255, 0.7)', fontSize: '0.8rem', letterSpacing: '2px' }}>
                SYS.STATUS: ONLINE // V.2.0.4
            </div>

            <div style={{ position: 'absolute', bottom: '2rem', right: '2rem', zIndex: 1, color: 'rgba(0, 243, 255, 0.7)', fontSize: '1rem', textAlign: 'right', fontFamily: 'monospace' }}>
                COORDS: {coordinates} <br />
                SECTOR: 7G
            </div>

            {/* Center Content */}
            <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', zIndex: 10, textAlign: 'center' }}>
                <h1 style={{
                    fontSize: '5rem',
                    marginBottom: '2rem',
                    textShadow: '0 0 30px rgba(0, 243, 255, 0.5)',
                    mixBlendMode: 'screen'
                }}>
                    GENESIS
                </h1>

                <button
                    onClick={onLaunch}
                    style={{
                        background: 'transparent',
                        border: '2px solid #00f3ff',
                        color: '#00f3ff',
                        padding: '1rem 3rem',
                        fontSize: '1.2rem',
                        letterSpacing: '0.3em',
                        cursor: 'pointer',
                        transition: 'all 0.3s',
                        fontFamily: '"Orbitron", sans-serif',
                        textTransform: 'uppercase'
                    }}
                    onMouseOver={(e) => {
                        e.currentTarget.style.background = '#00f3ff';
                        e.currentTarget.style.color = '#000';
                        e.currentTarget.style.boxShadow = '0 0 30px rgba(0, 243, 255, 0.8)';
                    }}
                    onMouseOut={(e) => {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.color = '#00f3ff';
                        e.currentTarget.style.boxShadow = 'none';
                    }}
                >
                    INITIATE LAUNCH SEQUENCE
                </button>
            </div>
        </div>
    );
};

export default Landing;
