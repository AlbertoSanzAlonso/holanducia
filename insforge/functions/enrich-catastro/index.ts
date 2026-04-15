export default async (req: Request) => {
  // Manejo de CORS
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
    const { address, city, province, catastro_ref } = await req.json();
    
    let result;
    if (catastro_ref) {
      result = await getDetailsByRC(catastro_ref);
    } else if (address && city) {
      const rc = await getRCByAddress(address, city, province || city);
      if (rc) {
        result = await getDetailsByRC(rc);
      }
    }

    if (!result) throw new Error("No se pudo localizar en Catastro");

    const data = await result.json();

    return new Response(JSON.stringify(data), {
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
};

async function getRCByAddress(address: string, city: string, province: string) {
  const url = `https://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCallejero.asmx/Consulta_DNPPP?Provincia=${encodeURIComponent(province)}&Municipio=${encodeURIComponent(city)}&Sigla=&Calle=${encodeURIComponent(address)}&Numero=&Bloque=&Escalera=&Planta=&Puerta=`;
  const response = await fetch(url);
  const text = await response.text();
  const rcMatch = text.match(/<pc1>(.*?)<\/pc1>.*?<pc2>(.*?)<\/pc2>/s);
  return rcMatch ? rcMatch[1] + rcMatch[2] : null;
}

async function getDetailsByRC(rc: string) {
  const url = `https://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCallejero.asmx/Consulta_RCCOOR?RC=${rc}&Provincia=&Municipio=`;
  const response = await fetch(url);
  const text = await response.text();
  const surface = text.match(/<sfc>(.*?)<\/sfc>/)?.[1] || "0";
  const year = text.match(/<ant>(.*?)<\/ant>/)?.[1] || "0";
  const use = text.match(/<uso>(.*?)<\/uso>/)?.[1] || "Residencial";

  return new Response(JSON.stringify({
    catastro_ref: rc,
    surface_m2: parseFloat(surface.replace(',', '.')),
    year_built: parseInt(year),
    use: use,
    is_verified: true
  }));
}
