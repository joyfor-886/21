import { useEffect, useRef } from 'react';

export type AIState = 'idle' | 'typing' | 'thinking' | 'long_thinking' | 'speaking';

interface ParticleSphereProps {
  appState: AIState;
  text?: string;
}

const NUM_PARTICLES = 3000;
const SPHERE_RADIUS = 160;

class Particle {
  x: number = (Math.random() - 0.5) * 1000;
  y: number = (Math.random() - 0.5) * 1000;
  z: number = (Math.random() - 0.5) * 1000;
  
  vx: number = 0;
  vy: number = 0;
  vz: number = 0;

  targetSize: number = 1.0;
  size: number = 1.0;

  color: [number, number, number] = [255, 255, 255];
  targetColor: [number, number, number] = [255, 255, 255];

  randomFactor: number = Math.random() * Math.PI * 2;
  speedFactor: number = 0.02 + Math.random() * 0.04;
}

function hexToRgb(hex: string): [number, number, number] {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? [
    parseInt(result[1], 16),
    parseInt(result[2], 16),
    parseInt(result[3], 16)
  ] : [255, 255, 255];
}

function lerpColor(c1: [number, number, number], c2: [number, number, number], amount: number): [number, number, number] {
  return [
    c1[0] + (c2[0] - c1[0]) * amount,
    c1[1] + (c2[1] - c1[1]) * amount,
    c1[2] + (c2[2] - c1[2]) * amount
  ];
}

export default function ParticleSphere({ appState, text = "SSUMA" }: ParticleSphereProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let particles: Particle[] = [];
    
    let width = window.innerWidth;
    let height = window.innerHeight;

    const resize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width;
      canvas.height = height;
    };
    window.addEventListener('resize', resize);
    resize();

    const formations: { text: {x:number, y:number, z:number}[], sphere: {x:number, y:number, z:number}[] } = {
      text: [],
      sphere: []
    };

    // 1. Generate text points
    const generateTextPoints = (str: string) => {
      const tCanvas = document.createElement('canvas');
      tCanvas.width = 800;
      tCanvas.height = 300;
      const tCtx = tCanvas.getContext('2d', { willReadFrequently: true });
      if (!tCtx) return [];

      tCtx.fillStyle = 'white';
      tCtx.font = '800 140px Inter, system-ui, sans-serif'; 
      tCtx.textAlign = 'center';
      tCtx.textBaseline = 'middle';
      tCtx.fillText(str, tCanvas.width / 2, tCanvas.height / 2);

      const imgData = tCtx.getImageData(0, 0, tCanvas.width, tCanvas.height).data;
      const validPoints = [];
      const skip = 3;
      for (let y = 0; y < tCanvas.height; y += skip) {
        for (let x = 0; x < tCanvas.width; x += skip) {
          const i = (y * tCanvas.width + x) * 4;
          if (imgData[i + 3] > 128) {
            validPoints.push({ 
              x: x - tCanvas.width / 2, 
              y: y - tCanvas.height / 2, 
              z: (Math.random() - 0.5) * 5 // Slight depth for 3D jitter
            });
          }
        }
      }
      return validPoints;
    };

    // 2. Generate Sphere points (Fibonacci)
    const generateSpherePoints = (n: number, radius: number) => {
      const pts = [];
      const phi = Math.PI * (3 - Math.sqrt(5));
      for (let i = 0; i < n; i++) {
        const y = 1 - (i / (n - 1)) * 2;
        const radiusAtY = Math.sqrt(1 - y * y);
        const theta = phi * i;
        pts.push({
          x: Math.cos(theta) * radiusAtY * radius,
          y: y * radius,
          z: Math.sin(theta) * radiusAtY * radius
        });
      }
      return pts;
    };

    let textPtsOrig = generateTextPoints(text);
    formations.sphere = generateSpherePoints(NUM_PARTICLES, SPHERE_RADIUS);

    document.fonts.ready.then(() => {
        const newPts = generateTextPoints(text);
        if (newPts.length > 0) {
           textPtsOrig = newPts;
        }
    });

    for (let i = 0; i < NUM_PARTICLES; i++) {
      const p = new Particle();
      // start at center initially
      p.x = (Math.random() - 0.5) * 100;
      p.y = (Math.random() - 0.5) * 100;
      p.z = (Math.random() - 0.5) * 100;
      particles.push(p);
    }

    let rotX = 0;
    let rotY = 0;
    let time = 0;
    let audioSim = 0;
    let audioTarget = 0;

    // We keep track of the blend from text (0) to sphere (1)
    let shapeMorph = 0;

    const render = () => {
      time += 0.016; 
      
      if (Math.random() < 0.1) audioTarget = Math.random();
      audioSim += (audioTarget - audioSim) * 0.2;

      ctx.fillStyle = 'rgba(10, 10, 15, 0.25)'; // Trail effect
      ctx.fillRect(0, 0, width, height);

      let isSphereState = appState !== 'idle';
      let targetRotSpeedY = 0;
      let targetRotSpeedX = 0;
      let baseColor = '#ffffff';
      let noiseScale = 0;
      let pulseMultiplier = 1;
      let targetMorph = isSphereState ? 1 : 0;

      switch(appState) {
        case 'idle':
          baseColor = '#ffffff';
          targetRotSpeedY = 0;
          targetRotSpeedX = 0;
          break;
        case 'typing':
          targetRotSpeedY = 0.01;
          targetRotSpeedX = 0.005;
          baseColor = '#00ffcc';
          pulseMultiplier = 1.05 + Math.sin(time * 3) * 0.05;
          noiseScale = 1;
          break;
        case 'thinking':
          targetRotSpeedY = 0.02;
          targetRotSpeedX = 0.015;
          baseColor = '#7a33ff';
          pulseMultiplier = 1 + Math.sin(time * 4) * 0.1;
          noiseScale = 5;
          break;
        case 'long_thinking':
          targetRotSpeedY = 0.04;
          targetRotSpeedX = 0.03;
          baseColor = '#ff3388';
          pulseMultiplier = 1.1 + Math.sin(time * 6) * 0.15;
          noiseScale = 15;
          break;
        case 'speaking':
          targetRotSpeedY = 0.015;
          targetRotSpeedX = -0.01;
          baseColor = '#00ccff';
          pulseMultiplier = 1 + audioSim * 0.3;
          noiseScale = audioSim * 8;
          break;
      }

      // Smooth transition for morphing
      shapeMorph += (targetMorph - shapeMorph) * 0.05;

      // Handle global rotation
      if (shapeMorph > 0.01) {
         rotY += targetRotSpeedY * shapeMorph;
         rotX += targetRotSpeedX * shapeMorph;
      } 
      
      if (shapeMorph < 0.99 && targetMorph === 0) {
         // Smoothly return character rotation back to 0 as it becomes flat text
         let ny = rotY % (Math.PI * 2);
         if (ny > Math.PI) ny -= Math.PI * 2;
         if (ny < -Math.PI) ny += Math.PI * 2;
         
         let nx = rotX % (Math.PI * 2);
         if (nx > Math.PI) nx -= Math.PI * 2;
         if (nx < -Math.PI) nx += Math.PI * 2;
         
         rotY += (0 - ny) * (1 - shapeMorph) * 0.1;
         rotX += (0 - nx) * (1 - shapeMorph) * 0.1;
      }

      const sinX = Math.sin(rotX);
      const cosX = Math.cos(rotX);
      const sinY = Math.sin(rotY);
      const cosY = Math.cos(rotY);

      if (textPtsOrig.length === 0) {
         textPtsOrig = formations.sphere; 
      }

      particles.forEach((p, i) => {
        // Interpolate between text shape and sphere shape
        const sp = formations.sphere[i % formations.sphere.length];
        const tp = textPtsOrig[i % textPtsOrig.length];
        
        // Add some noise to the text shape when typing so they vibrate
        let txIdle = tp.x + Math.sin(time * 2 + p.randomFactor) * 1.5;
        let tyIdle = tp.y + Math.cos(time * 3 + p.randomFactor) * 1.5;
        let tzIdle = tp.z + Math.sin(time * 4 + p.randomFactor) * 2.0;

        let tx = txIdle + (sp.x - txIdle) * shapeMorph;
        let ty = tyIdle + (sp.y - tyIdle) * shapeMorph;
        let tz = tzIdle + (sp.z - tzIdle) * shapeMorph;

        // Apply noise and pulse (mainly for sphere modes)
        let currentPulse = 1 + (pulseMultiplier - 1) * shapeMorph;
        if (noiseScale > 0) {
            const noise = Math.sin(time * 5 + p.randomFactor) * noiseScale * shapeMorph;
            // directional noise based on sphere normal
            const mag = Math.sqrt(tx*tx + ty*ty + tz*tz) || 1;
            tx += (tx / mag) * noise;
            ty += (ty / mag) * noise;
            tz += (tz / mag) * noise;
        }

        tx *= currentPulse;
        ty *= currentPulse;
        tz *= currentPulse;

        // Physics: Move particle towards target faster using unique speed
        const spring = p.speedFactor + (0.08 * shapeMorph); // stiffer when morphing
        p.vx += (tx - p.x) * spring;
        p.vy += (ty - p.y) * spring;
        p.vz += (tz - p.z) * spring;
        
        p.vx *= 0.78;
        p.vy *= 0.78;
        p.vz *= 0.78;

        p.x += p.vx;
        p.y += p.vy;
        p.z += p.vz;

        let rx = p.x;
        let ry = p.y * cosX - p.z * sinX;
        let rz = p.y * sinX + p.z * cosX;

        let finalX = rx * cosY - rz * sinY;
        let finalY = ry;
        let finalZ = rx * sinY + rz * cosY;

        if (Math.random() < 0.05) {
            // occassional sparkles
            p.targetColor = hexToRgb(Math.random() < 0.1 ? '#ffffff' : baseColor);
        }
        p.color = lerpColor(p.color, p.targetColor, 0.15);

        const fov = 800;
        const zOff = 600;
        const z = finalZ + zOff;
        if (z < 10) return; 

        const scale = fov / z;
        const x2d = finalX * scale + width / 2;
        const y2d = finalY * scale + height / 2 - 40; 

        const size = Math.max(0.1, p.targetSize * scale * (1.5 - shapeMorph * 0.7)); // Particles shrink slightly when becoming a sphere

        ctx.beginPath();
        const alpha = Math.min(1, Math.max(0.1, scale * 0.8));
        
        ctx.fillStyle = `rgba(${Math.round(p.color[0])}, ${Math.round(p.color[1])}, ${Math.round(p.color[2])}, ${alpha})`;
        ctx.arc(x2d, y2d, size, 0, Math.PI * 2);
        ctx.fill();
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationFrameId);
    };
  }, [appState, text]);

  return (
    <canvas 
      ref={canvasRef} 
      className="fixed top-0 left-0 w-full h-full -z-10 bg-black"
    />
  );
}
