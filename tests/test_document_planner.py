import pytest

from agents.document_planner import (
    DocumentPlanningError,
    build_document_plan,
    extract_topics,
)


def test_extracts_bullets_numbered_items_and_deduplicates():
    topics = extract_topics("- Regression\n2. Classification\n• Regression")
    assert topics == ["Regression", "Classification"]


def test_splits_comma_separated_portion():
    topics = extract_topics("Unit 1: Linear Algebra, Probability; Statistics")
    assert topics == ["Linear Algebra", "Probability", "Statistics"]


def test_builds_sessions_and_estimates():
    plan = build_document_plan("- DBMS\n- Operating Systems", "portion.txt")
    assert plan["source_file"] == "portion.txt"
    assert plan["topic_count"] == 2
    assert len(plan["items"]) == 2
    assert plan["estimated_total_minutes"] > 0
    assert plan["sessions"][0]["topics"] == ["DBMS", "Operating Systems"]


def test_empty_document_rejected():
    with pytest.raises(DocumentPlanningError):
        build_document_plan("  ")
