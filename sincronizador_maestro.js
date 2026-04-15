// HolanducIA - Sincronizador Maestro v1.0
// Pega esto en tu consola de desarrollador (F12) mientras navegas por Idealista/Milanuncios
// El sistema se encargará de "mirar" lo que tú ves y enviarlo a tu Dashboard.

(async function() {
  const INSFORGE_URL = "https://s7pytj95.eu-central.insforge.app";
  const ANON_KEY = "ik_0ed6e333e7a2e51c6c94939d8d8afbcf";

  console.log("🚀 HolanducIA: Sincronizador Activado. Ve navegando por la lista de inmuebles...");

  setInterval(async () => {
    const properties = [];
    
    // Extractor para Idealista
    if (location.href.includes("idealista.com")) {
      document.querySelectorAll("article.item").forEach(item => {
        const title = item.querySelector(".item-link")?.innerText;
        const price = item.querySelector(".item-price")?.innerText;
        const url = item.querySelector(".item-link")?.href;
        
        if (title && price && url) {
            properties.push({
                source: "Idealista",
                title,
                price: parseInt(price.replace(/[^\d]/g, '')),
                url,
                city: "Málaga", // Adaptado a la zona actual
                description: "Visto por el usuario"
            });
        }
      });
    }

    // Extractor para Milanuncios
    if (location.href.includes("milanuncios.com")) {
      document.querySelectorAll(".ma-AdCard-container").forEach(item => {
        const title = item.querySelector(".ma-AdCard-title")?.innerText;
        const price = item.querySelector(".ma-AdPrice-value")?.innerText;
        const url = item.querySelector(".ma-AdCard-titleLink")?.href;
        
        if (title && price && url) {
            properties.push({
                source: "Milanuncios",
                title,
                price: parseInt(price.replace(/[^\d]/g, '')),
                url,
                city: "Málaga",
                description: "Visto por el usuario"
            });
        }
      });
    }

    if (properties.length > 0) {
      console.log(`✨ HolanducIA está enviando ${properties.length} leads a tu dashboard...`);
      for (const prop of properties) {
          await fetch(`${INSFORGE_URL}/api/database/records/properties`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${ANON_KEY}`
            },
            body: JSON.stringify(prop)
          });
      }
    }
  }, 5000);
})();
