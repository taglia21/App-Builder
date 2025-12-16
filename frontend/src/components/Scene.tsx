import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Stars, Sphere } from '@react-three/drei';
import * as THREE from 'three';

const Scene: React.FC = () => {
    return (
        <>
            <ambientLight intensity={0.2} />
            <pointLight position={[10, 10, 10]} intensity={1.5} color="#00f3ff" />

            <Stars
                radius={300}
                depth={50}
                count={5000}
                factor={4}
                saturation={0}
                fade
                speed={0.5}
            />

            <HolographicGlobe />
        </>
    );
};

const HolographicGlobe = () => {
    const meshRef = useRef<THREE.Mesh>(null);

    useFrame((state, delta) => {
        if (meshRef.current) {
            meshRef.current.rotation.y += delta * 0.1;
        }
    });

    return (
        <Sphere ref={meshRef} args={[2.5, 64, 64]} position={[0, 0, 0]}>
            <meshStandardMaterial
                color="#00f3ff"
                wireframe
                transparent
                opacity={0.3}
                emissive="#00f3ff"
                emissiveIntensity={0.2}
            />
        </Sphere>
    );
};

export default Scene;
