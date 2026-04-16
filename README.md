# claude-automata

English | [한국어](README.ko.md)

Plugins that amplify Claude Code's autonomy.

## Getting Started

**[`uv` is required. Install it if you don't have it.](https://docs.astral.sh/uv/getting-started/installation/)**

Add this repository to the marketplace: `claude plugin marketplace add clomia/claude-automata`

# Parallax

### [**Why Parallax's Design Works — Theory Document (theory.md)**](plugins/parallax/theory.md)

Abstract principles behind Parallax's design, backed by academic literature and industry reports. Read this first if you want to understand Parallax in depth.

[**View Architecture Diagram**](https://mermaid.ai/live/view#pako:eNqNVttu4zYQ_RWCTwnWDiwn2nj1sIDgRZEWTdao6iAo_EJLY1m1RKokZTsb5N87Q8mOLt6ievBFOnN4ZubM2G88VgnwgBv4pwIZw7dMpFoUK8nwEpVVsirWoFeyuRNbpdmSCcOWhm7TzVJom8VZKaRlD3N69qDUzgwfPob08FFkks2VtHC0NWatjkyna3E1nUxGzPPxZer7Iza5mcyu2UJokefiOORbvBDfdx1vwVgtUNoQE0WEiaywgK9KwxAyfybIk9COoiutjQud_DDZZ6YPA5mcSrQcf_36MA_YQquitCxGGCacyZS4XCJ2m8ndCa4htk3ylPJ0ShWgMkxuvOl1jXlSKF7tQWN5R1EUuNrX_FG1LjLrCl5jH-Z4PmEisQemxYFVCGZlrUbIhHqY7YXNlGSF0LtTF1spOI5Pj2HAflH6IHTS5qghj-EYMWNK9M9KS0yzKHOwcKLIlSqp3qWTxq4KcWS3E6ZVJRPTpHU-avES1K4QKWCdDYaVkHyAFi9NTr8rkTADxpB4Qz39AEXRuKGi6rBMllWdr4aU4NsMefVrfYtkoOYKW3j2dq8bfSueu9HtyOJlNH8OGvdAk8FB6R15RYNIxDoHlqi4KvDJhZxcn-JKawqshVGHlDTEYKEo2SbLoRf5qXOow5N4pRMXRo1N1KGV2fy5Oe8P1HSJtq4f0YYuhx7p1W_R96frDh8ZoG5dfRiTTk-2hwtpfgOyx6WDW8a7NBCTCwMxaEFIXs2wdJWEY5njmJ_6bvqFI2goRf5qMtOxNF1heM7qCQ4n6-C0yyrPfyq55c8U_dVwazBVbk0bKHKLuoci8a1A_7e0NrTNLgnzXB0ab1nlBqQlJjfAlgPKDVlpQFjrXIBGhfYERcpmOn4m4Ff5t2tLjUeDbQCStYh33YCPxYHtzqg3ptIbEZ9VdeGuhTpLt5apDaOwZqmyshZo3LSmWh06ZaRL4TYL8fdpTJun8aqKcY56Rfy_O3agq71vF8rYeX1Oa9UOMicoDQPra9KQDEOg356eq_57zQ5Yuvsbo5ZuJETeGJEldUtICh_xVGcJD6yuYMQL0Gg__MrfiGDF7RYKWPEAPyawERi94iv5jmH4Q_iXUsUpEvdVuuXBRqAHR7wqE1xHzV-IMwSFgZ7TruWB7xh48MaPPJj6X24835_O7j1_Nvs88Ub8FSF32BR_4n3xbu_8W292_z7iP9yRHv4dQLR_N_W92WfPv5--_wsj4KGN)

> **Intelligence booster for complex tasks**  
> This plugin keeps Claude Code from stopping short and drives it to finish the job.

LLMs generate tokens starting from the representation space activated by their input, and the further generation proceeds, the more prior outputs tend to constrain subsequent exploration, narrowing its scope. Therefore, to explore regions the model struggles to reach on its own, input that activates new regions is needed.

This tendency is one of the factors that leave people unsatisfied with single-turn results in Claude Code and lead them to iterate across multiple turns.

parallax generates and injects input that activates new regions, enabling the model to reach regions it struggles to reach on its own — improving single-turn result quality.

### Installation

```
claude plugin install parallax@claude-automata
```

### Usage

**Automatically activates when the prompt ends with the `parallaxthink` keyword**

> Example: Make a tic-tac-toe game in HTML. parallaxthink

parallax operates based on the current prompt without prior context. It is therefore most effective when used at the start of a session.

After use, run `/parallax-log` to see what regions parallax surfaced.

# Appendix: Plugin Management Commands

> To use in local scope, add the `--scope local` option to the command.

- Install plugin: `claude plugin install {plugin}@claude-automata`
- Uninstall plugin: `claude plugin uninstall {plugin}@claude-automata`
- Enable plugin: `claude plugin enable {plugin}@claude-automata`
- Disable plugin: `claude plugin disable {plugin}@claude-automata`

### Updating plugins to the latest version

```
claude plugin marketplace update claude-automata
claude plugin update {plugin}@claude-automata
```
