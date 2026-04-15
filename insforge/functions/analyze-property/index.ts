export default async function(req: Request) {
  try {
    const body = await req.json()
    
    // Autodetectamos la URL base real (evitando localhost)
    const url = new URL(req.url)
    const INSFORGE_URL = `${url.protocol}//${url.host.replace('.functions', '.eu-central')}`
    const INSFORGE_KEY = Deno.env.get('INSFORGE_ANON_KEY') || Deno.env.get('SUPABASE_ANON_KEY')!
    
    // CASO A: Extracción desde texto bruto (Facebook)
    if (body.raw_text) {
      console.log(`🧠 Llamada Directa a la IA en: ${INSFORGE_URL}/api/ai/chat/completion`)
      
      const response = await fetch(`${INSFORGE_URL}/api/ai/chat/completion`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${INSFORGE_KEY}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          messages: [
            { role: 'system', content: 'Extract real estate data to JSON only.' },
            { role: 'user', content: body.raw_text }
          ],
          json: true,
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
        throw new Error(`AI API Real Error: ${errText}`)
      }

      const data = await response.json()
      return new Response(JSON.stringify(data), { headers: { "Content-Type": "application/json" } })
    }

    // CASO B: Análisis de puntuación
    const { property, market_avg } = body
    let score = (property?.price < (market_avg || 300000)) ? 80 : 50

    return new Response(JSON.stringify({ 
      score: score, 
      reasons: ["Análisis por precio de mercado"],
      opportunity_score: score
    }), { headers: { "Content-Type": "application/json" } })

  } catch (err: any) {
    return new Response(JSON.stringify({ error: err.message }), { 
      status: 400,
      headers: { "Content-Type": "application/json" } 
    })
  }
}
