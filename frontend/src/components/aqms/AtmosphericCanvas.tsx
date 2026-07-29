import React, { useEffect, useRef, useState } from 'react';

interface AtmosphericCanvasProps {
  windSpeed: number;
  windHeading: number;
}

export const AtmosphericCanvas: React.FC<AtmosphericCanvasProps> = ({
  windSpeed,
  windHeading,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [flowMode, setFlowMode] = useState<'particles' | 'heat'>('particles');
  const [theme, setTheme] = useState(() => document.documentElement.getAttribute('data-theme') || 'dark');

  useEffect(() => {
    const handleThemeChange = (e: Event) => {
      const customEvent = e as CustomEvent;
      setTheme(customEvent.detail);
    };
    window.addEventListener('theme-change', handleThemeChange);
    return () => {
      window.removeEventListener('theme-change', handleThemeChange);
    };
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let particles: Array<{
      x: number;
      y: number;
      speedMult: number;
      opacity: number;
    }> = [];

    const maxParticles = 100;

    const resizeCanvas = () => {
      if (!canvas) return;
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Init particles
    particles = [];
    for (let i = 0; i < maxParticles; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        speedMult: Math.random() * 0.8 + 0.4,
        opacity: Math.random() * 0.5 + 0.2,
      });
    }

    const draw = () => {
      const isDark = theme === 'dark';
      ctx.fillStyle = isDark ? 'rgba(11, 19, 38, 0.08)' : 'rgba(250, 246, 238, 0.08)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      const angleRad = ((90 - windHeading) * Math.PI) / 180;
      const speed = Math.max(1, windSpeed * 3);

      const vx = Math.cos(angleRad) * speed;
      const vy = -Math.sin(angleRad) * speed;

      particles.forEach((p) => {
        if (flowMode === 'particles') {
          ctx.strokeStyle = isDark
            ? `rgba(137, 206, 255, ${p.opacity})`
            : `rgba(37, 99, 235, ${p.opacity})`;
        } else {
          ctx.strokeStyle = isDark
            ? `rgba(255, 185, 95, ${p.opacity})`
            : `rgba(217, 119, 6, ${p.opacity})`;
        }

        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);

        const dx = vx * p.speedMult;
        const dy = vy * p.speedMult;
        ctx.lineTo(p.x - dx * 3, p.y - dy * 3);
        ctx.stroke();

        p.x += dx;
        p.y += dy;

        if (p.x < -30) p.x = canvas.width + 30;
        if (p.x > canvas.width + 30) p.x = -30;
        if (p.y < -30) p.y = canvas.height + 30;
        if (p.y > canvas.height + 30) p.y = -30;
      });

      animationFrameId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      cancelAnimationFrame(animationFrameId);
    };
  }, [windSpeed, windHeading, flowMode, theme]);

  return (
    <div className="aqms-canvas-container glass-card">
      <canvas ref={canvasRef} className="aqms-canvas-element" />
      <div className="aqms-canvas-overlay"></div>

      <div className="aqms-canvas-bottom-text">
        <h4>Simulasi Aliran Atmosfer</h4>
        <p>Model Prediktif 6 Jam Ke Depan Berdasarkan Data Real-time</p>
      </div>

      <div className="aqms-canvas-toolbar">
        <button
          onClick={() => setFlowMode('heat')}
          className={`aqms-canvas-btn ${flowMode === 'heat' ? 'active heat' : ''}`}
        >
          Mode Panas
        </button>
        <button
          onClick={() => setFlowMode('particles')}
          className={`aqms-canvas-btn ${flowMode === 'particles' ? 'active' : ''}`}
        >
          Aliran Partikel
        </button>
      </div>
    </div>
  );
};
