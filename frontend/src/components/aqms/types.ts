export interface SensorReading {
  id?: number;
  node_id: string;
  temperature: number;
  humidity: number;
  pressure: number;
  wind_speed: number;
  wind_direction: number;
  rain: number;
  light: number;
  radiation: number;
  pm25: number;
  pm10: number;
  negative_ion: number;
  noise?: number;
  co?: number;
  co2?: number;
  no2?: number;
  so2?: number;
  aqi?: number;
  timestamp: string;
}

export type RangeType = 'day' | 'week' | 'month';

export interface HistoryApiResponse {
  range: RangeType;
  count: number;
  results: SensorReading[];
}
