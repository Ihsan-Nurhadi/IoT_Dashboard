'use client';
import { useState, useEffect, useCallback } from 'react';

const API_BASE = '/api/verticality';

export interface SiteStatus {
    device_id: string;
    live_status: 'online' | 'warning' | 'offline';
    timestamp: string;
    wind_speed: number;
    wind_speed_ms: number;
    total_tilt: number;
    sway: number;
}

export function useSitesStatus(refreshInterval = 15000) {
    const [statuses, setStatuses] = useState<SiteStatus[]>([]);

    const fetchStatuses = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/sensor-data/sites-status/`);
            if (res.ok) {
                const data = await res.json();
                setStatuses(data);
            }
        } catch {
            // silent fail
        }
    }, []);

    useEffect(() => {
        fetchStatuses();
        const interval = setInterval(fetchStatuses, refreshInterval);
        return () => clearInterval(interval);
    }, [fetchStatuses, refreshInterval]);

    return statuses;
}
