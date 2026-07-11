from pydantic import BaseModel, Field


class UserProfileInput(BaseModel):
    age_group: str | None = None
    goal: str = "general"
    allergies: list[str] = Field(default_factory=list)
    diet: str | None = None
    disliked_ingredients: list[str] = Field(default_factory=list)
    budget_daily: float | None = None
    biological_sex: str | None = Field(default=None, pattern="^(male|female)$")
    age: int | None = Field(default=None, ge=18, le=100)
    height_cm: float | None = Field(default=None, ge=120, le=230)
    weight_kg: float | None = Field(default=None, ge=30, le=350)
    activity_level: str | None = Field(
        default=None,
        pattern="^(sedentary|light|moderate|very_active|extra_active)$",
    )
    target_weight_loss_kg_week: float | None = Field(default=None, ge=0, le=1.5)


class TdeeResult(BaseModel):
    bmr_kcal: int
    tdee_kcal: int
    requested_deficit_kcal: int
    recommended_deficit_kcal: int
    target_calories_kcal: int
    maintenance_range_kcal: tuple[int, int]
    recommended_loss_kg_week: float
    activity_factor: float
    warnings: list[str] = Field(default_factory=list)


class ProductOut(BaseModel):
    barcode: str
    name: str | None = None
    brand: str | None = None
    categories: list[str] = Field(default_factory=list)
    ingredients_text: str | None = None
    allergens: list[str] = Field(default_factory=list)
    additives: list[str] = Field(default_factory=list)
    nutriments: dict = Field(default_factory=dict)
    nutriscore: str | None = None
    ecoscore: str | None = None
    image_url: str | None = None
    source: str = "open_food_facts"
    completeness_score: float | None = None


class ProductScanRequest(BaseModel):
    barcode: str
    user_profile: UserProfileInput | None = None


class ProductScoreRequest(BaseModel):
    nutriments: dict = Field(default_factory=dict)
    allergens: list[str] = Field(default_factory=list)
    additives: list[str] = Field(default_factory=list)
    nutriscore: str | None = None
    ingredients_text: str | None = None
    user_profile: UserProfileInput = Field(default_factory=UserProfileInput)


class ProductScoreOut(BaseModel):
    score: int
    label: str
    risk_level: str
    warnings: list[str]
    good_points: list[str]
    missing_data: list[str]
    disclaimer: str


class ProductWithScore(BaseModel):
    product: ProductOut
    score: ProductScoreOut


class ProductCompareRequest(BaseModel):
    barcode_a: str
    barcode_b: str
    user_profile: UserProfileInput = Field(default_factory=UserProfileInput)


class ProductCompareOut(BaseModel):
    product_a: ProductWithScore
    product_b: ProductWithScore
    recommendation: str
    dimensions: list[dict]
