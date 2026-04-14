export interface Property {
  id?: number;
  external_id: string;
  source: string;
  url: string;
  title?: string;
  price: number;
  currency: string;
  location_raw?: string;
  city?: string;
  neighborhood?: string;
  address?: string;
  coordinates?: { x: number, y: number };
  catastro_ref?: string;
  rooms?: number;
  bathrooms?: number;
  size_m2?: number;
  description?: string;
  images: string[];
  is_individual: boolean;
  is_agency: boolean;
  last_seen: string; // ISO Date
  created_at?: string; // ISO Date
  updated_at?: string; // ISO Date
  price_history: PriceHistoryItem[];
  opportunity_score: number;
}

export interface PriceHistoryItem {
  price: number;
  date: string;
}

export interface AnalysisResult {
  score: number;
  reasons: string[];
  is_hot: boolean;
}
