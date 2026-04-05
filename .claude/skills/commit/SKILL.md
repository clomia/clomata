---
name: commit
description: 전체 변경사항을 git commit 합니다. (push 인수로 push까지 수행)
disable-model-invocation: true
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
