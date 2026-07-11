from pydantic import BaseModel, Field


class MealPlanRequest(BaseModel):
    days: int = Field(default=3, ge=1, le=14)
    budget: float | None = None
    goal: str = "general"
    excluded_ingredients: list[str] = Field(default_factory=list)
    available_items: list[str] = Field(default_factory=list)
    diet: str | None = None
    meals_per_day: int = Field(default=3, ge=2, le=3)
    target_calories: int | None = Field(default=None, ge=800, le=5000)


class MealPlanOut(BaseModel):
    id: str | None = None
    days: int
    budget: float | None
    goal: str
    meals: list[dict]
    shopping_list: list[dict]
    estimated_nutrition: dict
    warnings: list[str]
    diet: str = "general"
    meals_per_day: int = 3
    target_calories: int | None = None
