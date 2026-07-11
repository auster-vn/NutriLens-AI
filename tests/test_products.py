from app.products.openfoodfacts import normalize_open_food_facts


def test_normalize_open_food_facts_keeps_only_raw_summary():
    product = normalize_open_food_facts(
        "12345678",
        {
            "status": 1,
            "product": {
                "product_name": "Demo Bar",
                "brands": "Nutri Demo",
                "categories_tags": ["en:snacks"],
                "ingredients_text": "oats, milk",
                "allergens_tags": ["en:milk"],
                "additives_tags": ["en:e330"],
                "nutriments": {"sugars_100g": 12, "proteins_100g": 8},
                "nutriscore_grade": "c",
                "last_modified_t": 123,
                "very_large_field": "x" * 1000,
            },
        },
    )

    assert product["name"] == "Demo Bar"
    assert product["allergens"] == ["milk"]
    assert "raw_payload" not in product
    assert product["raw_summary"] == {"status": 1, "last_modified_t": 123, "rev": None}
    assert product["completeness_score"] > 0
