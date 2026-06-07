# Related Work

Our framework sits at the intersection of three lines of research, each of which our DAG
makes a first-class, composable axis: (i) **sampling-based ensembling and multi-agent
review**, which our topologies (parallel union, resampling, directed rounds, consensus-vote)
and terminal operators generalize; (ii) **code-review benchmarks and evaluation
methodology**, against which we position our dual-oracle, F2-for-triage scoring and our
treatment of harness integrity as method; and (iii) **external evidence** — retrieval,
execution, static analysis, structural graphs, and prompt framing — which our deterministic
*script nodes* inject into a small local model. We review each in turn, then state the gap
our design-space framing fills.

> **Citation note.** References were located and cross-checked against arXiv/web by research
> agents. Entries dated 2026 (and a few late-2025) post-date the authors' primary familiarity
> and were accepted on the basis of that verification; the most load-bearing of these should
> be re-confirmed against the canonical source before submission. Any item that could not be
> verified is marked **[unverified]**.

---

## Ensembling, self-consistency, and multi-agent LLM review

A long line of work improves LLM outputs by drawing *multiple* samples and reducing them,
rather than trusting a single greedy decode. Self-consistency (Wang et al., 2022,
arXiv:2203.11171) samples a diverse set of chain-of-thought reasoning paths and marginalizes
over them by majority vote, yielding large gains on arithmetic and commonsense benchmarks
(e.g. +17.9% on GSM8K). The principle generalizes: "More Agents Is All You Need" (Li et al.,
2024, arXiv:2402.05120) shows a brute-force sample-and-vote ensemble ("Agent Forest") scales
monotonically with the number of agents and lets a small model rival a larger one. In code
generation, AlphaCode (Li et al., 2022, arXiv:2203.07814) draws very large sample sets, then
*filters* on example tests and *clusters* by execution behavior to select submissions — a
reduction operator driven by external evidence rather than a vote. These works occupy the
same axes our framework parameterizes: breadth (sample count), decorrelation (temperature,
tag/format randomization), and a terminal merge operator. The key contrast is the operator's
objective. Self-consistency and Agent Forest *converge* via majority vote, which is right
when one answer is correct; for review triage we instead want to *accumulate* distinct true
defects, favoring union/coverage merges over voting. Our consensus-vote-versus-union axis
tests exactly this tension, and AlphaCode's execution-filtered clustering motivates our
verifier/judge nodes and deterministic script nodes as evidence-based reducers.

A parallel thread assigns *roles* to multiple LLM instances. Multiagent debate (Du et al.,
2023, arXiv:2305.14325) has several model instances propose, critique, and revise over
rounds, improving factuality and reducing hallucination on black-box models. This is a
depth/directed topology — later rounds condition on earlier outputs — analogous to our
directed and coverage-directed rounds, though debate aims for *agreement* whereas our
directed rounds aim to *extend coverage* into gaps a prior round missed.

For code review specifically, CodeAgent (Tang et al., 2024, arXiv:2402.02172) builds a
communicative multi-agent team (author, reviewer, decision-maker) plus a QA-Checker
supervisor to curb prompt drift, evaluated across consistency, vulnerability, style, and
revision tasks. In vulnerability detection, MulVul (Wu et al., 2026, arXiv:2601.18847) uses
a coarse-to-fine Router-then-Detector design with retrieval tools and "Cross-Model Prompt
Evolution," reporting state-of-the-art Macro-F1 on PrimeVul; the prompt-evolution loop is an
automated way to specialize lenses, which we instead obtain cheaply via fixed topic-scoped
lenses and affective framings. Most relevant to our local-model constraint, a "3+1"
heterogeneous architecture (Wang et al., 2026, arXiv:2604.21282) runs three cloud experts
over complementary perspectives in parallel with a *local* lightweight verifier for
adversarial validation, reporting high F1 at near-total recall. This validates two of our
axes — heterogeneous per-node perspectives and a verification node — but still leans on large
cloud experts, whereas our panel is entirely small and local.

**Gap.** These lines establish that sampling, role specialization, debate, and verification
each help, but they do not offer an explicit, comparable *taxonomy of topologies and merge
operators* within a single design space. None isolates *budget-neutral* decorrelation —
varying topic, framing/persona, and temperature at fixed sample count — as a controlled axis,
nor studies which axes actually move a *recall-weighted* triage metric (F2) for review. And
apart from a single cloud-plus-local hybrid, none targets a *fully local, small-model*
panel, where the breadth-versus-depth and decorrelation trade-offs we map are most acute.

---

## Code-review benchmarks and evaluation methodology

Automated code review is increasingly evaluated with dedicated benchmarks, but the field has
not converged on how to score a reviewer, what counts as a "hit," or how to weight precision
against recall.

**Context-enriched fine-grained benchmarks.** ContextCRBench (Wang et al., 2025,
arXiv:2511.07017) argues that prior benchmarks supply only diffs, are noisy, and operate at
coarse (file/commit) granularity. It contributes a large set of validated, context-enriched
entries spanning hunk-level quality assessment, line-level defect localization, and comment
generation. Its line-level localization is the closest analogue to our matching criterion;
where ContextCRBench scales context and entry count, our contribution is the *scoring
contract* — an impact-tagged dual oracle and a relaxed (file + line±5) match that tolerates
the off-by-a-few-lines noise endemic to small-model output.

**PR-feedback benchmarks and the context-dilution finding.** SWE-PRBench (Kumar, 2026,
arXiv:2603.26130) evaluates PRs against human-annotated ground truth via a validated
LLM-as-judge and reports that frontier models detect only 15–31% of human-flagged issues
even in the favorable diff-only setting, and that models *degrade monotonically* as context
expands — a concise diff-with-summary prompt beats a larger full-context prompt ("more
context dilutes attention"). This motivates two of our choices: the low detection ceiling
confirms single-pass review is fundamentally *recall-bound*, justifying **F2 (recall-weighted)
as the triage decision metric** rather than F1; and the dilution result supports evaluating a
small model on tightly scoped DAG nodes rather than whole-repository context.

**Signal-to-noise and the precision/recall tension.** CR-Bench (Pereira et al., 2026,
arXiv:2603.11078) frames real-world utility as a signal-to-noise problem: agents tuned to
"find all hidden issues" achieve high recall but flood developers with low-actionability
findings, and the authors document a hidden trade-off between resolution and spurious
findings. CR-Bench's stance — that recall and precision must be reported jointly — underwrites
our **dual full/real-bug oracle**, which separates "noisy but technically correct" findings
from findings that matter, a distinction a single aggregate F1 obscures.

**LLM-as-judge reliability.** The judges used by these benchmarks are themselves error-prone.
Jin and Chen (2026, arXiv:2603.00539) show LLM reviewers systematically *overcorrect*,
misclassifying correct code as defective, and that prompting for detailed explanations
*raises* misjudgment rates. The broader literature documents position, verbosity, and
self-enhancement biases in LLM judges. These gaps are why we treat **evaluation-harness
integrity as part of the method** and catalogue concrete silent-failure modes — shared
mutable state contaminating ensemble nodes and inflating inter-node agreement, treatment
nodes that fail *open* (so an ablation looks effective), and over-lenient line matching that
turns near-misses into spurious hits.

**Gap.** Existing benchmarks measure ever-larger models against richer context, but none
provides an *impact-tagged dual scoring* protocol, defends **F2-for-triage** under
recall-bound single-pass review, or offers a reproducible catalogue of ensemble-evaluation
harness pitfalls. We contribute all three for *local* small-LLM review.

---

## External evidence: retrieval, execution, static analysis, and framing

A complementary line argues the largest gains come not from a stronger model but from
*evidence drawn from outside the prompt*. Our framework makes external signal a first-class,
deterministic citizen of the review DAG: a knowledge-graph prefetch node (per-function caller
counts, blast radius, co-change history) and a coverage-map node feed objective context to a
small local model, and we treat heavier execution/static analysis as *deferred script nodes*
gated on a buildable corpus.

**Execution agreement.** CodeT (Chen et al., 2022, arXiv:2207.10397) auto-generates tests
and selects code by *dual execution agreement* (consistency with generated tests and mutual
agreement among candidates), lifting HumanEval pass@1 substantially. The lesson we carry over
is that execution is a powerful *ranking* signal over candidates rather than a hard oracle; in
our DAG, test execution would be a deferred node that re-weights findings, not silently
discards them.

**Retrieval-augmented vulnerability detection.** Vul-RAG (Du et al., 2024, arXiv:2406.11147)
distills knowledge from historical CVEs into a knowledge base, retrieves by functional
semantics, and reasons over retrieved causes/fixes, improving accuracy and surfacing
previously-unknown bugs. This validates retrieval as an evidence injector — analogous to our
KG-prefetch node — though Vul-RAG retrieves *cross-repository vulnerability knowledge* whereas
our prefetch supplies *intra-repository structural facts*.

**Static analysis and its ceiling.** An empirical study of static methods for code-library
hallucinations (arXiv:2604.07755) finds analyzers catch a wide but bounded fraction of
hallucinations and establishes an *upper bound* on what static methods can ever catch. This
quantified ceiling is the core of our benchmark-design argument: static signal is cheap and
high-precision but partial, so it belongs as one composable node among several — and an
isolated-snippet benchmark cannot host it at all.

**Static verification via intermediate representations.** Zhou et al. (2026,
arXiv:2605.17926), an industrial experience report, verify code against natural-language
requirements with an AI rule-miner plus auditor, introducing a *structured intermediate
representation explicitly to reduce hallucination, output variability, and context loss*
without compilation or execution — mirroring our use of deterministic script nodes to emit
structured objective signal that bounds confabulation.

**Framing and contextual bias.** "Measuring and Exploiting Contextual Bias in LLM-Assisted
Security Code Review" (arXiv:2603.18740) shows a systematic *framing effect* across LLMs:
PR-metadata presentation can override semantic content and bias verdicts, even as an attack
vector. We invert this: rather than treating framing only as a vulnerability to redact, we
deploy adversary/incident-persona framing nodes deliberately as a *decorrelation axis* —
different framings induce different error modes whose disagreement is itself signal.

**Code knowledge graphs for review.** Tree-sitter-based code knowledge graphs (e.g.
Codebase-Memory, arXiv:2603.27277 **[unverified]**; and relation-first graphs for security
audits, Hound, arXiv:2510.09633 **[unverified]**) supply blast radius, call chains, and
test-linkage context to LLM reviewers at large token savings. These confirm the value of
structural prefetch but stop at *context provision for an interactive agent*; we instead emit
graph facts as deterministic node outputs consumed by a fixed local-model DAG.

**Gap.** These lines each demonstrate one evidence source in isolation, typically paired with
a large/hosted model. None treats heterogeneous external evidence as *composable script nodes
in a review DAG* with explicit gating, confronts the *benchmark-buildability prerequisite*
(execution and static analysis require a compilable, test-bearing corpus that isolated-snippet
benchmarks structurally cannot provide), or repurposes framing as a *budget-neutral
decorrelation axis* rather than a bias to suppress.

---

## Positioning: what this paper contributes

Across the three threads, the common gap is the absence of a single, explicit **design space**
in which these choices are named, composed, and compared. Prior work demonstrates individual
mechanisms — sampling+vote, role specialization, debate, retrieval, execution, static checks,
framing — usually one at a time and usually with a large hosted model. Our contribution is the
DAG framework that unifies them:

1. an explicit **topology × merge-operator** taxonomy (parallel union, resampling,
   directed/coverage-directed rounds, consensus-vote, heterogeneous mixes; reduced by
   union / vote / judge), so any configuration is a coordinate in a comparable space;
2. **budget-neutral decorrelation** (topic / framing / temperature) as a controlled axis,
   and the question of which axis moves a recall-weighted triage metric;
3. **external evidence as composable, gated script nodes** (KG-prefetch, coverage-map; with
   static analysis and test execution as benchmark-gated extensions), with the
   *buildable-corpus prerequisite* stated as a benchmark-design choice; and
4. an **evaluation contract for the local small-model setting** — impact-tagged dual scoring,
   F2-for-triage, and a reproducible catalogue of ensemble-harness integrity invariants.

The result is a map that lets an implementer reason about the *space of choices* rather than a
single tuned system, and that makes the unexplored region — and the experiments that would
chart it — explicit.

---

## References

- Wang et al., 2022. *Self-Consistency Improves Chain of Thought Reasoning in Language Models.* arXiv:2203.11171
- Li et al., 2024. *More Agents Is All You Need.* arXiv:2402.05120
- Li et al., 2022. *Competition-Level Code Generation with AlphaCode.* arXiv:2203.07814
- Du et al., 2023. *Improving Factuality and Reasoning in Language Models through Multiagent Debate.* arXiv:2305.14325
- Tang et al., 2024. *CodeAgent: Collaborative Agents for Software Engineering.* arXiv:2402.02172
- Wu et al., 2026. *MulVul: Multi-Agent Vulnerability Detection with Cross-Model Prompt Evolution.* arXiv:2601.18847
- Wang et al., 2026. *A 3+1 Heterogeneous (cloud experts + local verifier) Code-Review Architecture.* arXiv:2604.21282
- Wang et al., 2025. *ContextCRBench: A Context-Enriched Benchmark for Code Review.* arXiv:2511.07017
- Kumar, 2026. *SWE-PRBench: Evaluating LLM PR Review against Human Feedback.* arXiv:2603.26130
- Pereira et al., 2026. *CR-Bench: Signal-to-Noise in Agentic Code Review.* arXiv:2603.11078
- Jin and Chen, 2026. *Overcorrection in LLM Code Reviewers; Fix-Guided Verification.* arXiv:2603.00539
- Chen et al., 2022. *CodeT: Code Generation with Generated Tests.* arXiv:2207.10397
- Du et al., 2024. *Vul-RAG: Knowledge-Augmented Vulnerability Detection.* arXiv:2406.11147
- (Authors), 2026. *Static Methods for Detecting LLM Code(-Library) Hallucinations: Coverage and Upper Bounds.* arXiv:2604.07755
- Zhou et al., 2026. *Static Requirements-vs-Code Verification via an AI Rule-Miner and Structured IR* (industrial report). arXiv:2605.17926
- (Authors), 2026. *Measuring and Exploiting Contextual Bias in LLM-Assisted Security Code Review.* arXiv:2603.18740
- *Codebase-Memory: Tree-sitter Code Knowledge Graphs for LLM Review.* arXiv:2603.27277 **[unverified]**
- *Hound: Relation-First Code Knowledge Graphs for Security Audits.* arXiv:2510.09633 **[unverified]**
