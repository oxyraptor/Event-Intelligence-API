from __future__ import annotations

from collections.abc import Mapping


def build_event_text(event_name: str, metadata: Mapping[str, object]) -> str:
    parts = [event_name.strip()]
    if metadata:
        formatted = []
        for key in sorted(metadata):
            value = metadata[key]
            formatted.append(f"{key}: {value}")
        parts.append(" | ".join(formatted))
    return " -- ".join(parts)
