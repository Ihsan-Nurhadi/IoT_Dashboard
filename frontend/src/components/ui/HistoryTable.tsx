'use client';
import { useState, useEffect, useRef } from 'react';
import { History, Wind, ArrowRightLeft, Droplet, ArrowUp, ArrowDown, Activity, Compass, Download } from 'lucide-react';
import { type SensorData } from '../../hooks/useSensorData';


import ExportModal from './ExportModal';

interface HistoryTableProps {
    history: SensorData[];
}

interface HistoryEvent {
    id: number;
    date: string;
    time: string;
    ago: string;
    param: string;
    icon: React.ReactNode;
    prev: string;
    curr: string;
    change: string;
    changeType: 'up' | 'down';
    status: string;
    color: string;
}

function getParamIcon(param: string) {
    switch (param) {
        case 'Wind Speed': return <Wind size={12} />;
        case 'Sway': return <ArrowRightLeft size={12} />;
        case 'Total Tilt': return <Droplet size={12} />;
        case 'Pitch': return <Compass size={12} />;
        case 'Roll': return <Activity size={12} />;
        default: return <Activity size={12} />;
    }
}

function getStatus(param: string, value: number): { status: string; color: string } {
    if (param === 'Sway') {
        if (value > 50) return { status: 'Critical', color: 'red' };
        if (value > 30) return { status: 'Warning', color: 'yellow' };
        return { status: 'Normal', color: 'green' };
    }
    if (param === 'Total Tilt') {
        if (value > 0.1) return { status: 'Critical', color: 'red' };
        if (value > 0.05) return { status: 'Warning', color: 'yellow' };
        return { status: 'Normal', color: 'green' };
    }
    if (param === 'Wind Speed') {
        if (value > 15) return { status: 'Critical', color: 'red' };
        if (value > 10) return { status: 'Warning', color: 'yellow' };
        return { status: 'Normal', color: 'green' };
    }
    return { status: 'Normal', color: 'green' };
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
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
}

export default function HistoryTable({ history }: HistoryTableProps) {
    const [events, setEvents] = useState<HistoryEvent[]>([]);
    const [newRowIds, setNewRowIds] = useState<number[]>([]);
    const prevHistoryRef = useRef<SensorData[]>([]);

    useEffect(() => {
        if (history.length < 2) return;

        const currentIds = history.map(h => h.id);
        const prevIds = prevHistoryRef.current.map(h => h.id);
        if (JSON.stringify(currentIds) === JSON.stringify(prevIds)) return;

        const addedIds = currentIds.filter(id => !prevIds.includes(id) && prevIds.length > 0);
        if (addedIds.length > 0) {
            setNewRowIds(prev => [...prev, ...addedIds]);
            setTimeout(() => {
                setNewRowIds(prev => prev.filter(id => !addedIds.includes(id)));
            }, 2000);
        }

        prevHistoryRef.current = history;

        const newEvents: HistoryEvent[] = [];
        const params = ['wind_speed', 'pitch', 'roll', 'sway', 'total_tilt'] as const;
        const paramNames: Record<string, string> = {
            wind_speed: 'Wind Speed',
            pitch: 'Pitch',
            roll: 'Roll',
            sway: 'Sway',
            total_tilt: 'Total Tilt',
        };
        const paramUnits: Record<string, string> = {
            wind_speed: 'knot',
            pitch: '°',
            roll: '°',
            sway: 'mm',
            total_tilt: '°',
        };

        for (let i = 0; i < history.length - 1 && newEvents.length < 50; i++) {
            const curr = history[i];
            const prev = history[i + 1];

            let biggestParam: typeof params[number] = params[0];
            let biggestDiff = 0;

            for (const p of params) {
                const diff = Math.abs(curr[p] - prev[p]);
                if (diff > biggestDiff) {
                    biggestDiff = diff;
                    biggestParam = p;
                }
            }

            const paramName = paramNames[biggestParam];
            const unit = paramUnits[biggestParam];
            const currVal = curr[biggestParam];
            const prevVal = prev[biggestParam];
            const diff = currVal - prevVal;
            const changeType = diff >= 0 ? 'up' : 'down';
            const { status, color } = getStatus(paramName, currVal);

            const d = new Date(curr.timestamp);
            const dateString = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
            const timeString = d.toTimeString().split(' ')[0];

            const decimals = biggestParam === 'sway' ? 0 : biggestParam === 'wind_speed' ? 2 : biggestParam === 'total_tilt' ? 4 : 3;

            newEvents.push({
                id: curr.id,
                date: dateString,
                time: timeString,
                ago: timeAgo(curr.timestamp),
                param: paramName,
                icon: getParamIcon(paramName),
                prev: `${prevVal.toFixed(decimals)} ${unit}`,
                curr: `${currVal.toFixed(decimals)} ${unit}`,
                change: `${diff >= 0 ? '+' : ''}${diff.toFixed(decimals)} ${unit}`,
                changeType: changeType as 'up' | 'down',
                status,
                color,
            });
        }

        setEvents(newEvents);
    }, [history]);

    useEffect(() => {
        const timer = setInterval(() => {
            if (history.length === 0) return;
            setEvents(prev => prev.map(e => {
                const matched = history.find(h => h.id === e.id);
                return matched ? { ...e, ago: timeAgo(matched.timestamp) } : e;
            }));
        }, 5000);
        return () => clearInterval(timer);
    }, [history]);

    const normalCount = events.filter(e => e.color === 'green').length;
    const warningCount = events.filter(e => e.color === 'yellow').length;
    const criticalCount = events.filter(e => e.color === 'red').length;

    const [isExportOpen, setIsExportOpen] = useState(false);

    const handleExportClick = () => {
        setIsExportOpen(true);
    };

    const exportToExcelConfirm = (startDate: Date | null, endDate: Date | null) => {
        setIsExportOpen(false);
        let exportData = events;

        if (startDate && endDate) {
            exportData = events.filter(e => {
                const eventDate = new Date(e.date + ' ' + e.time);
                const start = new Date(startDate);
                start.setHours(0, 0, 0, 0);
                const end = new Date(endDate);
                end.setHours(23, 59, 59, 999);
                return eventDate >= start && eventDate <= end;
            });
        }

        exportData = exportData.slice(0, 50);

        if (exportData.length === 0) return;

        const headers = ['Date', 'Time', 'Parameter', 'Previous', 'Current', 'Change', 'Status'];
        const rows = exportData.map(e => [
            e.date,
            e.time,
            e.param,
            e.prev,
            e.curr,
            e.change,
            e.status,
        ]);

        const csvContent = '\uFEFF' + [headers, ...rows]
            .map(row => row.map(cell => `"${cell}"`).join(','))
            .join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        const now = new Date();
        const filename = `SHM_History_${now.getFullYear()}${(now.getMonth() + 1).toString().padStart(2, '0')}${now.getDate().toString().padStart(2, '0')}_${now.getHours().toString().padStart(2, '0')}${now.getMinutes().toString().padStart(2, '0')}.csv`;
        link.href = url;
        link.download = filename;
        link.click();
        URL.revokeObjectURL(url);
    };

    return (
        <div className="history-section flex-col" style={{ display: 'flex', height: '100%' }}>
            <style>{`
                @keyframes rowHighlight {
                    0% { background-color: rgba(14, 189, 181, 0.15); }
                    10% { background-color: rgba(14, 189, 181, 0.2); }
                    100% { background-color: transparent; }
                }
                .new-row {
                    animation: rowHighlight 2s ease-out forwards;
                }
                .new-row td:first-child::before {
                    content: '';
                    position: absolute;
                    left: -0.5rem;
                    top: 0;
                    bottom: 0;
                    width: 3px;
                    background-color: var(--accent-teal);
                    box-shadow: 0 0 8px var(--accent-teal);
                    border-radius: 4px;
                }
                .new-badge {
                    background-color: rgba(14, 189, 181, 0.15);
                    color: var(--accent-teal);
                    border: 1px solid rgba(14, 189, 181, 0.3);
                    font-size: 0.55rem;
                    padding: 0.15rem 0.4rem;
                    border-radius: 4px;
                    margin-left: 0.5rem;
                    font-weight: 700;
                    letter-spacing: 0.05em;
                    animation: pulse-icon 2s infinite ease-in-out;
                }
                .history-table td {
                    position: relative;
                }
            `}</style>

            <div className="section-header" style={{ marginBottom: '1.25rem' }}>
                <div className="section-title-wrap">
                    <div className="section-icon" style={{ color: 'var(--text-secondary)', background: 'transparent', width: 'auto', height: 'auto', border: 'none', paddingRight: '0.25rem' }}>
                        <History size={20} />
                    </div>
                    <div className="flex-col" style={{ gap: '0.1rem' }}>
                        <h3 className="section-title" style={{ fontSize: '0.875rem' }}>History</h3>
                        <p className="section-subtitle">Live data from MQTT · auto-refresh every 5s</p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={handleExportClick}
                        disabled={events.length === 0}
                        className="badge flex items-center gap-1.5"
                        style={{
                            padding: '0.2rem 0.6rem',
                            cursor: events.length > 0 ? 'pointer' : 'not-allowed',
                            background: 'rgba(14, 165, 233, 0.1)',
                            border: '1px solid rgba(14, 165, 233, 0.3)',
                            color: '#38bdf8',
                            opacity: events.length === 0 ? 0.4 : 1,
                            transition: 'all 0.2s ease',
                        }}
                        onMouseEnter={e => { if (events.length > 0) { e.currentTarget.style.background = 'rgba(14, 165, 233, 0.2)'; e.currentTarget.style.borderColor = 'rgba(14, 165, 233, 0.5)'; } }}
                        onMouseLeave={e => { e.currentTarget.style.background = 'rgba(14, 165, 233, 0.1)'; e.currentTarget.style.borderColor = 'rgba(14, 165, 233, 0.3)'; }}
                    >
                        <Download size={12} />
                        <span style={{ fontSize: '0.65rem' }}>Export</span>
                    </button>
                    <div className="badge online flex items-center gap-1.5" style={{ padding: '0.2rem 0.6rem' }}>
                        <div className={`status-dot ${history.length > 0 ? 'green' : 'red'}`}></div>
                        <span style={{ fontSize: '0.65rem' }}>{history.length > 0 ? 'Live' : 'No Data'}</span>
                    </div>
                </div>
            </div>

            <ExportModal
                isOpen={isExportOpen}
                onClose={() => setIsExportOpen(false)}
                onExport={exportToExcelConfirm}
            />

            <div className="history-tabs flex justify-between items-center">
                <div className="flex gap-2">
                    <button className="history-tab active">
                        All <span className="tab-count gray">{events.length}</span>
                    </button>
                    <button className="history-tab">
                        Normal <span className="tab-count green">{normalCount}</span>
                    </button>
                    <button className="history-tab">
                        Warning <span className="tab-count yellow">{warningCount}</span>
                    </button>
                    <button className="history-tab">
                        Critical <span className="tab-count red">{criticalCount}</span>
                    </button>
                </div>
                <div className="text-tertiary" style={{ fontSize: '0.65rem' }}>Showing {events.length} events</div>
            </div>

            <div className="table-scroll-container" style={{
                maxHeight: '350px',
                overflowY: 'auto',
                paddingRight: '0.5rem',
                flex: 1
            }}>
                <table className="history-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead style={{ position: 'sticky', top: 0, background: 'var(--bg-card)', zIndex: 10 }}>
                        <tr>
                            <th>DATE & TIME</th>
                            <th>PARAMETER</th>
                            <th className="hide-mobile">PREVIOUS</th>
                            <th>CURRENT</th>
                            <th className="hide-mobile">CHANGE</th>
                            <th className="status-col-mobile">STATUS</th>
                        </tr>
                    </thead>
                    <tbody>
                        {events.length === 0 ? (
                            <tr>
                                <td colSpan={6} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-tertiary)' }}>
                                    Waiting for sensor data from MQTT...
                                </td>
                            </tr>
                        ) : events.map((row) => (
                            <tr key={row.id} className={newRowIds.includes(row.id) ? "new-row" : ""}>
                                <td>
                                    <div className="time-col" style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
                                        <span className="text-tertiary" style={{ fontSize: '0.6rem', fontWeight: 500 }}>{row.date}</span>
                                        <div className="history-time-wrap">
                                            <span className="font-mono text-primary" style={{ fontSize: '0.75rem', fontWeight: 600 }}>{row.time}</span>
                                            <span className="text-tertiary history-ago-text" style={{ fontSize: '0.6rem' }}>{row.ago}</span>
                                        </div>
                                    </div>
                                </td>
                                <td>
                                    <div className="param-name text-secondary">
                                        <div className="param-icon-wrap">{row.icon}</div>
                                        {row.param === 'Wind Speed' ? (
                                            <>
                                                <span className="hide-mobile">Wind Speed</span>
                                                <span className="show-mobile">Wind<br />Speed</span>
                                            </>
                                        ) : (
                                            row.param
                                        )}
                                        {newRowIds.includes(row.id) && (
                                            <span className="new-badge hide-mobile">NEW</span>
                                        )}
                                    </div>
                                </td>
                                <td className="text-tertiary font-mono hide-mobile" style={{ fontSize: '0.75rem' }}>{row.prev}</td>
                                <td className="font-mono text-primary" style={{ fontWeight: 700, fontSize: '0.75rem' }}>
                                    <div className="history-val-wrap">
                                        <span>{row.curr.split(' ')[0]}</span>
                                        <span className="history-unit text-tertiary" style={{ fontSize: '0.65rem' }}>
                                            {row.curr.split(' ').slice(1).join(' ')}
                                        </span>
                                    </div>
                                </td>
                                <td className="hide-mobile">
                                    <div className={`change-val ${row.changeType === 'down' ? 'text-green' : 'text-red'}`}>
                                        {row.changeType === 'up' ? <ArrowUp size={12} /> : <ArrowDown size={12} />} {row.change}
                                    </div>
                                </td>
                                <td className="status-col-mobile">
                                    <span className={`status-badge ${row.color}`}>
                                        <div className={`status-dot ${row.color}`}></div> {row.status}
                                    </span>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <div className="flex justify-between items-center" style={{ marginTop: '1.25rem', paddingTop: '1.25rem', borderTop: '1px solid rgba(255,255,255,0.03)', fontSize: '0.75rem', flexWrap: 'wrap', gap: '1rem' }}>
                <div className="flex gap-6">
                    <span className="flex items-center" style={{ gap: '0.375rem' }}><div className="status-dot green"></div> <span className="text-secondary">{normalCount} normal</span></span>
                    <span className="flex items-center" style={{ gap: '0.375rem' }}><div className="status-dot yellow"></div> <span className="text-secondary">{warningCount} warning</span></span>
                    <span className="flex items-center" style={{ gap: '0.375rem' }}><div className="status-dot red"></div> <span className="text-secondary">{criticalCount} critical</span></span>
                </div>
                <div className="text-tertiary" style={{ fontSize: '0.7rem' }}>Auto-updating · live from MQTT backend</div>
            </div>
        </div>
    );
}
