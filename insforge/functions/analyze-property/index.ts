export default async function(req: Request) {
  try {
    const body = await req.json()
    const INSFORGE_URL = Deno.env.get('INSFORGE_URL')!
    const INSFORGE_KEY = Deno.env.get('INSFORGE_ANON_KEY')!
    
    // CASO A: Extracción desde texto bruto (Facebook)
    if (body.raw_text) {
      console.log("🧠 Extrayendo con API Directa de IA...")
      
      const response = await fetch(`${INSFORGE_URL}/api/ai/extract`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${INSFORGE_KEY}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          text: body.raw_text,
          schema: {
            title: "string",
            price: "number",
            city: "string",
            rooms: "number",
            is_individual: "boolean",
            opportunity_score: "number"
          }
        })
      })

      if (!response.ok) {
        const errText = await response.text()
        throw new Error(`AI API Error: ${errText}`)
      }

      const data = await response.json()
      return new Response(JSON.stringify(data), { headers: { "Content-Type": "application/json" } })
    }

    // CASO B: Análisis de puntuación (Fallback simple)
    const { property, market_avg } = body
    let score = (property?.price < (market_avg || 300000)) ? 80 : 50

    return new Response(JSON.stringify({ 
      score: score, 
      reasons: ["Análisis por precio de zona"],
      opportunity_score: score
    }), { headers: { "Content-Type": "application/json" } })

  } catch (err: any) {
    return new Response(JSON.stringify({ error: err.message }), { 
      status: 400,
      headers: { "Content-Type": "application/json" } 
    })
  }
}
