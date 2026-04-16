# claude-automata

[English](README.md) | 한국어

클로드 코드의 자율성을 증폭시키는 플러그인들

## Getting Started

**[`uv`가 필요합니다. 없다면 설치하세요.](https://docs.astral.sh/uv/getting-started/installation/)**

이 레포지토리를 마켓플레이스에 추가하세요: `claude plugin marketplace add clomia/claude-automata`

# Parallax

### [**Parallax 설계가 왜 유효한가? - 이론 문서 (theory.md)**](plugins/parallax/theory.ko.md)

Parallax 설계의 추상 원리와 이를 뒷받침하는 학술 문헌·산업 보고. Parallax를 깊이 이해하고 싶다면 먼저 읽어보세요.

[**아키텍처 다이어그램 보기**](https://mermaid.ai/live/view#pako:eNqNVttu4zYQ_RWCTwnWDiwn2nj1sIDgRZEWTdao6iAo_EJLY1m1RKokZTsb5N87Q8mOLt6ievBFOnN4ZubM2G88VgnwgBv4pwIZw7dMpFoUK8nwEpVVsirWoFeyuRNbpdmSCcOWhm7TzVJom8VZKaRlD3N69qDUzgwfPob08FFkks2VtHC0NWatjkyna3E1nUxGzPPxZer7Iza5mcyu2UJokefiOORbvBDfdx1vwVgtUNoQE0WEiaywgK9KwxAyfybIk9COoiutjQud_DDZZ6YPA5mcSrQcf_36MA_YQquitCxGGCacyZS4XCJ2m8ndCa4htk3ylPJ0ShWgMkxuvOl1jXlSKF7tQWN5R1EUuNrX_FG1LjLrCl5jH-Z4PmEisQemxYFVCGZlrUbIhHqY7YXNlGSF0LtTF1spOI5Pj2HAflH6IHTS5qghj-EYMWNK9M9KS0yzKHOwcKLIlSqp3qWTxq4KcWS3E6ZVJRPTpHU-avES1K4QKWCdDYaVkHyAFi9NTr8rkTADxpB4Qz39AEXRuKGi6rBMllWdr4aU4NsMefVrfYtkoOYKW3j2dq8bfSueu9HtyOJlNH8OGvdAk8FB6R15RYNIxDoHlqi4KvDJhZxcn-JKawqshVGHlDTEYKEo2SbLoRf5qXOow5N4pRMXRo1N1KGV2fy5Oe8P1HSJtq4f0YYuhx7p1W_R96frDh8ZoG5dfRiTTk-2hwtpfgOyx6WDW8a7NBCTCwMxaEFIXs2wdJWEY5njmJ_6bvqFI2goRf5qMtOxNF1heM7qCQ4n6-C0yyrPfyq55c8U_dVwazBVbk0bKHKLuoci8a1A_7e0NrTNLgnzXB0ab1nlBqQlJjfAlgPKDVlpQFjrXIBGhfYERcpmOn4m4Ff5t2tLjUeDbQCStYh33YCPxYHtzqg3ptIbEZ9VdeGuhTpLt5apDaOwZqmyshZo3LSmWh06ZaRL4TYL8fdpTJun8aqKcY56Rfy_O3agq71vF8rYeX1Oa9UOMicoDQPra9KQDEOg356eq_57zQ5Yuvsbo5ZuJETeGJEldUtICh_xVGcJD6yuYMQL0Gg__MrfiGDF7RYKWPEAPyawERi94iv5jmH4Q_iXUsUpEvdVuuXBRqAHR7wqE1xHzV-IMwSFgZ7TruWB7xh48MaPPJj6X24835_O7j1_Nvs88Ub8FSF32BR_4n3xbu_8W292_z7iP9yRHv4dQLR_N_W92WfPv5--_wsj4KGN)

> **복잡한 작업을 위한 지능 부스터**  
> 이 플러그인은 클로드 코드가 멈추지 않고 완벽히 끝내도록 만듭니다.

LLM은 입력이 활성화한 representation space를 기점으로 토큰을 생성하며, 토큰을 생성할수록 이전 출력이 이후 탐색을 제약하여 탐색 범위가 축소되는 경향이 있습니다. 따라서 모델이 자발적으로 도달하기 어려운 영역을 탐색하려면, 새로운 영역을 활성화하는 입력이 필요합니다.

이런 특성은 사람이 클로드 코드를 사용할 때 단일 턴의 결과에 만족하지 못하고 여러 턴을 반복하게 되는 요인 중 하나입니다.

parallax는 모델이 자발적으로 도달하기 어려운 영역에 도달할 수 있도록 새로운 영역을 활성화 하는 입력을 생성하고 주입해서 단일 턴의 결과 품질을 높입니다.

### Installation

```
claude plugin install parallax@claude-automata
```

### Usage

**프롬프트가 `parallaxthink` 키워드로 끝나면 자동으로 활성화됩니다**

> 예시: HTML로 틱택토 게임 만들어줘. parallaxthink

`/parallax-log` 커멘드로 직전에 실행된 로그를 확인할 수 있습니다.

# Appendix: Plugin Management Commands

> 커멘드에 `--scope local` 옵션을 추가하면 로컬 스코프로 동작합니다.

- 플러그인 설치: `claude plugin install {plugin}@claude-automata`
- 플러그인 삭제: `claude plugin uninstall {plugin}@claude-automata`
- 플러그인 활성화: `claude plugin enable {plugin}@claude-automata`
- 플러그인 비활성화: `claude plugin disable {plugin}@claude-automata`

### 플러그인을 최신 버전으로 업데이트하기

```
claude plugin marketplace update claude-automata
claude plugin update {plugin}@claude-automata
```
