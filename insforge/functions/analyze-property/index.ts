import { createClient } from 'https://esm.sh/@insforge/sdk@1.2.4'

const insforge = createClient({
  baseUrl: Deno.env.get('INSFORGE_URL')!,
  anonKey: Deno.env.get('INSFORGE_ANON_KEY')!
})

export default async function(req: Request) {
  try {
    const body = await req.json()
    
    // CASO A: Extracción desde texto bruto (Lo que viene de Facebook)
    if (body.raw_text) {
      console.log("🧠 Extrayendo datos semánticos con IA...")
      
      const { data, error } = await insforge.ai.generate(
        `Extract real estate data from this property listing. Return JSON ONLY.
        Text: ${body.raw_text}`,
        {
          json: true,
          schema: {
            title: "string (Example: Loft reformado en Arroyo de la Miel)",
            price: "number (Only the digits)",
            city: "string (Example: Benalmádena, Torremolinos, Málaga)",
            rooms: "number",
            size_m2: "number",
            is_individual: "boolean (true if private owner, false if agency)",
            opportunity_score: "number (0-100 score based on investment potential)"
          }
        }
      )

      if (error) throw error
      return new Response(JSON.stringify(data), { headers: { "Content-Type": "application/json" } })
    }

    // CASO B: Análisis de puntuación (Lo que ya existía)
    const { property, market_avg } = body
    if (!property) throw new Error("Faltan datos de la propiedad para el análisis")

    let score = 0
    const reasons: string[] = []

    if (property.price < (market_avg || 300000)) {
        score += 30
        reasons.push("Precio competitivo")
    }
    
    if (property.is_individual) {
        score += 20
        reasons.push("Particular")
    }

    return new Response(JSON.stringify({ 
      score: Math.min(100, score), 
      reasons,
      opportunity_score: score
    }), { headers: { "Content-Type": "application/json" } })

  } catch (err: any) {
    return new Response(JSON.stringify({ error: err.message }), { 
      status: 400,
      headers: { "Content-Type": "application/json" } 
    })
  }
}
