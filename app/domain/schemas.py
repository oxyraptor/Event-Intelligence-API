from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EventCreate(BaseModel):
    user_id: str = Field(alias="userId")
    event: str
    timestamp: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)


class EventRead(BaseModel):
    id: str
    user_id: str = Field(alias="userId")
    event: str
    timestamp: datetime | None = None
    created_at: datetime = Field(alias="createdAt")
    metadata: dict[str, Any]
    raw_text: str = Field(alias="rawText")
    embedding_model: str | None = Field(default=None, alias="embeddingModel")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TrackResponse(BaseModel):
    event: EventRead
    vector_indexed: bool = Field(alias="vectorIndexed")

    model_config = ConfigDict(populate_by_name=True)


class AnalyticsBreakdownRow(BaseModel):
    key: str
    count: int


class AnalyticsResponse(BaseModel):
    total_count: int = Field(alias="totalCount")
    distinct_users: int = Field(alias="distinctUsers")
    event_breakdown: list[AnalyticsBreakdownRow] = Field(alias="eventBreakdown")
    top_users: list[AnalyticsBreakdownRow] = Field(alias="topUsers")

    model_config = ConfigDict(populate_by_name=True)


class SearchResult(BaseModel):
    event: EventRead
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


class SimilarUserRow(BaseModel):
    user_id: str = Field(alias="userId")
    score: float

    model_config = ConfigDict(populate_by_name=True)


class SimilarUsersResponse(BaseModel):
    user_id: str = Field(alias="userId")
    results: list[SimilarUserRow]

    model_config = ConfigDict(populate_by_name=True)
