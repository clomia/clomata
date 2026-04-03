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
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

MAX_ROUNDS = 7


# ── 데이터 타입 ──


@dataclass(frozen=True)
class HookInput:
    stop_hook_active: bool
    last_assistant_msg: str
    session_id: str
    transcript_path: str


@dataclass(frozen=True)
class Paths:
    prompt_file: Path
    state_file: Path
    log_file: Path


@dataclass(frozen=True)
class Decision:
    ok: bool
    reason: str


# ── 순수 함수 ──


def parse_hook_input(raw: str) -> HookInput:
    data = json.loads(raw)
    return HookInput(
        stop_hook_active=data.get("stop_hook_active", False),
        last_assistant_msg=data.get("last_assistant_message", ""),
        session_id=data.get("session_id", "default"),
        transcript_path=data.get("transcript_path", ""),
    )


def resolve_paths(plugin_root: str, plugin_data: str, session_id: str) -> Paths:
    data = Path(plugin_data)
    return Paths(
        prompt_file=Path(plugin_root) / "prompts" / "parallax-prompt.md",
        state_file=data / f"{session_id}.json",
        log_file=data / "debug.log",
    )


def load_round_state(raw_state: str | None, stop_hook_active: bool) -> dict:
    if stop_hook_active and raw_state is not None:
        return json.loads(raw_state)
    return {"round": 0}


def advance_round(state: dict) -> dict:
    return {**state, "round": state["round"] + 1}


def build_prompt(template: str, last_msg: str, truncate: int = 2000) -> str:
    return f"""{template}

---
## 에이전트의 마지막 응답:
{last_msg[:truncate]}
---
위 프로토콜에 따라 JSON으로만 응답하라. 다른 텍스트를 출력하지 마라."""


def build_command(prompt: str, model: str | None) -> list[str]:
    cmd = ["claude", "-p", prompt, "--effort", "max"]
    if model:
        cmd.extend(["--model", model])
    return cmd


def extract_model(transcript_lines: list[str]) -> str | None:
    model = None
    for line in transcript_lines:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = obj.get("message", {})
        if msg.get("role") == "assistant" and msg.get("model"):
            model = msg["model"]
    return model


def extract_json(raw: str) -> dict | None:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[^}]+\}", raw)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def parse_decision(raw: str) -> Decision | None:
    data = extract_json(raw)
    if data is None:
        return None
    ok = data.get("ok")
    if ok is not True and ok is not False:
        return None
    return Decision(ok=ok, reason=data.get("reason", ""))


# ── 부수효과 함수 ──


def is_recursion_guard_active() -> bool:
    return os.environ.get("PARALLAX_INSIDE_RECURSION") == "1"


def is_disabled() -> bool:
    plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
    return bool(plugin_data and Path(plugin_data, "disabled").exists())


def make_logger(log_file: Path):
    def log(msg: str) -> None:
        with open(log_file, "a") as f:
            f.write(f"[parallax] {datetime.now():%H:%M:%S} {msg}\n")

    return log


def read_lines(path: str) -> list[str]:
    if not path:
        return []
    try:
        return Path(path).read_text().splitlines()
    except OSError:
        return []


def run_claude(cmd: list[str]) -> str | None:
    env = {**os.environ, "PARALLAX_INSIDE_RECURSION": "1"}
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


# ── 오케스트레이션 ──


def main():
    if is_recursion_guard_active() or is_disabled():
        sys.exit(0)

    hook = parse_hook_input(sys.stdin.read())
    paths = resolve_paths(
        os.environ.get("CLAUDE_PLUGIN_ROOT", ""),
        os.environ.get("CLAUDE_PLUGIN_DATA", ""),
        hook.session_id,
    )
    log = make_logger(paths.log_file)

    # 라운드 관리
    raw_state = paths.state_file.read_text() if paths.state_file.exists() else None
    state = advance_round(load_round_state(raw_state, hook.stop_hook_active))
    paths.state_file.write_text(json.dumps(state))
    round_num = state["round"]

    if round_num > MAX_ROUNDS:
        log(f"TERMINATE round={round_num} > max={MAX_ROUNDS}")
        sys.exit(0)

    log(f"round={round_num}/{MAX_ROUNDS} stop_hook_active={hook.stop_hook_active}")

    # 세션 설정 상속
    model = extract_model(read_lines(hook.transcript_path))
    log(f"session: model={model}")

    # 별도 컨텍스트에서 분석
    prompt = build_prompt(paths.prompt_file.read_text(), hook.last_assistant_msg)
    raw = run_claude(build_command(prompt, model))

    if raw is None:
        log("WARN: parallax call failed")
        sys.exit(0)

    log(f"raw: {raw[:500]}")

    # 결정
    decision = parse_decision(raw)
    if decision is None:
        log("WARN: invalid response, allowing stop")
        sys.exit(0)

    log(f"parsed: ok={decision.ok} reason={decision.reason}")

    if decision.ok:
        log("ALLOW: no unexplored directions")
        sys.exit(0)

    log(f"INJECT round={round_num}: direction={decision.reason}")
    print(decision.reason, file=sys.stderr)
    sys.exit(2)
