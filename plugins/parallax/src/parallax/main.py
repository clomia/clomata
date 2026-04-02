"""parallax — 별도 시점에서 LLM 출력을 다시 바라보고 미탐색 방향을 주입하는 Stop hook

LLM이 출력을 종료할 때마다:
1) 라운드 카운터 관리 (무한 루프 방지)
2) 별도 claude -p 호출로 출력을 훑어봄 (컨텍스트 분리)
3) 미탐색 방향이 있으면 block + 방향 주입, 없으면 종료 허용

세션의 모델을 transcript에서 자동 상속하고, effort는 항상 max를 사용한다.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from parallax.config import MAX_ROUNDS
from parallax.transcript import get_session_model


def main():
    # ── 재귀 방지: parallax의 claude -p 호출에서 이 hook이 다시 실행되면 무시 ──
    if os.environ.get("PARALLAX_ACTIVE") == "1":
        sys.exit(0)

    # ── 비활성화 체크 ──
    plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
    if plugin_data and Path(plugin_data, "disabled").exists():
        sys.exit(0)

    # ── 입력 ──
    hook_input = json.loads(sys.stdin.read())
    stop_hook_active = hook_input.get("stop_hook_active", False)
    last_msg = hook_input.get("last_assistant_message", "")
    session_id = hook_input.get("session_id", "default")
    transcript_path = hook_input.get("transcript_path", "")

    # ── 경로 ──
    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", ""))
    prompt_file = plugin_root / "prompts" / "parallax-prompt.md"

    data_dir = Path(plugin_data)
    data_dir.mkdir(parents=True, exist_ok=True)
    state_file = data_dir / f"{session_id}.json"
    log_file = data_dir / "debug.log"

    def log(msg: str) -> None:
        with open(log_file, "a") as f:
            f.write(f"[parallax] {datetime.now():%H:%M:%S} {msg}\n")

    # ── 1. 라운드 관리 ──
    if not stop_hook_active:
        state = {"round": 0}
    elif state_file.exists():
        state = json.loads(state_file.read_text())
    else:
        state = {"round": 0}

    state["round"] += 1
    round_num = state["round"]

    if round_num > MAX_ROUNDS:
        state_file.write_text(json.dumps(state))
        log(f"TERMINATE round={round_num} > max={MAX_ROUNDS}")
        sys.exit(0)

    state_file.write_text(json.dumps(state))
    log(f"round={round_num}/{MAX_ROUNDS} stop_hook_active={stop_hook_active}")

    # ── 2. 세션 설정 상속 ──
    model = get_session_model(transcript_path)
    log(f"session: model={model}")

    # ── 3. 별도 컨텍스트에서 출력 훑어보기 ──
    truncated_msg = last_msg[:2000]
    prompt_text = prompt_file.read_text()
    prompt_input = f"""{prompt_text}

---
## 에이전트의 마지막 응답:
{truncated_msg}
---
위 프로토콜에 따라 JSON으로만 응답하라. 다른 텍스트를 출력하지 마라."""

    env = {**os.environ, "PARALLAX_ACTIVE": "1"}

    cmd = ["claude", "-p", prompt_input, "--effort", "max"]
    if model:
        cmd.extend(["--model", model])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
        )
        raw_result = result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        log(f"WARN: parallax call failed: {e}")
        sys.exit(0)

    log(f"raw: {raw_result[:500]}")

    # ── 4. 결과 파싱 ──
    try:
        decision = json.loads(raw_result)
    except json.JSONDecodeError:
        match = re.search(r"\{[^}]+\}", raw_result)
        if not match:
            log("WARN: no JSON found, allowing stop")
            sys.exit(0)
        try:
            decision = json.loads(match.group())
        except json.JSONDecodeError:
            log("WARN: JSON parse failed, allowing stop")
            sys.exit(0)

    log(f"parsed json: {decision}")

    ok = decision.get("ok")
    reason = decision.get("reason", "")

    if ok is True:
        log("ALLOW: no unexplored directions")
        sys.exit(0)

    if ok is False:
        log(f"INJECT round={round_num}: direction={reason}")
        print(reason, file=sys.stderr)
        sys.exit(2)

    log("WARN: unexpected ok value, allowing stop")
    sys.exit(0)
