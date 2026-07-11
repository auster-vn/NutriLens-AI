# Product Data

Open Food Facts is the primary source for product labels, ingredients, allergens, additives, images, Nutri-Score, and nutriments.

Backend flow:

1. Validate barcode format.
2. Check `product_cache`.
3. Fetch Open Food Facts only on cache miss.
4. Normalize fields.
5. Store the raw payload for traceability.
6. Score deterministically from normalized product data and user profile.

Missing values are surfaced to users and never guessed by RAG.
