# Interactive Bedtime Stories — Project Summary

## What I Built

This is my submission for the coding take-home assessment. I built an agent that takes a child's story request and turns it into an interactive bedtime story for ages 5–10, using GPT-3.5-turbo and an LLM judge to improve quality.

Novelty and a surprise element that I introduced: Instead of generating one block of text as a story, I made it a choose-your-own-adventure: the child picks A, B, or C at each decision point, and every segment is checked for safety and quality before they read it. I actually took an inspiration from the game 'Until Dawn' for this.

Run CLI with: `python3 main.py`<br>
Run UI with: `streamlit run app.py`<br>
Needs an OpenAI API Key.

---

## Setup

```bash
python3 -m pip install -r requirements.txt
```

Create a local `.env` file:

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

## Architecture

The architecture uses multiple agent roles - each with a specific job - coordinated by a simple Python loop in main.py. `main.py` runs the game loop; `engine.py` handles generation, judging, and revision; each step calls the LLM with a different prompt and temperature.

| Role | What it does | Temp |
|------|--------------|------|
| Content guardrail | Checks if the request is safe for bedtime | 0.1 |
| Storyteller | Writes each story segment | 0.7 |
| Segment judge | Scores a piece on 5 dimensions before the child sees it | 0.1 |
| Reviser | Fixes issues flagged by the judge | 0.5 |
| Full-story judge | Final holistic score at the end | 0.1 |

I tuned temperature per role on purpose. The storyteller runs at 0.7 so the prose stays imaginative and varied. The judges and guardrail use 0.1 so scoring and safety checks stay strict, consistent, and easy to parse as JSON. The reviser sits at 0.5 — creative enough to rewrite weak lines, but restrained enough to follow judge feedback instead of drifting off-theme.

**Segment evaluation (each piece before the child reads it):** Age Appropriateness, Bedtime Suitability, Continuity, Decision Relation Quality, Creativity — each scored 1–10.

**Full-story evaluation (at the end):** Age Appropriateness, Bedtime Suitability, Story Arc Cohesion, Moral Clarity, Creativity — each scored 1–10. The overall score is always the average of those five dimensions, computed in code — the LLM only returns the individual scores and feedback.

**Flow:** user request → safety check → generate segment → judge → refine until score plateaus → show to user → collect choice → repeat → ending → final whole-story score.

## Block Diagram

<img width="2910" height="3500" alt="image" src="https://github.com/user-attachments/assets/d6929434-3bc0-46ac-97a3-ffc16fbbab2f" />

**Files:**

```
app.py               — Streamlit UI
main.py              — game loop
story_engine/
  config.py          — temperatures, limits
  llm.py             — OpenAI wrapper
  prompts.py         — all prompt templates
  parsing.py         — JSON parsing, story/choice extraction
  errors.py          — custom exceptions
  engine.py          — generation, judging, revision, guardrails
  ui.py              — terminal output
```
I intentionally skipped LangChain-style agent frameworks and built this in plain Python: the story flow is always the same sequence of steps, so letting an LLM "orchestrate" mostly added latency, cost, and parse failures without improving outcomes - I even tried a ReAct agent early on and reverted to a simple loop in main.py once I confirmed the coordinator didn't need to think, only the storyteller and judge did.

---

## Where I Started

I started with a single ~300-line `main.py` with the basic idea already there: generate a beginning, loop through continuations, write an ending, call a judge. When I actually ran it, I hit real problems:

- Choices weren't propagating — the story kept following the first pick
- The judge only ran at the very end, after the child had already read everything
- The model ignored requests (I typed "Barbie story" and got a character named Lily)
- Continuations sometimes followed the wrong branch

My first pass was fixing those bugs: proper choice formatting, parsing with retries, and a judge-revise loop.

---

## How It Evolved

**Modularization** — I split the monolith into a `story_engine/` package, then consolidated down to 7 focused files. All prompts live in one place; all orchestration in `engine.py`.

**Per-segment judging** — This was a key design decision for me. Judging the whole story at the end felt wrong — the child had already read it. Now each segment (beginning, continuation, ending) is generated, judged, and refined until the score plateaus, and only then shown. A final whole-story judge runs once at the end for a holistic score.

**Story arcs and branching** — I structured prompts around Setup → Rising Action → Resolution. Continuations must open with exactly what the child chose, and A/B/C options have to be genuinely different perspectives — not three versions of the same idea.

**Content guardrails** — Before any generation, I check if the request is appropriate. If not, I print a polite redirect in the CLI and generate a creative safe alternative theme from the LLM.

**Agent experiment** — I tried a ReAct orchestrator where the LLM picked the next tool. The agent didn’t really choose anything — at each step there was usually only one logical next action, so the LLM just repeated what the code would have done anyway, while costing extra API calls. I moved the flow back to a straightforward loop in `main.py` and kept the intelligence in the prompts instead.

---

## Why Segments Matter

Three things make this more than a basic story generator:

1. **Interactivity** — The child's choices shape the story. Every run is different.
2. **Quality before exposure** — Each piece gets an editorial pass (judge + revise) before the child reads it. I check age appropriateness, bedtime suitability, continuity, decision fidelity, and creativity. The story with the best score gets displayed.
3. **Accountable branching** — The story actually follows what the child picked, and each choice opens a meaningfully different path.

That combination — interactive, quality-controlled, and responsive — is what I was going for.

---

## Prompts and Guardrails

I treated prompts as real engineering work. Everything lives in `prompts.py` with shared blocks (`CONTENT_GUARDRAIL_BLOCK`, `CHOICE_RULES`, rubrics, JSON schemas) so nothing drifts between segment types.

Each role gets its own prompt: storyteller prompts differ for beginning/continuation/ending; judge prompts adapt to segment type and include story context; revision prompts get formatted scores and feedback.

For guardrails, an LLM call runs first on the user's request. Safe requests proceed as-is. Unsafe ones get a child-friendly redirect in the terminal, then the story uses a creative safe theme the model generates on the spot.

---

## Failure Handling

- Missing `OPENAI_API_KEY` gives a clear setup error.
- OpenAI API calls retry before failing.
- Empty model responses are rejected and retried.
- Judge and guardrail JSON are validated and retried once.
- Story choices are parsed with regex, supporting `A.`, `A)`, `A -`, and `A:` formats.
- Engine errors are raised and handled in `main.py`, instead of exiting deep inside the story engine.

---
## Demo

https://drive.google.com/file/d/1P4MGGy8Ngwi1DeG2cry6NyohEiAu7U_D/view?usp=sharing

---
## Design Choices

I kept Python deterministic where I could and used LLMs where I needed judgment or creativity. `main.py` is just the game loop — no business logic buried in it. Refinement stops on plateau with a hard cap of 3 rounds.

The big idea for me: **judge before show, not after**. Quality gates should be a priority, especially for a children's bedtime product.

## Future Scope

If I were to continue expanding the project, I'd like to experiment with alternative orchestration approaches such as a supervising agent or ReAct-style agent that dynamically decides which agent or tool to invoke next. I'd also be interested in exploring frameworks like LangGraph for more complex multi-agent workflows, n8n for visual orchestration, and ComfyUI if the project evolves into multimodal storytelling with illustrations. These approaches would become more valuable as the system grows to include capabilities such as memory, RAG, external tools, or personalized story generation.

