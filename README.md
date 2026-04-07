# claude-automata

English | [한국어](README.ko.md)

Plugins that amplify Claude Code's autonomy.

## Installation

**[`uv` is required.](https://docs.astral.sh/uv/getting-started/installation/)**

```
claude plugin marketplace add clomia/claude-automata
```

## Commands

> To use in local scope, add the `--scope local` option to the command.

- Install plugin: `claude plugin install {plugin}@claude-automata`
- Update plugin: `claude plugin update {plugin}@claude-automata`
- Enable plugin: `claude plugin enable {plugin}@claude-automata`
- Disable plugin: `claude plugin disable {plugin}@claude-automata`
- Uninstall plugin: `claude plugin uninstall {plugin}@claude-automata`

# Parallax

> **Intelligence booster for complex tasks**  
> This plugin keeps Claude Code from stopping short and drives it to finish the job.

LLMs generate tokens starting from the representation space activated by their input, and the further generation proceeds, the more prior outputs tend to constrain subsequent exploration, narrowing the scope. To explore regions the model struggles to reach on its own, input that activates new regions is needed.

This tendency is one of the factors that leave people unsatisfied with single-turn results in Claude Code and lead them to iterate across multiple turns.

parallax generates and injects input that activates new regions, enabling the model to reach regions it struggles to reach on its own — improving single-turn result quality.

### Installation

```
claude plugin install parallax@claude-automata
```

### Usage

**Automatically activates when the prompt contains the `parallaxthink` keyword.**

> Example: Make a tic-tac-toe game in HTML. parallaxthink

Use the `/parallax-log` command to view the most recent parallax log.
