from app.products.scoring import score_product
from app.schemas.products import UserProfileInput


def test_score_warns_for_high_sugar_and_goal():
    score = score_product(
        {"sugars_100g": 24, "sodium_100g": 0.1, "saturated-fat_100g": 1, "proteins_100g": 4},
        [],
        [],
        "c",
        UserProfileInput(goal="low_sugar"),
    )

    assert score.score < 70
    assert any("Đường" in warning for warning in score.warnings)
    assert score.risk_level in {"medium", "high"}


def test_score_flags_profile_allergen():
    score = score_product(
        {"sugars_100g": 3, "sodium_100g": 0.1, "saturated-fat_100g": 1, "proteins_100g": 12},
        ["milk"],
        [],
        "b",
        UserProfileInput(allergies=["milk"]),
    )

    assert score.risk_level != "low"
    assert any("dị ứng" in warning for warning in score.warnings)
