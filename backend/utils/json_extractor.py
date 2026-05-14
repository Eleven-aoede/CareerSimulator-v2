import json
import re
from typing import Optional


def extract_tagged_json(text: str, tag: str = "extraction") -> Optional[dict]:
    pattern = rf"<{tag}>(.*?)</{tag}>"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        return None


def strip_extraction_tag(text: str, tag: str = "extraction") -> str:
    pattern = rf"\s*<{tag}>.*?</{tag}>\s*"
    return re.sub(pattern, "", text, flags=re.DOTALL).strip()


def extract_json_from_response(text: str) -> Optional[dict]:
    """Extract JSON from LLM response that may contain markdown fences or commentary."""
    fenced = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass

    brace_depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if brace_depth == 0:
                start = i
            brace_depth += 1
        elif ch == "}":
            brace_depth -= 1
            if brace_depth == 0 and start >= 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    start = -1

    return None
