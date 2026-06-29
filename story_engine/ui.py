"""
This file is just for determining how things display on the terminal for the interactive story CLI.

Functions:
  _full_line_divider()              — Returns a full-width "=" divider matching terminal width.
  _print_dimension_scores(evaluation) — Prints each judge dimension score with a label.
  _print_feedback(evaluation)       — Prints judge feedback as bullet points.
  print_story_segment(story, label) — Prints a story segment with a labeled header divider.
  print_evaluation(evaluation, label) — Prints segment quality check: scores, average, feedback, iterations.
  print_full_story_score(evaluation)  — Prints the final whole-story evaluation (no story reprint).
  print_choices(choices)            — Displays A/B/C options and prompts user until valid input;
                                      returns (letter, choice_text).
"""


import shutil
import re

from story_engine.parsing import DIMENSION_LABELS, parse_choice_line


def _full_line_divider() -> str:
    try:
        width = shutil.get_terminal_size().columns
    except OSError:
        width = 80
    return "=" * width


def _print_dimension_scores(evaluation: dict):
    dimensions = evaluation.get("dimensions", {})
    for key, value in dimensions.items():
        label = DIMENSION_LABELS.get(key, key.replace("_", " ").title())
        print(f"{label}: {value}")


def _print_feedback(evaluation: dict):
    feedback = evaluation.get("feedback", [])
    if feedback:
        print("\nFeedback:")
        for item in feedback:
            print(f"- {item}")


def print_story_segment(story: str, piece_label: str):
    divider = _full_line_divider()
    print(f"\n{divider}")
    print(f"Story segment — {piece_label}")
    print(f"{divider}\n")
    print(story)


def print_evaluation(evaluation: dict, piece_label: str):
    divider = _full_line_divider()
    iterations = evaluation.get("refinement_iterations", 0)
    initial = evaluation.get("initial_score")
    score = evaluation.get("score", "N/A")
    print(f"\n{divider}")
    print(f"Quality check — {piece_label}")
    if initial is not None:
        print(f"Initial Score: {initial}/10  →  Final Score: {score}/10")
    else:
        print(f"Overall Score: {score}/10")
    print(f"Refinement iterations: {iterations}")
    print()
    _print_dimension_scores(evaluation)
    print(f"\nOverall Score: {score}/10  (average of dimensions above)")
    _print_feedback(evaluation)
    print(f"{divider}\n")


def print_full_story_score(evaluation: dict):
    divider = _full_line_divider()
    score = evaluation.get("score", "N/A")
    print(f"\n{divider}")
    print("Complete story evaluation")
    print()
    _print_dimension_scores(evaluation)
    print(f"\nOverall Score: {score}/10  (average of dimensions above)")
    _print_feedback(evaluation)
    print(f"{divider}\n")


def print_choices(choices: list) -> tuple:
    if not choices:
        raise ValueError("No choices available. Cannot continue the story.")

    print("\nChoose what happens next:\n")

    choice_map = {}
    for choice in choices:
        parsed = parse_choice_line(choice)
        if parsed:
            key, text = parsed
            choice_map[key] = text
            print(f"{key}. {text}")

    if not choice_map:
        raise ValueError("No valid A/B/C choices available. Cannot continue the story.")

    print()
    while True:
        raw_choice = input("> ").strip().upper()
        match = re.match(r"^\s*([ABC])[\s\.\)\-:/]*$", raw_choice)
        user_choice = match.group(1) if match else raw_choice
        if user_choice in choice_map:
            return user_choice, choice_map[user_choice]
        print("Please choose A, B, or C.")
