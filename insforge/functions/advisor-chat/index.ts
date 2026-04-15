import { createClient } from "https://esm.sh/@insforge/sdk@1.2.4"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

export default async (req: Request) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: corsHeaders })

  try {
    const { message, previousMessages } = await req.json()
    const groqKey = Deno.env.get("GROQ_API_KEY") || Deno.env.get("LLM_API_KEY")

    if (!groqKey) {
      throw new Error("No hay ninguna API KEY de IA configurada en el servidor.")
    }

    // Initialize InsForge Client
    const insforge = createClient({
      baseUrl: Deno.env.get("INSFORGE_INTERNAL_URL") || "",
      anonKey: Deno.env.get("ANON_KEY") || ""
    })

    // Fetch context (Top 30)
    const { data: properties, error: dbError } = await insforge.database
      .from('properties')
      .select('title, price, city, rooms, size_m2, has_parking, has_pool, url')
      .order('created_at', { ascending: false })
      .limit(30)

    const propertyContext = (properties || []).map(p => 
      `- ${p.title} en ${p.city}: ${p.price}€, ${p.rooms} hab, ${p.size_m2}m2. Parking: ${p.has_parking}, Piscina: ${p.has_pool}. URL: ${p.url}`
    ).join('\n')

    const prompt = {
      model: "llama3-70b-8192",
      messages: [
        {
          role: "system",
          content: `Eres el Agente Asesor de HolanducIA. Experto inmobiliario de élite.
          
          CONTEXTO DE MERCADO ACTUAL:
          ${propertyContext}
          
          Instrucciones:
          - Analiza los datos reales proporcionados.
          - Sé directo y profesional. Usa Markdown.`
        },
        ...(previousMessages || []).slice(-4),
        { role: "user", content: message }
      ],
      temperature: 0.7
    }

    // Call Groq Direct (or OpenAI compatible)
    const groqRes = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${groqKey}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(prompt)
    })

    const groqData = await groqRes.json()
    
    if (!groqData.choices || groqData.choices.length === 0) {
       console.error("AI Error:", JSON.stringify(groqData))
       throw new Error(groqData.error?.message || "La IA externa ha devuelto un error.")
    }

    return new Response(JSON.stringify({ response: groqData.choices[0].message.content }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    })

  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 400,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    })
  }
}
