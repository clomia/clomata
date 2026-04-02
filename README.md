# claude-automata

English | [한국어](README.ko.md)

A system that amplifies Claude Code's autonomy.

## Installation

**[uv](https://docs.astral.sh/uv/getting-started/installation/) is required.**

```
/plugin marketplace add clomia/claude-automata
```

## Plugin - parallax

LLMs generate tokens starting from the representation space activated by their input, and as generation proceeds, prior outputs tend to constrain subsequent exploration, narrowing the exploration scope. Exploring regions the model cannot spontaneously reach therefore requires input that activates new regions.

This is one of the factors that cause people using Claude Code to be dissatisfied with single-turn output and iterate across multiple turns.

parallax generates and injects input that activates new regions, enabling the model to reach areas beyond its spontaneous reach — improving single-turn output quality.

### Usage

```
/plugin install parallax@claude-automata
```

- `/parallax off` — disable
- `/parallax on` — enable
- `/parallax` — check current status
