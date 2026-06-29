"""
This file has all the prompt templates for all LLM roles in the story pipeline.

I defined some constants:
  CHOICE_RULES            — Rules requiring distinct, perspective-driven A/B/C choices.
  CONTENT_GUARDRAIL_BLOCK — Safety rules appended to all story generation prompts.
  SEGMENT_RUBRIC          — One-sentence definitions for segment judge parameters.
  FULL_STORY_RUBRIC       — One-sentence definitions for full-story judge parameters.
  SEGMENT_JSON_SCHEMA     — Expected JSON shape for segment judge output.
  FULL_STORY_JSON_SCHEMA  — Expected JSON shape for full-story judge output.

  I am making sure to instruct the LLM to return only the JSON object and not any other text so that it can be parsed easily.

Functions:
  build_content_guardrail_prompt(user_request)
      — Prompt for safety check; returns JSON with is_safe, redirect_message, safe_theme.

  build_story_beginning_prompt(user_request)
      — Prompt for the opening segment (Setup); includes A/B/C choices.

  build_story_continuation_prompt(story_so_far, selected_choice, decision_number, user_request, is_final)
      — Prompt for a middle segment (Rising Action); honors the reader's chosen branch.

  build_story_ending_prompt(story_so_far, selected_choice, user_request)
      — Prompt for the final segment (Resolution); no choices.

  build_piece_judge_prompt(piece_text, user_request, piece_type, story_so_far, selected_choice)
      — Prompt for per-segment quality evaluation; returns JSON with 5 dimension scores.

  build_piece_revision_prompt(piece_text, judge_feedback, user_request, piece_type, ...)
      — Prompt to improve a segment based on judge feedback.

  build_full_story_judge_prompt(full_story, user_request)
      — Prompt for holistic evaluation of the complete story; returns JSON with 5 dimensions.
"""








# --- Story prompts ---

CHOICE_RULES = """
CHOICE RULES (when providing A/B/C):
- Each choice must be UNIQUE in action and perspective (e.g. brave vs cautious vs curious).
- No two choices may lead to the same outcome or rephrase the same idea.
- Each choice must open a meaningfully different path for the child.
- Before writing choices, mentally assign each one a distinct perspective — do not show this to the reader.
"""

CONTENT_GUARDRAIL_BLOCK = """
CONTENT SAFETY (MANDATORY):
- This story is for children aged 5-10 at bedtime.
- NEVER include scary, violent, horror, adult, inappropriate, or disturbing content.
- NEVER include weapons, death, gore, bullying, or mature themes.
- If the request implies unsafe content, write a calm, gentle alternative instead.
"""

def build_content_guardrail_prompt(user_request: str) -> str:
    return f"""
You are a content safety checker for a children's bedtime story app (ages 5-10).

Review this story request:
"{user_request}"

Decide if it is safe for a bedtime story. Block requests involving:
- Scary, horror, or frightening content
- Violence, weapons, fighting, or death
- Adult, inappropriate, or mature themes
- Anything not suitable for children aged 5-10 at bedtime

Important:
- Names of fictional or ordinary characters are SAFE by themselves.
- Requests like "a story about Alice", "a story about a boy named Max", or
  "a Barbie story" are SAFE unless the requested plot includes unsafe content.
- Do not mark a request unsafe only because it contains a person's name,
  character name, brand-like name, or proper noun.

Return ONLY valid JSON. No markdown, no prose outside the JSON object.

If SAFE:
{{"is_safe": true, "redirect_message": "", "safe_theme": ""}}

If UNSAFE:
{{"is_safe": false, "redirect_message": "<polite child-friendly explanation that this kind of story is not good for bedtime>", "safe_theme": "<REQUIRED: one specific, creative, gentle bedtime story idea — not generic>"}}

When UNSAFE, safe_theme is REQUIRED and must be non-empty. Make it specific and
imaginative — not a generic placeholder. Vary your suggestions; avoid repeating
the same fallback every time. You may borrow harmless, cozy elements from the
original request when possible (e.g. "zombie horror" → "a sleepy garden where
friendly vegetables come alive at dusk"), but it must remain fully safe for ages 5-10.
"""


def build_story_beginning_prompt(user_request: str) -> str:
    return f"""
You are an expert children's bedtime storyteller.

USER REQUEST (THIS IS THE #1 PRIORITY — DO NOT IGNORE):
"{user_request}"

Your story MUST directly fulfill this request. Build the entire story around it.
Do NOT invent an unrelated generic character or plot instead.

{CONTENT_GUARDRAIL_BLOCK}
STORY ARC — this segment is SETUP:
- Introduce the main character(s) and world from the user's request
- Establish a calm, imaginative setting appropriate for ages 5-10
- Present a gentle inciting moment that leads to a decision point

RULES:
- Calm, safe, comforting tone
- Simple vocabulary
- Light imaginative world-building tied to the user's request

{CHOICE_RULES}

At the end, provide EXACTLY 3 choices labeled A, B, C.

FORMAT STRICTLY:

STORY:
<story beginning>

CHOICES:
A. ...
B. ...
C. ...

Begin the story now, centered on: "{user_request}"
"""


def build_story_continuation_prompt(story_so_far: str,
                                     selected_choice: str,
                                     decision_number: int,
                                     user_request: str,
                                     is_final: bool = False) -> str:
    final_note = ""
    if is_final:
        final_note = """
This IS the final decision point before the story ends.
Choices should lead toward resolution while remaining distinct in perspective.
"""

    return f"""
You are continuing a children's interactive bedtime story.

READER'S CHOSEN DECISION (THIS IS MANDATORY — DO NOT IGNORE OR SWAP):
{selected_choice}

The opening 1-2 sentences of your continuation MUST depict the character doing
EXACTLY what the reader chose above. Do NOT follow a different option.

ORIGINAL USER REQUEST:
"{user_request}"

{CONTENT_GUARDRAIL_BLOCK}

STORY ARC — this segment is RISING ACTION (decision point #{decision_number}):
- Advance the plot from the chosen branch only
- Escalate gently toward the climax
- Keep the same main character(s), theme, and world
- Do NOT restart the story or swap in unrelated characters

RULES:
- Maintain continuity with the previous story
- Keep tone calm and magical, age appropriate for 5-10
- Only continue from the chosen branch; ignore paths implied by other options
- Do NOT introduce unrelated plot elements
{final_note}

{CHOICE_RULES}

PREVIOUS STORY:
{story_so_far}

TASK:
Continue the story from the chosen decision above. Stay faithful to: "{user_request}"

At the end, provide EXACTLY 3 new choices:

FORMAT:

STORY:
<continuation>

CHOICES:
A. ...
B. ...
C. ...
"""


def build_story_ending_prompt(story_so_far: str,
                              selected_choice: str,
                              user_request: str) -> str:
    return f"""
You are writing the FINAL part of a children's bedtime story.

READER'S CHOSEN DECISION (THIS IS MANDATORY — DO NOT IGNORE OR SWAP):
{selected_choice}

The opening 1-2 sentences MUST depict the character doing EXACTLY what the reader
chose above. Do NOT follow a different option.

ORIGINAL USER REQUEST:
"{user_request}"

{CONTENT_GUARDRAIL_BLOCK}

STORY ARC — this segment is RESOLUTION:
- Deliver a gentle climax and satisfying ending
- Resolve the thread opened in the setup
- Reinforce a positive moral lesson
- End with a calm, wind-down image suitable for sleep

RULES:
- Honor the user's original request throughout
- Keep the same main character(s) and theme from the story so far
- Age appropriate (5-10), no scary or negative imagery
- Do NOT introduce new unrelated characters or change the subject

FULL STORY SO FAR:
{story_so_far}

TASK:
Write the final ending only.

FORMAT:

STORY:
<final ending>

Do NOT include choices.
"""


# --- Segment judge / revise prompts ---

SEGMENT_RUBRIC = """
Score each dimension from 1-10. Be strict; a typical good segment is 6-8, NOT 9-10.

- age_appropriateness: Language, themes, and content are suitable for children aged 5-10 with no adult or frightening material.
- bedtime_suitability: Tone is calm, comforting, and wind-down friendly — not scary, violent, or overstimulating before sleep.
- continuity: Characters, events, and world stay consistent with prior segments (or set up the user's request well for openings).
- decision_relation_quality: The segment honors the reader's chosen decision, or (for openings) A/B/C choices are distinct and meaningful.
- creativity: The segment uses original, imaginative ideas rather than generic or repetitive storytelling.
"""

FULL_STORY_RUBRIC = """
Score each dimension from 1-10. Be strict; a typical good story is 6-8, NOT 9-10.

- age_appropriateness: Language, themes, and content are suitable for children aged 5-10 with no adult or frightening material.
- bedtime_suitability: Tone is calm, comforting, and wind-down friendly — not scary, violent, or overstimulating before sleep.
- story_arc_cohesion: The complete story has a clear setup, rising action, and satisfying resolution that flow naturally together.
- moral_clarity: A positive, age-appropriate lesson is clear and gently delivered without being preachy.
- creativity: The story uses original, imaginative ideas rather than generic or repetitive storytelling.
"""

SEGMENT_JSON_SCHEMA = """{
  "age_appropriateness": <1-10>,
  "bedtime_suitability": <1-10>,
  "continuity": <1-10>,
  "decision_relation_quality": <1-10>,
  "creativity": <1-10>,
  "feedback": ["<bullet 1>", "<bullet 2>", "<bullet 3>"]
}"""

FULL_STORY_JSON_SCHEMA = """{
  "age_appropriateness": <1-10>,
  "bedtime_suitability": <1-10>,
  "story_arc_cohesion": <1-10>,
  "moral_clarity": <1-10>,
  "creativity": <1-10>,
  "feedback": ["<bullet 1>", "<bullet 2>", "<bullet 3>"]
}"""


def build_piece_judge_prompt(piece_text: str,
                             user_request: str,
                             piece_type: str,
                             story_so_far: str = "",
                             selected_choice: str = "") -> str:
    if piece_type == "beginning":
        context_block = """
This is the OPENING segment (Setup phase). The child has NOT read this yet.
Score continuity based on how well it sets up the user's request.
Score decision_relation_quality based on how distinct and meaningful the A/B/C choices are.
"""
    elif piece_type == "continuation":
        context_block = f"""
This is a MIDDLE segment (Rising Action).

Story so far:
{story_so_far}

Reader's chosen decision — this segment MUST follow it:
{selected_choice}

Score continuity based on consistency with the previous story.
Score decision_relation_quality based on how well the segment honors the chosen decision.
"""
    else:
        context_block = f"""
This is the FINAL segment (Resolution).

Story so far:
{story_so_far}

Reader's last decision — the ending MUST follow it:
{selected_choice}

Score continuity based on consistency with the full story so far.
Score decision_relation_quality based on how well the ending honors the chosen decision.
No choices expected in this segment.
"""

    return f"""
You are a STRICT children's book editor reviewing ONE segment of a bedtime story
for ages 5-10. The child will read this segment next.

ORIGINAL USER REQUEST:
"{user_request}"

PIECE TYPE: {piece_type}
{context_block}

{SEGMENT_RUBRIC}

IMPORTANT:
- Heavily penalize segments that ignore the reader's chosen decision
- Heavily penalize choices that are too similar to each other
- Do NOT include an overall score — only score the five dimensions

Return ONLY valid JSON matching this schema (no markdown, no extra text):
{SEGMENT_JSON_SCHEMA}

SEGMENT TO REVIEW:
{piece_text}
"""


def build_piece_revision_prompt(piece_text: str,
                                judge_feedback: str,
                                user_request: str,
                                piece_type: str,
                                story_so_far: str = "",
                                selected_choice: str = "",
                                has_choices: bool = False) -> str:
    format_instruction = """
Return the improved segment in this EXACT format:

STORY:
<improved segment text>

CHOICES:
A. ...
B. ...
C. ...
""" if has_choices else """
Return ONLY the improved final segment text (no choices, no labels).
"""

    context_block = ""
    if piece_type == "continuation":
        context_block = f"""
Story so far:
{story_so_far}

Reader's chosen decision (opening MUST reflect this):
{selected_choice}
"""
    elif piece_type == "ending":
        context_block = f"""
Story so far:
{story_so_far}

Reader's last decision (opening MUST reflect this):
{selected_choice}
"""

    return f"""
You are improving ONE segment of a children's bedtime story before a child reads it.

ORIGINAL USER REQUEST (MUST still be honored):
"{user_request}"

PIECE TYPE: {piece_type}
{context_block}

Fix issues in these dimensions: age_appropriateness, bedtime_suitability,
continuity, decision_relation_quality, creativity.

If choices are too similar, rewrite them so each opens a distinct perspective.
If the segment ignores the reader's decision, rewrite the opening to follow it exactly.
Keep the same plot direction, characters, and theme.

JUDGE FEEDBACK:
{judge_feedback}

ORIGINAL SEGMENT:
{piece_text}

{format_instruction}
"""


def build_full_story_judge_prompt(full_story: str, user_request: str) -> str:
    return f"""
You are a STRICT children's book editor reviewing a COMPLETE bedtime story for ages 5-10.

The reader originally asked for:
"{user_request}"

Evaluate the ENTIRE story as one cohesive piece. Do NOT reference segment numbers.

{FULL_STORY_RUBRIC}

Do NOT include an overall score — only score the five dimensions.

Return ONLY valid JSON matching this schema (no markdown, no extra text):
{FULL_STORY_JSON_SCHEMA}

COMPLETE STORY:
{full_story}
"""
