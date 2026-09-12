import json
import os
import sys

# Ensure CRUD API folder is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from llm.service import triage_message, PROMPT_VERSION, LLM_MODEL

EVAL_CASES_FILE = os.path.join(os.path.dirname(__file__), "cases.json")


def run_evaluation():
    print("=" * 60)
    print(f"Running Evaluation Set - Prompt Version: {PROMPT_VERSION} | Model: {LLM_MODEL}")
    print("=" * 60)

    if not os.path.exists(EVAL_CASES_FILE):
        print(f"Error: Eval cases file not found at {EVAL_CASES_FILE}")
        return

    with open(EVAL_CASES_FILE, "r", encoding="utf-8") as f:
        cases = json.load(f)

    total = len(cases)
    passed = 0

    for case in cases:
        case_id = case["id"]
        text = case["text"]
        expected_cat = case["expected_category"]
        expected_urgency = case.get("expected_urgency")

        try:
            res = triage_message(text)
            actual_cat = res.category.value if hasattr(res.category, "value") else str(res.category)
            actual_urgency = res.urgency.value if hasattr(res.urgency, "value") else str(res.urgency)

            match = (actual_cat == expected_cat)
            if match:
                passed += 1
                status_str = "PASS"
            else:
                status_str = "FAIL"

            print(f"Case #{case_id} [{status_str}]:")
            print(f"  Input:    '{text}'")
            print(f"  Expected: category={expected_cat}, urgency={expected_urgency}")
            print(f"  Actual:   category={actual_cat}, urgency={actual_urgency}, confidence={res.confidence:.2f}")
            print(f"  Reason:   {res.reason}")
            print("-" * 60)

        except Exception as exc:
            print(f"Case #{case_id} [ERROR]: {str(exc)}")
            print("-" * 60)

    score_pct = (passed / total) * 100 if total > 0 else 0
    print("=" * 60)
    print(f"Evaluation Results: {passed}/{total} passed ({score_pct:.1f}%)")
    print("=" * 60)


if __name__ == "__main__":
    run_evaluation()
