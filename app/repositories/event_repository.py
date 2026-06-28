from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.domain.models import Event


class EventRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        user_id: str,
        event_name: str,
        timestamp: datetime | None,
        metadata: dict[str, object],
        raw_text: str,
        embedding_model: str | None,
    ) -> Event:
        event = Event(
            user_id=user_id,
            event=event_name,
            timestamp=timestamp,
            metadata_json=metadata,
            raw_text=raw_text,
            embedding_model=embedding_model,
        )
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event

    def get_by_ids(self, event_ids: Sequence[str]) -> list[Event]:
        if not event_ids:
            return []
        rows = self.session.execute(select(Event).where(Event.id.in_(list(event_ids))))
        events = list(rows.scalars().all())
        event_map = {event.id: event for event in events}
        return [event_map[event_id] for event_id in event_ids if event_id in event_map]

    def distinct_user_ids(self) -> list[str]:
        rows = self.session.execute(select(Event.user_id).distinct().order_by(Event.user_id.asc()))
        return [row[0] for row in rows.all()]

    def events_for_user(self, user_id: str) -> list[Event]:
        rows = self.session.execute(select(Event).where(Event.user_id == user_id))
        return list(rows.scalars().all())

    def analytics_statement(
        self,
        *,
        event_name: str | None = None,
        user_id: str | None = None,
        from_timestamp: datetime | None = None,
        to_timestamp: datetime | None = None,
    ) -> Select[tuple[Event]]:
        stmt: Select[tuple[Event]] = select(Event)
        if event_name is not None:
            stmt = stmt.where(Event.event == event_name)
        if user_id is not None:
            stmt = stmt.where(Event.user_id == user_id)
        if from_timestamp is not None:
            stmt = stmt.where(Event.timestamp >= from_timestamp)
        if to_timestamp is not None:
            stmt = stmt.where(Event.timestamp <= to_timestamp)
        return stmt

    def analytics_subquery(
        self,
        *,
        event_name: str | None = None,
        user_id: str | None = None,
        from_timestamp: datetime | None = None,
        to_timestamp: datetime | None = None,
    ):
        return self.analytics_statement(
            event_name=event_name,
            user_id=user_id,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        ).subquery()

    def count_total(
        self,
        *,
        event_name: str | None = None,
        user_id: str | None = None,
        from_timestamp: datetime | None = None,
        to_timestamp: datetime | None = None,
    ) -> int:
        stmt = self.analytics_subquery(
            event_name=event_name,
            user_id=user_id,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )
        count_stmt = select(func.count()).select_from(stmt)
        return int(self.session.execute(count_stmt).scalar_one())

    def count_distinct_users(
        self,
        *,
        event_name: str | None = None,
        user_id: str | None = None,
        from_timestamp: datetime | None = None,
        to_timestamp: datetime | None = None,
    ) -> int:
        stmt = self.analytics_subquery(
            event_name=event_name,
            user_id=user_id,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )
        count_stmt = select(func.count(func.distinct(stmt.c.user_id))).select_from(stmt)
        return int(self.session.execute(count_stmt).scalar_one())

    def grouped_counts(
        self,
        group_column_name: str,
        *,
        event_name: str | None = None,
        user_id: str | None = None,
        from_timestamp: datetime | None = None,
        to_timestamp: datetime | None = None,
        limit: int | None = None,
    ) -> list[tuple[str, int]]:
        stmt = self.analytics_subquery(
            event_name=event_name,
            user_id=user_id,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )
        group_column = stmt.c[group_column_name]
        grouped = select(group_column.label("key"), func.count().label("count")).select_from(stmt).group_by(group_column).order_by(func.count().desc(), group_column.asc())
        if limit is not None:
            grouped = grouped.limit(limit)
        rows = self.session.execute(grouped).all()
        return [(row.key, int(row.count)) for row in rows]
