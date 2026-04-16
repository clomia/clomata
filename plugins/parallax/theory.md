# Parallax Theory of Operation

This document explains why Parallax works. The body has two layers. The earlier **Design** part states what Parallax does at an abstract level in a few sentences, and the later **Evidence** part backs the design up concretely with academic literature and industry reports.

## 1. Design

Parallax is not a **critic** that evaluates and corrects the main agent's outputs, but an **Advisor** that surfaces regions the main agent has not considered, shifting the starting point of the next round's generation representation. A critic says "this is wrong, fix it"; an Advisor says "consider this region as well." The former accumulates judgments about right and wrong of outputs; the latter shifts the activation location from which the next round of representation begins. This distinction is inscribed directly in the code and prompts. `prompts/role.md` defines the Advisor as "an advisory agent that surfaces regions the main agent has not considered," and `prompts/instruction.md` states "Only raise the issue. The main agent finds the answer."

Parallax is an external Advisor loop that simultaneously implements the following four abstract principles.

1. **Isolated Advisor.** A separate context with the same model as the main agent is freshly created each round to decide which region to surface in the next round. The Advisor is bound neither to the main agent's output distribution nor to its own prior round's output.
2. **Distance-accumulating diversity exploration.** The Advisor receives all regions surfaced in prior rounds as input, and the next surfacing target is constrained to be the one farthest from that set. Diversity is achieved not through training but through input conditioning and prompt instructions.
3. **Abstract-level regions.** What is injected into the main agent is not an instruction about what to do or how to do it, but a region indicating what to consider further. The region only shifts the activation of the next generation; it does not determine the concrete action. Autonomous reasoning is preserved.
4. **Information transformation layer.** The main agent's raw action records (JSON) are transformed into a markdown narrative at the abstraction level a user observes in the terminal, then delivered to the Advisor. The Advisor decides the next region at the same abstraction level as the user.

Loop termination is determined by two signals: a fixed round limit, and a dedicated termination token output by the Advisor. No domain-specific convergence metric is required.

## 2. Evidence

### 2.1. Autoregressive generation itself narrows exploration

Sequential token generation strongly conditions subsequent representations on prior outputs, leaving the model unable on its own to move into a different region. This limit is reported as a structural phenomenon, not merely a decoding heuristic problem.

[**Tree of Thoughts: Deliberate Problem Solving with Large Language Models** (Yao et al., NeurIPS 2023)](https://arxiv.org/abs/2305.10601) showed that GPT-4 with standard chain-of-thought solved only 4% of Game of 24, but the same model reached 74% when an external tree-based search was imposed. With identical model and identical weights, the difference came from an external structure that forcibly branched the token generation flow.

[**How Language Model Hallucinations Can Snowball** (Zhang et al., 2023)](https://arxiv.org/abs/2305.13534) provides more microscopic evidence. ChatGPT and GPT-4 identify 67% and 87% of their own errors when checking their outputs separately, but during generation they over-commit to early errors and stack falsehoods on top. That is, even when a model has the capacity to discriminate right from wrong, it cannot access that capacity within the generation flow.

[**Verbalized Sampling: How to Mitigate Mode Collapse and Unlock LLM Diversity** (Zhang et al., 2025)](https://arxiv.org/abs/2510.01171) quantifies the mode collapse by which alignment training narrows the LLM's output distribution and shows that diversity can be recovered 1.6–2.1× through a simple inference-time prompt alone. The cause of the diversity loss lies not in the weights but in the activation pattern, and can be partially reversed by input conditioning alone.

[**The Road Less Traveled: Enhancing Exploration in LLMs via Sequential Sampling** (2025)](https://arxiv.org/abs/2510.15502) points out that parallel sampling repeatedly draws from the same distribution and loses diversity, and shows that sequential sampling — **accumulating prior outputs as conditioning for the next input** — produces broader exploration. Parallax's region history accumulation transposes this principle to multi-turn agent work.

These four results point in one direction. To reach regions a model cannot activate on its own, an external signal must enter as input.

### 2.2. Models cannot surface new regions on their own

Direct evidence for why the Advisor must be a separate context isolated from the main agent. These results show what fails when the same context attempts to give itself a new-region signal.

[**Large Language Models Cannot Self-Correct Reasoning Yet** (Huang et al., ICLR 2024)](https://arxiv.org/abs/2310.01798) shows across multiple benchmarks that intrinsic self-correction without external feedback or oracle information is ineffective on reasoning tasks, sometimes even degrading performance. An attempt by the same context to produce signals in new directions toward its own output is unreliable. Not only self-correction but also self-surfacing — the attempt to identify regions oneself failed to consider — falls under the same limit.

[**Towards Understanding Sycophancy in Language Models** (Sharma et al., Anthropic, ICLR 2024)](https://arxiv.org/abs/2310.13548) provides corroborating evidence. Five state-of-the-art assistants consistently exhibited sycophantic responses, and both humans and preference models preferred "convincingly-written sycophantic responses over correct ones" at non-negligible rates. Self-surfacing within the same context is exposed to conformity pressure toward its own output and fails to move into a new region.

The reason Parallax separates the Advisor into its own `claude -p` process and freshly initializes the context each round is to bypass these two results. The Advisor decides the next region without sycophancy stemming from the main agent's output distribution and without commitment to its own prior answer.

### 2.3. Once conviction forms, self-reflection produces no new thought

[**Encouraging Divergent Thinking in Large Language Models through Multi-Agent Debate** (Liang et al., EMNLP 2024)](https://arxiv.org/abs/2305.19118) formalized the Degeneration-of-Thought (DoT) problem: once a model forms conviction in its own answer, subsequent self-reflection cannot produce new thoughts. This is a more direct statement of the inability to move oneself to a new region. The authors' remedy was multi-agent debate in which multiple agents holding different positions engage in tit-for-tat argumentation while a separate judge reaches a conclusion.

DoT justifies a key decision in Parallax's design: the Advisor must be a context that begins anew each round. Conviction about regions surfaced by the prior round's Advisor does not transfer to the next round's Advisor, and is also isolated from the conviction the main agent has accumulated. The Advisor's context starts each round flat across the entire region candidate space.

### 2.4. Externally arriving input shifts the next generation

Self-surfacing fails, but externally arriving input consistently shifts the next generation into a different region. Most prior work calls this input "critique" or "feedback," but mechanistically it works because the input becomes conditioning for the next generation. Parallax borrows this very mechanism, only with the input's content shifted from judgments of right/wrong to surfacing of regions.

[**Self-Refine: Iterative Refinement with Self-Feedback** (Madaan et al., NeurIPS 2023)](https://arxiv.org/abs/2303.17651) obtained an average ~20% absolute improvement across 7 tasks using a simple loop in which the same model plays generation, feedback, and revision roles. Even without tools or training, merely appending references to its own output as the next round's input shifts the output. Combined with Huang et al., however, same-context self-feedback is limited to tasks with low reasoning dependence and does not generalize to reasoning tasks.

[**Reflexion: Language Agents with Verbal Reinforcement Learning** (Shinn et al., NeurIPS 2023)](https://arxiv.org/abs/2303.11366) stores verbal reflection after episodic failure in memory and uses it in the next attempt, achieving large improvements in coding, sequential decision-making, and reasoning tasks without weight updates. It achieved 91% pass@1 on HumanEval, surpassing GPT-4's 80% by 11 percentage points. A structure that converts external environment signals to language and accumulates them in context shifts the next attempt into a different region. Parallax's region history accumulation is a variant that transposes this idea from post-failure reflection to pre-emptive region surfacing.

[**CRITIC: Large Language Models Can Self-Correct with Tool-Interactive Critiquing** (Gou et al., ICLR 2024)](https://arxiv.org/abs/2305.11738) showed that model evaluation only begins to work when combined with external tools (search, code execution, etc.). External tools serve to add signals to the input that the same model alone could not reach. Parallax's decision to allow the Advisor investigation tools such as `Read, Glob, Grep` (the inverted whitelist `DISALLOWED_TOOLS = "Bash,Write,Edit,NotebookEdit"` in `src/main.py`) aligns with this result. Because the Advisor surfaces regions after directly inspecting the codebase, it delivers regions grounded in codebase facts rather than mere conjecture.

[**Constitutional AI: Harmlessness from AI Feedback** (Bai et al., 2022)](https://arxiv.org/abs/2212.08073) showed that a structure in which one model (or a separate call of the same model) applies a set of principles to another's output to produce a new output is powerful enough as a training signal. This is industrial-scale verification that input from a different context can drive even weight learning, and Parallax's position is to use the same mechanism at inference time.

Synthesizing these four results, input arriving from outside or from an isolated context is itself a powerful resource for shifting the next generation. Parallax's decision to place a separate Advisor alongside the main agent is a direct application of this stream, only with the meaning of the input shifted from evaluation to region surfacing.

### 2.5. The asymmetry that observation is easier than generation

Here lies the answer to how the Advisor, being the same model as the main agent, can identify regions the main missed. Prior work formalizes this asymmetry as separation of verification from generation, but the same asymmetry holds between region identification and within-region action generation.

[**Let's Verify Step by Step** (Lightman, Cobbe et al., OpenAI, 2023)](https://arxiv.org/abs/2305.20050) shows that evaluating the correctness of an answer is structurally a different task from generating that answer, and that a process reward model trained on step-wise verification substantially outperforms outcome-based reward models. External verification of an output is a separate capability from generation.

[**Scaling LLM Test-Time Compute Optimally can be More Effective than Scaling Model Parameters** (Snell et al., 2024)](https://arxiv.org/abs/2408.03314) quantifies that spending more compute at inference time can be more effective than scaling model parameters. With the right strategy, the same base model surpassed a 14× larger model ("test-time compute can be used to outperform a 14x larger model"). An inference-time loop of looking again from outside is itself a resource exchangeable with model capacity.

The asymmetry has two implications in Parallax. First, even the same model, when re-examining action records from an isolated context with an outside view, identifies regions that were not activated at the generation site. Second, adding a parallax round is not mere repetition but an asymmetric use of inference-time compute.

### 2.6. Diverse exploration produces better answers

Direct evidence for why distance-accumulating diversity raises accuracy.

[**Self-Consistency Improves Chain of Thought Reasoning in Language Models** (Wang et al., ICLR 2023)](https://arxiv.org/abs/2203.11171) obtained, by simply sampling diverse reasoning paths instead of a single chain-of-thought and taking a majority vote, +17.9% on GSM8K, +11.0% on SVAMP, and +12.2% on AQuA. Same model, same context — the result of merely increasing exploration diversity.

[**Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models** (Zhou et al., ICML 2024)](https://arxiv.org/abs/2310.04406) overlaid MCTS on an LLM agent and recorded 92.7% pass@1 on HumanEval with GPT-4. Tree search's effect of going beyond single-path generation generalizes to tool-using agents.

[**Diverse Beam Search: Decoding Diverse Solutions from Neural Sequence Models** (Vijayakumar et al., 2016)](https://arxiv.org/abs/1610.02424) early on pointed out that standard beam search repeatedly generates near-identical sequences and showed that diversity must be imposed as an explicit objective to obtain a meaningful candidate set. Diversity is secured not by chance but only by explicit constraint.

[**ThoughtProbe: Classifier-Guided Thought Space Exploration** (2025)](https://arxiv.org/abs/2510.27355) shows that distinguishing signals capable of identifying diverse reasoning branches latent in the LLM's hidden representations can be used as pruning criteria for tree search. Diversity exploration can be guided by the model's own internal signals rather than random tries.

Parallax obtains the same effect on top of multi-turn agent work without introducing learning or a tree data structure, by simply accumulating region history as part of the Advisor's input and imposing the natural-language constraint "The farther it is from regions already considered, the more valuable it is" (`prompts/instruction.md`).

### 2.7. Multi-agent collaboration outperforms a single agent

The macro justification for placing the Advisor as a separate agent in Parallax.

[**How we built our multi-agent research system** (Anthropic, 2025)](https://www.anthropic.com/engineering/multi-agent-research-system) reports that a multi-agent system composed of a Claude Opus 4 lead and Claude Sonnet 4 subagents showed a 90.2% improvement over a single Opus 4 on internal research evaluations. Industrial-scale evidence that even within the same model family, separating roles and parallelizing produces greater performance than a single context.

[**Mixture-of-Agents Enhances Large Language Model Capabilities** (Wang et al., 2024)](https://arxiv.org/abs/2406.04692) formalized the inherent collaborativeness phenomenon in which an LLM produces higher quality output when receiving another LLM's output as auxiliary information. An open-source MoA outperformed GPT-4 Omni 65.1% to 57.5% on AlpacaEval 2.0. Even when the main agent and Advisor are the same model family, a structure that synthesizes outputs from isolated calls creates value.

[**AI safety via debate** (Irving, Christiano, Amodei, 2018)](https://arxiv.org/abs/1805.00899) showed that zero-sum debate between two agents can theoretically identify a wider truth space than a single agent's direct judgment. An early justification that there exists a structural mechanism by which multiple agents bypass a single agent's capacity limit.

[**AgentCoder: Multi-Agent-based Code Generation with Iterative Testing and Optimisation** (Huang et al., 2023)](https://arxiv.org/abs/2312.13010) recorded HumanEval-ET 77.4% and MBPP-ET 89.1% pass@1 on GPT-3.5 with a structure that separates coder, test designer, and test executor — substantially ahead of SOTA single agents (69.5%, 63.0% respectively). It shows the concrete effect in code work of separating evaluation and verification roles into separate agents. Parallax adopts the same separation structure but places the separate agent's role at region surfacing rather than evaluation.

### 2.8. Abstract guidance shifts behavior while preserving autonomy

Justification for Parallax's decision to surface only regions instead of concrete instructions.

[**Decision-Time Guidance: Keeping Replit Agent Reliable** (Replit, 2025)](https://blog.replit.com/decision-time-guidance) reports that pre-loading all rules into a static system prompt pollutes the context and increases priority ambiguity. Injecting the same guidance briefly at the bottom of the trace (decision time) increased tools per loop by 15% over placing it in the system prompt ("injecting a short prompt at the bottom of the trace led the agent to execute 15% more tools per loop than placing the same guidance in the system prompt"). An industrial observation that, due to recency bias, brief and timely guidance is more effective than long, static rules.

Parallax exploits this observation in two ways. First, it injects feedback exactly once at the Stop hook moment. Second, to avoid violating the main agent's autonomy, it conveys only regions of "what to consider further" and leaves concrete code changes or step-by-step instructions to the main agent's own decision.

### 2.9. Context position and the information transformation layer

[**Lost in the Middle: How Language Models Use Long Contexts** (Liu et al., TACL 2024)](https://arxiv.org/abs/2307.03172) quantifies the tendency of models to use information at the beginning and end of input well while ignoring information in the middle. Parallax's approach of explicitly isolating the analysis prompt as a 5-section XML and injecting brief advice into the main agent at round end aligns with this result.

In addition, the value of inter-layer information transfer demonstrated by Mixture-of-Agents justifies Parallax's Narrator layer (`convert_actions_to_markdown` in `src/main.py`). Giving the Advisor raw JSON action records surfaces regions misaligned with the abstraction level the user actually sees. Once converted by Sonnet to a markdown narrative and delivered to the Advisor, the Advisor decides the next region at the same abstraction level as a user observing the work in the terminal.

### 2.10. Termination signal: convergence detection without a domain metric

The trickiest problem in a multi-round loop is deciding when to stop. If a domain-specific correctness function exists, a verifier can decide termination (Snell et al.), but no such function exists for general coding or document work.

Parallax solves this with a combination of two signals. First, the Advisor receives an explicit instruction to output a dedicated termination token (`I_FIND_NO_FURTHER_REGION_WORTH_SURFACING_ENDING_THE_PARALLAX_TURN`) when it judges there are no more regions worth surfacing. Because an isolated context judges anew each round, the termination signal naturally appears once the main agent's accumulated regions are sufficiently broad. Second, even without the signal, an absolute limit of 30 rounds (`ROUND_LIMIT = 30` in `src/state.py`) cuts off infinite loops.

This combination detects convergence without assuming verifiability. Because the Advisor judges from a fresh context each round on the entire region history, "is there a region worth surfacing left" is evaluated by the same procedure regardless of domain.

## 3. Synthesis

Parallax's four abstract principles are each backed by separate academic streams and industrial observations.

**Isolated Advisor** is justified by [Huang ICLR 2024](https://arxiv.org/abs/2310.01798)'s self-correction failure, [Liang EMNLP 2024](https://arxiv.org/abs/2305.19118)'s DoT, and [Sharma 2023](https://arxiv.org/abs/2310.13548)'s sycophancy, while the value of an isolated separate context is empirically established by quantitative results from [Anthropic Multi-Agent](https://www.anthropic.com/engineering/multi-agent-research-system), [MoA](https://arxiv.org/abs/2406.04692), and [AgentCoder](https://arxiv.org/abs/2312.13010).

**Distance-accumulating diversity exploration** is supported by the consistent results of [ToT](https://arxiv.org/abs/2305.10601), [Self-Consistency](https://arxiv.org/abs/2203.11171), [LATS](https://arxiv.org/abs/2310.04406), [Diverse Beam Search](https://arxiv.org/abs/1610.02424), [Verbalized Sampling](https://arxiv.org/abs/2510.01171), and [Sequential Sampling](https://arxiv.org/abs/2510.15502).

**Abstract-level regions** is justified by the industrial observation of [Replit Decision-Time Guidance](https://blog.replit.com/decision-time-guidance) and the position effect of [Lost in the Middle](https://arxiv.org/abs/2307.03172).

**Information transformation layer** is justified by [MoA](https://arxiv.org/abs/2406.04692)'s inter-layer information transfer and alignment with the user's observation abstraction level.

When these four principles combine on top of the Stop hook, Parallax simultaneously achieves: (1) bypassing the structural limit of autoregressive generation ([Snowball](https://arxiv.org/abs/2305.13534)) via external conditioning input, (2) using the asymmetry between region identification and within-region action generation ([Verify Step by Step](https://arxiv.org/abs/2305.20050)) to see the same model's blind spots with the same model, (3) performing inference-time compute scaling ([Snell 2024](https://arxiv.org/abs/2408.03314)) without changing model size, and (4) detecting convergence without a domain metric.

Parallax neither trains a new model nor introduces a new decoding algorithm. It combines the results of the four streams above at a single integration point — Claude Code's Stop hook — to push up the limit of result reliability a user can obtain in a single turn.

## 4. Side Effect: Overcoming the Context Window Limit

Parallax's core is reasoning enhancement, but its implementation incidentally produces a solution to the context window limit — specifically, to the information loss caused by Claude Code's auto-compact. This section addresses a problem of a different dimension from the core design.

### 4.1. Design

The Parallax loop operates on the assumption that **the original mission text does not change**. The Advisor decides which region to surface based on the mission, and the main agent decides its next action based on the mission. Claude Code's auto-compact threatens this assumption. Compaction is a lossy transformation that replaces accumulated messages with a summary, and the exact wording of the mission the user typed is not guaranteed preservation through that transformation. Parallax blocks this threat with the combination of two mechanisms.

**Mechanism 1: External preservation.** The user's mission is saved to a separate file outside the session transcript. The mission delivered to the Advisor each round is read from this file, not from the transcript. However compaction summarizes the transcript, the mission the Advisor sees is always identical to the text the user actually typed.

**Mechanism 2: Post-event re-injection.** Only in rounds where auto-compact occurred, the next Stop hook ships the original mission together with the advice when injecting into the main agent. Even though the main agent begins the next round on top of the compacted summary, the original mission text is laid on as new input at the end of the context, pulling the next generation back toward the original intent.

The two mechanisms block the same risk from different sides. Mechanism 1 keeps the mission outside the lossy channel so the Advisor's judgment criterion does not waver. Mechanism 2 re-anchors the mission through a new channel immediately after the loss event so the main agent's next generation does not drift.

### 4.2. Evidence

#### As context grows, agents drift from the mission

[**Technical Report: Evaluating Goal Drift in Language Model Agents** (Chen et al., 2025)](https://arxiv.org/abs/2505.02709) measured that SOTA agents all show some degree of goal drift — deviation from the originally instructed goal over time. Even the most robust Claude 3.5 Sonnet variant showed some drift at the 100K token scale, and the authors point to the cause as "models' increasing susceptibility to pattern-matching behaviors as the context length grows." As context grows, the agent is increasingly pulled by accumulated patterns inside the transcript rather than by the explicit mission in the system prompt.

[**Drift No More? Context Equilibria in Multi-Turn LLM Interactions** (2025)](https://arxiv.org/abs/2510.07777) formalizes the same phenomenon over multi-turn interaction as turn-wise KL divergence. Drift is not a single-turn error but a temporal phenomenon that accumulates across many turns and is poorly captured by static evaluation metrics. In a system like Parallax that drags work out long with a round loop, this accumulation is fatal — if mission interpretation is slightly off each round, by the time the round limit is reached both the main agent and the Advisor are doing something different from what the user intended.

#### Compaction is intrinsically lossy, and what is lost cannot be controlled in advance

[**ACON: Optimizing Context Compression for Long-horizon LLM Agents** (2025)](https://arxiv.org/html/2510.00615) approaches context compression for long-horizon agents as an explicit optimization problem. The authors' methodology is to collect "paired trajectories where full context succeeds but compressed context fails" and learn what must not be lost. The methodology itself underscores a fact — generic summarization compresses without knowing which information is decisive for the subsequent task, so the event that decisive information is precisely what gets lost is statistically not rare. Claude Code's auto-compact runs at a moment when the user's next intent is unknown, so it cannot guarantee how much of the mission text will be preserved.

Industrial observation points the same way. JetBrains' [**Cutting Through the Noise: Smarter Context Management for LLM-Powered Agents** (2025)](https://blog.jetbrains.com/research/2025/12/efficient-context-management/) reports that "naive strategies like token truncation or generic summarization easily lose critical details essential for long-horizon reasoning," and proposes as a remedy a multi-scale structure that preserves the latest interaction as raw and places an abstract summary in a separate channel. **Mechanism 1's external file is precisely such a separate channel.** Even when the main transcript is exposed to compaction loss, the mission anchor is preserved in a raw channel that is not exposed.

#### Newly arriving input pulls the next generation more strongly than other locations in the context

The basis for Mechanism 2 re-pinning the mission as the most recent input rather than at the front of the main agent's context.

[**Lost in the Middle: How Language Models Use Long Contexts** (Liu et al., TACL 2024)](https://arxiv.org/abs/2307.03172) quantifies the tendency of models to use information at the beginning and end of input well while ignoring information in the middle. Even if a trace of the mission remains somewhere inside the compacted summary, it is mostly buried in the middle of the context and barely affects the next generation. The Stop hook injection always lands at the very end of the context, so the same mission text contributes strongly to activation with the help of the position effect.

[**Decision-Time Guidance: Keeping Replit Agent Reliable** (Replit, 2025)](https://blog.replit.com/decision-time-guidance) reports that injecting the same guidance at the end of the trace rather than into the system prompt increased tools per loop by 15% ("injecting a short prompt at the bottom of the trace led the agent to execute 15% more tools per loop than placing the same guidance in the system prompt"). An industrial observation that input near the decision time acts on behavior more strongly than input at a static location, and the justification for Mechanism 2's decision to re-inject the mission once at the Stop hook moment rather than at system message time.

#### Effect of the combination

When the two mechanisms combine, the Parallax loop can robustly maintain the assumption that the original mission text does not change against compaction. The Advisor does not lose the mission anchor through the external channel, and the main agent receives the same anchor as new input every time a compaction event occurs. On top of this safety net, Parallax can perform work much longer than a single context window up to the round limit while maintaining the same mission alignment.

The mechanisms in this section solve a problem of a different dimension from reasoning enhancement. But they are a precondition for Parallax to be a tool applicable to long work, and they are implemented at the same integration points (`UserPromptSubmit`/`PostCompact`/`Stop` hooks) as the core loop without added weight.

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
