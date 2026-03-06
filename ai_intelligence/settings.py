from __future__ import annotations
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AIIntelligenceSettings:
    # OpenRouter
    openrouter_base_url: str
    match_model: str
    judge_model: str

    # runtime knobs
    temperature: float
    max_retries: int


def _get_env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def _get_env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def load_settings() -> AIIntelligenceSettings:
    """
    Priority order (so we align with your existing codebase):
    1) Try importing from src.config (shared pipeline)
    2) Try importing from ResumeParserAgent.config (standalone agent)
    3) Fall back to ENV variables
    4) Fall back to minimal defaults (only if nothing else available)
    """

    # --- 1) src.config (preferred) ---
    try:
        import src.config as cfg  # type: ignore

        # These attribute names may vary across repos.
        # We try common ones; if missing we fall through to env defaults.
        base_url = getattr(cfg, "OPENROUTER_BASE_URL", None) or getattr(cfg, "openrouter_base_url", None)
        match_model = getattr(cfg, "MATCH_MODEL", None) or getattr(cfg, "OPENROUTER_MATCH_MODEL", None)
        judge_model = getattr(cfg, "JUDGE_MODEL", None) or getattr(cfg, "OPENROUTER_JUDGE_MODEL", None)
        temperature = getattr(cfg, "TEMPERATURE", None)
        max_retries = getattr(cfg, "MAX_RETRIES", None)

        if match_model and judge_model:
            return AIIntelligenceSettings(
                openrouter_base_url=base_url or "https://openrouter.ai/api/v1",
                match_model=str(match_model),
                judge_model=str(judge_model),
                temperature=float(temperature) if temperature is not None else _get_env_float("TEMPERATURE", 0.2),
                max_retries=int(max_retries) if max_retries is not None else _get_env_int("MAX_RETRIES", 2),
            )
    except Exception:
        pass

    # --- 2) ResumeParserAgent.config (backup) ---
    try:
        import ResumeParserAgent.config as cfg  # type: ignore

        base_url = getattr(cfg, "OPENROUTER_BASE_URL", None) or getattr(cfg, "openrouter_base_url", None)
        match_model = getattr(cfg, "MATCH_MODEL", None) or getattr(cfg, "OPENROUTER_MATCH_MODEL", None)
        judge_model = getattr(cfg, "JUDGE_MODEL", None) or getattr(cfg, "OPENROUTER_JUDGE_MODEL", None)
        temperature = getattr(cfg, "TEMPERATURE", None)
        max_retries = getattr(cfg, "MAX_RETRIES", None)

        if match_model and judge_model:
            return AIIntelligenceSettings(
                openrouter_base_url=base_url or "https://openrouter.ai/api/v1",
                match_model=str(match_model),
                judge_model=str(judge_model),
                temperature=float(temperature) if temperature is not None else _get_env_float("TEMPERATURE", 0.2),
                max_retries=int(max_retries) if max_retries is not None else _get_env_int("MAX_RETRIES", 2),
            )
    except Exception:
        pass

    # --- 3) Environment variables ---
    env_base = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    env_match = os.getenv("OPENROUTER_MATCH_MODEL") or os.getenv("MATCH_MODEL")
    env_judge = os.getenv("OPENROUTER_JUDGE_MODEL") or os.getenv("JUDGE_MODEL")

    # --- 4) Minimal defaults (only used if env/config do not provide models) ---
    return AIIntelligenceSettings(
        openrouter_base_url=env_base,
        match_model=env_match or "anthropic/claude-3.5-sonnet",
        judge_model=env_judge or "openai/gpt-4o-mini",
        temperature=_get_env_float("TEMPERATURE", 0.2),
        max_retries=_get_env_int("MAX_RETRIES", 2),
    )