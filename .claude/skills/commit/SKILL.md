---
name: commit
description: 전체 변경사항을 git commit 합니다. (push 인수로 push까지 수행)
disable-model-invocation: true
model: haiku
argument-hint: "[push]"
---

별도의 지시가 없을 시 전체 변경사항을 `git commit` 을 합니다. **untracked 파일을 남기지 마세요.**
변경사항이 없는 경우 아무런 작업도 하지 말고 무시하세요.

- 커밋 형식은 [Conventional Commits 가이드](conventional-commits.md)를 따르세요.
- git 커멘드로 변경사항을 이해한 뒤 직관적인 커밋 메세지를 작성하세요.
- 커밋 메세지는 영어로 작성하세요.
- 모든 변경사항을 하나의 commit으로 묶지 않아도 됩니다.
- **인수가 `push`이면 커밋 완료 후 `git push`까지 수행합니다. (변경사항이 없는 경우 `git push`만 수행)**

인수: $ARGUMENTS

# push 수행 전 버전 수정하기 (중요)

플러그인 소스가 변경된 경우 `.claude-plugin/marketplace.json`, `해당 프로젝트의 pyproject.toml` 양쪽에서 해당 플러그인의 버전을 한단계 올려야 합니다.
버전을 변경하지 않으면 다른 사용자의 update가 작동하지 않으므로 수정사항 push 전, 반드시 버전을 변경하세요.

양쪽 파일에서 버저닝은 동일해야 합니다.
