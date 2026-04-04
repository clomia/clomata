---
name: parallax
description: parallax 플러그인 활성화/비활성화
---

`/parallax` 커맨드 인수: $ARGUMENTS

## 동작
- `off`: `${CLAUDE_PLUGIN_DATA}/disabled` 파일을 생성하여 비활성화
- `on`: `${CLAUDE_PLUGIN_DATA}/disabled` 파일을 삭제하여 활성화
- 인수 없음: `${CLAUDE_PLUGIN_DATA}/disabled` 파일 존재 여부로 현재 상태 확인

결과를 한 줄로 보고하라.
