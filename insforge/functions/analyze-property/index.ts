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

export default async (req: Request) => {
  try {
    const { property, market_avg }: { property: Property, market_avg: number } = await req.json()
    
    let score = 0
    const reasons: string[] = []

    // 1. Price Drop (if history provided)
    if (property.price_history && property.price_history.length > 0) {
      const last_price = property.price_history[property.price_history.length - 1].price
      if (property.price < last_price) {
        const discount = ((last_price - property.price) / last_price) * 100
        if (discount >= 5) {
          score += Math.min(40, discount * 2)
          reasons.push(`Bajada de precio: ${discount.toFixed(1)}%`)
        }
      }
    }

    // 2. Under Market Average
    if (property.price < market_avg) {
      const infra_value = ((market_avg - property.price) / market_avg) * 100
      if (infra_value >= 10) {
        score += Math.min(40, infra_value * 1.5)
        reasons.push(`${infra_value.toFixed(1)}% por debajo de la media de zona`)
      }
    }

    // 3. Individual Owner
    if (property.is_individual) {
      score += 20
      reasons.push("Vendedor particular (Oportunidad de captación)")
    }

    return new Response(
      JSON.stringify({ 
        score: Math.min(100, score), 
        reasons,
        is_hot: score >= 80 
      }),
      { headers: { "Content-Type": "application/json" } }
    )
  } catch (err: any) {
    return new Response(JSON.stringify({ error: err.message }), { 
      status: 400,
      headers: { "Content-Type": "application/json" } 
    })
  }
}
