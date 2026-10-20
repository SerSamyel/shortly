from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from shortly.codes import alias_error


class Credentials(BaseModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def lower_email(cls, value: str) -> str:
        return value.lower()


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserOut


class LinkCreate(BaseModel):
    target_url: str = Field(min_length=1)
    alias: str | None = None
    expires_at: datetime | None = None

    @field_validator("target_url")
    @classmethod
    def strip_url(cls, value: str) -> str:
        return value.strip()

    @field_validator("alias")
    @classmethod
    def check_alias(cls, value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None
        value = value.strip().lower()
        error = alias_error(value)
        if error:
            raise ValueError(error)
        return value


class LinkUpdate(BaseModel):
    is_active: bool


LinkStatus = Literal["active", "disabled", "expired"]


class LinkOut(BaseModel):
    id: int
    code: str
    short_url: str
    target_url: str
    status: LinkStatus
    is_active: bool
    expires_at: datetime | None
    created_at: datetime
    total_clicks: int


class LinkPage(BaseModel):
    items: list[LinkOut]
    total: int
    page: int
    page_size: int


class DailyClicks(BaseModel):
    date: date
    clicks: int
    unique_visitors: int


class NamedCount(BaseModel):
    name: str
    clicks: int


class LinkStats(BaseModel):
    link_id: int
    total_clicks: int
    daily: list[DailyClicks]
    referrers: list[NamedCount]
    countries: list[NamedCount]


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
