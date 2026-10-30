'use client';

import { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

// Deterministic PRNG (mulberry32) so particle layout is pure and stable across renders
function createRandom(seed: number) {
    return () => {
        seed |= 0;
        seed = (seed + 0x6d2b79f5) | 0;
        let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

function ParticleField() {
    const ref = useRef<THREE.Points>(null);

    const geometry = useMemo(() => {
        const count = 3000;
        const random = createRandom(42);
        const positions = new Float32Array(count * 3);
        const colors = new Float32Array(count * 3);

        for (let i = 0; i < count; i++) {
            const i3 = i * 3;
            positions[i3] = (random() - 0.5) * 20;
            positions[i3 + 1] = (random() - 0.5) * 20;
            positions[i3 + 2] = (random() - 0.5) * 20;

            const t = random();
            colors[i3] = 0.42 * (1 - t) + 0.0 * t;
            colors[i3 + 1] = 0.39 * (1 - t) + 0.9 * t;
            colors[i3 + 2] = 1.0;
        }

        const geo = new THREE.BufferGeometry();
        geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        return geo;
    }, []);

    const material = useMemo(() => {
        return new THREE.PointsMaterial({
            vertexColors: true,
            size: 0.04,
            sizeAttenuation: true,
            transparent: true,
            opacity: 0.6,
            depthWrite: false,
        });
    }, []);

    useFrame((_state, delta) => {
        if (ref.current) {
            ref.current.rotation.x += delta * 0.02;
            ref.current.rotation.y += delta * 0.03;
        }
    });

    return <points ref={ref} geometry={geometry} material={material} />;
}

function FloatingRing() {
    const ref = useRef<THREE.Mesh>(null);

    useFrame((_state, delta) => {
        if (ref.current) {
            ref.current.rotation.x += delta * 0.1;
            ref.current.rotation.z += delta * 0.05;
        }
    });

    return (
        <mesh ref={ref} position={[0, 0, 0]}>
            <torusGeometry args={[3, 0.02, 16, 100]} />
            <meshBasicMaterial color="#6c63ff" transparent opacity={0.3} />
        </mesh>
    );
}

export default function ParticleScene() {
    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            zIndex: 0,
            pointerEvents: 'none',
        }}>
            <Canvas
                camera={{ position: [0, 0, 8], fov: 60 }}
                gl={{ alpha: true, antialias: true }}
            >
                <ambientLight intensity={0.5} />
                <ParticleField />
                <FloatingRing />
            </Canvas>
        </div>
    );
}
