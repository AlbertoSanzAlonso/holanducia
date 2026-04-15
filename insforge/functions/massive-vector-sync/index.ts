import { createClient } from "https://esm.sh/@insforge/sdk@1.2.4"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

export default async (req: Request) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: corsHeaders })

  try {
    const insforge = createClient({
      baseUrl: Deno.env.get("INSFORGE_INTERNAL_URL") || "",
      anonKey: Deno.env.get("ANON_KEY") || ""
    })

    // Fetch batch of properties without embeddings
    const { data: properties, error: fetchError } = await insforge.database
      .from('properties')
      .select('id, title, description, city')
      .is('embedding', null)
      .limit(10) // Process in small batches to avoid timeouts

    if (fetchError) throw fetchError
    if (!properties || properties.length === 0) {
      return new Response(JSON.stringify({ message: "No properties left to sync." }), { headers: corsHeaders })
    }

    const results = []
    for (const prop of properties) {
      const textToEmbed = `${prop.title} ${prop.city} ${prop.description || ''}`
      
      // Use InsForge AI service for embeddings
      const { data: embedding, error: aiError } = await insforge.ai.embeddings.create({
        input: textToEmbed.substring(0, 1000), // Safety cut
        model: "text-embedding-3-small" // Or equivalent standard
      })

      if (embedding) {
        await insforge.database
          .from('properties')
          .update({ embedding: embedding })
          .eq('id', prop.id)
        results.push(prop.id)
      }
    }

    return new Response(JSON.stringify({ 
        synced: results.length, 
        ids: results,
        remaining: "Call again for next batch" 
    }), { headers: corsHeaders })

  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), { status: 400, headers: corsHeaders })
  }
}
