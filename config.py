from pathlib import Path
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent

load_dotenv(ROOT / ".env")
load_dotenv(PARENT / ".env")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

if not OPENROUTER_API_KEY:
    raise RuntimeError(
        f"OPENROUTER_API_KEY not found. Put .env in either {ROOT} or {PARENT}"
    )


def get_match_llm() -> ChatOpenAI:
    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        model="anthropic/claude-3.5-sonnet",
        temperature=0.2,
    )