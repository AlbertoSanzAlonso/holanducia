# Real Estate Intelligence Knowledge Base (RAG)

## 1. Quality Indicators
- **High Opportunity**: Properties where price_m2 is 20% below the city average.
- **Urgency Signals**: "Urgente", "Oportunidad", "Bajada de precio", "Herencia".
- **Amenity Value**: 
    - Parking adds ~10-15k€ in Madrid/Malaga.
    - Terrace adds ~15% to high-floor properties.
    - Pool is a critical filter for vacation rentals.

## 2. Infiltration Rules
- **Anti-Blocking**: If a portal returns "Error" or "Interrupción" 3 times, wait 10 mins.
- **De-duplication**: Never extract a URL that exists in the DB (checked by Director).
- **Portal Specifics**:
    - Fotocasa: High quality images, strict on bot detection.
    - Habitalcla: Good for Cataluña/Comunidad Valenciana.
    - Pisos.com: Often has older listings with negotiation room.

## 3. Data Integrity
- Title must be descriptive.
- Price MUST be a number > 0.
- City must be normalized (Málaga vs Malaga).
