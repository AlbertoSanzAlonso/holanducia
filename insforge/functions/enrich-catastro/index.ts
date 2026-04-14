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
  price_history: any[];
  opportunity_score: number;
}

export default async (req: Request) => {
  try {
    const { catastro_ref } = await req.json()
    
    if (!catastro_ref) {
      throw new Error("Missing catastro_ref")
    }

    // Mocking Catastro Response
    // In production, this would call: https://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCallejero.asmx
    const mockData = {
      year_built: 1985 + Math.floor(Math.random() * 30),
      use: "Residencial",
      surface_m2: 85.0,
      floor: "2"
    }

    return new Response(
      JSON.stringify(mockData),
      { headers: { "Content-Type": "application/json" } }
    )
  } catch (err: any) {
    return new Response(JSON.stringify({ error: err.message }), { 
      status: 400,
      headers: { "Content-Type": "application/json" } 
    })
  }
}
