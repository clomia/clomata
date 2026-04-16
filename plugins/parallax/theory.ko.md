# Parallax 작동 이론

이 문서는 Parallax가 왜 효과적인지를 설명한다. 본문은 두 층으로 나뉜다. 앞의 **설계** 부분은 Parallax가 무엇을 하는지를 추상 수준에서 짧게 기술하고, 뒤의 **근거** 부분은 그 설계가 작동한다는 사실을 학술 문헌과 산업 보고로 구체적으로 뒷받침한다.

## 1. 설계

Parallax는 메인 에이전트의 출력을 평가·수정하는 **비평자**가 아니라, 메인 에이전트가 고려하지 못한 영역을 surface하여 다음 라운드 생성의 representation 출발점을 옮기는 **Advisor**(조언가)이다. 비평자는 "이것이 틀렸으니 고쳐라"라고 말하고, Advisor는 "이 영역도 생각해 보라"고 말한다. 전자는 출력의 옳고 그름에 대한 판단을 누적시키고, 후자는 다음 라운드가 출발할 representation의 활성화 위치를 옮긴다. 이 구분은 코드와 프롬프트에 직접 새겨져 있다. `prompts/role.md`는 Advisor를 "an advisory agent that surfaces regions the main agent has not considered"로 정의하고, `prompts/instruction.md`는 "Only raise the issue. The main agent finds the answer"라고 명시한다.

Parallax는 다음 네 가지 추상 원칙을 동시에 구현하는 외부 Advisor 루프이다.

1. **격리된 Advisor.** 메인 에이전트와 동일한 모델을 가진 별개 컨텍스트가 매 라운드 새로 생성되어 다음 라운드에 surface할 영역을 결정한다. Advisor는 메인 에이전트의 출력 분포에도, 직전 라운드 자기 출력에도 묶이지 않는다.
2. **거리 누적의 다양성 탐색.** Advisor는 이전 라운드에서 surface된 모든 영역을 입력으로 받고, 다음 surface 대상은 그 집합으로부터 가장 먼 것이어야 한다는 제약을 받는다. 다양성은 학습이 아니라 입력 조건과 프롬프트 지시로 달성된다.
3. **추상 수준의 영역.** 메인 에이전트에 주입되는 것은 무엇을 어떻게 하라는 지시가 아니라, 무엇을 더 생각해 볼 것인지의 영역이다. 영역은 다음 생성의 활성화를 옮길 뿐, 구체적 행동을 결정하지 않는다. 자율적 추론이 보존된다.
4. **정보 변환 계층.** 메인 에이전트의 원시 행동 기록(JSON)은 사용자가 터미널에서 관찰하는 수준의 마크다운 서사로 변환되어 Advisor에게 전달된다. Advisor는 사용자와 같은 추상 수준에서 다음 영역을 결정한다.

루프 종료는 고정된 라운드 한계와, Advisor가 출력하는 전용 종료 토큰의 두 신호로 결정된다. 도메인별 수렴 메트릭을 요구하지 않는다.

## 2. 근거

### 2.1. 자기회귀 생성 자체가 탐색을 좁힌다

순차적 토큰 생성은 이전 출력이 이후의 representation을 강하게 제약하여, 모델이 자력으로는 다른 영역으로 옮겨 가지 못하게 만든다. 이 한계는 단순한 디코딩 휴리스틱 문제가 아니라 구조적 현상으로 보고된다.

[**Tree of Thoughts: Deliberate Problem Solving with Large Language Models** (Yao et al., NeurIPS 2023)](https://arxiv.org/abs/2305.10601)는 GPT-4가 표준 chain-of-thought로는 Game of 24를 4% 해결하는 데 그쳤지만, 트리 기반 탐색을 외부에서 부과하면 같은 모델이 74%까지 도달함을 보였다. 동일한 모델, 동일한 가중치에서 차이를 만든 것은 토큰 생성 흐름을 강제로 분기시키는 외부 구조였다.

[**How Language Model Hallucinations Can Snowball** (Zhang et al., 2023)](https://arxiv.org/abs/2305.13534)은 더 미시적인 증거를 제공한다. ChatGPT와 GPT-4는 자기 출력을 별도로 검사하면 자신의 오류를 67%, 87% 식별하지만, 생성 도중에는 초기 오류에 과잉 commit하여 그 위에 거짓을 쌓는다. 즉 모델은 옳고 그름을 분간하는 능력이 있어도, 생성 흐름 안에서는 그 능력에 접근하지 못한다.

[**Verbalized Sampling: How to Mitigate Mode Collapse and Unlock LLM Diversity** (Zhang et al., 2025)](https://arxiv.org/abs/2510.01171)는 정렬 학습이 LLM의 출력 분포를 좁히는 mode collapse를 정량화하고, 단순한 추론 시점 프롬프트만으로 다양성을 1.6–2.1배 회복할 수 있음을 보였다. 다양성 손실의 원인이 가중치가 아니라 활성화 패턴에 있으며, 입력 조건만으로 부분적으로 되돌릴 수 있다는 의미이다.

[**The Road Less Traveled: Enhancing Exploration in LLMs via Sequential Sampling** (2025)](https://arxiv.org/abs/2510.15502)는 병렬 샘플링이 같은 분포에서 반복 추출되어 다양성을 잃는 문제를 지적하고, **이전 출력을 다음 입력의 조건으로 누적시키는** sequential sampling이 더 넓은 탐색을 만든다는 결과를 냈다. Parallax의 region history 누적은 이 원리를 다중 턴 에이전트 작업에 옮긴 형태이다.

이 네 결과는 한 방향을 가리킨다. 모델이 자력으로 활성화하지 못하는 영역으로 가려면 외부 신호가 입력으로 들어와야 한다.

### 2.2. 모델은 스스로 새 영역을 surface하지 못한다

Advisor가 왜 메인 에이전트와 분리된 별개 컨텍스트여야 하는가에 대한 직접적 증거다. 같은 컨텍스트가 자기 자신에게 새 영역 신호를 부여하려고 시도할 때 무엇이 실패하는지를 보여 주는 결과들이다.

[**Large Language Models Cannot Self-Correct Reasoning Yet** (Huang et al., ICLR 2024)](https://arxiv.org/abs/2310.01798)는 외부 피드백이나 oracle 정보가 없는 상태에서의 intrinsic self-correction이 추론 과제에서 효과가 없거나 오히려 성능을 저하시킨다는 것을 여러 벤치마크에서 보였다. 같은 컨텍스트가 자기 출력에 대해 새 방향의 신호를 만들어 내는 시도는 신뢰할 수 없다. 자기 수정뿐 아니라 자기 surface — 즉 스스로 고려하지 못한 영역을 스스로 식별하는 시도 — 도 같은 한계 아래 있다.

[**Towards Understanding Sycophancy in Language Models** (Sharma et al., Anthropic, ICLR 2024)](https://arxiv.org/abs/2310.13548)은 보조적 증거를 제공한다. 다섯 개의 state-of-the-art 어시스턴트가 일관되게 sycophantic 응답을 보였고, 인간과 preference model 모두 "convincingly-written sycophantic responses over correct ones"를 무시할 수 없는 비율로 선호했다. 같은 컨텍스트 안에서 발생하는 자기 surface는 자기 출력에 대한 동조 압력에 노출되어 새 영역으로의 이동에 실패한다.

Parallax가 Advisor를 별도 `claude -p` 프로세스로 분리하고 매 라운드 컨텍스트를 초기화하는 이유는 이 두 결과를 우회하기 위함이다. Advisor는 메인 에이전트의 자기 출력 분포에서 기인한 sycophancy도, 자기 답에 대한 commitment도 가지지 않은 채 다음 영역을 결정한다.

### 2.3. 확신이 형성되면 자기 반성으로는 새 사고가 나오지 않는다

[**Encouraging Divergent Thinking in Large Language Models through Multi-Agent Debate** (Liang et al., EMNLP 2024)](https://arxiv.org/abs/2305.19118)는 Degeneration-of-Thought (DoT) 문제를 정식화했다. 일단 모델이 자기 답에 확신을 형성하면 이후의 자기 반성으로는 새로운 사고를 만들어 내지 못한다는 것이다. 자기 자신을 새 영역으로 옮기지 못한다는 더 직접적 진술이다. 저자들의 해법은 입장이 다른 다수의 에이전트가 tit-for-tat 토론을 벌이고 별도의 judge가 결론을 내는 multi-agent debate였다.

DoT는 Parallax 설계의 핵심 결정 한 가지를 정당화한다. Advisor가 매 라운드 새로 시작되는 컨텍스트여야 한다는 것. 이전 라운드의 Advisor가 surface해 둔 영역에 대한 확신은 다음 라운드 Advisor에 전이되지 않으며, 메인 에이전트가 누적한 확신과도 격리된다. Advisor의 컨텍스트는 매 라운드 영역 후보 공간 전체에 대해 평평하게 시작한다.

### 2.4. 외부에서 들어오는 입력은 다음 생성을 옮긴다

자기 surface는 실패하지만, 외부에서 새로 들어오는 입력은 일관되게 다음 생성을 다른 영역으로 옮긴다. 선행 연구의 다수는 이 입력을 "비평"이나 "피드백"으로 부르지만, 메커니즘적으로 그것이 작동하는 이유는 입력이 다음 생성의 조건이 되기 때문이다. Parallax는 이 메커니즘 자체를 차용하되, 입력의 내용을 옳고 그름의 판단이 아닌 영역의 surface로 둔다.

[**Self-Refine: Iterative Refinement with Self-Feedback** (Madaan et al., NeurIPS 2023)](https://arxiv.org/abs/2303.17651)은 같은 모델이 생성·피드백·수정 역할을 모두 맡는 단순한 루프만으로도 7개 과제에 걸쳐 평균 약 20% 절대 개선을 얻었다. 도구나 학습이 없어도 다음 라운드 입력으로 자기 출력에 대한 언급을 덧붙이는 것만으로 출력이 옮겨진다. 다만 Huang et al.의 결과와 합쳐 보면 같은 컨텍스트 안의 자기 피드백은 추론 의존도가 낮은 과제에 한정되며, 추론 과제로 일반화되지 않는다.

[**Reflexion: Language Agents with Verbal Reinforcement Learning** (Shinn et al., NeurIPS 2023)](https://arxiv.org/abs/2303.11366)은 에피소드 실패 후의 언어적 반성을 메모리에 저장해 다음 시도에서 활용하는 방식으로, 가중치 갱신 없이도 코딩·순차 의사결정·추론 과제에서 큰 폭의 개선을 보였다. HumanEval에서 91% pass@1을 달성해 GPT-4의 80%를 11퍼센트포인트 앞섰다. 외부 환경 신호를 언어로 변환해 컨텍스트에 누적시키는 구조가 다음 시도를 다른 영역으로 옮긴다. Parallax의 region history 누적은 이 아이디어를 실패 사후 반성이 아닌 사전 영역 surface로 옮긴 변형이다.

[**CRITIC: Large Language Models Can Self-Correct with Tool-Interactive Critiquing** (Gou et al., ICLR 2024)](https://arxiv.org/abs/2305.11738)은 모델의 평가가 외부 도구(검색·코드 실행 등)와 결합될 때 자기 수정이 비로소 작동한다는 것을 보였다. 외부 도구가 같은 모델로는 도달하지 못하는 신호를 입력에 더해 주는 역할을 한 셈이다. Parallax의 Advisor에게 `Read, Glob, Grep` 같은 조사 도구를 허용한 결정(`src/main.py`의 `DISALLOWED_TOOLS = "Bash,Write,Edit,NotebookEdit"` 화이트리스트 반전)은 이 결과에 부합한다. Advisor가 코드베이스를 직접 확인한 뒤 surface하므로, 단순한 추측이 아닌 코드베이스 사실에 근거한 영역을 메인 에이전트에 전달한다.

[**Constitutional AI: Harmlessness from AI Feedback** (Bai et al., 2022)](https://arxiv.org/abs/2212.08073)는 한 모델이 다른 모델(또는 자기 자신의 별개 호출)의 출력에 대해 일련의 원칙을 적용해 새 출력을 만드는 구조가 학습 신호로 충분히 강력함을 보였다. 다른 컨텍스트에서 만들어진 입력이 가중치 학습마저 견인한다는 산업 규모의 검증이며, 같은 메커니즘을 추론 시점에서 활용하는 것이 Parallax의 위치다.

이 네 결과를 종합하면, 외부에서 또는 격리된 컨텍스트에서 들어오는 입력 자체가 다음 생성을 옮기는 강력한 자원이다. Parallax가 메인 에이전트 옆에 별개 Advisor를 두는 결정은 이 흐름의 직접적 적용이며, 다만 입력의 의미를 평가에서 영역 surface로 바꾼 것이다.

### 2.5. 관찰은 생성보다 쉽다는 비대칭성

Advisor가 메인 에이전트와 같은 모델인데 어떻게 메인이 놓친 영역을 식별하는가에 대한 답이 여기 있다. 선행 연구는 이 비대칭성을 검증과 생성의 분리로 정식화하지만, 같은 비대칭성은 영역 식별과 영역 내부 행동 생성 사이에서도 성립한다.

[**Let's Verify Step by Step** (Lightman, Cobbe et al., OpenAI, 2023)](https://arxiv.org/abs/2305.20050)는 답의 옳음을 평가하는 것이 그 답을 생성하는 것보다 구조적으로 다른 작업이며, 단계별 검증으로 학습된 process reward model이 outcome 기반 reward model을 큰 차이로 능가함을 보였다. 출력에 대한 외부 검증은 생성과 별개의 능력이다.

[**Scaling LLM Test-Time Compute Optimally can be More Effective than Scaling Model Parameters** (Snell et al., 2024)](https://arxiv.org/abs/2408.03314)은 추론 시점에 compute를 더 쓰는 것이 모델 크기를 키우는 것보다 효과적일 수 있음을 정량화했다. 적절한 전략에서 같은 base 모델을 14배 큰 모델보다 우위에 올렸다("test-time compute can be used to outperform a 14x larger model"). 외부에서 다시 보는 추론 시점 루프 자체가 모델 capacity와 교환 가능한 자원이라는 의미다.

비대칭성은 Parallax에서 두 가지 함의를 갖는다. 첫째, 같은 모델이라도 격리된 컨텍스트에서 행동 기록을 외부 시선으로 다시 볼 때, 생성 위치에서는 활성화되지 않았던 영역을 식별해 낸다. 둘째, parallax 라운드를 추가하는 것은 단순한 반복이 아니라 추론 시점 compute를 비대칭적으로 활용하는 행위다.

### 2.6. 다양성 있는 탐색이 더 나은 답을 만든다

거리 누적 다양성이 왜 정답률을 높이는가에 대한 직접 증거다.

[**Self-Consistency Improves Chain of Thought Reasoning in Language Models** (Wang et al., ICLR 2023)](https://arxiv.org/abs/2203.11171)은 단일 chain-of-thought 대신 다양한 reasoning path를 샘플링하고 majority vote를 취하는 단순한 변경만으로 GSM8K에서 +17.9%, SVAMP에서 +11.0%, AQuA에서 +12.2%의 개선을 얻었다. 동일 모델·동일 컨텍스트에서 단지 탐색 다양성을 늘린 결과다.

[**Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models** (Zhou et al., ICML 2024)](https://arxiv.org/abs/2310.04406)은 MCTS를 LLM 에이전트 위에 얹어 HumanEval에서 GPT-4 기준 92.7% pass@1을 기록했다. 트리 탐색이 단일 경로 생성을 넘어서는 효과가 도구 사용 에이전트로도 일반화됨을 보였다.

[**Diverse Beam Search: Decoding Diverse Solutions from Neural Sequence Models** (Vijayakumar et al., 2016)](https://arxiv.org/abs/1610.02424)은 표준 빔 서치가 거의 동일한 시퀀스를 반복 생성하는 현상을 지적하고, 다양성을 명시적 목적으로 부과해야 의미 있는 후보 집합이 나온다는 점을 일찍부터 보였다. 다양성은 우연이 아니라 명시적 제약으로만 확보된다.

[**ThoughtProbe: Classifier-Guided Thought Space Exploration** (2025)](https://arxiv.org/abs/2510.27355)는 LLM의 hidden representation에 다양한 reasoning 분기를 식별할 수 있는 구별 신호가 잠재해 있고, 이를 트리 탐색의 가지치기 기준으로 활용할 수 있음을 보였다. 다양성 탐색이 random 시도가 아니라 모델 내부 신호로 지도될 수 있다는 의미다.

Parallax는 학습이나 트리 자료구조를 도입하지 않고, 단지 region history를 Advisor 입력의 일부로 누적시키고 "기존과 가장 먼 것을 고르라"는 자연어 제약(`prompts/instruction.md`의 "The farther it is from regions already considered, the more valuable it is")을 부과해 같은 효과를 다중 턴 에이전트 위에서 얻는다.

### 2.7. 다중 에이전트 협업이 단일 에이전트를 능가한다

Parallax가 Advisor를 별개 에이전트로 두는 거시적 정당화다.

[**How we built our multi-agent research system** (Anthropic, 2025)](https://www.anthropic.com/engineering/multi-agent-research-system)은 Claude Opus 4 lead와 Claude Sonnet 4 subagent로 구성된 다중 에이전트 시스템이 단일 Opus 4 대비 내부 research 평가에서 90.2% 개선을 보였다고 보고했다. 같은 모델 패밀리라도 역할을 분리해 병렬화하면 단일 컨텍스트보다 큰 성능이 나온다는 산업 규모의 증거다.

[**Mixture-of-Agents Enhances Large Language Model Capabilities** (Wang et al., 2024)](https://arxiv.org/abs/2406.04692)는 LLM이 다른 LLM의 출력을 보조 정보로 받을 때 더 높은 품질을 생성하는 inherent collaborativeness 현상을 정식화했다. 오픈소스 모델로 구성된 MoA가 AlpacaEval 2.0에서 GPT-4 Omni를 65.1% 대 57.5%로 능가했다. 메인 에이전트와 Advisor가 같은 모델 가족이어도 격리된 호출의 출력을 합성하는 구조가 가치를 만든다.

[**AI safety via debate** (Irving, Christiano, Amodei, 2018)](https://arxiv.org/abs/1805.00899)는 두 에이전트의 zero-sum debate가 단일 에이전트의 직접 판단보다 이론적으로 더 넓은 진리 공간을 식별할 수 있음을 보였다. 다중 에이전트가 단일 에이전트의 능력 한계를 우회하는 구조적 메커니즘이 있다는 초기 정당화다.

[**AgentCoder: Multi-Agent-based Code Generation with Iterative Testing and Optimisation** (Huang et al., 2023)](https://arxiv.org/abs/2312.13010)는 코더, 테스트 설계자, 테스트 실행자를 분리한 구조가 GPT-3.5에서 HumanEval-ET 77.4%, MBPP-ET 89.1% pass@1을 기록해 SOTA 단일 에이전트(각 69.5%, 63.0%)를 큰 폭으로 앞섰다. 코드 작업에서 평가·검증 역할을 별개 에이전트로 분리하는 것의 구체적 효과를 보여 준다. Parallax는 같은 분리 구조를 채용하되 별개 에이전트의 역할을 평가가 아닌 영역 surface로 둔다.

### 2.8. 추상적 가이드가 자율성을 보존하면서 행동을 바꾼다

Parallax가 구체적 지시 대신 영역만 surface하는 결정의 정당화다.

[**Decision-Time Guidance: Keeping Replit Agent Reliable** (Replit, 2025)](https://blog.replit.com/decision-time-guidance)은 정적 시스템 프롬프트에 모든 규칙을 미리 적재하면 컨텍스트가 오염되고 우선순위 모호성이 커진다는 문제를 보고했다. 같은 가이드를 트레이스 끝(결정 시점)에 짧게 주입하면 시스템 프롬프트에 둘 때보다 루프당 도구 호출이 15% 늘어났다("injecting a short prompt at the bottom of the trace led the agent to execute 15% more tools per loop than placing the same guidance in the system prompt"). recency bias로 인해 짧고 적시의 가이드가 길고 정적인 규칙보다 효과적이라는 산업 관찰이다.

Parallax는 이 관찰을 두 방식으로 활용한다. 첫째, 피드백을 Stop 훅 시점에 정확히 한 번 주입한다. 둘째, 메인 에이전트의 자율성을 침해하지 않도록 "무엇을 더 생각해 볼 것인지"의 영역만 전달하고, 구체적 코드 변경이나 단계별 지시는 메인 에이전트가 스스로 결정하게 둔다.

### 2.9. 컨텍스트 위치와 정보 변환 계층

[**Lost in the Middle: How Language Models Use Long Contexts** (Liu et al., TACL 2024)](https://arxiv.org/abs/2307.03172)는 모델이 입력의 시작과 끝에 있는 정보는 잘 사용하지만 중간에 있는 정보는 무시하는 경향을 정량화했다. Parallax가 분석 프롬프트를 5-section XML로 명시적으로 격리하고, 메인 에이전트에는 짧은 advice를 라운드 끝에 주입하는 방식은 이 결과에 부합한다.

추가로, Mixture-of-Agents가 보인 계층 간 정보 전달의 가치는 Parallax의 Narrator 계층(`src/main.py`의 `convert_actions_to_markdown`)을 정당화한다. Advisor에게 원시 JSON 행동 기록을 주면 사용자가 실제로 보는 추상 수준과 어긋난 영역이 surface된다. Sonnet으로 한 번 마크다운 서사로 변환한 뒤 Advisor에게 전달하면, Advisor는 사용자가 터미널에서 작업을 관찰하는 시점과 같은 추상 수준에서 다음 영역을 결정한다.

### 2.10. 종료 신호: 도메인 메트릭 없는 수렴 감지

다중 라운드 루프의 가장 까다로운 문제는 언제 멈출지를 결정하는 것이다. 도메인별 정답 함수가 있다면 verifier가 종료를 결정할 수 있지만(Snell et al.), 일반 코딩·문서 작업에는 그런 함수가 없다.

Parallax는 이 문제를 두 신호의 결합으로 해결한다. 첫째, Advisor가 더 surface할 영역이 없다고 판단하면 전용 종료 토큰(`I_FIND_NO_FURTHER_REGION_WORTH_SURFACING_ENDING_THE_PARALLAX_TURN`)을 출력하도록 명시적 지시를 받는다. 격리된 컨텍스트가 매 라운드 새로 판단하므로, 메인 에이전트의 누적 영역이 충분히 넓어진 시점에 자연스럽게 종료 신호가 나온다. 둘째, 신호가 나오지 않더라도 30라운드의 절대 한계(`src/state.py`의 `ROUND_LIMIT = 30`)가 무한 루프를 차단한다.

이 결합은 검증 가능성 가정을 두지 않으면서 수렴을 감지한다. Advisor가 매번 새 컨텍스트로 전체 region history를 보고 판단하므로, "더 surface할 가치가 있는 영역이 남았는가"는 도메인과 무관하게 같은 절차로 평가된다.

## 3. 종합

Parallax의 네 가지 추상 원칙은 각각 별개의 학술적 흐름과 산업 관찰에 의해 뒷받침된다.

**격리된 Advisor**는 [Huang ICLR 2024](https://arxiv.org/abs/2310.01798)의 self-correction 실패, [Liang EMNLP 2024](https://arxiv.org/abs/2305.19118)의 DoT, [Sharma 2023](https://arxiv.org/abs/2310.13548)의 sycophancy로부터 정당화되며, [Anthropic Multi-Agent](https://www.anthropic.com/engineering/multi-agent-research-system), [MoA](https://arxiv.org/abs/2406.04692), [AgentCoder](https://arxiv.org/abs/2312.13010)의 양적 결과로 격리된 별개 컨텍스트의 가치가 입증된다.

**거리 누적 다양성 탐색**은 [ToT](https://arxiv.org/abs/2305.10601), [Self-Consistency](https://arxiv.org/abs/2203.11171), [LATS](https://arxiv.org/abs/2310.04406), [Diverse Beam Search](https://arxiv.org/abs/1610.02424), [Verbalized Sampling](https://arxiv.org/abs/2510.01171), [Sequential Sampling](https://arxiv.org/abs/2510.15502)의 일관된 결과로 뒷받침된다.

**추상 수준의 영역**은 [Replit Decision-Time Guidance](https://blog.replit.com/decision-time-guidance)의 산업 관찰과 [Lost in the Middle](https://arxiv.org/abs/2307.03172)의 위치 효과로 정당화된다.

**정보 변환 계층**은 [MoA](https://arxiv.org/abs/2406.04692)의 계층 간 정보 전달과 사용자 관찰 추상 수준 정합으로 정당화된다.

이 네 원칙이 Stop 훅 위에 결합되었을 때 Parallax는 다음을 동시에 달성한다. (1) 자기회귀 생성의 구조적 한계([Snowball](https://arxiv.org/abs/2305.13534))를 외부 조건 입력으로 우회하고, (2) 영역 식별과 영역 내부 행동 생성 사이의 비대칭성([Verify Step by Step](https://arxiv.org/abs/2305.20050))을 활용해 같은 모델로 같은 모델의 사각을 본다. (3) 추론 시점 compute 확장([Snell 2024](https://arxiv.org/abs/2408.03314))을 모델 크기 변경 없이 수행하며, (4) 도메인 메트릭 없이 수렴을 감지한다.

Parallax는 새 모델을 학습시키지도, 새 디코딩 알고리즘을 도입하지도 않는다. 위 네 흐름의 결과를 Claude Code의 Stop 훅이라는 단일 통합 지점에서 결합해, 사용자가 단일 턴에서 얻을 수 있는 결과 신뢰도의 한계를 끌어올린다.

## 4. 부수적 효과: 컨텍스트 윈도우 한계 극복

Parallax의 핵심은 추론 고도화이지만, 그 구현 과정에서 부수적으로 컨텍스트 윈도우 한계 — 구체적으로는 Claude Code의 auto-compact가 야기하는 정보 손실 — 에 대한 해법이 함께 만들어진다. 이 절은 핵심 설계와 차원이 다른 별개의 문제 해결을 다룬다.

### 4.1. 설계

Parallax 루프는 **원본 미션 텍스트가 변하지 않는다**는 가정 위에서 작동한다. Advisor는 미션을 기준으로 surface할 영역을 결정하고, 메인 에이전트는 미션을 기준으로 다음 행동을 정한다. Claude Code의 auto-compact는 이 가정을 위협한다. compaction은 누적된 메시지를 요약본으로 치환하는 손실 변환이고, 사용자가 입력한 미션의 정확한 표현은 그 변환에서 보존을 보장받지 못한다. Parallax는 이 위협을 두 메커니즘의 결합으로 차단한다.

**메커니즘 1: 외부 보존.** 사용자 미션을 세션 트랜스크립트 바깥의 별도 파일에 저장한다. 매 라운드 Advisor에게 전달되는 미션은 트랜스크립트가 아닌 이 파일에서 읽힌다. Compaction이 트랜스크립트를 어떻게 요약하든, Advisor가 보는 미션은 사용자가 실제로 타이핑한 텍스트와 항상 동일하다.

**메커니즘 2: 사후 재주입.** Auto-compact가 발생한 라운드에 한해, 다음 Stop 훅이 메인 에이전트에 advice를 주입할 때 원본 미션을 함께 실어 보낸다. 메인 에이전트가 compaction된 요약본 위에서 다음 라운드를 시작하더라도, 컨텍스트 끝에 원본 미션 텍스트가 새 입력으로 얹혀 다음 생성을 원본 의도 쪽으로 끌어 당긴다.

두 메커니즘은 다른 측에서 같은 위험을 막는다. 메커니즘 1은 Advisor의 판단 기준이 흔들리지 않도록 미션을 손실 채널 바깥에 둔다. 메커니즘 2는 메인 에이전트의 다음 생성이 표류하지 않도록 손실 사건 직후 미션을 새 채널로 다시 박는다.

### 4.2. 근거

#### 컨텍스트가 길어지면 에이전트는 미션에서 표류한다

[**Technical Report: Evaluating Goal Drift in Language Model Agents** (Chen et al., 2025)](https://arxiv.org/abs/2505.02709)은 SOTA 에이전트들이 모두 어느 정도의 goal drift — 시간이 지남에 따라 원래 지시된 목표에서 벗어나는 현상 — 를 보인다는 것을 측정했다. 가장 강건한 Claude 3.5 Sonnet 변형조차 100K 토큰 규모에서 일부 drift를 보였고, 저자들은 그 원인을 "models' increasing susceptibility to pattern-matching behaviors as the context length grows"로 지목한다. 컨텍스트가 자라면 에이전트는 시스템 프롬프트의 명시적 미션보다 트랜스크립트 안의 누적된 패턴에 점점 더 끌려간다.

[**Drift No More? Context Equilibria in Multi-Turn LLM Interactions** (2025)](https://arxiv.org/abs/2510.07777)는 같은 현상을 다중 턴 상호작용 위에서 turn-wise KL divergence로 정식화한다. drift는 단일 턴의 오류가 아니라 여러 턴에 걸쳐 누적되는 시간적 현상이며, 정적 평가 메트릭으로는 잘 포착되지 않는다. Parallax처럼 라운드 루프로 작업을 길게 끌고 가는 시스템에서는 이 누적이 치명적이다 — 매 라운드 미션 해석이 약간씩 어긋나면, 라운드 한계까지 도달했을 때 메인 에이전트와 Advisor 모두 사용자가 의도한 작업과는 다른 어떤 것을 수행하고 있게 된다.

#### Compaction은 본질적으로 손실이며, 무엇이 손실되는지를 사전에 통제할 수 없다

[**ACON: Optimizing Context Compression for Long-horizon LLM Agents** (2025)](https://arxiv.org/html/2510.00615)은 long-horizon 에이전트의 context compression을 명시적 최적화 문제로 접근한다. 저자들의 방법론은 "paired trajectories where full context succeeds but compressed context fails"를 수집해 무엇이 손실되어선 안 되는지를 학습하는 것이다. 이 방법론 자체가 원래 강조하는 사실이 있다 — 일반적인 요약은 어느 정보가 후속 작업에 결정적인지를 알지 못한 채 압축을 수행하므로, 결정적 정보가 정확히 손실되는 사건이 통계적으로 드물지 않다. Claude Code의 auto-compact는 사용자의 다음 의도를 모르는 시점에 작동하므로, 미션 텍스트가 어느 정도 보존될지를 보장할 수 없다.

산업 관찰도 같은 방향을 가리킨다. JetBrains의 [**Cutting Through the Noise: Smarter Context Management for LLM-Powered Agents** (2025)](https://blog.jetbrains.com/research/2025/12/efficient-context-management/)는 "naive strategies like token truncation or generic summarization easily lose critical details essential for long-horizon reasoning"이라고 보고하며, 해법으로 다중 스케일 — 최신 상호작용은 raw로 보존하고 별개 채널로 추상 요약을 두는 — 구조를 제시한다. **메커니즘 1의 외부 파일은 정확히 이런 별개 채널이다.** 메인 트랜스크립트는 compaction의 손실에 노출되더라도, 미션 anchor는 노출되지 않는 raw 채널에 보존된다.

#### 새로 들어온 입력은 컨텍스트의 다른 위치보다 강하게 다음 생성을 끈다

메커니즘 2가 미션을 메인 에이전트의 컨텍스트 앞쪽이 아니라 가장 최근 입력으로 다시 박는 것의 근거다.

[**Lost in the Middle: How Language Models Use Long Contexts** (Liu et al., TACL 2024)](https://arxiv.org/abs/2307.03172)는 모델이 입력의 시작과 끝에 있는 정보는 잘 사용하지만 중간에 있는 정보는 무시하는 경향을 정량화했다. compaction된 요약본의 내부 어딘가에 미션 흔적이 남아 있더라도, 그것은 대체로 컨텍스트의 중간에 묻혀 다음 생성에 거의 영향을 주지 못한다. Stop 훅 주입은 항상 컨텍스트의 가장 끝에 위치하므로, 같은 미션 텍스트가 위치 효과의 도움을 받아 활성화에 강하게 기여한다.

[**Decision-Time Guidance: Keeping Replit Agent Reliable** (Replit, 2025)](https://blog.replit.com/decision-time-guidance)는 같은 가이드를 시스템 프롬프트가 아닌 트레이스 끝에 주입했을 때 루프당 도구 호출이 15% 늘어났음을 보고했다("injecting a short prompt at the bottom of the trace led the agent to execute 15% more tools per loop than placing the same guidance in the system prompt"). 정적인 위치보다 결정 시점에 가까운 위치의 입력이 행동에 더 강하게 작용한다는 산업 관찰이며, 메커니즘 2가 미션을 시스템 메시지 시점이 아닌 Stop 훅 시점에, 한 번에 한해 재주입하는 결정의 정당화다.

#### 결합의 효과

두 메커니즘이 결합되면 Parallax 루프는 원본 미션 텍스트가 변하지 않는다는 가정을 compaction에 대해 견고하게 유지할 수 있다. Advisor는 외부 채널로 미션 anchor를 잃지 않고, 메인 에이전트는 compaction 사건이 발생할 때마다 같은 anchor를 새 입력으로 다시 받는다. 이 안전판 위에서 Parallax는 단일 컨텍스트 윈도우보다 훨씬 긴 작업을 라운드 한계까지 같은 미션 정렬을 유지한 채 수행할 수 있다.

이 절의 메커니즘들은 추론 고도화와는 다른 차원의 문제를 푼다. 그러나 Parallax가 긴 작업에 적용 가능한 도구가 되기 위한 전제 조건이며, 핵심 루프와 같은 통합 지점(`UserPromptSubmit`/`PostCompact`/`Stop` 훅)에서 무게 추가 없이 함께 구현되어 있다.

## Sources

- [Tree of Thoughts (Yao et al., NeurIPS 2023)](https://arxiv.org/abs/2305.10601)
- [Large Language Models Cannot Self-Correct Reasoning Yet (Huang et al., ICLR 2024)](https://arxiv.org/abs/2310.01798)
- [Encouraging Divergent Thinking through Multi-Agent Debate (Liang et al., EMNLP 2024)](https://arxiv.org/abs/2305.19118)
- [Self-Refine (Madaan et al., NeurIPS 2023)](https://arxiv.org/abs/2303.17651)
- [Reflexion (Shinn et al., NeurIPS 2023)](https://arxiv.org/abs/2303.11366)
- [CRITIC (Gou et al., ICLR 2024)](https://arxiv.org/abs/2305.11738)
- [Mixture-of-Agents (Wang et al., 2024)](https://arxiv.org/abs/2406.04692)
- [Language Agent Tree Search (Zhou et al., ICML 2024)](https://arxiv.org/abs/2310.04406)
- [Self-Consistency (Wang et al., ICLR 2023)](https://arxiv.org/abs/2203.11171)
- [Let's Verify Step by Step (Lightman, Cobbe et al., 2023)](https://arxiv.org/abs/2305.20050)
- [Anthropic Multi-Agent Research System](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Scaling LLM Test-Time Compute Optimally (Snell et al., 2024)](https://arxiv.org/abs/2408.03314)
- [AI safety via debate (Irving, Christiano, Amodei, 2018)](https://arxiv.org/abs/1805.00899)
- [Diverse Beam Search (Vijayakumar et al., 2016)](https://arxiv.org/abs/1610.02424)
- [Lost in the Middle (Liu et al., TACL 2024)](https://arxiv.org/abs/2307.03172)
- [Towards Understanding Sycophancy (Sharma et al., Anthropic, ICLR 2024)](https://arxiv.org/abs/2310.13548)
- [Constitutional AI (Bai et al., Anthropic, 2022)](https://arxiv.org/abs/2212.08073)
- [Replit Decision-Time Guidance](https://blog.replit.com/decision-time-guidance)
- [AgentCoder (Huang et al., 2023)](https://arxiv.org/abs/2312.13010)
- [How Language Model Hallucinations Can Snowball (Zhang et al., 2023)](https://arxiv.org/abs/2305.13534)
- [Verbalized Sampling (Zhang et al., 2025)](https://arxiv.org/abs/2510.01171)
- [The Road Less Traveled: Sequential Sampling (2025)](https://arxiv.org/abs/2510.15502)
- [ThoughtProbe (2025)](https://arxiv.org/abs/2510.27355)
- [Evaluating Goal Drift in Language Model Agents (Chen et al., 2025)](https://arxiv.org/abs/2505.02709)
- [Drift No More? Context Equilibria in Multi-Turn LLM Interactions (2025)](https://arxiv.org/abs/2510.07777)
- [ACON: Optimizing Context Compression for Long-horizon LLM Agents (2025)](https://arxiv.org/html/2510.00615)
- [Cutting Through the Noise: Smarter Context Management for LLM-Powered Agents (JetBrains, 2025)](https://blog.jetbrains.com/research/2025/12/efficient-context-management/)
