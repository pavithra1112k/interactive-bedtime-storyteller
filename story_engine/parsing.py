"""
Parsing and formatting utilities for LLM responses and story text.

Module constants:
  SEGMENT_DIMENSION_KEYS  — Parameters that I definedfor per-segment judge JSON (5 dimensions).
  FULL_STORY_DIMENSION_KEYS — Parameters that I defined for full-story judge JSON (5 dimensions).
  DIMENSION_LABELS        — Just writing the parameters in a readable format for the user.

Functions:
  _strip_json_fences(text)           — Removes optional ```json code fences before parsing.
  parse_judge_json(response, keys)   — Parses judge JSON; validates scores (1–10) and feedback list.
  parse_guardrail_json(response)     — Parses guardrail JSON; requires safe_theme when unsafe.
  compute_overall_score(dimensions)  — Returns the rounded average of dimension scores (1 decimal).
  format_evaluation_feedback(eval)   — Formats dimension scores + feedback for revision prompts.
  format_choice(letter, text)        — Formats a choice as "A - ..." for prompt context.
  parse_story_and_choices(response)  — Splits LLM story output into story text and A/B/C choices.
  is_final_decision(decision_number) — True if this is the last choice point before the ending.
  strip_story_label(text)            — Removes the "STORY:" prefix from generated text.
  format_piece_with_choices(story, choices) — Combines story + choices for segment judging.
"""


import json
import re

from story_engine.config import NUMBER_OF_DECISIONS

SEGMENT_DIMENSION_KEYS = [
    "age_appropriateness",
    "bedtime_suitability",
    "continuity",
    "decision_relation_quality",
    "creativity",
]

FULL_STORY_DIMENSION_KEYS = [
    "age_appropriateness",
    "bedtime_suitability",
    "story_arc_cohesion",
    "moral_clarity",
    "creativity",
]

DIMENSION_LABELS = {
    "age_appropriateness": "Age Appropriateness",
    "bedtime_suitability": "Bedtime Suitability",
    "continuity": "Continuity",
    "decision_relation_quality": "Decision Relation Quality",
    "creativity": "Creativity",
    "story_arc_cohesion": "Story Arc Cohesion",
    "moral_clarity": "Moral Clarity",
}


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_judge_json(response: str, expected_keys: list) -> dict:
    data = json.loads(_strip_json_fences(response))
    if not isinstance(data, dict):
        raise ValueError("Judge response must be a JSON object")

    for key in expected_keys:
        if key not in data:
            raise ValueError(f"Missing dimension: {key}")
        score = data[key]
        if not isinstance(score, (int, float)) or not 1 <= score <= 10:
            raise ValueError(f"Invalid score for {key}: {score}")

    if "feedback" not in data or not isinstance(data["feedback"], list):
        raise ValueError("Missing or invalid feedback array")

    dimensions = {key: float(data[key]) for key in expected_keys}
    return {
        "dimensions": dimensions,
        "feedback": [str(item) for item in data["feedback"]],
    }


def parse_guardrail_json(response: str) -> dict:
    data = json.loads(_strip_json_fences(response))
    if not isinstance(data, dict):
        raise ValueError("Guardrail response must be a JSON object")

    is_safe = data.get("is_safe", True)
    if not isinstance(is_safe, bool):
        is_safe = bool(is_safe)

    redirect_message = str(data.get("redirect_message", "")).strip()
    safe_theme = str(data.get("safe_theme", "")).strip()

    if not is_safe and not safe_theme:
        raise ValueError("Unsafe request missing required safe_theme")

    return {
        "is_safe": is_safe,
        "redirect_message": redirect_message,
        "safe_theme": safe_theme,
    }


def compute_overall_score(dimensions: dict) -> float:
    if not dimensions:
        return 0.0
    return round(sum(dimensions.values()) / len(dimensions), 1)


def format_evaluation_feedback(evaluation: dict) -> str:
    lines = []
    for key, value in evaluation.get("dimensions", {}).items():
        label = DIMENSION_LABELS.get(key, key.replace("_", " ").title())
        lines.append(f"{label}: {value}")
    lines.append(f"Overall Score (average): {evaluation.get('score', 0)}/10")
    lines.append("")
    lines.append("Feedback:")
    for item in evaluation.get("feedback", []):
        lines.append(f"- {item}")
    return "\n".join(lines)


def format_choice(letter: str, text: str) -> str:
    return f"{letter} - {text}"


def parse_choice_line(line: str):
    match = re.match(r"^\s*([ABC])\s*[\.\)\-:]\s*(.+?)\s*$", line, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).upper(), match.group(2).strip()


def parse_story_and_choices(response: str) -> tuple:
    story = response
    choices = []

    if "CHOICES:" in response:
        parts = response.split("CHOICES:", 1)
        story = parts[0].replace("STORY:", "").strip()
        for line in parts[1].strip().split("\n"):
            parsed = parse_choice_line(line)
            if parsed:
                letter, text = parsed
                choices.append(f"{letter}. {text}")
    else:
        story = response.replace("STORY:", "").strip()

    if len(choices) < 3:
        found = []
        for line in response.splitlines():
            parsed = parse_choice_line(line)
            if parsed:
                letter, text = parsed
                found.append(f"{letter}. {text}")
        if len(found) >= 3:
            choices = found[:3]

    return story, choices


def is_final_decision(decision_number: int) -> bool:
    return decision_number >= NUMBER_OF_DECISIONS - 1


def strip_story_label(text: str) -> str:
    return text.replace("STORY:", "").strip()


def format_piece_with_choices(story: str, choices: list) -> str:
    return f"{story}\n\nCHOICES:\n" + "\n".join(choices)
