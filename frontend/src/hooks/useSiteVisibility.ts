'use client';

import { useState, useEffect, useCallback } from 'react';
import { sites, Site } from '../data/sites';

const API_BASE = '/api/verticality';


export interface SiteVisibilityState {
    device_id: string;
    is_hidden: boolean;
}

export function useSiteVisibility(customSites?: Site[]) {
    const [hiddenSiteIds, setHiddenSiteIds] = useState<Set<string>>(new Set());
    const [isLoading, setIsLoading] = useState(true);

    const fetchVisibility = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/sensor-data/sites-visibility/`);
            if (res.ok) {
                const data: SiteVisibilityState[] = await res.json();
                
                const hiddenFromBackend = data.filter(s => s.is_hidden).map(s => s.device_id);
                const backendSet = new Set(hiddenFromBackend);
                
                // Fallback to default list if not stored in DB yet.
                const activeSites = customSites || sites;
                const defaultHidden = activeSites.filter(s => s.isHidden).map(s => s.id);
                const hasExistingData = data.length > 0;

                setHiddenSiteIds(hasExistingData ? backendSet : new Set(defaultHidden));
            }
        } catch (e) {
            console.error('Failed to fetch site visibility:', e);
        } finally {
            setIsLoading(false);
        }
    }, [customSites]);

    useEffect(() => {
        fetchVisibility();
        // Optionially refresh every few seconds if we want truly live updates across multiple browsers
        const intervalId = setInterval(fetchVisibility, 10000);
        return () => clearInterval(intervalId);
    }, [fetchVisibility]);

    const toggleVisibility = async (deviceId: string) => {
        const newHiddenSites = new Set(hiddenSiteIds);
        const isCurrentlyHidden = newHiddenSites.has(deviceId);
        const newHiddenState = !isCurrentlyHidden;
        
        if (newHiddenState) {
            newHiddenSites.add(deviceId);
        } else {
            newHiddenSites.delete(deviceId);
        }

        // Optimistic update
        setHiddenSiteIds(newHiddenSites);

        try {
            await fetch(`${API_BASE}/sensor-data/sites-visibility/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify([{
                    device_id: deviceId,
                    is_hidden: newHiddenState
                }]),
            });
        } catch (e) {
            console.error('Failed to sync site visibility to server:', e);
            // Revert on failure
            setHiddenSiteIds(hiddenSiteIds);
        }
    };

    return { hiddenSiteIds, toggleVisibility, isLoading };
}
