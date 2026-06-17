"""
Pydantic models for the Movie entity.

Design decisions:
- Three models per entity (Create, Update, Read) to make request/response
shapes explicit and let /docs show accurate schemas.
- Server-set fields (id, created_at, updated_at) only appear on MovieRead.
- MovieUpdate has all fields optional to support PATCH, the client only sends
fields they want to change.
- Status is an enum to constrain values; rating is bounded 1-10.
"""

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


class MovieStatus(StrEnum):
    TO_WATCH = "to_watch"
    WATCHED = "watched"


# Reusable annotated types - defined once, used across models
Title = Annotated[str, Field(min_length=1, max_length=200)]
Year = Annotated[int, Field(ge=1888, le=2100)]
Rating = Annotated[int, Field(ge=1, le=10)]
Notes = Annotated[str, Field(min_length=1, max_length=2000)]
# Whitespace is trimmed first, so a blank or spaces-only name fails the min_length.
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class MovieCreate(BaseModel):
    """Shape of the request body when creating a movie (POST /movies)."""

    title: Title
    year: Year | None = None
    status: MovieStatus = MovieStatus.TO_WATCH
    rating: Rating | None = None
    notes: Notes | None = None


class MovieUpdate(BaseModel):
    """Shape of the request body for partial updates (PATCH /movies/{id})."""

    title: Title | None = None
    year: Year | None = None
    status: MovieStatus | None = None
    rating: Rating | None = None
    notes: Notes | None = None

    @field_validator("title", mode="before")
    @classmethod
    def title_cannot_be_null(cls, v):
        if v is None:
            raise ValueError("title cannot be null; omit the field to leave it unchanged")
        return v


class MovieRead(BaseModel):
    """Shape of a movie returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    year: int | None
    status: MovieStatus
    rating: int | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
