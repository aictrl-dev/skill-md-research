# Literature Review: Task Decomposition & Chained Execution for LLM Tasks

**Last updated**: 2026-02-21
**Purpose**: Assess whether breaking tasks into intermediate artifacts and chained execution produces better results than one-shot prompting.

---

## 1. Research Question

**Does task decomposition with intermediate artifacts improve LLM performance on verifiable tasks?**

### Example Use Case: Visualization Generation

| Approach | Steps |
|----------|-------|
| **One-shot** | Single prompt: "Create a bar chart showing GDP by country with proper styling" |
| **Chained** | Step 1: Analyze data → Choose chart type |
| | Step 2: Define chart schema (YAML/JSON) |
| | Step 3: Implement visualization from schema |

---

## 2. Core Papers on Task Decomposition

### 2.1 MAKER: Solving Million-Step LLM Tasks (arXiv:2511.09030)

**Citation**: Meyerson et al. "Solving a Million-Step LLM Task with Zero Errors." November 2025.

**Key findings**:
- First system to solve 1M+ LLM steps with zero errors
- Approach: "Extreme decomposition" into subtasks, each handled by focused microagents
- Multi-agent voting at each step for error correction
- High modularity enables localized error correction

**Quote**: "Instead of relying on continual improvement of current LLMs, massively decomposed agentic processes (MDAPs) may provide a way to efficiently solve problems at the level of organizations and societies."

**Relevance**: Demonstrates that decomposition is not just helpful but essential for reliability at scale.

---

### 2.2 Divide-and-Conquer Reasoning (arXiv:2602.02477)

**Citation**: Liang et al. "Training LLMs for Divide-and-Conquer Reasoning Elevates Test-Time Scalability." February 2026.

**Key findings**:
- DAC reasoning decomposes problems into subproblems, solves sequentially, combines
- **+8.6% Pass@1** and **+6.3% Pass@32** over Chain-of-Thought
- CoT's "strictly sequential nature constrains test-time scalability"
- End-to-end RL framework for DAC-style reasoning

**Relevance**: Direct evidence that decomposition outperforms sequential CoT on complex tasks.

---

### 2.3 Lifecycle-Aware Code Generation (arXiv:2510.24019)

**Citation**: Xing et al. "Lifecycle-Aware code generation: Leveraging Software Engineering Phases in LLMs." October 2025.

**Key findings**:
- Incorporates intermediate artifacts: requirements analysis, state machine modeling, pseudocode
- **75% improvement** in code correctness with lifecycle-level fine-tuning
- Multi-step inference consistently surpasses single-step generation
- **Key result**: "State machine modeling yields the most substantial impact"
- Each intermediate artifact contributes distinctly to final quality

**Quote**: "Performance gains compound across intermediate stages."

**Relevance**: For visualization, defining structure (schema) before implementation should have highest impact.

---

### 2.4 TMK Framework for Planning (arXiv:2602.03900)

**Citation**: Goh et al. "Knowledge Model Prompting Increases LLM Performance on Planning Tasks." February 2026.

**Key findings**:
- Task-Method-Knowledge (TMK) framework for task decomposition
- TMK prompting: 31.5% → **97.3% accuracy** on symbolic planning tasks
- TMK provides explicit representations of "what to do, how to do it, and why"

**Relevance**: Structured decomposition frameworks outperform implicit CoT.

---

## 3. Papers on Intermediate Artifacts

### 3.1 SemanticALLI: Caching Intermediate Representations (arXiv:2601.16286)

**Citation**: Chillara et al. "SemanticALLI: Caching Reasoning, Not Just Responses, in Agentic Systems." January 2026.

**Key findings**:
- Decomposes visualization generation into: Analytic Intent Resolution (AIR) → Visualization Synthesis (VS)
- Intermediate representations (IRs) as first-class, cacheable artifacts
- **83.10% hit rate** on Visualization Synthesis stage
- Bypassed 4,023 LLM calls with 2.66ms median latency
- Monolithic caching: only 38.7% hit rate due to linguistic variance

**Key insight**: "Even when users rarely repeat themselves, the pipeline often does, at stable, structured checkpoints where caching is most reliable."

**Relevance**: Chained execution enables reuse, not just quality improvement.

---

### 3.2 π-CoT: Prolog-Initialized CoT (arXiv:2506.20642)

**Citation**: Wan et al. "$\pi$-CoT: Prolog-Initialized Chain-of-Thought Prompting for Multi-Hop QA." June 2025.

**Key findings**:
- Reformulates questions into Prolog queries → single-hop sub-queries
- Resolves sequentially, producing intermediate artifacts
- Uses artifacts to initialize subsequent CoT reasoning
- Significantly outperforms standard RAG and in-context CoT

**Relevance**: Intermediate artifacts can be formal/verifiable (Prolog, not just natural language).

---

### 3.3 R-LAM: Reproducibility-Constrained LAMs (arXiv:2601.09749)

**Citation**: Sureshkumar. "R-LAM: Reproducibility-Constrained Large Action Models." January 2026.

**Key findings**:
- Structured action schemas, deterministic execution policies
- Explicit provenance tracking for every intermediate artifact
- Enables auditability and replayability
- Failure-aware execution loops with controlled workflow forking

**Relevance**: Intermediate artifacts enable verification, debugging, and reproducibility.

---

### 3.4 CLIPPER: Compression-Based Synthetic Data (arXiv:2502.14854)

**Citation**: Pham & Chang. "CLIPPER: Compression enables long-context synthetic data generation." February 2025.

**Key findings**:
- Compresses books into chapter outlines and summaries (intermediate representations)
- Uses IRs to generate complex claims with CoT reasoning
- **28% → 76% accuracy** improvement over naive approaches

**Relevance**: Intermediate representations improve generation quality even for synthetic data.

---

## 4. Multi-Step Reasoning & Planning

### 4.1 daVinci-Agency: Long-Horizon Agency (arXiv:2602.02619)

**Citation**: Jiang et al. "daVinci-Agency: Unlocking Long-Horizon Agency Data-Efficiently." February 2026.

**Key findings**:
- Progressive task decomposition via continuous commits
- Long-term consistency through unified functional objectives
- Verifiable refinement from bug-fix trajectories
- 239 samples yield **47% relative gain** on Toolathlon benchmark

**Relevance**: PR-like decomposition preserves causal dependencies across steps.

---

### 4.2 ToolCoder: Code-Empowered Tool Learning (arXiv:2502.11404)

**Citation**: Ding et al. "ToolCoder: A Systematic Code-Empowered Tool Learning Framework." ACL 2025.

**Key findings**:
- Transforms NL queries into Python function scaffolds
- Descriptive comments break down tasks
- Code reuse via repository storage
- Systematic debugging via error traceback

**Relevance**: Code as intermediate representation enables verification.

---

### 4.3 EviPath: Evidence-Anchored Reasoning (arXiv:2509.23071)

**Citation**: Li et al. "From Evidence to Trajectory: Abductive Reasoning Path Synthesis." September 2025.

**Key findings**:
- Abductive Subtask Planning: decomposes problems into sub-questions
- Plans optimal path based on dependencies
- Faithful Sub-question Answering with supporting evidence
- **14.7% EM gain** over baselines

**Relevance**: Dependency-aware decomposition outperforms sequential decomposition.

---

## 5. Domain-Specific Studies

### 5.1 Chart/Visualization Generation

**ChartGPT** (Tian et al., IEEE VIS 2024):
- Step-by-step reasoning pipeline for chart generation
- Fine-tuning on decomposition-style data

**VisEval** (Chen et al., IEEE TVCG 2025):
- 2,524 NL2VIS queries
- Automated evaluation: validity, legality, readability

**LORE** (Lu et al., arXiv:2512.03025):
- "CoT often hits performance ceiling" in relevance tasks
- Qualitative-driven decomposition breaks through bottlenecks
- Decomposes into: knowledge/reasoning, multi-modal matching, rule adherence

### 5.2 Code Generation

**Lifecycle-Aware** (Xing et al., arXiv:2510.24019):
- Requirements analysis → State machine → Pseudocode → Code
- 75% improvement; state machines have highest impact

**MOSAIC** (Raghavan & Mallick, arXiv:2510.08804):
- Multi-agent for scientific coding
- Consolidated Context Window (CCW) for chained subproblems

### 5.3 SQL/Query Generation

**DeKeyNLU** (Chen et al., arXiv:2509.14507):
- Task decomposition + keyword extraction for NL2SQL
- **62.31% → 69.10%** on BIRD, **84.2% → 88.7%** on Spider

---

## 6. Key Synthesis: What the Literature Tells Us

### 6.1 Decomposition Helps (Strong Evidence)

| Paper | Improvement | Task Type |
|-------|-------------|-----------|
| MAKER | 0% error rate (from derailment) | Long-horizon planning |
| Divide-and-Conquer | +8.6% Pass@1 | Competition benchmarks |
| Lifecycle-Aware | +75% correctness | Code generation |
| TMK Framework | 31.5% → 97.3% | Symbolic planning |
| SemanticALLI | 83% cache hit rate | Visualization |

### 6.2 Intermediate Artifacts Enable (Strong Evidence)

| Capability | Evidence |
|------------|----------|
| **Verification** | R-LAM, π-CoT |
| **Caching/Reuse** | SemanticALLI |
| **Debugging** | ToolCoder, MOSAIC |
| **Reproducibility** | R-LAM |

### 6.3 Decomposition Granularity (Moderate Evidence)

- **MAKER**: Extreme decomposition (microagents) enables million-step tasks
- **Lifecycle-Aware**: 3-4 stages (requirements, state machine, pseudocode, code) sufficient
- **SemanticALLI**: 2 stages (intent, visualization) enable 83% caching

### 6.4 Artifact Format (Moderate Evidence)

| Format | Use Case | Paper |
|--------|----------|-------|
| Code/Python | Tool use, debugging | ToolCoder |
| Prolog/Logic | Multi-hop reasoning | π-CoT |
| State machines | Code generation | Lifecycle-Aware |
| Summaries/Outlines | Long-context synthesis | CLIPPER |
| JSON/YAML schemas | Visualization | SemanticALLI |

---

## 7. Gap Analysis: What's Missing

### 7.1 Direct Comparison: One-Shot vs. Chained

**No paper directly compares**:
1. One-shot: "Create visualization" with all rules in prompt
2. Chained: Choose type → Define schema → Implement

The closest is Lifecycle-Aware Code Gen, which shows multi-step > single-step but doesn't isolate the effect of intermediate artifacts.

### 7.2 Cost-Latency Trade-offs

Most papers report quality improvements but not:
- Token cost comparison (chained vs. one-shot)
- Latency impact of additional LLM calls
- When decomposition is overkill

### 7.3 Model Size Interaction

Unclear whether frontier models (Claude, GPT-4) benefit as much as smaller models.

### 7.4 Artifact Quality Metrics

How to measure whether an intermediate artifact (e.g., YAML schema) is correct before proceeding?

---

## 8. Implications for Product Development

See `implications-aictrl.md` for detailed product recommendations.

**Summary**:
1. **Planning tools**: Should generate structured intermediate artifacts (schemas, state machines)
2. **Validation tools**: Can verify intermediate artifacts before execution
3. **Caching**: Decomposition enables reuse across similar requests
4. **Debugging**: Intermediate artifacts expose failure points

---

## 9. Recommended Reading Order

1. MAKER (arXiv:2511.09030) - Vision for extreme decomposition
2. Lifecycle-Aware (arXiv:2510.24019) - Practical intermediate artifacts
3. SemanticALLI (arXiv:2601.16286) - Caching and reuse
4. Divide-and-Conquer (arXiv:2602.02477) - Quantitative comparison vs. CoT

---

## 10. References (BibTeX)

```bibtex
@article{meyerson2025maker,
  title={Solving a Million-Step LLM Task with Zero Errors},
  author={Meyerson, Elliot and others},
  journal={arXiv preprint arXiv:2511.09030},
  year={2025}
}

@article{liang2026dac,
  title={Training LLMs for Divide-and-Conquer Reasoning Elevates Test-Time Scalability},
  author={Liang, Xiao and others},
  journal={arXiv preprint arXiv:2602.02477},
  year={2026}
}

@article{xing2025lifecycle,
  title={Lifecycle-Aware code generation: Leveraging Software Engineering Phases in LLMs},
  author={Xing, Xing and others},
  journal={arXiv preprint arXiv:2510.24019},
  year={2025}
}

@article{chillara2026semanticalli,
  title={SemanticALLI: Caching Reasoning, Not Just Responses, in Agentic Systems},
  author={Chillara, Varun and others},
  journal={arXiv preprint arXiv:2601.16286},
  year={2026}
}

@article{wan2025picot,
  title={$\pi$-CoT: Prolog-Initialized Chain-of-Thought Prompting for Multi-Hop Question-Answering},
  author={Wan, Chao and others},
  journal={arXiv preprint arXiv:2506.20642},
  year={2025}
}

@article{goh2026tmk,
  title={Knowledge Model Prompting Increases LLM Performance on Planning Tasks},
  author={Goh, Erik and Kos, John and Goel, Ashok},
  journal={arXiv preprint arXiv:2602.03900},
  year={2026}
}
```
