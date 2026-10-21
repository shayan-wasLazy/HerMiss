"""Source-grounded MCQ generation and adaptive practice with a small Q-learning policy.

Questions are generated from readable plain-text notes using transparent heuristics.
This is not an LLM and does not infer facts that are absent from the uploaded text.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any


class QuizGenerationError(ValueError):
    """Raised when the notes do not contain enough usable material."""


def _sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return []
    # Split at sentence boundaries and at semicolons; retain useful short definitions.
    parts = re.split(r"(?<=[.!?])\s+|\s*;\s*", cleaned)
    return [p.strip(" \t\n•-") for p in parts if len(p.split()) >= 5]


def _candidate_terms(sentence: str) -> list[str]:
    # Prefer capitalized technical terms, acronyms, and multiword terms; fall back to content words.
    candidates = re.findall(
        r"\b(?:[A-Z][A-Za-z0-9+.#-]*(?:\s+[A-Z][A-Za-z0-9+.#-]*){0,2}|[A-Z]{2,}[A-Z0-9-]*|[A-Za-z][A-Za-z0-9+.#-]{4,})\b",
        sentence,
    )
    stop = {
        "This", "That", "These", "Those", "There", "Their", "Which", "When",
        "Where", "While", "Because", "Using", "Used", "From", "Into", "With",
        "Without", "Between", "After", "Before", "Then", "They", "Have",
        "Has", "Will", "Can", "Each", "Also", "Such", "Other",
    }
    seen = set()
    out = []
    for term in candidates:
        term = term.strip(".,:;()[]{}")
        if len(term) < 3 or term in stop or term.casefold() in seen:
            continue
        seen.add(term.casefold())
        out.append(term)
    return out


def generate_mcqs(text: str, count: int = 10, source_name: str = "uploaded notes") -> list[dict[str, Any]]:
    """Create fill-the-key-term MCQs from statements in the supplied notes."""
    if not text or not text.strip():
        raise QuizGenerationError("The uploaded notes are empty.")
    sentences = _sentences(text)
    term_pool = []
    for sentence in sentences:
        term_pool.extend(_candidate_terms(sentence))
    # Preserve order while removing duplicate terms.
    term_pool = list(dict.fromkeys(term_pool))
    if len(term_pool) < 4:
        raise QuizGenerationError(
            "Not enough readable terms to build four-option MCQs. Upload notes with fuller sentences or definitions."
        )

    questions = []
    seen_stems = set()
    for sentence in sentences:
        terms = [t for t in _candidate_terms(sentence) if t.casefold() in {x.casefold() for x in term_pool}]
        # A term must be useful and leave a readable statement when blanked.
        terms.sort(key=lambda t: (len(t.split()), len(t)), reverse=True)
        for answer in terms:
            blanked = re.sub(re.escape(answer), "________", sentence, count=1, flags=re.I)
            if blanked == sentence or len(blanked.split()) < 5:
                continue
            stem = f"According to the uploaded notes, which term completes this statement?\n\n“{blanked}”"
            if stem.casefold() in seen_stems:
                continue
            distractors = [t for t in term_pool if t.casefold() != answer.casefold() and t.casefold() not in sentence.casefold()]
            # If all terms appear in the sentence, use distinct terms from elsewhere in the notes.
            if len(distractors) < 3:
                distractors = [t for t in term_pool if t.casefold() != answer.casefold()]
            distractors = list(dict.fromkeys(distractors))
            if len(distractors) < 3:
                continue
            # Deterministic order based on a stable sentence/answer seed.
            rng = random.Random(f"{source_name}:{sentence}:{answer}")
            options = rng.sample(distractors, 3) + [answer]
            rng.shuffle(options)
            questions.append({
                "id": hashlib.sha1(f"{source_name}:{sentence}:{answer}".encode("utf-8")).hexdigest()[:12],
                "question": stem,
                "source_sentence": sentence,
                "answer": answer,
                "options": options,
                "source_name": Path(source_name).name,
            })
            seen_stems.add(stem.casefold())
            if len(questions) >= max(1, min(int(count), 50)):
                return questions
    if not questions:
        raise QuizGenerationError(
            "Could not form reliable MCQs from these notes. Use prose definitions or explanatory sentences rather than headings alone."
        )
    return questions


class AdaptiveQuizPolicy:
    """Small tabular Q-learning policy choosing a practice priority from learner state."""

    ACTIONS = ("target_weak", "review_slow", "mixed_practice")

    def __init__(self, path: str | Path | None = None, seed: int = 42):
        self.path = Path(path) if path else None
        self.random = random.Random(seed)
        self.alpha = 0.25
        self.gamma = 0.8
        self.epsilon = 0.15
        self.q: dict[str, dict[str, float]] = {}
        self.stats: dict[str, dict[str, Any]] = {}
        if self.path and self.path.exists():
            try:
                saved = json.loads(self.path.read_text(encoding="utf-8"))
                self.q = saved.get("q", {})
                self.stats = saved.get("stats", {})
            except (OSError, json.JSONDecodeError):
                self.q, self.stats = {}, {}

    def _save(self) -> None:
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps({"q": self.q, "stats": self.stats}, indent=2), encoding="utf-8")

    def _state(self) -> str:
        stats = list(self.stats.values())
        if not stats:
            return "new"
        weak = sum(s.get("wrong", 0) >= 2 for s in stats)
        slow = sum(s.get("slow", 0) >= 1 for s in stats)
        if weak:
            return "weak"
        if slow:
            return "slow"
        return "developing"

    def choose_strategy(self) -> str:
        state = self._state()
        values = self.q.get(state, {})
        if self.random.random() < self.epsilon or not values:
            if state == "weak":
                return "target_weak"
            if state == "slow":
                return "review_slow"
            return self.random.choice(list(self.ACTIONS))
        return max(self.ACTIONS, key=lambda action: values.get(action, 0.0))

    def record_answer(self, question_id: str, correct: bool, elapsed_seconds: float) -> dict[str, Any]:
        stats = self.stats.setdefault(question_id, {"attempts": 0, "wrong": 0, "slow": 0, "correct": 0, "last_seconds": 0.0})
        previous_state = self._state()
        stats["attempts"] += 1
        stats["last_seconds"] = round(max(0.0, elapsed_seconds), 2)
        if correct:
            stats["correct"] += 1
        else:
            stats["wrong"] += 1
        # A response above 20 seconds is treated as slow; user can still be correct.
        if elapsed_seconds > 20:
            stats["slow"] += 1
        reward = (1.0 if correct else -1.0) - (0.35 if elapsed_seconds > 20 else 0.0)
        if stats["wrong"] >= 2 and not correct:
            reward -= 0.5
        action = "target_weak" if stats["wrong"] >= 2 else ("review_slow" if elapsed_seconds > 20 else "mixed_practice")
        next_state = self._state()
        row = self.q.setdefault(previous_state, {})
        old = row.get(action, 0.0)
        future = max(self.q.get(next_state, {}).get(a, 0.0) for a in self.ACTIONS)
        row[action] = old + self.alpha * (reward + self.gamma * future - old)
        self._save()
        return {
            "reward": round(reward, 2),
            "strategy": self.choose_strategy(),
            "attempts": stats["attempts"],
            "wrong": stats["wrong"],
            "slow": stats["slow"],
            "correct": stats["correct"],
            "mastered": stats["correct"] >= 2 and stats["wrong"] == 0 and stats["last_seconds"] <= 20,
        }

    def prioritize(self, questions: list[dict[str, Any]], strategy: str) -> list[dict[str, Any]]:
        def score(question: dict[str, Any]) -> tuple[float, float]:
            s = self.stats.get(question["id"], {})
            wrong = s.get("wrong", 0)
            slow = s.get("slow", 0)
            attempts = s.get("attempts", 0)
            if strategy == "target_weak":
                priority = wrong * 3 + slow
            elif strategy == "review_slow":
                priority = slow * 3 + wrong
            else:
                priority = wrong + slow + (0.5 if attempts == 0 else 0)
            return (priority, self.random.random())
        return sorted(questions, key=score, reverse=True)

    def summary(self) -> dict[str, Any]:
        stats = list(self.stats.values())
        attempts = sum(s.get("attempts", 0) for s in stats)
        correct = sum(s.get("correct", 0) for s in stats)
        return {
            "questions_tracked": len(stats),
            "attempts": attempts,
            "accuracy": correct / attempts if attempts else 0.0,
            "repeatedly_missed": sum(s.get("wrong", 0) >= 2 for s in stats),
            "slow_questions": sum(s.get("slow", 0) >= 1 for s in stats),
            "policy_q_values": sum(len(v) for v in self.q.values()),
        }
