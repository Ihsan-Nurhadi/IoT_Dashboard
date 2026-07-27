'use client';
import { useState, useEffect } from 'react';
import {
    Activity,
    Compass,
    ArrowRightLeft,
    Droplet,
    Wind,
} from 'lucide-react';
import { type SensorData } from '../../hooks/useSensorData';
import { sites, type Site } from '../../data/sites';



interface TelemetrySectionProps {
    latest: SensorData | null;
    isConnected: boolean;
    site?: Site | null;
}

function timeAgo(timestamp: string): string {
    const diff = Date.now() - new Date(timestamp).getTime();
    const secs = Math.floor(diff / 1000);
    if (secs < 5) return 'just now';
    if (secs < 60) return `${secs}s ago`;
    const mins = Math.floor(secs / 60);
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return 'recently';
}

export default function TelemetrySection({ latest, isConnected, site }: TelemetrySectionProps) {
    const [agoText, setAgoText] = useState('just now');

    useEffect(() => {
        if (!latest) return;
        setAgoText(timeAgo(latest.timestamp));
        const interval = setInterval(() => {
            setAgoText(timeAgo(latest.timestamp));
        }, 5000);
        return () => clearInterval(interval);
    }, [latest]);

    const windSpeed = latest?.wind_speed ?? 0;
    const windSpeedMs = latest?.wind_speed_ms ?? 0;
    const pitch = latest?.pitch ?? 0;
    const sway = latest?.sway ?? 0;
    const totalTilt = latest?.total_tilt ?? 0;
    const indikator = latest?.indikator ?? 'tolerance';

    const maxWind = 35;
    const windPercent = Math.min((windSpeed / maxWind) * 100, 100);

    const activeSite = site ?? sites.find(s => s.code === latest?.device_id);
    const swayTolerance = activeSite ? activeSite.towerHeight * 5 : 30; // dynamic: height * 5
    const tiltTolerance = 0.286;

    const isTolerance = indikator === 'tolerance';
    const statusColor = isTolerance ? '#08b87c' : '#f43f5e';
    const statusBg = isTolerance ? 'rgba(8, 184, 124, 0.1)' : 'rgba(244, 63, 94, 0.15)';
    const statusBorder = isTolerance ? 'rgba(8, 184, 124, 0.3)' : 'rgba(244, 63, 94, 0.4)';
    const towerStatus = isTolerance ? 'TOLERANCE' : 'INTOLERANCE';

    // Calculate dynamic rotation angle for tower based on X-axis tilt (pitch)
    const visualAngle = Math.max(-15, Math.min(15, pitch * 50)); 
    // Calculate dynamic spin speed for windmill based on wind speed
    const spinDuration = windSpeed > 0 ? Math.max(0.15, 12 / windSpeed) : 0;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', width: '100%' }}>
            {/* Styles for windmill animation */}
            <style>{`
                @keyframes spinWindmill {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
                .spin-blades {
                    animation: spinWindmill var(--spin-time, 0s) linear infinite;
                }
            `}</style>

            {/* Top Header Row */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#38bdf8' }}>
                    <Activity size={18} />
                    <span style={{ fontSize: '0.85rem', fontWeight: 800, letterSpacing: '0.05em' }}>FATIGUE</span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.35rem',
                        padding: '0.25rem 0.6rem',
                        fontSize: '0.65rem',
                        fontWeight: 700,
                        backgroundColor: statusBg,
                        border: `1px solid ${statusBorder}`,
                        borderRadius: '6px',
                        color: statusColor,
                        textTransform: 'uppercase',
                        letterSpacing: '0.02em'
                    }}>
                        <span style={{
                            width: '6px',
                            height: '6px',
                            borderRadius: '50%',
                            backgroundColor: statusColor,
                            display: 'inline-block'
                        }} />
                        {towerStatus}
                    </span>
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)' }}>
                        {latest ? `-${agoText}` : '--'}
                    </span>
                </div>
            </div>

            {/* Main Double Panel Grid */}
            <div className="telemetry-layout-grid" style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                gap: '1rem',
                width: '100%'
            }}>
                {/* Left Panel: Gerakan Struktural */}
                <div className="sensor-card" style={{
                    display: 'flex',
                    flexDirection: 'column',
                    padding: '1.25rem',
                    background: 'var(--bg-card)',
                    border: '1px solid rgba(255,255,255,0.05)',
                    borderRadius: '12px',
                    minHeight: '340px'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-secondary)', fontSize: '0.65rem', fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                        <Compass size={14} />
                        GERAKAN STRUKTURAL
                    </div>

                    {/* SVG Leaning Tower Schematic */}
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flex: 1, padding: '1rem 0' }}>
                        <div style={{ position: 'relative', width: '200px', height: '170px' }}>
                            <svg width="200" height="170" viewBox="0 0 200 170" fill="none">
                                <g style={{
                                    transform: `rotate(${visualAngle}deg)`,
                                    transformOrigin: '100px 150px',
                                    transition: 'transform 1s cubic-bezier(0.4, 0, 0.2, 1)',
                                }}>
                                    {/* Lattice Tower Legs */}
                                    <line x1="80" y1="150" x2="96" y2="20" stroke={statusColor} strokeWidth="2.5" style={{ transition: 'stroke 0.5s ease', filter: isTolerance ? 'none' : 'drop-shadow(0 0 5px #f43f5e)' }} />
                                    <line x1="120" y1="150" x2="104" y2="20" stroke={statusColor} strokeWidth="2.5" style={{ transition: 'stroke 0.5s ease', filter: isTolerance ? 'none' : 'drop-shadow(0 0 5px #f43f5e)' }} />

                                    {/* Horizontal Beams */}
                                    <line x1="80" y1="150" x2="120" y2="150" stroke={statusColor} strokeWidth="1.5" style={{ transition: 'stroke 0.5s ease' }} />
                                    <line x1="84" y1="117.5" x2="116" y2="117.5" stroke={statusColor} strokeWidth="1.5" style={{ transition: 'stroke 0.5s ease' }} />
                                    <line x1="88" y1="85" x2="112" y2="85" stroke={statusColor} strokeWidth="1.5" style={{ transition: 'stroke 0.5s ease' }} />
                                    <line x1="92" y1="52.5" x2="108" y2="52.5" stroke={statusColor} strokeWidth="1.5" style={{ transition: 'stroke 0.5s ease' }} />
                                    <line x1="96" y1="20" x2="104" y2="20" stroke={statusColor} strokeWidth="1.5" style={{ transition: 'stroke 0.5s ease' }} />

                                    {/* Cross Diagonal Bracing */}
                                    {/* Segment 1 */}
                                    <line x1="80" y1="150" x2="116" y2="117.5" stroke={statusColor} strokeWidth="1" opacity="0.8" style={{ transition: 'stroke 0.5s ease' }} />
                                    <line x1="120" y1="150" x2="84" y2="117.5" stroke={statusColor} strokeWidth="1" opacity="0.8" style={{ transition: 'stroke 0.5s ease' }} />
                                    {/* Segment 2 */}
                                    <line x1="84" y1="117.5" x2="112" y2="85" stroke={statusColor} strokeWidth="1" opacity="0.8" style={{ transition: 'stroke 0.5s ease' }} />
                                    <line x1="116" y1="117.5" x2="88" y2="85" stroke={statusColor} strokeWidth="1" opacity="0.8" style={{ transition: 'stroke 0.5s ease' }} />
                                    {/* Segment 3 */}
                                    <line x1="88" y1="85" x2="108" y2="52.5" stroke={statusColor} strokeWidth="1" opacity="0.8" style={{ transition: 'stroke 0.5s ease' }} />
                                    <line x1="112" y1="85" x2="92" y2="52.5" stroke={statusColor} strokeWidth="1" opacity="0.8" style={{ transition: 'stroke 0.5s ease' }} />
                                    {/* Segment 4 */}
                                    <line x1="92" y1="52.5" x2="104" y2="20" stroke={statusColor} strokeWidth="1" opacity="0.8" style={{ transition: 'stroke 0.5s ease' }} />
                                    <line x1="108" y1="52.5" x2="96" y2="20" stroke={statusColor} strokeWidth="1" opacity="0.8" style={{ transition: 'stroke 0.5s ease' }} />

                                    {/* Glowing top dot */}
                                    <circle cx="100" cy="20" r="4.5" fill={statusColor} style={{ transition: 'fill 0.5s ease', filter: 'drop-shadow(0 0 4px currentColor)' }} />
                                    
                                    {/* Degree label text next to top dot */}
                                    <text x="110" y="24" fill={statusColor} fontSize="10" fontWeight="bold" fontFamily="monospace" style={{ transition: 'fill 0.5s ease' }}>
                                        θ {totalTilt.toFixed(2)}°
                                    </text>
                                </g>
                            </svg>
                        </div>
                    </div>

                    {/* Foundation identifier */}
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: '1.25rem' }}>
                        <div style={{ width: '60px', height: '2px', backgroundColor: '#374151', borderRadius: '1px' }}></div>
                        <span style={{ fontSize: '0.55rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: '0.2rem' }}>
                            Fondasi
                        </span>
                    </div>

                    {/* Text Cards underneath the animation */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                        {/* Kemiringan Card */}
                        <div style={{
                            background: 'rgba(255,255,255,0.01)',
                            border: '1px solid rgba(255,255,255,0.04)',
                            borderRadius: '10px',
                            padding: '0.6rem 0.8rem',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '0.1rem'
                        }}>
                            <span style={{ fontSize: '0.55rem', color: 'var(--text-tertiary)', fontWeight: 600, letterSpacing: '0.02em' }}>KEMIRINGAN</span>
                            <span style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)', fontFamily: "'JetBrains Mono', monospace" }}>
                                {totalTilt.toFixed(2)}<span style={{ fontSize: '0.85rem', color: 'var(--text-tertiary)' }}>°</span>
                            </span>
                            <span style={{ fontSize: '0.6rem', color: 'var(--text-tertiary)' }}>
                                Toleransi: {tiltTolerance.toFixed(3)}°
                            </span>
                        </div>

                        {/* Goyangan Card */}
                        <div style={{
                            background: 'rgba(255,255,255,0.01)',
                            border: '1px solid rgba(255,255,255,0.04)',
                            borderRadius: '10px',
                            padding: '0.6rem 0.8rem',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '0.1rem'
                        }}>
                            <span style={{ fontSize: '0.55rem', color: 'var(--text-tertiary)', fontWeight: 600, letterSpacing: '0.02em' }}>GOYANGAN</span>
                            <span style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)', fontFamily: "'JetBrains Mono', monospace" }}>
                                {sway.toFixed(0)}<span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', marginLeft: '1px' }}>mm</span>
                            </span>
                            <span style={{ fontSize: '0.6rem', color: 'var(--text-tertiary)' }}>
                                Toleransi: {swayTolerance} mm
                            </span>
                        </div>
                    </div>
                </div>

                {/* Right Panel: Sensor Angin */}
                <div className="sensor-card" style={{
                    display: 'flex',
                    flexDirection: 'column',
                    padding: '1.25rem',
                    background: 'var(--bg-card)',
                    border: '1px solid rgba(255,255,255,0.05)',
                    borderRadius: '12px',
                    minHeight: '340px'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-secondary)', fontSize: '0.65rem', fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                        <Wind size={14} />
                        SENSOR ANGIN
                    </div>

                    {/* SVG Windmill Animation */}
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flex: 1, padding: '1rem 0' }}>
                        <svg width="200" height="170" viewBox="0 0 200 170" fill="none">
                            <defs>
                                <linearGradient id="windmillBlade" x1="0%" y1="0%" x2="0%" y2="100%">
                                    <stop offset="0%" stopColor="#06b6d4" />
                                    <stop offset="100%" stopColor="#08b87c" />
                                </linearGradient>
                            </defs>
                            
                            {/* Windmill Stand */}
                            <line x1="100" y1="150" x2="100" y2="70" stroke="#4b5563" strokeWidth="3" />
                            <ellipse cx="100" cy="150" rx="16" ry="4" fill="#374151" stroke="#4b5563" strokeWidth="1" />

                            {/* Rotating Blades Group */}
                            <g className="spin-blades" style={{
                                '--spin-time': `${spinDuration}s`,
                                transformOrigin: '100px 70px'
                            } as React.CSSProperties}>
                                
                                {/* Blade 1 (Top) */}
                                <line x1="100" y1="70" x2="100" y2="35" stroke="#4b5563" strokeWidth="2" />
                                <path d="M100,35 C88,40 88,50 100,55 C112,50 112,40 100,35 Z" fill="url(#windmillBlade)" opacity="0.9" />

                                {/* Blade 2 (120 deg) */}
                                <g transform="rotate(120, 100, 70)">
                                    <line x1="100" y1="70" x2="100" y2="35" stroke="#4b5563" strokeWidth="2" />
                                    <path d="M100,35 C88,40 88,50 100,55 C112,50 112,40 100,35 Z" fill="url(#windmillBlade)" opacity="0.9" />
                                </g>

                                {/* Blade 3 (240 deg) */}
                                <g transform="rotate(240, 100, 70)">
                                    <line x1="100" y1="70" x2="100" y2="35" stroke="#4b5563" strokeWidth="2" />
                                    <path d="M100,35 C88,40 88,50 100,55 C112,50 112,40 100,35 Z" fill="url(#windmillBlade)" opacity="0.9" />
                                </g>

                                {/* Center Hub */}
                                <circle cx="100" cy="70" r="5" fill="#374151" stroke="#9ca3af" strokeWidth="1.5" />
                            </g>
                        </svg>
                    </div>

                    {/* Ground line or spacer */}
                    <div style={{ height: '2px', backgroundColor: 'transparent', marginBottom: '1.25rem' }}></div>

                    {/* Wind Speed stats card underneath */}
                    <div style={{
                        background: 'rgba(255,255,255,0.01)',
                        border: '1px solid rgba(255,255,255,0.04)',
                        borderRadius: '10px',
                        padding: '0.8rem 1rem',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.4rem',
                        marginTop: 'auto'
                    }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.2rem' }}>
                                <span style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)', fontFamily: "'JetBrains Mono', monospace" }}>
                                    {windSpeed.toFixed(2)}
                                </span>
                                <span style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)', fontWeight: 600 }}>knot</span>
                            </div>
                            <span style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)', fontFamily: "'JetBrains Mono', monospace" }}>
                                {windSpeedMs.toFixed(2)} m/s
                            </span>
                        </div>

                        {/* Progress Bar */}
                        <div style={{
                            width: '100%',
                            height: '4px',
                            background: 'rgba(255,255,255,0.05)',
                            borderRadius: '2px',
                            overflow: 'hidden'
                        }}>
                            <div style={{
                                width: `${windPercent}%`,
                                height: '100%',
                                background: 'linear-gradient(90deg, #06b6d4, #08b87c)',
                                borderRadius: '2px',
                                transition: 'width 0.5s ease-out'
                            }}></div>
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.55rem', color: 'var(--text-tertiary)' }}>
                            <span>Toleransi: {maxWind} knot</span>
                            <span style={{ color: windSpeed > 22 ? 'var(--accent-red)' : 'var(--accent-green)', fontWeight: 700 }}>
                                {windSpeed > 22 ? 'Diatas ambang batas aman' : 'Dalam ambang batas aman'}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
