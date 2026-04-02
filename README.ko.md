# claude-automata

[English](README.md) | 한국어

LLM의 entropy scope를 확장하는 Claude Code 플러그인 마켓플레이스.

## parallax 플러그인

LLM은 **entropy scope**의 한계를 가진다 — 주어진 지시의 명시적 표면 안에서만 작동하고, 그 의도를 완전히 달성하는 데 필요한 추가 고려사항들로 자발적으로 확장되지 못한다. "코드를 검수해"라고 하면 표면적인 검수만 수행하고 멈춘다. 인간이라면 메타검수, 구조 점검, 테스트 등으로 자연스럽게 확장한다.

parallax는 이 한계를 깨뜨린다. 별도 관점(별도 `claude -p` 컨텍스트)에서 에이전트의 출력을 훑어보고 미탐색 방향을 주입한다:

```
에이전트 출력 종료 → Stop hook 발동
  → parallax(별도 컨텍스트)가 출력을 훑어봄
  → 미탐색 방향이 있으면 block + 방향 주입 → 에이전트 계속 작업
  → 없거나 최대 라운드 도달 → 종료 허용
```

기존 Stop hook 구현들(ralph loop 등)과의 차이:
- **별도 관점**: 에이전트의 좁아진 entropy scope에 오염되지 않은 별도 컨텍스트에서 훑어봄
- **방향 주입**: 단순 반복 프롬프트가 아니라 미탐색 방향을 추상적으로 제시
- **반복**: 1회가 아닌 N회 라운드

## 설치

Claude Code 안에서:

```
/plugin marketplace add clomia/claude-automata
/plugin install parallax@claude-automata
```

## 전제 조건

[uv](https://docs.astral.sh/uv/) 설치 필요:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 설정

| 환경변수 | 기본값 | 설명 |
|---|---|---|
| `PARALLAX_MAX_ROUNDS` | `3` | 최대 라운드 수 |
| `PARALLAX_MODEL` | `opus` | parallax가 사용할 모델 |

예: 5라운드로 실행

```bash
PARALLAX_MAX_ROUNDS=5 claude
```

## 제거

```
/plugin uninstall parallax@claude-automata
/plugin marketplace remove claude-automata
```

## 런타임 파일

`~/.claude/plugins/data/` 하위에 세션별 상태와 디버그 로그가 저장된다.
`CLAUDE_PLUGIN_DATA`가 없는 환경에서는 프로젝트 디렉토리에 폴백:

```
.parallax-state.json
.parallax-debug.log
```
