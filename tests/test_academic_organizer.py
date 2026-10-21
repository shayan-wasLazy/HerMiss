from pathlib import Path
import zipfile

import pytest

from automation.academic_organizer import (
    apply_organization, build_organization_plan, extract_zip_safely,
)


def test_plan_classifies_subject_and_lab_type(tmp_path):
    p = tmp_path / "DBMS_lab_experiment_1.txt"
    p.write_text("DBMS SQL transaction practical lab experiment", encoding="utf-8")
    plan = build_organization_plan(tmp_path)
    assert plan[0]["subject"] == "DBMS"
    assert plan[0]["category"] == "Labs"


def test_unknown_file_is_flagged_and_copied_for_review(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "random.bin").write_bytes(b"abc")
    plan = build_organization_plan(source)
    assert plan[0]["needs_review"]
    result = apply_organization(source, tmp_path / "organized", plan)
    assert result["copied_count"] == 1
    assert (tmp_path / "organized" / "Needs_Review" / "Unclassified_Subject" / "Other" / "random.bin").exists()
    assert (source / "random.bin").exists()


def test_collisions_do_not_overwrite(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "DBMS_theory_notes.txt").write_text("DBMS theory unit 1", encoding="utf-8")
    plan = build_organization_plan(source)
    destination = tmp_path / "organized"
    result1 = apply_organization(source, destination, plan)
    result2 = apply_organization(source, destination, plan)
    assert result1["copied_count"] == result2["copied_count"] == 1
    assert len(list(destination.rglob("DBMS_theory_notes*"))) == 2


def test_zip_traversal_is_rejected(tmp_path):
    archive_path = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../escape.txt", "bad")
    with pytest.raises(ValueError, match="Unsafe path"):
        extract_zip_safely(archive_path, tmp_path / "out")
