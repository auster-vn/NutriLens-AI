from fastapi import HTTPException

from app.schemas.products import TdeeResult, UserProfileInput

ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "very_active": 1.725,
    "extra_active": 1.9,
}


def calculate_tdee(profile: UserProfileInput) -> TdeeResult:
    required = {
        "biological_sex": profile.biological_sex,
        "age": profile.age,
        "height_cm": profile.height_cm,
        "weight_kg": profile.weight_kg,
        "activity_level": profile.activity_level,
    }
    missing = [field for field, value in required.items() if value is None]
    if missing:
        raise HTTPException(status_code=422, detail="Thiếu dữ liệu để tính TDEE: " + ", ".join(missing))

    assert profile.age is not None
    assert profile.height_cm is not None
    assert profile.weight_kg is not None
    assert profile.activity_level is not None
    sex_offset = 5 if profile.biological_sex == "male" else -161
    bmr = 10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age + sex_offset
    factor = ACTIVITY_FACTORS[profile.activity_level]
    tdee = bmr * factor

    requested_loss = profile.target_weight_loss_kg_week or 0.0
    requested_deficit = requested_loss * 7700 / 7
    calorie_floor = 1500 if profile.biological_sex == "male" else 1200
    max_deficit = min(tdee * 0.25, max(0, tdee - calorie_floor))
    recommended_deficit = min(requested_deficit, max_deficit)
    warnings: list[str] = []
    if requested_deficit > max_deficit:
        warnings.append(
            "Tốc độ đã chọn cần mức thâm hụt quá lớn; hệ thống giới hạn ở 25% TDEE "
            "và không hạ thấp hơn calorie floor tham khảo."
        )
    if requested_loss > profile.weight_kg * 0.01:
        warnings.append("Mục tiêu vượt 1% cân nặng mỗi tuần; nên trao đổi với chuyên gia dinh dưỡng hoặc bác sĩ.")
    warnings.append(
        "TDEE là ước tính từ công thức dân số, không phải chẩn đoán. Theo dõi cân nặng 2-4 tuần và điều chỉnh dần."
    )
    return TdeeResult(
        bmr_kcal=round(bmr),
        tdee_kcal=round(tdee),
        requested_deficit_kcal=round(requested_deficit),
        recommended_deficit_kcal=round(recommended_deficit),
        target_calories_kcal=round(tdee - recommended_deficit),
        maintenance_range_kcal=(round(tdee * 0.9), round(tdee * 1.1)),
        recommended_loss_kg_week=round(recommended_deficit * 7 / 7700, 2),
        activity_factor=factor,
        warnings=warnings,
    )
