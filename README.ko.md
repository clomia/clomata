# claude-automata

[English](README.md) | 한국어

클로드 코드의 자율성을 증폭시키는 시스템

## Installation

**[uv가 설치되어 있어야 합니다.](https://docs.astral.sh/uv/getting-started/installation/)**

```
claude plugin marketplace add clomia/claude-automata
```

## Plugin - parallax

> 복잡한 작업을 위한 지능 부스터

LLM은 입력이 활성화한 representation space를 기점으로 토큰을 생성하며, 토큰을 생성할수록 이전 출력이 이후 탐색을 제약하여 탐색 범위가 축소되는 경향이 있습니다. 따라서 모델이 자발적으로 도달하기 어려운 영역을 탐색하려면, 새로운 영역을 활성화하는 입력이 필요합니다.

이런 특성은 사람이 클로드 코드를 사용할 때 단일 턴의 결과에 만족하지 못하고 여러 턴을 반복하게 되는 요인 중 하나입니다.

parallax는 모델이 자발적으로 도달하기 어려운 영역에 도달할 수 있도록 새로운 영역을 활성화 하는 입력을 생성하고 주입해서 단일 턴의 결과 품질을 높입니다.

### 사용하기

```
claude plugin install parallax@claude-automata
claude plugin uninstall parallax@claude-automata # 제거
```

- `/parallax` — 활성화 여부 확인
- `/parallax on` — 활성화
- `/parallax off` — 비활성화
- `/parallax log` — 디버깅용 로그
