from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class Meal:
    id: str
    name: str
    meal_types: tuple[str, ...]
    goals: tuple[str, ...]
    diets: tuple[str, ...]
    ingredients: dict[str, tuple[float, str]]
    aliases: tuple[str, ...]
    allergens: tuple[str, ...]
    kcal: int
    protein_g: float
    fiber_g: float
    cost_vnd: int


CATALOG = (
    Meal(
        "oats-yogurt",
        "Yến mạch, yogurt không đường và berries",
        ("breakfast",),
        ("general", "low_sugar", "weight_loss"),
        ("general", "vegetarian"),
        {"Yến mạch": (50, "g"), "Yogurt không đường": (150, "g"), "Trái cây ít đường": (100, "g")},
        ("oat", "yến mạch", "yogurt", "sữa chua", "fruit", "trái cây"),
        ("milk",),
        390,
        20,
        8,
        28000,
    ),
    Meal(
        "egg-toast",
        "Trứng, bánh mì nguyên cám và cà chua",
        ("breakfast",),
        ("general", "high_protein", "weight_loss"),
        ("general", "vegetarian"),
        {"Trứng": (2, "quả"), "Bánh mì nguyên cám": (2, "lát"), "Cà chua": (100, "g")},
        ("egg", "trứng", "bread", "bánh mì", "tomato", "cà chua"),
        ("egg", "gluten"),
        410,
        24,
        7,
        26000,
    ),
    Meal(
        "tofu-banhmi",
        "Bánh mì nguyên cám kẹp đậu hũ và rau",
        ("breakfast",),
        ("general", "vegan", "high_protein"),
        ("general", "vegetarian", "vegan"),
        {"Bánh mì nguyên cám": (2, "lát"), "Đậu hũ": (120, "g"), "Rau xà lách": (80, "g")},
        ("tofu", "đậu hũ", "bread", "bánh mì", "vegetable", "rau"),
        ("soy", "gluten"),
        380,
        22,
        8,
        24000,
    ),
    Meal(
        "sweet-potato-milk",
        "Khoai lang, sữa đậu nành và hạt",
        ("breakfast",),
        ("low_sugar", "vegan", "weight_loss"),
        ("general", "vegetarian", "vegan"),
        {"Khoai lang": (200, "g"), "Sữa đậu nành không đường": (250, "ml"), "Hạt hỗn hợp": (15, "g")},
        ("sweet potato", "khoai lang", "soy", "đậu nành", "nut", "hạt"),
        ("soy", "nuts"),
        400,
        18,
        9,
        25000,
    ),
    Meal(
        "chia-oats",
        "Yến mạch ngâm hạt chia, chuối và quế",
        ("breakfast",),
        ("general", "vegan", "weight_loss"),
        ("general", "vegetarian", "vegan"),
        {"Yến mạch": (55, "g"), "Hạt chia": (20, "g"), "Chuối": (100, "g")},
        ("oat", "yến mạch", "chia", "hạt chia", "banana", "chuối"),
        (),
        405,
        14,
        13,
        22000,
    ),
    Meal(
        "chicken-rice",
        "Ức gà, cơm gạo lứt và rau luộc",
        ("lunch", "dinner"),
        ("general", "high_protein", "weight_loss", "low_sugar"),
        ("general",),
        {"Ức gà": (160, "g"), "Gạo lứt": (80, "g"), "Rau theo mùa": (200, "g")},
        ("chicken", "gà", "rice", "gạo", "vegetable", "rau"),
        (),
        610,
        50,
        10,
        48000,
    ),
    Meal(
        "salmon-potato",
        "Cá hồi áp chảo, khoai tây và salad",
        ("lunch", "dinner"),
        ("general", "high_protein", "low_sugar"),
        ("general", "pescatarian"),
        {"Cá hồi": (150, "g"), "Khoai tây": (220, "g"), "Rau salad": (150, "g")},
        ("fish", "cá", "salmon", "cá hồi", "potato", "khoai tây", "vegetable", "rau"),
        ("fish",),
        620,
        42,
        9,
        72000,
    ),
    Meal(
        "tofu-rice",
        "Đậu hũ sốt cà chua, gạo lứt và cải xanh",
        ("lunch", "dinner"),
        ("general", "vegan", "low_sugar"),
        ("general", "vegetarian", "vegan"),
        {"Đậu hũ": (180, "g"), "Cà chua": (120, "g"), "Gạo lứt": (75, "g"), "Cải xanh": (180, "g")},
        ("tofu", "đậu hũ", "tomato", "cà chua", "rice", "gạo", "vegetable", "rau"),
        ("soy",),
        540,
        28,
        12,
        34000,
    ),
    Meal(
        "lentil-curry",
        "Cà ri đậu lăng, cơm và rau củ",
        ("lunch", "dinner"),
        ("general", "vegan", "high_protein"),
        ("general", "vegetarian", "vegan"),
        {"Đậu lăng": (100, "g"), "Gạo": (70, "g"), "Rau củ": (200, "g")},
        ("lentil", "đậu lăng", "rice", "gạo", "vegetable", "rau"),
        (),
        590,
        27,
        17,
        32000,
    ),
    Meal(
        "beef-noodle",
        "Bún bò nạc và nhiều rau",
        ("lunch",),
        ("general", "high_protein"),
        ("general",),
        {"Thịt bò nạc": (130, "g"), "Bún": (180, "g"), "Rau ăn kèm": (180, "g")},
        ("beef", "bò", "noodle", "bún", "vegetable", "rau"),
        (),
        600,
        40,
        8,
        52000,
    ),
    Meal(
        "fish-rice",
        "Cá trắng hấp, cơm và rau xào ít dầu",
        ("lunch", "dinner"),
        ("general", "weight_loss", "low_sugar"),
        ("general", "pescatarian"),
        {"Cá trắng": (170, "g"), "Gạo": (70, "g"), "Rau theo mùa": (220, "g")},
        ("fish", "cá", "rice", "gạo", "vegetable", "rau"),
        ("fish",),
        530,
        40,
        10,
        43000,
    ),
    Meal(
        "chicken-soup",
        "Súp gà, nấm và rau củ",
        ("dinner",),
        ("general", "weight_loss", "high_protein"),
        ("general",),
        {"Ức gà": (140, "g"), "Nấm": (100, "g"), "Rau củ": (250, "g"), "Khoai tây": (120, "g")},
        ("chicken", "gà", "mushroom", "nấm", "vegetable", "rau"),
        (),
        470,
        42,
        11,
        39000,
    ),
    Meal(
        "bean-soup",
        "Súp đậu trắng, bí đỏ và rau xanh",
        ("dinner",),
        ("general", "vegan", "weight_loss"),
        ("general", "vegetarian", "vegan"),
        {"Đậu trắng": (100, "g"), "Bí đỏ": (200, "g"), "Rau xanh": (180, "g")},
        ("bean", "đậu", "pumpkin", "bí đỏ", "vegetable", "rau"),
        (),
        450,
        24,
        18,
        28000,
    ),
)

MEAL_LABELS = {"breakfast": "Sáng", "lunch": "Trưa", "dinner": "Tối"}


def build_meal_plan(
    *,
    days: int,
    goal: str,
    budget: float | None,
    diet: str | None,
    excluded: list[str],
    available: list[str],
    meals_per_day: int = 3,
    target_calories: int | None = None,
) -> dict:
    slots = ("breakfast", "lunch", "dinner")[:meals_per_day]
    blocked = {term.strip().lower() for term in excluded if term.strip()}
    pantry = {term.strip().lower() for term in available if term.strip()}
    selected_ids: list[str] = []
    schedule: list[dict] = []
    shopping: defaultdict[tuple[str, str], float] = defaultdict(float)
    totals = {"calories_kcal": 0.0, "protein_g": 0.0, "fiber_g": 0.0, "estimated_cost_vnd": 0.0}

    for day in range(1, days + 1):
        day_meals: list[dict] = []
        for slot in slots:
            candidates = [meal for meal in CATALOG if slot in meal.meal_types and _allowed(meal, diet, blocked)]
            if not candidates:
                raise ValueError("Không còn món phù hợp sau khi áp dụng chế độ ăn và nguyên liệu cần tránh.")
            meal = max(candidates, key=lambda item: _score(item, goal, pantry, selected_ids, day, budget))
            selected_ids.append(meal.id)
            pantry_hits = sorted(
                alias
                for alias in pantry
                if alias in meal.aliases or any(alias in ingredient.lower() for ingredient in meal.ingredients)
            )
            day_meals.append(
                {
                    "type": slot,
                    "label": MEAL_LABELS[slot],
                    "name": meal.name,
                    "calories_kcal": meal.kcal,
                    "protein_g": meal.protein_g,
                    "fiber_g": meal.fiber_g,
                    "estimated_cost_vnd": meal.cost_vnd,
                    "pantry_matches": pantry_hits,
                    "reason": _reason(meal, goal, pantry_hits),
                }
            )
            for ingredient, (quantity, unit) in meal.ingredients.items():
                if not any(term in ingredient.lower() or term in meal.aliases for term in pantry):
                    shopping[(ingredient, unit)] += quantity
            totals["calories_kcal"] += meal.kcal
            totals["protein_g"] += meal.protein_g
            totals["fiber_g"] += meal.fiber_g
            totals["estimated_cost_vnd"] += meal.cost_vnd
        schedule.append(
            {
                "day": day,
                "meals": day_meals,
                **{slot: next(item["name"] for item in day_meals if item["type"] == slot) for slot in slots},
            }
        )

    warnings = [
        "Các giá trị dinh dưỡng và chi phí là ước tính theo khẩu phần; "
        "hãy kiểm tra nhãn và điều chỉnh theo nhu cầu thực tế."
    ]
    if budget and totals["estimated_cost_vnd"] > budget:
        warnings.append(f"Chi phí ước tính vượt ngân sách khoảng {int(totals['estimated_cost_vnd'] - budget):,} VND.")
    if target_calories:
        average = totals["calories_kcal"] / days
        if abs(average - target_calories) / target_calories > 0.2:
            warnings.append(
                f"Năng lượng trung bình {average:.0f} kcal/ngày lệch hơn 20% so với mục tiêu; "
                "điều chỉnh khẩu phần cùng chuyên gia nếu cần."
            )
    return {
        "days": days,
        "budget": budget,
        "goal": goal,
        "diet": diet or "general",
        "meals_per_day": meals_per_day,
        "target_calories": target_calories,
        "meals": schedule,
        "shopping_list": [
            {"item": item, "quantity": f"{quantity:g} {unit}"} for (item, unit), quantity in sorted(shopping.items())
        ],
        "estimated_nutrition": {
            **{key: round(value, 1) for key, value in totals.items()},
            "daily_calories_kcal": round(totals["calories_kcal"] / days),
            "daily_protein_g": round(totals["protein_g"] / days, 1),
            "daily_fiber_g": round(totals["fiber_g"] / days, 1),
        },
        "warnings": warnings,
    }


def _allowed(meal: Meal, diet: str | None, blocked: set[str]) -> bool:
    if diet and diet != "general" and diet not in meal.diets:
        return False
    searchable = " ".join((meal.name, *meal.aliases, *meal.allergens, *meal.ingredients)).lower()
    return not any(term in searchable for term in blocked)


def _score(meal: Meal, goal: str, pantry: set[str], history: list[str], day: int, budget: float | None) -> float:
    score = 12 if goal in meal.goals else 0
    score += sum(
        5
        for term in pantry
        if term in meal.aliases or any(term in ingredient.lower() for ingredient in meal.ingredients)
    )
    score -= history.count(meal.id) * 18
    if meal.id in history[-3:]:
        score -= 24
    if goal == "high_protein":
        score += meal.protein_g / 5
    if goal == "weight_loss":
        score += meal.fiber_g - meal.kcal / 100
    if budget:
        score -= max(0, meal.cost_vnd - budget / max(day, 1) / 3) / 5000
    return score


def _reason(meal: Meal, goal: str, pantry_hits: list[str]) -> str:
    reasons = []
    if goal in meal.goals:
        reasons.append("phù hợp mục tiêu")
    if meal.protein_g >= 30:
        reasons.append("giàu protein")
    if meal.fiber_g >= 10:
        reasons.append("nhiều chất xơ")
    if pantry_hits:
        reasons.append("tận dụng " + ", ".join(pantry_hits))
    return ", ".join(reasons) or "tăng độ đa dạng thực phẩm"
