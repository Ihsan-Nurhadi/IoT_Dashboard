'use client';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip } from 'recharts';
import { type SensorData } from '../../hooks/useSensorData';



interface TrendAnalysisProps {
    history: SensorData[];
}

const CustomizedDot = (props: any) => {
    const { cx, cy, stroke, fill } = props;
    return (
        <circle cx={cx} cy={cy} r={2.5} stroke={stroke} strokeWidth={1} fill={fill} />
    );
};

const CustomTooltip = ({ active, payload, label, unit, color }: any) => {
    if (active && payload && payload.length) {
        return (
            <div style={{
                backgroundColor: 'rgba(12, 18, 30, 0.9)',
                backdropFilter: 'blur(8px)',
                border: '1px solid rgba(255,255,255,0.05)',
                borderRadius: '8px',
                padding: '0.5rem 0.75rem',
                color: 'var(--text-primary)',
                fontSize: '0.75rem',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.5)'
            }}>
                <div style={{ color: 'var(--text-tertiary)', fontSize: '0.6rem', marginBottom: '0.2rem' }}>{label}</div>
                <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                    <div style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: color }}></div>
                    {payload[0].value} <span style={{ color: 'var(--text-secondary)', fontSize: '0.65rem' }}>{unit}</span>
                </div>
            </div>
        );
    }
    return null;
};

export default function TrendAnalysis({ history }: TrendAnalysisProps) {
    const recentData = history.slice(0, 30).reverse();

    const windData = recentData.map(d => ({
        time: new Date(d.timestamp).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }),
        pv: d.wind_speed
    }));

    const tiltData = recentData.map(d => ({
        time: new Date(d.timestamp).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }),
        pv: d.total_tilt
    }));

    const swayData = recentData.map(d => ({
        time: new Date(d.timestamp).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }),
        pv: d.sway
    }));

    const windValues = windData.map(d => d.pv);
    const windMin = windValues.length > 0 ? Math.max(0, Math.floor(Math.min(...windValues) * 5) / 5) : 0;
    const windMax = windValues.length > 0 ? Math.ceil(Math.max(...windValues) * 5) / 5 + 0.2 : 2;

    const tiltValues = tiltData.map(d => d.pv);
    const tiltMin = tiltValues.length > 0 ? Math.max(0, Math.floor(Math.min(...tiltValues) * 100) / 100) : 0;
    const tiltMax = tiltValues.length > 0 ? Math.ceil(Math.max(...tiltValues) * 100) / 100 + 0.01 : 0.1;

    const swayValues = swayData.map(d => d.pv);
    const swayMin = swayValues.length > 0 ? Math.max(0, Math.floor(Math.min(...swayValues) / 5) * 5) : 0;
    const swayMax = swayValues.length > 0 ? Math.ceil(Math.max(...swayValues) / 5) * 5 + 5 : 80;

    return (
        <div className="flex-col gap-3">
            <div className="section-header" style={{ marginBottom: 0 }}>
                <div className="section-title-wrap">
                    <div className="deco-line"></div>
                    <h3 className="section-title">Trend Analysis</h3>
                </div>
            </div>

            <div className="charts-grid">
                <div className="chart-card">
                    <div className="chart-header">
                        <h4 className="chart-title text-primary">Wind Speed Trend</h4>
                        <div className="time-badge">Last {windData.length} readings</div>
                    </div>
                    <div className="chart-container">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={windData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                                <defs>
                                    <linearGradient id="colorTeal" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="var(--accent-teal)" stopOpacity={0.15} />
                                        <stop offset="95%" stopColor="var(--accent-teal)" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="1 0" stroke="rgba(255,255,255,0.05)" vertical={true} />
                                <XAxis dataKey="time" stroke="var(--text-tertiary)" fontSize={9} tickLine={false} axisLine={{ stroke: 'rgba(255,255,255,0.05)' }} tickMargin={8} />
                                <YAxis stroke="var(--text-tertiary)" fontSize={9} tickLine={false} axisLine={false} domain={[windMin, windMax]} />
                                <Tooltip content={<CustomTooltip unit="knot" color="var(--accent-teal)" />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1, strokeDasharray: '4 4' }} />
                                <Area type="monotone" dataKey="pv" stroke="var(--accent-teal)" strokeWidth={2} fillOpacity={1} fill="url(#colorTeal)" dot={<CustomizedDot fill="var(--bg-main)" stroke="var(--accent-teal)" />} />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                <div className="chart-card">
                    <div className="chart-header">
                        <h4 className="chart-title text-primary">Total Tilt Trend</h4>
                        <div className="time-badge">Last {tiltData.length} readings</div>
                    </div>
                    <div className="chart-container">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={tiltData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                                <defs>
                                    <linearGradient id="colorRed" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="var(--accent-red)" stopOpacity={0.15} />
                                        <stop offset="95%" stopColor="var(--accent-red)" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="1 0" stroke="rgba(255,255,255,0.05)" vertical={true} />
                                <XAxis dataKey="time" stroke="var(--text-tertiary)" fontSize={9} tickLine={false} axisLine={{ stroke: 'rgba(255,255,255,0.05)' }} tickMargin={8} />
                                <YAxis stroke="var(--text-tertiary)" fontSize={9} tickLine={false} axisLine={false} domain={[tiltMin, tiltMax]} />
                                <Tooltip content={<CustomTooltip unit="°" color="var(--accent-red)" />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1, strokeDasharray: '4 4' }} />
                                <Area type="monotone" dataKey="pv" stroke="var(--accent-red)" strokeWidth={2} fillOpacity={1} fill="url(#colorRed)" dot={<CustomizedDot fill="var(--bg-main)" stroke="var(--accent-red)" />} />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                <div className="chart-card">
                    <div className="chart-header">
                        <h4 className="chart-title text-primary">Sway Trend</h4>
                        <div className="time-badge">Last {swayData.length} readings</div>
                    </div>
                    <div className="chart-container">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={swayData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                                <defs>
                                    <linearGradient id="colorBlue" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="var(--accent-blue)" stopOpacity={0.15} />
                                        <stop offset="95%" stopColor="var(--accent-blue)" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="1 0" stroke="rgba(255,255,255,0.05)" vertical={true} />
                                <XAxis dataKey="time" stroke="var(--text-tertiary)" fontSize={9} tickLine={false} axisLine={{ stroke: 'rgba(255,255,255,0.05)' }} tickMargin={8} />
                                <YAxis stroke="var(--text-tertiary)" fontSize={9} tickLine={false} axisLine={false} domain={[swayMin, swayMax]} />
                                <Tooltip content={<CustomTooltip unit="mm" color="var(--accent-blue)" />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1, strokeDasharray: '4 4' }} />
                                <Area type="monotone" dataKey="pv" stroke="var(--accent-blue)" strokeWidth={2} fillOpacity={1} fill="url(#colorBlue)" dot={<CustomizedDot fill="var(--bg-main)" stroke="var(--accent-blue)" />} />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        </div>
    );
}
