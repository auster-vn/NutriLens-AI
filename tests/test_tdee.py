import pytest
from app.profile.tdee import calculate_tdee
from app.schemas.products import UserProfileInput
from fastapi import HTTPException


def test_tdee_uses_mifflin_st_jeor_and_activity_factor():
    result = calculate_tdee(
        UserProfileInput(
            biological_sex="male",
            age=30,
            height_cm=175,
            weight_kg=75,
            activity_level="moderate",
            target_weight_loss_kg_week=0.5,
        )
    )

    assert result.bmr_kcal == 1699
    assert result.tdee_kcal == 2633
    assert result.requested_deficit_kcal == 550
    assert result.recommended_deficit_kcal == 550
    assert result.target_calories_kcal == 2083
    assert result.recommended_loss_kg_week == 0.5


def test_tdee_caps_aggressive_deficit_and_returns_warning():
    result = calculate_tdee(
        UserProfileInput(
            biological_sex="female",
            age=40,
            height_cm=160,
            weight_kg=55,
            activity_level="sedentary",
            target_weight_loss_kg_week=1.5,
        )
    )

    assert result.recommended_deficit_kcal <= result.tdee_kcal * 0.25
    assert result.target_calories_kcal >= 1200
    assert any("giới hạn" in warning for warning in result.warnings)


def test_tdee_requires_all_body_inputs():
    with pytest.raises(HTTPException) as exc_info:
        calculate_tdee(UserProfileInput(age=30))

    assert exc_info.value.status_code == 422
    assert "biological_sex" in exc_info.value.detail
