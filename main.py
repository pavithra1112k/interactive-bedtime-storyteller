"""
Before submitting the assignment, describe here in a few sentences what you would have built next if you spent 2 more hours on this project:

1) I’d add text-to-speech narration with a calm, child-friendly voice so parents can play stories aloud at bedtime without reading the terminal themselves.
2) Create personal accounts for each child. Get feedback from them after each story narration and adapt story narration more to their liking by incorporating on the feedback
3) I’d let children save favorite stories and replay different branches from earlier choice points, turning one session into a reusable library of bedtime adventures.
4) I’d build a simple web app (frontend + API + database) so families can use it in the browser, with accounts and stored story history instead of a one-off CLI run

"""

"""
This is the main function where we will run the interactive bedtime stories CLI.

This file controls and orchestrates the full user session: collects the story request, runs content
safety check, generates/refines/shows each story segment, collects A/B/C choices,
and prints the final whole-story evaluation. We will be showing both the story and the feedback as output. But this is for
our understanding and not for the user. User obviously will only see the story.

Functions:
  _full_text(parts)       — Joins all story segments into one string for context.
  _show_and_choose(...)   — Prints evaluation + story segment + choices; returns user's pick.
  main()                  — Runs the complete interactive story loop from input to final score.
"""

from dotenv import load_dotenv

from story_engine.config import NUMBER_OF_DECISIONS
from story_engine.engine import (
    check_content_safety,
    generate_beginning,
    generate_continuation,
    generate_ending,
    judge_full_story,
    refine_until_plateau,
)
from story_engine.parsing import format_choice
from story_engine.ui import (
    print_choices,
    print_evaluation,
    print_full_story_score,
    print_story_segment,
)
from story_engine.errors import StoryEngineError

load_dotenv()


def _full_text(parts: list) -> str:
    return "\n\n".join(parts).strip()


def _show_and_choose(story, choices, evaluation, label):
    print_evaluation(evaluation, label)
    print_story_segment(story, label)
    return print_choices(choices)


def main():
    print("\nWelcome to Interactive Bedtime Stories\n")

    user_request = input("What kind of story do you want?\n> ").strip()
    if not user_request:
        print("\nPlease enter a story idea.")
        return

    try:
        print("\n\nLet me think...")
        safety = check_content_safety(user_request)
        if not safety["is_safe"]:
            print(f"\n{safety['redirect_message']}\n")
            user_request = safety["effective_request"]

        parts = []

        story, choices = generate_beginning(user_request)
        story, choices, evaluation = refine_until_plateau(
            user_request, "beginning", story=story, choices=choices,
        )
        choice_letter, choice_text = _show_and_choose(
            story, choices, evaluation, "Story beginning",
        )
        parts.append(story)

        for part in range(1, NUMBER_OF_DECISIONS):
            selected = format_choice(choice_letter, choice_text)
            story, choices = generate_continuation(
                _full_text(parts), selected, part, user_request,
            )
            story, choices, evaluation = refine_until_plateau(
                user_request, "continuation",
                story=story, choices=choices,
                story_so_far=_full_text(parts), selected_choice=selected,
            )
            choice_letter, choice_text = _show_and_choose(
                story, choices, evaluation, f"Story continuation (part {part})",
            )
            parts.append(story)

        selected = format_choice(choice_letter, choice_text)
        ending = generate_ending(_full_text(parts), selected, user_request)
        ending, evaluation = refine_until_plateau(
            user_request, "ending", text=ending,
            story_so_far=_full_text(parts), selected_choice=selected,
        )
        print_evaluation(evaluation, "Story ending")
        print_story_segment(ending, "Story ending")
        parts.append(ending)

        print("\n" + "=" * 60)
        print("Sweet dreams! Your bedtime story is complete.")
        print("=" * 60)

        full_eval = judge_full_story(_full_text(parts), user_request)
        print_full_story_score(full_eval)

    except StoryEngineError as exc:
        print(f"\nCould not complete the story: {exc}")
    except ValueError as exc:
        print(f"\nCould not continue: {exc}")
    except KeyboardInterrupt:
        print("\nStory cancelled.")


if __name__ == "__main__":
    main()
