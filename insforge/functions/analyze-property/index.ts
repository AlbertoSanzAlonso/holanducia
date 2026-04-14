export default async (req: Request) => {
  try {
    const { property, market_avg } = await req.json()
    
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
