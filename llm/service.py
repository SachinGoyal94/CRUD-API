import json
import os
import time
from datetime import datetime
from typing import Dict, Any, Tuple

from dotenv import load_dotenv
from fastapi import HTTPException, status
from openai import OpenAI

from llm.schema import CategoryEnum, TriageResponse, UrgencyEnum

load_dotenv()

PROMPT_VERSION = "v1"
PROMPT_FILE_PATH = os.path.join("prompts", f"triage-{PROMPT_VERSION}.md")

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")
LLM_MODEL = os.getenv("LLM_MODEL", "openrouter/free")
LLM_STUB = os.getenv("LLM_STUB", "0").lower() in ("1", "true", "yes")
LLM_ENABLED = os.getenv("LLM_ENABLED", "true").lower() not in ("0", "false", "no")

LOGS_DIR = "logs"
QUARANTINE_LOG = os.path.join(LOGS_DIR, "quarantine.jsonl")
COST_LOG = os.path.join(LOGS_DIR, "llm_cost.log")


def _ensure_logs_dir():
    os.makedirs(LOGS_DIR, exist_ok=True)


def load_system_prompt() -> str:
    """Load the versioned system prompt file."""
    if os.path.exists(PROMPT_FILE_PATH):
        with open(PROMPT_FILE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return (
        "You are an AI triage assistant. Classify input into category (billing, bug, feature, other), "
        "urgency (low, normal, high), confidence (0.0-1.0), and a short reason sentence."
    )


def _clean_json_text(raw_text: str) -> str:
    """Strip markdown code fences and whitespace from model raw output."""
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _log_quarantine(user_input: str, raw_output: str, error_msg: str):
    """Write failed model responses to quarantine log."""
    _ensure_logs_dir()
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "prompt_version": PROMPT_VERSION,
        "input": user_input,
        "raw_output": raw_output,
        "error": error_msg,
    }
    with open(QUARANTINE_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _log_cost(prompt_version: str, model: str, prompt_tokens: int, completion_tokens: int, duration_ms: float, repaired: bool):
    """Log token usage and cost metrics to structured log file."""
    _ensure_logs_dir()
    log_line = (
        f"[{datetime.utcnow().isoformat()}] version={prompt_version} model={model} "
        f"input_tokens={prompt_tokens} output_tokens={completion_tokens} "
        f"duration_ms={duration_ms:.2f} repaired={repaired}\n"
    )
    with open(COST_LOG, "a", encoding="utf-8") as f:
        f.write(log_line)


def triage_message(user_text: str) -> TriageResponse:
    """
    Main triage handler:
    1. Check kill switch (LLM_ENABLED=false -> 503 fallback).
    2. Check stub mode (LLM_STUB=1 -> return fake valid response).
    3. Call LLM with 30s timeout and 1 repair retry on schema validation failure.
    """
    # 1. Kill Switch Check
    if not LLM_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM triage feature is currently disabled by kill switch",
        )

    # 2. Stub Mode Check
    if LLM_STUB:
        return TriageResponse(
            category=CategoryEnum.BUG,
            urgency=UrgencyEnum.HIGH,
            confidence=0.98,
            reason="[STUB MODE] Simulated high priority bug classification",
        )

    client = OpenAI(
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        timeout=30.0,
        max_retries=0,
    )

    system_prompt = load_system_prompt()
    start_time = time.time()

    # Attempt 1: Call Model
    try:
        completion = client.chat.completions.create(
            model=LLM_MODEL,
            temperature=0.1,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps({"text": user_text})},
            ],
        )
    except Exception as exc:
        duration_ms = (time.time() - start_time) * 1000
        if "timeout" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="LLM model request timed out after 30 seconds",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM provider error: {str(exc)}",
        )

    raw_text = completion.choices[0].message.content or ""
    cleaned_text = _clean_json_text(raw_text)

    # Validate Attempt 1
    try:
        validated = TriageResponse.model_validate_json(cleaned_text)
        duration_ms = (time.time() - start_time) * 1000
        usage = getattr(completion, "usage", None)
        p_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        c_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        _log_cost(PROMPT_VERSION, LLM_MODEL, p_tokens, c_tokens, duration_ms, repaired=False)
        return validated
    except Exception as val_error:
        # Attempt 2: Repair Retry
        repair_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps({"text": user_text})},
            {"role": "assistant", "content": raw_text},
            {
                "role": "user",
                "content": f"Your previous answer was rejected for this reason: {str(val_error)}. Return ONLY corrected raw JSON matching the schema.",
            },
        ]

        try:
            repair_completion = client.chat.completions.create(
                model=LLM_MODEL,
                temperature=0.0,
                messages=repair_messages,
            )
            repair_raw = repair_completion.choices[0].message.content or ""
            repair_cleaned = _clean_json_text(repair_raw)
            repaired_val = TriageResponse.model_validate_json(repair_cleaned)
            
            duration_ms = (time.time() - start_time) * 1000
            usage = getattr(repair_completion, "usage", None)
            p_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
            c_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
            _log_cost(PROMPT_VERSION, LLM_MODEL, p_tokens, c_tokens, duration_ms, repaired=True)
            return repaired_val
        except Exception as repair_error:
            # Failure after repair -> Quarantine and return 422
            _log_quarantine(user_text, raw_text, str(repair_error))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unprocessable Entity: LLM output failed schema validation after repair attempt: {str(repair_error)}",
            )
