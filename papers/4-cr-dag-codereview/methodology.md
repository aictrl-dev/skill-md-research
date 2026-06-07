# Code Review as a Directed Acyclic Graph: Framework, Node Roles, and the Design Space

**Status:** methodology draft (no results). This document specifies the framework, the
catalogue of graph topologies, the roles nodes play, and the axes of the design space.
Its purpose is to give a precise vocabulary for *describing the space of choices* in
local-LLM code review, so that empirical work can be positioned against an explicit map
rather than an ad-hoc list of experiments.

---

## 1. Framework: review as artefact-passing over a DAG

We model an automated code review as a directed acyclic graph `G = (V, E)`. Each node
`v ∈ V` is a transformation that consumes a set of typed **artefacts** and produces one
or more typed artefacts; each edge `e ∈ E` carries an artefact from a producer to a
consumer. Execution is a topological pass; a designated **terminal operator** reduces the
nodes' outputs into the review's final finding set.

Three artefact types suffice for the work described here:

| Artefact | Produced by | Shape |
|---|---|---|
| `code` | the task (input) | source file(s) under review |
| `findings` | model nodes | list of `{file, line, severity, title, description, confidence}` |
| `context` | script nodes | free text injected into a downstream prompt |

A node declares its `inputs` (artefacts it reads) and `outputs` (artefacts it emits).
Because inputs reference named upstream nodes, the graph is explicit and the data flow is
auditable — a property we exploit both for ablation (score any single node in isolation)
and for failure handling (a node that cannot produce its artefact excludes the task
rather than silently emitting an empty one).

### 1.1 Two node classes, one budget

The dominant cost of local-LLM review is model invocation. We therefore distinguish:

- **Model nodes** — invoke the LLM; each consumes one unit of the **AI-node budget**.
- **Script nodes** — deterministic programs; **no AI-node budget**. They exist to move
  work *out* of the model wherever a computation is exact (graph queries, set arithmetic
  over prior findings, static checks).

The AI-node budget is the primary cost axis: a topology's price is the number of model
nodes per review, independent of how many script nodes it uses. This separation is a
design lever in itself — pushing a sub-task into a script node buys determinism and
removes a model call.

---

## 2. Node roles

### 2.1 Model nodes

- **Review lens.** A reviewer scoped to one *topic* of defect (e.g. security/authorization,
  correctness/logic, concurrency, input-validation/contracts, edge-cases). Lenses are the
  unit of *breadth*: each is prompted to ignore other classes, so the panel partitions the
  defect space.
- **Framing / persona.** A reviewer whose *stance* is varied rather than its topic
  (e.g. neutral auditor, adversary probing for exploits, on-call engineer in an incident).
  Framings are a unit of *decorrelation*: the same code viewed under a different affective
  prompt activates different behaviour, surfacing a partly different finding set.
- **Verifier / judge.** A node that consumes a *findings* artefact (not raw code) and
  emits a filtered or annotated set — intended as a precision gate. Variants include a
  list-pruning judge and a per-finding *proof-obligation* (require a reproduction + a
  failing test). A model run with extended deliberation ("thinking") is a degenerate
  verifier: high precision, low yield.

### 2.2 Script nodes (deterministic, no AI budget)

- **Context prefetch.** Queries an external source and injects the result as `context`.
  The instance used here pulls a code knowledge-graph (per-function caller counts, file
  blast-radius, historical co-changes) so a downstream lens can weight findings by impact
  and discount unreferenced (dead) code.
- **Coverage map.** Reduces all prior-round `findings` into a structured statement of what
  has been covered and what has not: `already_found`, `covered_files`,
  `covered_bug_classes`, `unexplored_symbols`, `unexplored_failure_modes`. This converts
  the implicit "look elsewhere" instruction into an explicit, computed target set.
- **(Anticipated) static analysis / test execution.** On a buildable corpus these would be
  script nodes producing objective `context`/verdicts; the present benchmark (isolated
  snippets) cannot host them, which is itself a finding about benchmark design (§5).

### 2.3 Terminal operators (how node outputs become the review)

- **single** — emit one named node's findings verbatim (used by replace/filter chains).
- **union** — merge all nodes' findings, de-duplicated by `file + line` proximity. The
  default when later nodes emit *incremental* findings; maximises recall.
- **vote** — like union, but every retained finding is annotated with `votes` (how many
  nodes surfaced it) and `nLenses` (how many distinct lenses agreed). Keeps all findings
  (recall preserved) while exposing an *agreement* signal for downstream ranking.
- **judge** — a model node is the terminal reducer (see Verifier).

The terminal operator is a first-class design choice, not an implementation detail: it
determines whether the graph optimises for coverage, for a ranked/triaged list, or for a
filtered high-precision set.

---

## 3. Topology catalogue

Each topology is a reusable graph pattern. We describe its structure and the design
question it isolates; results are deliberately out of scope here.

1. **Single pass.** One review lens over the code. The floor of the curve; establishes the
   single-call baseline and the recall ceiling of one generation.

2. **Parallel union panel (breadth).** `N` distinct topic lenses over the same code,
   `union` terminal. Probes whether *distinct lenses* find distinct defects — i.e. the
   marginal value of breadth.

3. **Resampling (depth).** A lens repeated `K` times (same prompt), `union`/`vote`
   terminal. Exploits sampling stochasticity: repetition surfaces different findings each
   run. Probes breadth-vs-depth at equal budget.

4. **Directed rounds.** Resampling where later rounds *see prior findings* and are told to
   avoid them. Two carry-forward mechanisms: (a) **free-text** — prior findings listed in
   the prompt; (b) **structured** — a *coverage-map* script node computes the uncovered
   cells. Probes whether directing the resample converts rediscovery into fresh coverage.

5. **Coverage-directed panel.** The winning recall shape's structure: `5 lenses × 3 rounds`
   with a coverage-map script node between rounds and a `vote` terminal. Combines breadth
   (lenses), depth (rounds), and directed carry-forward (coverage) in one graph.

6. **Consensus-vote.** Independent resamples with a `vote` terminal, using `votes`/`nLenses`
   as a *local* agreement signal. Probes whether statistical agreement across decorrelated
   voters is a usable precision/triage signal (as opposed to a model self-judgment).

7. **Heterogeneous / mix.** A layer whose nodes differ in *capability* or *stance*: e.g. a
   subset of lenses receives KG `context` while the rest do not, or each round carries a
   different framing. Probes whether a panel that is diverse in capability/stance beats a
   homogeneous one — targeted use of an external signal rather than blanket use.

8. **Verification gate.** A discovery panel followed by a verifier node (judge /
   proof-obligation / thinking pass). Probes the precision/recall trade of model-side
   filtering.

---

## 4. The design space

The topologies above are points in a structured space. We name the axes so that any
configuration can be specified as a coordinate, and so that the unexplored region is
visible.

| Axis | Question it answers | Options instantiated here |
|---|---|---|
| **Budget** | how many model calls per review | 1, 3, 5, 10, 15 AI nodes |
| **Breadth** | how many *distinct* lenses | 1 … 15 topic lenses |
| **Depth** | how many *resamples* per lens | ×1 … ×3 rounds |
| **Decorrelation axis** | what makes resamples differ | topic / affective framing / sampling **temperature** |
| **Direction** | do later resamples avoid prior coverage | independent / directed-free-text / directed-coverage-map |
| **Terminal operator** | how outputs reduce to the review | single / union / vote / judge |
| **External evidence** | objective signal beyond the prompt | none / KG (model-driven *or* prefetch) / (static-analysis, test-exec — benchmark-gated) |
| **Per-node heterogeneity** | is the layer uniform or mixed | homogeneous / capability-mix / framing-mix |
| **Verification** | is there a precision gate | none / list-judge / proof-obligation / thinking |

Two structural observations frame the space:

- **Breadth and depth both spend the same budget** but exploit different mechanisms
  (partitioning the defect space vs sampling variance). Their relative value, and the point
  of diminishing returns on each, is the first thing the space asks.
- **Decorrelation is the lever that makes depth pay.** Identical resamples rediscover the
  same findings; resamples that differ along a decorrelation axis (topic, framing, or
  temperature) cover more. Temperature and framing are *budget-neutral* decorrelation
  (no extra nodes), which makes them attractive coordinates to probe.

---

## 5. Methodological commitments

These hold regardless of which point in the space is under test, and are stated here so
results elsewhere can be read against them.

- **Dual scoring.** Every finding set is scored twice: against the *full* oracle and
  against a *real-bug* subset (entries tagged as user-impacting, as opposed to
  theoretical/cosmetic). The two diverge sharply and must be reported together.
- **Relaxed matching.** A finding matches an oracle entry on `file` and `line ±5`, without
  requiring severity agreement; unparsable line references do not match (they would
  otherwise match any entry in the file).
- **F2 as the decision metric.** For triage, a missed real defect costs more than a false
  positive; we weight recall over precision (β = 2). F2 is the metric against which design
  choices are judged.
- **Budget accounting in model nodes.** Cost is reported in AI-node count; script nodes are
  free. This keeps the cost axis comparable across topologies.
- **Harness integrity is part of the method.** Ensemble evaluation is unusually easy to
  corrupt silently. We treat three failure modes as first-class: (a) shared scratch state
  leaking artefacts between configurations (a merge that globs stale node outputs inflates
  recall and agreement counts); (b) a treatment node failing open (an unresolved context
  template or an errored script node turns a "KG" or "coverage" run into an untreated one);
  (c) over-lenient matching (null/[]-line findings matching anything). Each is detectable
  by an invariant — e.g. *votes ≤ number of model nodes* — and we report these invariants
  alongside results. A benchmark corpus of **isolated snippets** further bounds the space:
  it precludes static-analysis and test-execution nodes, so any precision lever that
  depends on objective execution cannot be evaluated here.

---

## 6. Implications and the experiment frontier

Describing the space this way makes the open questions explicit and gives an implementer a
starting map:

1. **Where is the breadth/depth knee, and does it move with budget?** (Axes: breadth ×
   depth × budget.)
2. **Which decorrelation axis is most efficient per node — topic, framing, or temperature
   — and do they stack?** Temperature and framing are budget-neutral, so a positive result
   is "free" recall.
3. **Does *directing* resampling (coverage-map) beat independent resampling at equal
   budget, once the carry-forward is actually injected?** (Direction axis.)
4. **Is cross-voter agreement (`votes`) a usable triage signal, and does it survive on
   held-out tasks** — i.e. is it a ranking aid even where it is not an F2 filter?
5. **Does heterogeneous capability (KG on a subset, framing-mix) beat a uniform layer**, and
   is targeted external evidence worth more than blanket use?
6. **What is the precision ceiling, and can any model-side verifier raise it** without
   surrendering the recall that the discovery panel produces?

For a practitioner, the immediate implications follow from the axes rather than from any
single number: spend budget on **decorrelated** model nodes (the recall engine); move exact
sub-tasks into **script nodes** (free determinism); pick the **terminal operator** to match
the goal (coverage vs ranked triage vs filtered set); and treat **objective external
evidence** as the lever most likely to raise precision — available only on a buildable
corpus, which is the single most consequential choice in benchmark design.
