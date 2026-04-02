# claude-automata

English | [한국어](README.ko.md)

A system that amplifies Claude's autonomy.

## parallax plugin

LLMs suffer from **entropy scope** limitations — they operate only within the explicit surface of the given instruction, unable to spontaneously expand into the additional considerations needed to fully achieve its intent. When told to "review this code," an LLM performs a surface-level review and stops. A human would naturally expand into meta-review, structural checks, testing, and more.

parallax breaks this limitation. From a separate perspective (a separate `claude -p` context), it skims the agent's output and injects unexplored directions:

```
Agent output complete → Stop hook fires
  → parallax (separate context) skims the output
  → Unexplored directions found → block + inject direction → agent continues
  → None found or max rounds reached → allow stop
```

How parallax differs from existing Stop hook implementations (e.g. ralph loop):

- **Separate perspective**: Skims from a context uncontaminated by the agent's narrowed entropy scope
- **Direction injection**: Not a repeated generic prompt, but specific unexplored directions stated abstractly
- **Iterative**: Not a single pass, but up to 7 rounds of expansion

## Install

In Claude Code:

```
/plugin marketplace add clomia/claude-automata
/plugin install parallax@claude-automata
```

## Prerequisites

[uv](https://docs.astral.sh/uv/) is required:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Usage

- `/parallax off` — disable
- `/parallax on` — enable
- `/parallax` — check current status

## How it works

- **Model**: Automatically inherits the main session's model (extracted from transcript)
- **Effort**: Always max
- **Max rounds**: 7
- Zero configuration. No environment variables.

## Uninstall

```
/plugin uninstall parallax@claude-automata
/plugin marketplace remove claude-automata
```

## Runtime files

Per-session state and debug logs are stored under `~/.claude/plugins/data/`.
