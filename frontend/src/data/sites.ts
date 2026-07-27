export interface Site {
    id: string;
    name: string;
    siteId: string;
    code: string;
    lat: number;
    lng: number;
    area: string;
    region: string;
    kabupaten: string;
    status: 'online' | 'offline' | 'warning';
    towerType: string;
    towerHeight: number;
    isHidden?: boolean;
}

export const sites: Site[] = [
    {
        id: 'ckg-04-031',
        name: 'Nayaka WS',
        siteId: '20TS10B1529',
        code: 'E32_VER_WS',
        lat: -6.237318,
        lng: 106.919108,
        area: 'AREA 2',
        region: 'Jabodetabek Provinsi DKI Jakarta',
        kabupaten: 'Kota Adm. Jakarta Timur',
        status: 'online',
        towerType: 'SST',
        towerHeight: 42,
    }
];
