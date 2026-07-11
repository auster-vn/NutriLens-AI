from app.products.scoring import score_product
from app.schemas.products import UserProfileInput


def test_vegan_goal_warns_on_milk_allergen_and_ingredient():
    score = score_product(
        {"sugars_100g": 4, "sodium_100g": 0.1, "saturated-fat_100g": 1, "proteins_100g": 8},
        ["milk"],
        [],
        "b",
        UserProfileInput(goal="vegan"),
        "skimmed milk, cocoa",
    )

    assert score.score < 70
    assert any("vegan" in warning for warning in score.warnings)


def test_gluten_free_goal_warns_on_wheat():
    score = score_product(
        {"sugars_100g": 2, "sodium_100g": 0.1, "saturated-fat_100g": 1, "proteins_100g": 6},
        ["wheat"],
        [],
        "b",
        UserProfileInput(goal="gluten_free"),
        "whole wheat flour",
    )

    assert any("gluten" in warning.lower() for warning in score.warnings)
