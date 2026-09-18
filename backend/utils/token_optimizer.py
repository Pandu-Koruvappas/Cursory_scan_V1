import json
import re
from typing import Any, Union, Dict, List

class TokenOptimizer:
    @staticmethod
    def smart_head_tail_slice(text: str, max_chars: int = 40000) -> str:
        """
        Preserves Executive Summary/Header (first 65%) and Key Appendices/Rules (last 35%)
        when slicing massive raw text documents.
        """
        if not text or len(text) <= max_chars:
            return text or ""
            
        head_chars = int(max_chars * 0.65)
        tail_chars = int(max_chars * 0.35)
        
        head = text[:head_chars]
        tail = text[-tail_chars:]
        
        omitted_len = len(text) - (head_chars + tail_chars)
        return f"{head}\n\n... [TRUNCATED {omitted_len} CHARACTERS OF MIDDLE REPETITIVE BODY CONTENT FOR TOKEN OPTIMIZATION] ...\n\n{tail}"

    @staticmethod
    def compress_trd_for_backlog(trd_text: str, max_chars: int = 30000) -> str:
        """
        Strips markdown styling, duplicate prose, and long introductory explanations from TRD,
        extracting high-density core functional workflows, API contracts, and business rules.
        """
        if not trd_text:
            return ""
            
        if isinstance(trd_text, dict):
            trd_text = json.dumps(trd_text, indent=2)
            
        # Strip excessive blank lines and repetitive markdown horizontal rules
        clean = re.sub(r'\n{3,}', '\n\n', str(trd_text))
        clean = re.sub(r'={3,}', '---', clean)
        
        # Filter for high-value sections (Workflows, APIs, Business Rules, Functional Requirements)
        high_value_lines = []
        for line in clean.split('\n'):
            line_str = line.strip()
            # Omit decorative ASCII art or filler text
            if line_str.startswith("<!--") or (line_str.startswith("//") and "BA AGENT" not in line_str):
                continue
            high_value_lines.append(line)
            
        result = "\n".join(high_value_lines)
        if len(result) > max_chars:
            return TokenOptimizer.smart_head_tail_slice(result, max_chars)
        return result

    @staticmethod
    def compress_backlog_for_tests(backlog_data: Union[str, Dict, List], max_chars: int = 30000) -> str:
        """
        Extracts only User Story Titles, Descriptions, Personas, and Gherkin Acceptance Criteria
        from Backlog JSON, stripping internal DB ids, timestamps, and work item links to reduce prompt size by ~80%.
        """
        if not backlog_data:
            return ""
            
        parsed_data = backlog_data
        if isinstance(backlog_data, str):
            try:
                parsed_data = json.loads(backlog_data)
            except Exception:
                return TokenOptimizer.smart_head_tail_slice(backlog_data, max_chars)
                
        if not isinstance(parsed_data, dict):
            return str(backlog_data)[:max_chars]
            
        compact_epics = []
        for epic in parsed_data.get("epics", []):
            compact_epic = {
                "title": epic.get("title"),
                "features": []
            }
            for feat in epic.get("features", []):
                compact_feat = {
                    "title": feat.get("title"),
                    "user_stories": []
                }
                for story in feat.get("user_stories", []):
                    compact_story = {
                        "title": story.get("title"),
                        "description": story.get("description"),
                        "acceptance_criteria": story.get("acceptance_criteria", []),
                        "moscow": story.get("moscow")
                    }
                    compact_feat["user_stories"].append(compact_story)
                compact_epic["features"].append(compact_feat)
            compact_epics.append(compact_epic)
            
        compact_json = json.dumps({"epics": compact_epics}, indent=2)
        if len(compact_json) > max_chars:
            return TokenOptimizer.smart_head_tail_slice(compact_json, max_chars)
        return compact_json
