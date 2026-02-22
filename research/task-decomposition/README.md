# Task Decomposition & Chained Execution for Verifiable LLM Tasks

## Research Question

**Does breaking down a task into intermediate artifacts and chained execution steps produce better results than one-shot prompting?**

Example: For creating a data visualization:
- **Chained approach**: 1. Choose chart type → 2. Define schema (YAML) → 3. Implement
- **One-shot approach**: Single prompt with all instructions

---

## TL;DR: Key Findings

| Finding | Evidence Strength | Source |
|---------|-------------------|--------|
| Decomposition improves complex task performance | Strong | Multiple papers (MAKER, DAC, Lifecycle-Aware) |
| Intermediate artifacts enable verification and caching | Strong | SemanticALLI, R-LAM |
| State machine/structure modeling has highest impact | Moderate | Lifecycle-Aware Code Gen |
| CoT alone hits performance ceiling | Strong | LORE, Divide-and-Conquer |
| Smaller models benefit more from decomposition | Moderate | Various ablation studies |

---

## Repository Structure

```
research/task-decomposition/
  README.md                    # This file - overview and TL;DR
  literature-review.md         # Full academic literature review
  implications-aictrl.md       # Product implications for aictrl.dev
  enterprise-decomposition.md  # Decomposing Epics/Stories
  experiment-design.md         # Visualization experiment design
  experiment-enterprise.md     # Enterprise task experiment
  codebase-selection.md        # Open-source codebase selection (Outline)
```

---

## Related Research in This Repo

- `../literature-review.md` - Pseudocode vs Markdown instruction formats
- `../experiment-plan.md` - Skill format comparison methodology
- `../../domains/chart/` - Chart generation experiments

---

## Quick Reference: Most Relevant Papers

### 1. MAKER: Million-Step LLM Tasks (arXiv:2511.09030)
**Key insight**: "Extreme decomposition" into microagents + multi-agent voting at each step enables **zero errors over 1M+ steps**.

**Relevance**: Shows decomposition is essential for reliability at scale.

### 2. Divide-and-Conquer Reasoning (arXiv:2602.02477)
**Key insight**: DAC-style reasoning achieves **+8.6% Pass@1** over Chain-of-Thought on competition-level benchmarks.

**Relevance**: Direct evidence that decomposition outperforms sequential reasoning.

### 3. Lifecycle-Aware Code Generation (arXiv:2510.24019)
**Key insight**: Intermediate artifacts (requirements, state machines, pseudocode) improve code correctness by **75%**. "State machine modeling yields the most substantial impact."

**Relevance**: For visualization - defining structure before implementation matters most.

### 4. SemanticALLI (arXiv:2601.16286)
**Key insight**: Decomposing visualization into Intent Resolution → Visualization Synthesis enables **83% cache hit rate** on intermediate representations.

**Relevance**: Chained execution enables reuse, not just quality.

### 5. π-CoT: Prolog-Initialized CoT (arXiv:2506.20642)
**Key insight**: Generating intermediate Prolog artifacts, then using them to initialize CoT, significantly outperforms standard RAG and CoT.

**Relevance**: Intermediate artifacts can be formal/verifiable, not just natural language.

---

## Open Questions

1. **Granularity trade-off**: How fine should decomposition be? (MAKER suggests extreme, but cost/latency?)
2. **Artifact format**: Should intermediate artifacts be structured (YAML, JSON, code) or natural language?
3. **Model size interaction**: Do frontier models (Claude, GPT-4) still benefit from decomposition?
4. **Domain specificity**: Does decomposition help equally for code vs. visualization vs. SQL?

## Enterprise Software Decomposition (NEW)

For decomposing Epics/Stories into executable work items:

| Task Type | Best Decomposition | Optimal Artifacts |
|-----------|-------------------|-------------------|
| **CRUD feature** | Stack (DB → API → UI → Test) | SQL → OpenAPI → HTML → Gherkin |
| **Business workflow** | Domain (bounded contexts) | State diagram → Gherkin → OpenAPI |
| **User flow** | Journey (per user action) | Gherkin → HTML → Component schema |
| **Integration** | Stack (isolate external) | OpenAPI → Gherkin → Code |

**Key hypothesis**: `Gherkin + OpenAPI + SQL` artifact set provides optimal verifiability.

See `enterprise-decomposition.md` for full analysis.

---

## Next Steps

1. Run experiment comparing one-shot vs. chained execution on chart generation
2. Measure intermediate artifact quality (schema validity, type correctness)
3. Test caching/reuse potential for common transformation patterns
