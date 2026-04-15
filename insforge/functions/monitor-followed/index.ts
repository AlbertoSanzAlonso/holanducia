import { createClient } from 'https://esm.sh/@insforge/sdk@1.2.4'

const insforge = createClient({
  baseUrl: Deno.env.get('INSFORGE_URL')!,
  anonKey: Deno.env.get('INSFORGE_ANON_KEY')!
})

export default async function(req: Request) {
  console.log("🔍 Iniciando ronda de vigilancia de 10 días...")
  
  try {
    // 1. Buscamos propiedades que lleven más de 10 días sin actualizarse
    const tenDaysAgo = new Date()
    tenDaysAgo.setDate(tenDaysAgo.getDate() - 10)

    const { data: properties, error } = await insforge.database
      .from('properties')
      .select('id, url, source')
      .lt('updated_at', tenDaysAgo.toISOString())
      .limit(20) 

    if (error) throw error

    if (!properties || properties.length === 0) {
      return new Response(JSON.stringify({ message: "Sistemas al día. No hay nada que vigilar hoy." }), {
        headers: { "Content-Type": "application/json" }
      })
    }

    // 2. Creamos misiones de rascado para cada una
    const requests = properties.map(p => ({
      status: 'pending',
      requested_at: new Date().toISOString(),
      source_name: `Monitoring: ${p.source}`,
      url: p.url
    }))

    await insforge.database.from('scraping_requests').insert(requests)

    return new Response(JSON.stringify({ 
      message: `🎯 Vigilancia activada para ${properties.length} propiedades.`,
      ids: properties.map(p => p.id)
    }), {
      headers: { "Content-Type": "application/json" }
    })

  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), { status: 500 })
  }
}
