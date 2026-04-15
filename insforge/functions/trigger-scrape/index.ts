export default async (req: Request) => {
  // Manejo de CORS (Preflight request)
  if (req.method === "OPTIONS") {
    return new Response("ok", {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
      },
    });
  }

  try {
    const internal_url = Deno.env.get("INSFORGE_INTERNAL_URL");
    const api_key = Deno.env.get("API_KEY");
    
    // Inserts REQUIRE array format: [{...}]
    const response = await fetch(`${internal_url}/api/database/records/scraping_requests`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${api_key}`,
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
      },
      body: JSON.stringify([{
        status: "pending"
      }])
    });

    if (!response.ok) {
      const errorDetail = await response.text();
      console.error("DB Insert Error:", errorDetail);
      return new Response(JSON.stringify({ error: "Failed to queue", details: errorDetail }), { 
        status: 500,
        headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" } 
      });
    }

    return new Response(JSON.stringify({ status: "success", message: "Scraping request queued" }), {
      headers: { 
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*" 
      }
    });

  } catch (err: any) {
    return new Response(JSON.stringify({ error: err.message }), { 
      status: 400,
      headers: { 
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*" 
      } 
    });
  }
}
