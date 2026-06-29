from html import escape

from dotenv import load_dotenv
import streamlit as st

from story_engine.config import NUMBER_OF_DECISIONS
from story_engine.engine import (
    check_content_safety,
    generate_beginning,
    generate_continuation,
    generate_ending,
    judge_full_story,
    refine_until_plateau,
)
from story_engine.errors import StoryEngineError
from story_engine.parsing import parse_choice_line, format_choice


load_dotenv()


def _full_text(parts: list) -> str:
    return "\n\n".join(parts).strip()


def _reset_state():
    st.session_state.request = ""
    st.session_state.effective_request = ""
    st.session_state.parts = []
    st.session_state.current_story = ""
    st.session_state.current_choices = []
    st.session_state.current_eval = None
    st.session_state.current_label = ""
    st.session_state.decision_number = 1
    st.session_state.final_eval = None
    st.session_state.safety_message = ""
    st.session_state.complete = False
    st.session_state.error = ""


def _init_state():
    if "parts" not in st.session_state:
        _reset_state()


def _start_story(user_request: str):
    _reset_state()
    st.session_state.request = user_request

    safety = check_content_safety(user_request)
    effective_request = safety["effective_request"]
    st.session_state.effective_request = effective_request

    if not safety["is_safe"]:
        st.session_state.safety_message = safety["redirect_message"]

    story, choices = generate_beginning(effective_request)
    story, choices, evaluation = refine_until_plateau(
        effective_request, "beginning", story=story, choices=choices,
    )

    st.session_state.parts = [story]
    st.session_state.current_story = story
    st.session_state.current_choices = choices
    st.session_state.current_eval = evaluation
    st.session_state.current_label = "Story beginning"
    st.session_state.decision_number = 1


def _choose_path(choice: str):
    parsed = parse_choice_line(choice)
    if not parsed:
        raise ValueError("Choice could not be read.")

    choice_letter, choice_text = parsed
    selected = format_choice(choice_letter, choice_text)
    request = st.session_state.effective_request
    story_so_far = _full_text(st.session_state.parts)

    if st.session_state.decision_number < NUMBER_OF_DECISIONS:
        story, choices = generate_continuation(
            story_so_far,
            selected,
            st.session_state.decision_number,
            request,
        )
        story, choices, evaluation = refine_until_plateau(
            request,
            "continuation",
            story=story,
            choices=choices,
            story_so_far=story_so_far,
            selected_choice=selected,
        )

        st.session_state.parts.append(story)
        st.session_state.current_story = story
        st.session_state.current_choices = choices
        st.session_state.current_eval = evaluation
        st.session_state.current_label = (
            f"Story continuation (part {st.session_state.decision_number})"
        )
        st.session_state.decision_number += 1
        return

    ending = generate_ending(story_so_far, selected, request)
    ending, evaluation = refine_until_plateau(
        request,
        "ending",
        text=ending,
        story_so_far=story_so_far,
        selected_choice=selected,
    )

    st.session_state.parts.append(ending)
    st.session_state.current_story = ending
    st.session_state.current_choices = []
    st.session_state.current_eval = evaluation
    st.session_state.current_label = "Story ending"
    st.session_state.final_eval = judge_full_story(_full_text(st.session_state.parts), request)
    st.session_state.complete = True


def _score_badge(evaluation: dict) -> str:
    if not evaluation:
        return ""
    return f"{evaluation.get('score', 'N/A')}/10"


def _render_evaluation(evaluation: dict, title: str):
    if not evaluation:
        return

    with st.expander(f"{title}: {_score_badge(evaluation)}", expanded=False):
        initial = evaluation.get("initial_score")
        if initial is not None:
            st.caption(
                f"Initial score: {initial}/10 | Final score: {evaluation.get('score')}/10 | "
                f"Refinement iterations: {evaluation.get('refinement_iterations', 0)}"
            )
        else:
            st.caption(f"Overall score: {evaluation.get('score')}/10")

        st.write("Scores")
        st.json(evaluation.get("dimensions", {}))

        feedback = evaluation.get("feedback", [])
        if feedback:
            st.write("Feedback")
            for item in feedback:
                st.write(f"- {item}")


def _render_story():
    if not st.session_state.parts:
        return

    st.subheader(st.session_state.current_label)
    story_html = escape(st.session_state.current_story).replace("\n", "<br>")
    st.markdown(
        f"""
        <div class="story-card">
            {story_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_evaluation(st.session_state.current_eval, "Quality check")

    if st.session_state.complete:
        st.success("Sweet dreams. Your bedtime story is complete.")
        _render_evaluation(st.session_state.final_eval, "Complete story evaluation")
        with st.expander("Full story", expanded=True):
            st.write(_full_text(st.session_state.parts))
        return

    if st.session_state.current_choices:
        st.subheader("Choose what happens next")
        clicked_choice = None
        for choice in st.session_state.current_choices:
            parsed = parse_choice_line(choice)
            if not parsed:
                continue
            letter, text = parsed
            if st.button(f"{letter}. {text}", key=f"choice-{st.session_state.decision_number}-{letter}"):
                clicked_choice = choice

        if clicked_choice:
            try:
                with st.spinner("Writing the next part..."):
                    _choose_path(clicked_choice)
                st.rerun()
            except (StoryEngineError, ValueError) as exc:
                st.session_state.error = str(exc)
                st.rerun()


def main():
    st.set_page_config(
        page_title="Interactive Bedtime Stories",
        page_icon="🌙",
        layout="centered",
    )
    _init_state()

    st.markdown(
        """
        <style>
        .block-container {
            max-width: 900px;
            padding-top: 2rem;
        }
        .story-card {
            border: 1px solid #c7d2fe;
            border-radius: 8px;
            padding: 1.25rem;
            background: #f8fafc;
            color: #111827;
            line-height: 1.75;
            font-size: 1.05rem;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
        }
        div.stButton > button {
            width: 100%;
            border-radius: 8px;
            text-align: left;
            padding: 0.75rem 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("Interactive Bedtime Stories")
    st.caption("A calm choose-your-own-adventure storyteller for ages 5-10.")

    with st.sidebar:
        st.header("Story setup")
        user_request = st.text_area(
            "What kind of story do you want?",
            placeholder="A cozy story about a bunny who finds a moonlit garden",
            height=120,
        )
        start = st.button("Start story", type="primary")
        reset = st.button("Reset")

        if reset:
            _reset_state()
            st.rerun()

    if start:
        if not user_request.strip():
            st.session_state.error = "Please enter a story idea."
        else:
            try:
                st.session_state.error = ""
                placeholder = st.empty()
                with placeholder, st.spinner("Thinking of a safe bedtime story..."):
                    _start_story(user_request.strip())
            except (StoryEngineError, ValueError) as exc:
                st.session_state.error = str(exc)

    if st.session_state.error:
        st.error(st.session_state.error)

    if st.session_state.safety_message:
        st.info(st.session_state.safety_message)

    if st.session_state.parts:
        _render_story()
    elif not start:
        st.markdown(
            """
            Start with a short idea, then pick A, B, or C as the story unfolds.
            The app checks each segment with an LLM judge before showing it.
            """
        )


if __name__ == "__main__":
    main()
