import json
import re
from typing import Any

def _fix_invalid_escapes(json_str: str) -> str:
    # Fix backslashes that are not valid JSON escape sequences: \", \\, \/, \b, \f, \n, \r, \t, \uXXXX
    return re.sub(r'\\(?![\\"/bfnrt]|u[0-9a-fA-F]{4})', r'\\\\', json_str)

def _fix_nested_stringified_json(json_str: str) -> str:
    # Fix "test_data": "{\"vehicle_type\": \"car\"}" unescaped/escaped nested double quotes in JSON
    def unquote_inner(match):
        key_part = match.group(1)
        inner_obj = match.group(2)
        clean_obj = inner_obj.replace('\\"', '"')
        return f"{key_part}: {clean_obj}"

    fixed = re.sub(r'("(?:test_data|test_inputs|payload|data|preconditions)")\s*:\s*"(?:\\")?(\s*\{[\s\S]*?\}\s*)"', unquote_inner, json_str)
    return fixed

def _fix_control_chars_in_json_strings(json_str: str) -> str:
    # Replaces unescaped raw newlines/tabs inside double-quoted string values (e.g. playwright_script)
    def replace_newlines(m):
        content = m.group(0)
        return content.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
    return re.sub(r'"(?:[^"\\]|\\.)*"', replace_newlines, json_str)

def _try_parse(text: str):
    if not text or not isinstance(text, str):
        return None

    # Pre-pass 1: Fix unescaped raw newlines/control characters inside string values
    text_fixed_ctrl = _fix_control_chars_in_json_strings(text)

    # Pre-pass 2: Fix nested unescaped quotes in test_data fields
    text_fixed_nested = _fix_nested_stringified_json(text_fixed_ctrl)

    # 1. Direct parse with strict=False
    try:
        return json.loads(text_fixed_nested, strict=False)
    except Exception:
        pass
        
    # 2. Try raw_decode from first '{' or '[' to ignore trailing conversational prose
    start_idx = text_fixed_nested.find('{')
    if start_idx == -1:
        start_idx = text_fixed_nested.find('[')
    if start_idx != -1:
        sub_str = text_fixed_nested[start_idx:]
        try:
            decoder = json.JSONDecoder(strict=False)
            obj, _ = decoder.raw_decode(sub_str)
            return obj
        except Exception:
            pass

    # 3. Fix invalid backslash escapes (e.g. C:\Users\... or \d+)
    fixed_escapes = _fix_invalid_escapes(text_fixed_nested)
    try:
        return json.loads(fixed_escapes, strict=False)
    except Exception:
        pass

    # 4. Clean trailing commas before closing brackets
    fixed_commas = re.sub(r',\s*([\}\]])', r'\1', fixed_escapes)
    try:
        return json.loads(fixed_commas, strict=False)
    except Exception:
        pass

    # 4. Handle truncated JSON payloads (auto-close open quotes and brackets)
    res = fixed_commas.strip()
    if res.startswith('{') or res.startswith('['):
        quote_count = len(re.findall(r'(?<!\\)"', res))
        if quote_count % 2 != 0:
            res += '"'
        
        res = re.sub(r',\s*$', '', res)
        open_braces = res.count('{') - res.count('}')
        open_brackets = res.count('[') - res.count(']')

        res += ']' * max(0, open_brackets)
        res += '}' * max(0, open_braces)
        
        try:
            return json.loads(res, strict=False)
        except Exception:
            pass

    return None

def extract_json_from_llm_response(res_text: Any):
    """
    Extracts and parses JSON object or array from an LLM response string.
    Handles conversational preamble, markdown code blocks, invalid backslash escapes,
    trailing commas, control characters, truncated JSON payloads, and error wrapper dicts.
    """
    if not res_text:
        return {"error": "Empty or invalid response from AI model", "raw": str(res_text)}
        
    if isinstance(res_text, dict):
        if "raw" in res_text and isinstance(res_text["raw"], str):
            recovered = extract_json_from_llm_response(res_text["raw"])
            if isinstance(recovered, (dict, list)) and "error" not in recovered:
                return recovered
        return res_text

    if not isinstance(res_text, str):
        return {"error": "Invalid response type", "raw": str(res_text)}
    
    clean = res_text.strip()
    
    # 0. Sanitize special tokens, reserved tokens, and corrupted code block headers
    # E.g. ```json BoxFitassistant<|reserved_special_token_109 -> ```json
    clean = re.sub(r"<\|[a-zA-Z0-9_\-\s:]+\|?>", "", clean)
    clean = re.sub(r"```\s*json\s*[a-zA-Z_<|]+", "```json", clean, flags=re.I)
    clean = clean.strip()

    # 1. Handle markdown code blocks (stripping any language header like ```json or ```jsoncpp,jsonc...)
    if "```" in clean:
        code_blocks = re.findall(r'```[^\n]*\n([\s\S]*?)```', clean, re.IGNORECASE)
        for block in code_blocks:
            parsed = _try_parse(block.strip())
            if parsed is not None:
                return parsed

    # 2. Direct parse
    parsed = _try_parse(clean)
    if parsed is not None:
        return parsed

    # 3. Regex extraction of JSON object {...} or array [...]
    match = re.search(r'(\[\s*\{[\s\S]*?\}\s*\]|\{[\s\S]*?\})', clean)
    if match:
        json_str = match.group(1).strip()
        parsed = _try_parse(json_str)
        if parsed is not None:
            return parsed

    # 4. Fallback regex extraction for TC-xxx blocks if structured JSON parse failed
    if "TC-" in clean or "test_case" in clean.lower():
        fallback_res = _fallback_extract_test_cases(clean)
        if fallback_res.get("test_cases") and len(fallback_res["test_cases"]) > 0:
            return fallback_res

    snippet = clean[:250].replace('\n', ' ')
    print(f"⚠️ [JSONExtractor ERROR] Failed to parse JSON from LLM response.")
    print(f"   Raw Response Snippet (first 250 chars): \"{snippet}\"")
    return {"error": "Failed to parse extracted JSON due to formatting or truncation", "raw": clean}

def _fallback_extract_test_cases(text: str) -> dict:
    if not text or not isinstance(text, str):
        return {"test_cases": [], "playwright_script": ""}

    parts = re.split(r'(?i)(?=TC-\d+)', text)
    tc_blocks = [p for p in parts if re.match(r'(?i)TC-\d+', p)]
    cases = []
    
    for block in tc_blocks:
        b_text = block.strip()
        if not b_text:
            continue

        tc_id_match = re.search(r'(TC-\d+)', b_text, re.IGNORECASE)
        tc_id = tc_id_match.group(1).upper() if tc_id_match else f"TC-{len(cases)+1:03d}"
        
        title_match = re.search(r'TC-\d+\s*(?::\s*)?([^\n]+)', b_text, re.IGNORECASE) or re.search(r'title\s*(?::\s*)?([^\n]+)', b_text, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else f"Test Case {tc_id}"
        
        prio_match = re.search(r'priority\s*(?::\s*)?(\w+)', b_text, re.IGNORECASE)
        type_match = re.search(r'type\s*(?::\s*)?(\w+)', b_text, re.IGNORECASE)
        desc_match = re.search(r'description\s*(?::\s*)?([^\n]+)', b_text, re.IGNORECASE)
        data_match = re.search(r'test\s*data\s*(?::\s*)?([^\n]+)', b_text, re.IGNORECASE)

        steps = []
        for line in b_text.split('\n'):
            step_m = re.match(r'^\s*\d+\.\s*(.+)', line)
            if step_m:
                steps.append(step_m.group(1).strip())

        cases.append({
            "test_case_id": tc_id,
            "title": title,
            "priority": prio_match.group(1) if prio_match else "High",
            "test_type": type_match.group(1) if type_match else "Functional",
            "description": desc_match.group(1) if desc_match else title,
            "test_data": data_match.group(1) if data_match else None,
            "steps": steps if steps else ["Execute test scenario per description"]
        })

    return {"test_cases": cases, "playwright_script": ""}
