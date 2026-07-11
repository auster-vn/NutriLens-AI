from app.schemas.products import ProductScoreOut, UserProfileInput

DISCLAIMER = (
    "NutriLens AI provides general nutrition information and product-label assistance. "
    "It does not diagnose, treat, or replace advice from a qualified medical professional."
)


def _num(nutriments: dict, *keys: str) -> float | None:
    for key in keys:
        value = nutriments.get(key)
        if isinstance(value, int | float):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                continue
    return None


def _normalized_tokens(values: list[str]) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        cleaned = value.lower().replace("en:", "").strip()
        tokens.add(cleaned)
        tokens.update(part.strip() for part in cleaned.replace("_", "-").split("-") if part.strip())
    return tokens


def _contains_any(text: str | None, keywords: set[str]) -> list[str]:
    if not text:
        return []
    lowered = text.lower()
    return sorted(keyword for keyword in keywords if keyword in lowered)


def score_product(
    nutriments: dict,
    allergens: list[str],
    additives: list[str],
    nutriscore: str | None,
    user_profile: UserProfileInput,
    ingredients_text: str | None = None,
) -> ProductScoreOut:
    score = 70
    warnings: list[str] = []
    good_points: list[str] = []
    missing: list[str] = []

    sugar = _num(nutriments, "sugars_100g", "sugars")
    sodium = _num(nutriments, "sodium_100g", "sodium")
    salt = _num(nutriments, "salt_100g", "salt")
    saturated_fat = _num(nutriments, "saturated-fat_100g", "saturated_fat_100g")
    protein = _num(nutriments, "proteins_100g", "protein_100g")
    fiber = _num(nutriments, "fiber_100g", "fiber")
    energy_kcal = _num(nutriments, "energy-kcal_100g", "energy_kcal_100g", "energy-kcal")

    if sugar is None:
        missing.append("sugars_100g")
    elif sugar >= 22.5:
        score -= 18
        warnings.append("Đường cao trên mỗi 100g/ml.")
    elif sugar >= 10:
        score -= 8
        warnings.append("Đường hơi cao, nên cân nhắc nếu đang hạn chế đường.")
    else:
        good_points.append("Lượng đường thấp hoặc vừa phải.")

    sodium_value = sodium if sodium is not None else (salt / 2.5 if salt is not None else None)
    if sodium_value is None:
        missing.append("sodium_100g")
    elif sodium_value >= 0.6:
        score -= 14
        warnings.append("Sodium cao, không lý tưởng cho mục tiêu ít muối.")
    elif sodium_value <= 0.12:
        good_points.append("Sodium ở mức thấp.")

    if saturated_fat is None:
        missing.append("saturated-fat_100g")
    elif saturated_fat >= 5:
        score -= 12
        warnings.append("Chất béo bão hòa cao.")
    elif saturated_fat <= 1.5:
        good_points.append("Chất béo bão hòa thấp.")

    if protein is None:
        missing.append("proteins_100g")
    elif protein >= 10:
        score += 8
        good_points.append("Protein khá tốt.")
    elif user_profile.goal == "high_protein":
        score -= 8
        warnings.append("Protein chưa nổi bật so với mục tiêu tăng protein.")

    if fiber is None:
        missing.append("fiber_100g")
    elif fiber >= 6:
        score += 6
        good_points.append("Chất xơ tốt.")

    if energy_kcal is None:
        missing.append("energy-kcal_100g")
    elif energy_kcal >= 450 and user_profile.goal == "weight_loss":
        score -= 10
        warnings.append("Năng lượng cao cho mục tiêu kiểm soát cân nặng.")

    profile_allergies = _normalized_tokens(user_profile.allergies)
    product_allergens = _normalized_tokens(allergens)
    matched_allergens = sorted(profile_allergies & product_allergens)
    if matched_allergens:
        score -= 35
        warnings.append("Có chất gây dị ứng trùng với hồ sơ: " + ", ".join(matched_allergens) + ".")

    if len(additives) >= 6:
        score -= 8
        warnings.append("Sản phẩm có nhiều phụ gia; nên đọc kỹ thành phần.")
    elif additives:
        warnings.append("Có phụ gia: " + ", ".join(additives[:4]) + ".")

    if nutriscore:
        grade = nutriscore.lower()
        if grade in {"a", "b"}:
            score += 6
            good_points.append(f"Nutri-Score {grade.upper()} là tín hiệu tích cực.")
        elif grade in {"d", "e"}:
            score -= 8
            warnings.append(f"Nutri-Score {grade.upper()} cho thấy cần cân nhắc.")

    if user_profile.goal == "low_sugar" and sugar is not None and sugar >= 10:
        score -= 8
        warnings.append("Không phù hợp nếu cần hạn chế đường nghiêm ngặt.")
    if user_profile.goal == "low_sodium" and sodium_value is not None and sodium_value >= 0.12:
        score -= 6
        warnings.append("Chưa tối ưu cho mục tiêu ít sodium.")

    diet_goal = (user_profile.diet or user_profile.goal or "").lower().replace("-", "_")
    combined_allergens = product_allergens | _normalized_tokens(additives)
    animal_keywords = {
        "beef",
        "pork",
        "chicken",
        "fish",
        "meat",
        "gelatin",
        "bacon",
        "ham",
        "cá",
        "thịt",
        "gà",
        "bò",
        "heo",
    }
    dairy_keywords = {"milk", "lactose", "whey", "casein", "cheese", "butter", "sữa", "phô mai", "bơ"}
    egg_keywords = {"egg", "albumin", "trứng"}
    gluten_keywords = {"gluten", "wheat", "barley", "rye", "malt", "lúa mì", "đại mạch"}
    if diet_goal == "vegetarian":
        matches = _contains_any(ingredients_text, animal_keywords)
        if matches:
            score -= 18
            warnings.append(
                "Có dấu hiệu nguyên liệu từ thịt/cá, không phù hợp vegetarian: "
                + ", ".join(matches[:4])
                + "."
            )
    if diet_goal == "vegan":
        vegan_keywords = animal_keywords | dairy_keywords | egg_keywords | {"honey", "mật ong"}
        matches = _contains_any(ingredients_text, vegan_keywords)
        allergen_matches = sorted(combined_allergens & {"milk", "egg", "eggs"})
        if matches or allergen_matches:
            score -= 22
            warnings.append(
                "Có dấu hiệu không phù hợp vegan: " + ", ".join(sorted(set(matches + allergen_matches))[:5]) + "."
            )
    if diet_goal == "gluten_free":
        matches = _contains_any(ingredients_text, gluten_keywords)
        allergen_matches = sorted(product_allergens & {"gluten", "wheat", "barley"})
        if matches or allergen_matches:
            score -= 24
            warnings.append(
                "Có dấu hiệu chứa gluten/lúa mì: " + ", ".join(sorted(set(matches + allergen_matches))[:5]) + "."
            )
    if diet_goal == "lactose_free":
        matches = _contains_any(ingredients_text, dairy_keywords)
        allergen_matches = sorted(product_allergens & {"milk", "lactose"})
        if matches or allergen_matches:
            score -= 24
            warnings.append(
                "Có dấu hiệu chứa sữa/lactose: " + ", ".join(sorted(set(matches + allergen_matches))[:5]) + "."
            )

    score = max(0, min(100, round(score)))
    risk_level = "low" if score >= 75 else "medium" if score >= 45 else "high"
    label = "Tốt" if score >= 80 else "Khá ổn" if score >= 65 else "Cần cân nhắc" if score >= 45 else "Rủi ro cao"

    return ProductScoreOut(
        score=score,
        label=label,
        risk_level=risk_level,
        warnings=warnings or ["Không phát hiện cảnh báo lớn từ dữ liệu hiện có."],
        good_points=good_points,
        missing_data=sorted(set(missing)),
        disclaimer=DISCLAIMER,
    )
