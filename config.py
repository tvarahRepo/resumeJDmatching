import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from mistralai import Mistral

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

def get_match_llm():

    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        model="anthropic/claude-3.5-sonnet",
        temperature=0.2
    )


def get_judge_llm():

    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        model="openai/gpt-4o-mini",
        temperature=0
    )


def get_mistral_client():

    return Mistral(api_key=MISTRAL_API_KEY)