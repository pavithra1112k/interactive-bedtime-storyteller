"""
Core orchestration: story generation, judging, revision, and content safety.

The functions defined here mostly end up calling the functions in prompts.py and the llm.py file. 
They are orchestrating the story pipeline.

Functions:
  _call_story(prompt)              — Calls LLM at STORY_TEMPERATURE for story generation using the current prompt passed.
  _call_judge(prompt, keys)        — Calls judge LLM, parses JSON, computes average score; retries once.
  check_content_safety(user_request) — LLM guardrail check; returns is_safe, redirect_message, safe_theme.
  _generate_with_choices(fn)       — Generates story + 3 choices; retries if parsing fails.
  generate_beginning(user_request)   — Generates the opening segment with A/B/C choices.
  generate_continuation(...)       — Generates a middle segment continuing from the chosen branch.
  generate_ending(...)               — Generates the final segment (no choices).
  judge_piece(...)                   — Scores one segment on 5 dimensions (segment judge).
  judge_full_story(full_story, ...)  — Scores the complete story on 5 dimensions (full-story judge).
  _revise(...)                       — Revises a segment using formatted judge feedback.
  refine_until_plateau(...)          — Judge-revise loop; keeps revising until score stops improving
                                       or MAX_REFINEMENT_ROUNDS is reached.
"""

from story_engine.config import (
    JUDGE_TEMPERATURE,
    MAX_REFINEMENT_ROUNDS,
    REVISION_TEMPERATURE,
    STORY_TEMPERATURE,
)
from story_engine.errors import ModelOutputError
from story_engine.llm import call_model
from story_engine.parsing import (
    FULL_STORY_DIMENSION_KEYS,
    SEGMENT_DIMENSION_KEYS,
    compute_overall_score,
    format_evaluation_feedback,
    format_piece_with_choices,
    is_final_decision,
    parse_guardrail_json,
    parse_judge_json,
    parse_story_and_choices,
    strip_story_label,
)
from story_engine.prompts import (
    build_content_guardrail_prompt,
    build_full_story_judge_prompt,
    build_piece_judge_prompt,
    build_piece_revision_prompt,
    build_story_beginning_prompt,
    build_story_continuation_prompt,
    build_story_ending_prompt,
)


def _call_story(prompt: str) -> str:
    return call_model(prompt, temperature=STORY_TEMPERATURE)


def _call_judge(prompt: str, expected_keys: list) -> dict:
    last_error = None
    for attempt in range(2):
        response = call_model(prompt, temperature=JUDGE_TEMPERATURE)
        try:
            parsed = parse_judge_json(response, expected_keys)
            dimensions = parsed["dimensions"]
            score = compute_overall_score(dimensions)
            return {
                "score": score,
                "dimensions": dimensions,
                "feedback": parsed["feedback"],
                "raw": response,
            }
        except (ValueError, KeyError) as exc:
            last_error = exc
            if attempt == 0:
                continue
    raise ModelOutputError(f"Judge returned invalid JSON after retry: {last_error}")


def check_content_safety(user_request: str) -> dict:
    prompt = build_content_guardrail_prompt(user_request)
    last_error = None
    for attempt in range(2):
        response = call_model(prompt, temperature=JUDGE_TEMPERATURE)
        try:
            result = parse_guardrail_json(response)
            effective_request = user_request if result["is_safe"] else result["safe_theme"]
            return {
                "is_safe": result["is_safe"],
                "redirect_message": result["redirect_message"],
                "safe_theme": result["safe_theme"],
                "effective_request": effective_request,
            }
        except (ValueError, KeyError) as exc:
            last_error = exc
            if attempt == 0:
                continue
    raise ModelOutputError(
        f"Content guardrail returned invalid JSON after retry: {last_error}"
    )


def _generate_with_choices(build_prompt_fn, max_retries=2) -> tuple:
    for _ in range(max_retries + 1):
        response = _call_story(build_prompt_fn())
        story, choices = parse_story_and_choices(response)
        if len(choices) >= 3:
            return story, choices
    raise ModelOutputError("Could not generate valid story choices after retries.")


def generate_beginning(user_request: str) -> tuple:
    return _generate_with_choices(
        lambda: build_story_beginning_prompt(user_request)
    )


def generate_continuation(story_so_far: str,
                          selected_choice: str,
                          decision_number: int,
                          user_request: str) -> tuple:
    return _generate_with_choices(
        lambda: build_story_continuation_prompt(
            story_so_far, selected_choice, decision_number,
            user_request, is_final=is_final_decision(decision_number),
        )
    )


def generate_ending(story_so_far: str,
                    selected_choice: str,
                    user_request: str) -> str:
    return _call_story(
        build_story_ending_prompt(story_so_far, selected_choice, user_request)
    )


def judge_piece(piece_text: str,
                user_request: str,
                piece_type: str,
                *,
                story_so_far: str = "",
                selected_choice: str = "") -> dict:
    return _call_judge(
        build_piece_judge_prompt(
            piece_text, user_request, piece_type,
            story_so_far=story_so_far, selected_choice=selected_choice,
        ),
        SEGMENT_DIMENSION_KEYS,
    )


def judge_full_story(full_story: str, user_request: str) -> dict:
    return _call_judge(
        build_full_story_judge_prompt(full_story, user_request),
        FULL_STORY_DIMENSION_KEYS,
    )


def _revise(piece_text: str, evaluation: dict, user_request: str,
            piece_type: str, *, story_so_far: str, selected_choice: str,
            has_choices: bool) -> str:
    feedback = format_evaluation_feedback(evaluation)
    return call_model(
        build_piece_revision_prompt(
            piece_text, feedback, user_request, piece_type,
            story_so_far=story_so_far, selected_choice=selected_choice,
            has_choices=has_choices,
        ),
        temperature=REVISION_TEMPERATURE,
    )


def refine_until_plateau(user_request: str,
                         piece_type: str,
                         *,
                         story: str = "",
                         choices: list = None,
                         text: str = "",
                         story_so_far: str = "",
                         selected_choice: str = ""):
    has_choices = choices is not None

    if has_choices:
        best_story, best_choices = story, choices
        judge_text = format_piece_with_choices(best_story, best_choices)
    else:
        best_text = strip_story_label(text)
        judge_text = best_text

    best_eval = judge_piece(
        judge_text, user_request, piece_type,
        story_so_far=story_so_far, selected_choice=selected_choice,
    )
    initial_score = best_eval["score"]
    refinement_iterations = 0

    for _ in range(MAX_REFINEMENT_ROUNDS):
        revised = _revise(
            judge_text, best_eval, user_request, piece_type,
            story_so_far=story_so_far, selected_choice=selected_choice,
            has_choices=has_choices,
        )
        refinement_iterations += 1

        if has_choices:
            parsed_story, parsed_choices = parse_story_and_choices(revised)
            if parsed_choices:
                candidate_story, candidate_choices = parsed_story, parsed_choices
            else:
                candidate_story, candidate_choices = strip_story_label(revised), best_choices
            candidate_text = format_piece_with_choices(candidate_story, candidate_choices)
        else:
            candidate_text = strip_story_label(revised)

        new_eval = judge_piece(
            candidate_text, user_request, piece_type,
            story_so_far=story_so_far, selected_choice=selected_choice,
        )

        if new_eval["score"] > best_eval["score"]:
            best_eval = new_eval
            judge_text = candidate_text
            if has_choices:
                best_story, best_choices = candidate_story, candidate_choices
            else:
                best_text = candidate_text
        else:
            break

    best_eval["initial_score"] = initial_score
    best_eval["refinement_iterations"] = refinement_iterations

    if has_choices:
        return best_story, best_choices, best_eval
    return best_text, best_eval
