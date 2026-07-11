from app.meal.planner import build_meal_plan


def test_meal_plan_is_diverse_and_aggregates_real_ingredients():
    plan = build_meal_plan(
        days=3,
        goal="general",
        budget=450_000,
        diet="general",
        excluded=[],
        available=[],
    )

    names = [meal["name"] for day in plan["meals"] for meal in day["meals"]]
    assert len(names) == 9
    assert len(set(names)) == 9
    assert len(plan["shopping_list"]) > 10
    assert plan["estimated_nutrition"]["daily_protein_g"] > 0
    assert all(day["meals"][0]["type"] == "breakfast" for day in plan["meals"])


def test_meal_plan_respects_vegan_diet_and_exclusions():
    plan = build_meal_plan(
        days=2,
        goal="vegan",
        budget=None,
        diet="vegan",
        excluded=["soy", "đậu hũ"],
        available=["bí đỏ"],
    )

    names = " ".join(meal["name"].lower() for day in plan["meals"] for meal in day["meals"])
    assert "gà" not in names
    assert "cá" not in names
    assert "trứng" not in names
    assert "đậu hũ" not in names


def test_meal_plan_reports_budget_and_calorie_mismatch():
    plan = build_meal_plan(
        days=3,
        goal="high_protein",
        budget=50_000,
        diet="general",
        excluded=[],
        available=[],
        target_calories=3000,
    )

    assert any("vượt ngân sách" in warning for warning in plan["warnings"])
    assert any("lệch hơn 20%" in warning for warning in plan["warnings"])


def test_everyday_food_questions_retrieve_grounded_sources():
    from app.rag.service import answer_question

    cases = {
        "Ăn trứng có tốt không?": "eggs_and_health.md",
        "Uống cà phê mỗi ngày có sao không?": "coffee_and_caffeine.md",
        "Yogurt và yến mạch có phù hợp cho bữa sáng không?": "breakfast_yogurt_oats_fruit.md",
    }
    for question, expected_source in cases.items():
        answer = answer_question(question)
        assert not answer.abstained
        assert expected_source in {citation.source for citation in answer.citations}
