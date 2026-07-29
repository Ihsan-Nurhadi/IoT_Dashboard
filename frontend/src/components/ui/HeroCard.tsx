'use client';
import { RefreshCw, MapPin, Hash, Ratio, ArrowUp } from 'lucide-react';
import { type SensorData } from '../../hooks/useSensorData';
import { type Site } from '../../data/sites';



interface HeroCardProps {
    latest: SensorData | null;
    isConnected: boolean;
    site?: Site;
    deviceId?: string;
}

export default function HeroCard({ latest, isConnected, site, deviceId }: HeroCardProps) {
    const formatTimestamp = (ts: string) => {
        const d = new Date(ts);
        const pad = (n: number) => n.toString().padStart(2, '0');
        return `${pad(d.getDate())}-${pad(d.getMonth() + 1)}-${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
    };

    const siteName = site?.name ?? 'SHM Site';
    const siteCode = deviceId ?? site?.code ?? '-';
    const towerType = site?.towerType ?? 'Monopole';
    const towerHeight = site?.towerHeight ?? '-';

    return (
        <div className="hero-card">
            <div className="hero-bg"></div>
            <div className="hero-content">

                <div className="hero-badges">
                    <div className="flex gap-2">
                        <span className={`badge online`} style={{ borderColor: isConnected ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                            <div className={`status-dot ${isConnected ? 'green' : 'red'}`}></div>
                            {isConnected ? 'Online' : 'Offline'}
                        </span>
                        <span className="badge">Structural Health Monitoring</span>
                    </div>

                    <span className="badge badge-update">
                        <RefreshCw size={12} className="text-teal" />
                        <div className="flex-col" style={{ gap: '0' }}>
                            <span style={{ color: 'var(--text-tertiary)', fontSize: '0.55rem', lineHeight: 1 }}>Last Update</span>
                            <span className="text-teal font-mono" style={{ fontSize: '0.65rem', lineHeight: 1.2 }}>
                                {latest ? formatTimestamp(latest.timestamp) : '-- no data --'}
                            </span>
                        </div>
                    </span>
                </div>

                <div>
                    <h2 className="hero-title">{siteName}</h2>
                    <p className="hero-subtitle">Vertically Monitored IoT Asset</p>
                </div>

                <div className="hero-stats-bar">
                    <div className="stat-item">
                        <div className="stat-icon-wrap"><MapPin size={14} /></div>
                        <div className="flex-col" style={{ gap: '0' }}>
                            <span className="stat-label">Site Name</span>
                            <span className="stat-value text-primary">{siteName}</span>
                        </div>
                    </div>

                    <div className="stat-item">
                        <div className="stat-icon-wrap"><Hash size={14} /></div>
                        <div className="flex-col" style={{ gap: '0' }}>
                            <span className="stat-label">Device ID</span>
                            <span className="stat-value text-primary">{siteCode}</span>
                        </div>
                    </div>

                    <div className="stat-item">
                        <div className="stat-icon-wrap"><Ratio size={14} /></div>
                        <div className="flex-col" style={{ gap: '0' }}>
                            <span className="stat-label">Tower Type</span>
                            <span className="stat-value text-primary">{towerType}</span>
                        </div>
                    </div>

                    <div className="stat-item">
                        <div className="stat-icon-wrap"><ArrowUp size={14} /></div>
                        <div className="flex-col" style={{ gap: '0' }}>
                            <span className="stat-label">Tinggi</span>
                            <span className="stat-value text-primary">{towerHeight} Meter</span>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    );
}
