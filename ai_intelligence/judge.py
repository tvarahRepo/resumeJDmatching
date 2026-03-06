from __future__ import annotations

from .client import OpenRouterClient
from .models import JudgeVerdict
from .utils import safe_load_json, pretty_json


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def run_judge(resume_json: dict, jd_json: dict, hmi_json: dict, match_result_json: dict, judge_model: str) -> JudgeVerdict:
    client = OpenRouterClient()

    sys_prompt = _read("ai_intelligence/prompts/judge_system.txt")
    user_prompt = _read("ai_intelligence/prompts/judge_user.txt")

    judge_schema = JudgeVerdict.model_json_schema()

    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt.format(
            resume_json=pretty_json(resume_json),
            jd_json=pretty_json(jd_json),
            hmi_json=pretty_json(hmi_json),
            match_result_json=pretty_json(match_result_json),
            judge_schema_json=pretty_json(judge_schema),
        )},
    ]

    raw = client.chat(model=judge_model, messages=messages, temperature=0.0)
    data = safe_load_json(raw)
    return JudgeVerdict(**data)