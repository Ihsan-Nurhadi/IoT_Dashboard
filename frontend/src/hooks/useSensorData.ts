'use client';
import { useState, useEffect, useCallback } from 'react';

const API_BASE = '/api/verticality';

export interface SensorData {
    id: number;
    device_id?: string;
    timestamp: string;
    wind_speed: number;
    wind_speed_ms: number;
    pitch: number;
    roll: number;
    tilt_rate: number;
    sway: number;
    total_tilt: number;
    indikator?: string;
}

export function useSensorData(refreshInterval = 5000, deviceId?: string) {
    const [latest, setLatest] = useState<SensorData | null>(null);
    const [history, setHistory] = useState<SensorData[]>([]);
    const [isConnected, setIsConnected] = useState(false);

    const fetchData = useCallback(async () => {
        try {
            const params = deviceId ? `?device_id=${encodeURIComponent(deviceId)}` : '';
            const historyParams = deviceId
                ? `?limit=100&device_id=${encodeURIComponent(deviceId)}`
                : '?limit=100';

            const [latestRes, historyRes] = await Promise.all([
                fetch(`${API_BASE}/sensor-data/latest/${params}`),
                fetch(`${API_BASE}/sensor-data/history/${historyParams}`),
            ]);

            if (latestRes.ok) {
                const latestData = await latestRes.json();
                setLatest(latestData);
                setIsConnected(true);
            }

            if (historyRes.ok) {
                const historyData = await historyRes.json();
                setHistory(historyData);
            }
        } catch {
            setIsConnected(false);
        }
    }, [deviceId]);

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, refreshInterval);
        return () => clearInterval(interval);
    }, [fetchData, refreshInterval]);

    return { latest, history, isConnected };
}
