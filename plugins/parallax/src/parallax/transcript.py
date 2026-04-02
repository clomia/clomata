"""Transcript 파싱 유틸리티"""

import json


def get_session_model(path: str) -> str | None:
    """Transcript JSONL에서 세션 모델을 추출"""
    model = None
    if not path:
        return model
    try:
        with open(path) as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = obj.get("message", {})
                if msg.get("role") == "assistant" and msg.get("model"):
                    model = msg["model"]
    except OSError:
        pass
    return model
