from __future__ import annotations

from datetime import datetime

from app.domain.schemas import AnalyticsBreakdownRow, AnalyticsResponse
from app.repositories.event_repository import EventRepository


class AnalyticsService:
    def __init__(self, repository: EventRepository) -> None:
        self.repository = repository

    def summarize(
        self,
        *,
        event_name: str | None,
        user_id: str | None,
        from_timestamp: datetime | None,
        to_timestamp: datetime | None,
        top_limit: int,
    ) -> AnalyticsResponse:
        total_count = self.repository.count_total(
            event_name=event_name,
            user_id=user_id,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )
        distinct_users = self.repository.count_distinct_users(
            event_name=event_name,
            user_id=user_id,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )
        event_rows = self.repository.grouped_counts(
            "event",
            event_name=event_name,
            user_id=user_id,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )
        user_rows = self.repository.grouped_counts(
            "user_id",
            event_name=event_name,
            user_id=user_id,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            limit=top_limit,
        )
        return AnalyticsResponse(
            totalCount=total_count,
            distinctUsers=distinct_users,
            eventBreakdown=[AnalyticsBreakdownRow(key=key, count=count) for key, count in event_rows],
            topUsers=[AnalyticsBreakdownRow(key=key, count=count) for key, count in user_rows],
        )
