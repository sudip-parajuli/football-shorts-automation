"""
Centralized, env-overridable LLM model names/lists.

Both Google (Gemini) and Groq have repeatedly retired or renamed specific
model snapshots this project depended on — four separate retirements hit in
production within about two weeks:
  - gemini-2.0-flash        -> retired, Google suggests gemini-3.6-flash
  - gemini-2.5-flash-lite   -> "no longer available to new users"
  - gemini-2.5-pro          -> "no longer available to new users",
                                 Google suggests gemini-3.1-pro-preview
  - llama-3.3-70b-versatile -> deprecated by Groq 2026-06-17 for free/dev
                                 tier, Groq suggests openai/gpt-oss-120b

Hardcoding a model name/list separately in every call site meant each
retirement required hunting down and fixing every one of them again (this
had spread to 12+ places across the codebase). Centralizing here means a
future retirement is fixed in ONE place — or even without a code change at
all, by overriding the env var.
"""
import os


def _model_list(env_var: str, default_csv: str) -> list:
    return [m.strip() for m in os.getenv(env_var, default_csv).split(",") if m.strip()]


# Groq script/headline-generation model. llama-3.3-70b-versatile was
# deprecated for free/developer tier on 2026-06-17
# (console.groq.com/docs/deprecations); openai/gpt-oss-120b is Groq's own
# recommended replacement for it.
GROQ_SCRIPT_MODEL = os.getenv("GROQ_SCRIPT_MODEL", "openai/gpt-oss-120b")

# Gemini text-generation fallback chain (script generation, headline
# selection, etc.) — tried in order, first success wins. gemini-2.5-flash is
# the one confirmed still working in production logs as of 2026-08; 3.6-flash
# (released 2026-07-21, still listed stable by Google after 3.7's release) is
# a real second option, not a guess at a model that may not exist.
GEMINI_TEXT_MODELS = _model_list("GEMINI_TEXT_MODELS", "gemini-2.5-flash,gemini-3.6-flash")

# Gemini vision-safety/relevance-check model(s) — see media_sourcer.py.
GEMINI_VISION_MODELS = _model_list("GEMINI_VISION_MODELS", "gemini-2.5-flash")
