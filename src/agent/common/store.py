from pydantic import BaseModel, Field


class ReservedInfo(BaseModel):
    order_id: str
    title: str
    phone_number: str
    status: str = "confirmed"
    viewing_time: str | None = None
    created_at: str | None = None
    price: float | None = None
    intro: str | None = None
    city_name: str | None = None
    region: str | None = None


class UserPreferences(BaseModel):
    budget_min: float | None = Field(default=None)
    budget_max: float | None = Field(default=None)
    reserved_info: list[ReservedInfo] | None = Field(default=None)
