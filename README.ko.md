# claude-automata

[English](README.md) | 한국어

클로드 코드의 자율성을 증폭시키는 시스템

## Installation

**[uv](https://docs.astral.sh/uv/getting-started/installation/) 가 설치되어 있어야 합니다.**

```
/plugin marketplace add clomia/claude-automata
```

## Plugin - parallax

LLM은 입력이 활성화한 representation space를 기점으로 토큰을 생성하며, 토큰을 생성할수록 이전 출력이 이후 탐색을 제약하여 탐색 범위가 축소되는 경향이 있습니다. 따라서 모델이 자발적으로 도달하기 어려운 영역을 탐색하려면, 새로운 영역을 활성화하는 입력이 필요합니다.

이런 특성은 클로드 코드를 사용할 때 단일 턴의 결과에 만족하지 못하고 여러 턴을 반복하게 되는 요인 중 하나입니다.

parallax는 모델이 자발적으로 도달하기 어려운 영역에 도달할 수 있도록 새로운 영역을 활성화 하는 입력을 생성하고 주입해서 단일 턴의 결과 품질을 높입니다.

### 사용하기

```
/plugin install parallax@claude-automata
```

- `/parallax off` — 비활성화
- `/parallax on` — 활성화
- `/parallax` — 현재 상태 확인
