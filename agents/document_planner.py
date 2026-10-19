"""Build a practical study/work plan from a plain-text portion or task brief."""
from __future__ import annotations

import re
from pathlib import Path


class DocumentPlanningError(ValueError):
    """Raised when a text document does not contain usable plan items."""


def extract_topics(text: str) -> list[str]:
    """Extract readable topics from headings, bullets, numbered lists, or plain lines."""
    if not text or not text.strip():
        raise DocumentPlanningError("The text file is empty.")

    topics: list[str] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        # Remove Markdown heading markers, list prefixes, and section labels.
        line = re.sub(r"^#+\s*", "", line)
        line = re.sub(r"^(?:[-*•▪‣]+|\d+[.)]|(?:topic|unit|chapter)\s*\d*\s*[:.-])\s*", "", line, flags=re.I)
        line = line.strip(" \t:-")
        if not line:
            continue
        # Treat comma/semicolon separated syllabus entries as individual topics.
        parts = re.split(r"\s*[;,]\s*", line)
        for part in parts:
            topic = re.sub(r"\s+", " ", part).strip(" .:-")
            if len(topic) < 2:
                continue
            key = topic.casefold()
            if key not in seen:
                seen.add(key)
                topics.append(topic)
    if not topics:
        raise DocumentPlanningError("No topics or tasks could be extracted from this file.")
    return topics


def build_document_plan(text: str, filename: str = "portion.txt") -> dict:
    """Create a transparent, heuristic plan; it does not claim to understand hidden context."""
    topics = extract_topics(text)
    items = []
    for index, topic in enumerate(topics, start=1):
        words = len(topic.split())
        minutes = min(90, max(25, 15 + words * 5))
        items.append({
            "step": index,
            "topic": topic,
            "estimated_minutes": minutes,
            "task": f"Study {topic}; write a short summary and solve one practice question.",
            "priority": "High" if index <= max(1, len(topics) // 3) else "Normal",
        })

    total_minutes = sum(item["estimated_minutes"] for item in items)
    sessions = []
    # Pack topics into sessions of approximately 90 minutes, preserving source order.
    current, current_minutes = [], 0
    for item in items:
        if current and current_minutes + item["estimated_minutes"] > 90:
            sessions.append({"session": len(sessions) + 1, "topics": current, "estimated_minutes": current_minutes})
            current, current_minutes = [], 0
        current.append(item["topic"])
        current_minutes += item["estimated_minutes"]
    if current:
        sessions.append({"session": len(sessions) + 1, "topics": current, "estimated_minutes": current_minutes})

    return {
        "source_file": Path(filename).name,
        "topic_count": len(items),
        "estimated_total_minutes": total_minutes,
        "estimated_total_hours": round(total_minutes / 60, 1),
        "items": items,
        "sessions": sessions,
        "review": "Finish with a 15-minute active-recall review and revisit topics you could not explain without notes.",
        "note": "This is a heuristic plan based on the text and topic lengths, not an AI-verified interpretation of the syllabus.",
    }
