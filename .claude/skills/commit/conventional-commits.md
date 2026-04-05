# Conventional Commits 가이드

## 기본 구조

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

## 커밋 타입

### 필수 타입

- **feat**: 새로운 기능 추가
- **fix**: 버그 수정

### 권장 추가 타입

- **build**: 빌드 시스템 또는 외부 종속성 변경
- **chore**: 코드 수정 없는 설정 변경
- **ci**: CI 설정 파일 및 스크립트 변경
- **docs**: 문서만 변경
- **style**: 코드 의미에 영향 없는 변경 (공백, 포맷팅, 세미콜론 등)
- **refactor**: 버그 수정이나 기능 추가가 아닌 코드 변경
- **perf**: 성능 개선
- **test**: 테스트 추가 또는 수정
- **revert**: 이전 커밋 되돌리기

## 작성 규칙

### 필수 규칙

1. 타입 다음에는 콜론(:)과 공백이 **반드시** 와야 함
2. 설명(description)은 타입/스코프 접두사 뒤에 **즉시** 작성
3. 설명은 코드 변경 사항의 짧은 요약

### 선택 규칙

1. **scope**: 타입 뒤에 괄호로 감싸서 추가 가능
   - 예: `feat(parser): add ability to parse arrays`
   - 코드베이스의 특정 섹션을 나타내는 명사 사용

2. **body**: 설명 다음 한 줄 공백 후 작성
   - 변경 사항의 추가 맥락 정보 제공
   - 여러 단락 가능

3. **footer**: 본문 다음 한 줄 공백 후 작성
   - 형식: `<token>: <value>` 또는 `<token> #<value>`
   - 토큰의 공백은 `-`로 대체 (예: `Reviewed-by`)

## Breaking Change 표시

Breaking change는 두 가지 방법으로 표시 가능:

### 방법 1: 느낌표(!) 사용

```
feat!: send email when product shipped
feat(api)!: change authentication method
```

### 방법 2: BREAKING CHANGE 푸터

```
feat: allow config object to extend others

BREAKING CHANGE: extends key now used for extending config files
```

### 방법 3: 둘 다 사용

```
chore!: drop Node 6 support

BREAKING CHANGE: use JavaScript features not available in Node 6
```

## 예시

### 간단한 커밋

```
fix: array parsing issue with multiple spaces
docs: correct spelling of CHANGELOG
feat(lang): add Polish language
```

### 본문 포함 커밋

```
fix: prevent racing of requests

Introduce a request id and reference to latest request.
Dismiss incoming responses other than from latest request.

Remove obsolete timeouts.
```

### 푸터 포함 커밋

```
fix: prevent racing of requests

Introduce request id to track latest request.

Reviewed-by: Alice
Refs: #123
```

### 리버트 커밋

```
revert: let us never speak of the noodle incident

Refs: 676104e, a215868
```

## 주의사항

1. 대소문자는 일관성 있게 사용 (BREAKING CHANGE는 예외로 대문자 필수)
2. 하나의 커밋은 하나의 논리적 변경사항만 포함
3. 타입이 명확하지 않으면 가장 적합한 것 선택
4. 초기 개발 단계에서도 규칙 준수 권장

## 시맨틱 버저닝 연관성

- **fix** → PATCH 릴리스 (0.0.X)
- **feat** → MINOR 릴리스 (0.X.0)
- **BREAKING CHANGE** → MAJOR 릴리스 (X.0.0)
