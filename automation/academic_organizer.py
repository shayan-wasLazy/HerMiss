"""Heuristic academic notes organizer for extracted folders and ZIP uploads.

Classification uses paths, filenames, and readable text snippets. It never deletes
source files; ambiguous files are placed in Needs_Review. This is a heuristic,
not a semantic guarantee, so preview the plan before applying it.
"""
from pathlib import Path
import re
import shutil
import zipfile


SUBJECT_RULES = {
    "DBMS": ("dbms", "database management", "sql", "normalization", "er diagram", "transaction"),
    "Data_Structures": ("data structures", "dsa", "linked list", "binary tree", "graph traversal", "stack", "queue"),
    "Machine_Learning": ("machine learning", " ml ", "regression", "classification", "clustering", "supervised learning"),
    "Deep_Learning": ("deep learning", "neural network", "cnn", "rnn", "transformer", "backpropagation"),
    "Computer_Networks": ("computer networks", "tcp", "udp", "osi model", "network layer", "routing"),
    "Operating_Systems": ("operating systems", "operating system", "deadlock", "process scheduling", "virtual memory"),
    "Mathematics": ("linear algebra", "probability", "statistics", "calculus", "differential equation"),
    "Data_Science": ("data science", "data visualization", "pandas", "data analytics", "exploratory data analysis"),
    "Software_Engineering": ("software engineering", "sdlc", "agile", "uml", "software testing"),
}
TYPE_RULES = {
    "Labs": ("lab", "practical", "experiment", "observation", "viva", "lab manual", "lab assignment"),
    "Assignments": ("assignment", "homework", "worksheet", "problem set", "submission"),
    "Question_Papers": ("question paper", "question bank", "previous year", "pyq", "midsem paper", "endsem paper", "sample paper"),
    "Presentations": ("presentation", "slides", "ppt", "seminar"),
    "Projects": ("project", "mini project", "capstone"),
    "Theory": ("theory", "lecture", "unit", "chapter", "module", "notes", "syllabus"),
}
TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".py", ".html", ".xml", ".sql", ".yaml", ".yml"}


def _readable_text(path: Path) -> str:
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:12000].lower()
    except OSError:
        return ""


def classify_file(path: Path, relative_path: str) -> dict:
    """Return deterministic subject/type guesses with simple confidence values."""
    filename = path.name.lower().replace("_", " ").replace("-", " ")
    context = f" {relative_path.lower().replace('_', ' ').replace('-', ' ')} {filename} {_readable_text(path)} "
    subject_scores = {
        subject: sum(1 for keyword in keywords if keyword in context)
        for subject, keywords in SUBJECT_RULES.items()
    }
    best_subject = max(subject_scores, key=subject_scores.get)
    subject_score = subject_scores[best_subject]
    if subject_score == 0:
        subject, subject_confidence = "Unclassified_Subject", 0.0
    else:
        subject, subject_confidence = best_subject, min(0.95, 0.5 + subject_score * 0.12)

    type_scores = {
        category: sum(1 for keyword in keywords if keyword in f" {filename} {relative_path.lower().replace('_', ' ')} ")
        for category, keywords in TYPE_RULES.items()
    }
    best_type = max(type_scores, key=type_scores.get)
    type_score = type_scores[best_type]
    if type_score == 0:
        # Common file extensions can suggest a format, but not whether it is theory or lab.
        category, type_confidence = "Other", 0.0
    else:
        category, type_confidence = best_type, min(0.95, 0.55 + type_score * 0.12)

    if subject_confidence < 0.5 or type_confidence < 0.55:
        review = True
    else:
        review = False
    return {
        "source": relative_path,
        "subject": subject,
        "category": category,
        "confidence": round(min(subject_confidence, type_confidence), 2),
        "needs_review": review,
    }


def build_organization_plan(source_root: Path) -> list[dict]:
    root = Path(source_root).resolve()
    plan = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        # Ignore common OS metadata and avoid re-organizing prior outputs.
        if any(part in {"__MACOSX", ".DS_Store"} for part in Path(relative).parts):
            continue
        plan.append(classify_file(path, relative))
    return plan


def apply_organization(source_root: Path, destination_root: Path, plan: list[dict]) -> dict:
    """Copy, never move, files into the academic structure; avoid overwrites."""
    source_root = Path(source_root).resolve()
    destination_root = Path(destination_root).resolve()
    if destination_root == source_root or source_root in destination_root.parents:
        raise ValueError("Destination must not be the source folder or inside it.")
    copied, skipped = [], []
    for item in plan:
        source = (source_root / item["source"]).resolve()
        if source_root not in source.parents or not source.is_file():
            skipped.append({"source": item["source"], "reason": "Source path is invalid or missing"})
            continue
        if item["needs_review"]:
            relative_dest = Path("Needs_Review") / item["subject"] / item["category"] / source.name
        else:
            relative_dest = Path(item["subject"]) / item["category"] / source.name
        target = destination_root / relative_dest
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            stem, suffix = target.stem, target.suffix
            index = 2
            while target.exists():
                target = target.with_name(f"{stem}_{index}{suffix}")
                index += 1
        shutil.copy2(source, target)
        copied.append({"source": item["source"], "destination": target.relative_to(destination_root).as_posix()})
    return {"copied_count": len(copied), "skipped_count": len(skipped), "copied": copied, "skipped": skipped}


def extract_zip_safely(zip_path: Path, destination: Path) -> Path:
    """Extract an archive while rejecting path traversal and symlink entries."""
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            member = Path(info.filename)
            if member.is_absolute() or ".." in member.parts:
                raise ValueError(f"Unsafe path in ZIP: {info.filename}")
            unix_mode = info.external_attr >> 16
            if unix_mode and (unix_mode & 0o170000) == 0o120000:
                raise ValueError(f"Symbolic links are not allowed in ZIP uploads: {info.filename}")
            target = (destination / member).resolve()
            if target != destination and destination not in target.parents:
                raise ValueError(f"Unsafe path in ZIP: {info.filename}")
        archive.extractall(destination)
    return destination
