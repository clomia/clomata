# clomata

Stop hook 기반 감독관 플러그인. 수행자가 완료를 선언할 때마다 독립적으로 평가하여 미탐색 방향을 반복 주입한다.

## 작동 원리

```
수행자 작업 완료 → Stop hook 발동
  → 감독관(별도 컨텍스트)이 작업 평가
  → 부족하면 block + 방향 제시 → 수행자 계속 작업
  → 충분하거나 최대 라운드 도달 → 종료 허용
```

기존 Stop hook 구현들과의 차이:
- **반복 평가**: 1회가 아닌 N회 라운드 평가
- **방향 제시**: 단순 품질 게이트가 아니라 미탐색 방향을 추상적으로 제시
- **컨텍스트 분리**: 감독관은 수행자의 전체 추론을 보지 않고 독립적으로 사고

## 설치

```bash
git clone https://github.com/clomia/clomata.git ~/.claude/clomata
```

## 사용

```bash
claude --plugin-dir ~/.claude/clomata
```

환경변수로 라운드 수를 조정할 수 있다:

```bash
CLOMATA_MAX_ROUNDS=5 claude --plugin-dir ~/.claude/clomata
```

## 설정

| 환경변수 | 기본값 | 설명 |
|----------|--------|------|
| `CLOMATA_MAX_ROUNDS` | `3` | 최대 평가 라운드 수 |
| `CLOMATA_MODEL` | `opus` | 감독관이 사용할 모델 |

## 런타임 파일

프로젝트 디렉토리에 생성된다. `.gitignore`에 추가를 권장:

```
.clomata-state.json
.clomata-debug.log
```
