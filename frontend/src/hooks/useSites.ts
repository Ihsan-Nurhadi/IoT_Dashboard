'use client';

import { useState, useEffect, useCallback } from 'react';
import { type Site } from '../data/sites';


const API_BASE = '/api/verticality';


export function useSites() {
    const [sites, setSites] = useState<Site[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    const fetchSites = useCallback(async () => {
        try {
            setLoading(true);
            const res = await fetch(`${API_BASE}/sensor-data/sites/`);
            if (res.ok) {
                const data = await res.json();
                setSites(data);
                setError(null);
            } else {
                setError('Gagal mengambil data site dari server.');
            }
        } catch {
            setError('Terjadi kesalahan jaringan.');
        } finally {
            setLoading(false);
        }
    }, []);

    const addSite = async (newSite: Site): Promise<boolean> => {
        try {
            const res = await fetch(`${API_BASE}/sensor-data/sites/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(newSite),
            });
            if (res.ok) {
                await fetchSites();
                return true;
            }
            return false;
        } catch {
            return false;
        }
    };

    const updateSite = async (id: string, updatedFields: Partial<Site>): Promise<boolean> => {
        try {
            const res = await fetch(`${API_BASE}/sensor-data/sites/${id}/`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(updatedFields),
            });
            if (res.ok) {
                await fetchSites();
                return true;
            }
            return false;
        } catch {
            return false;
        }
    };

    const deleteSite = async (id: string): Promise<boolean> => {
        try {
            const res = await fetch(`${API_BASE}/sensor-data/sites/${id}/`, {
                method: 'DELETE',
            });
            if (res.ok) {
                await fetchSites();
                return true;
            }
            return false;
        } catch {
            return false;
        }
    };

    useEffect(() => {
        fetchSites();
    }, [fetchSites]);

    return {
        sites,
        loading,
        error,
        refreshSites: fetchSites,
        addSite,
        updateSite,
        deleteSite,
    };
}
