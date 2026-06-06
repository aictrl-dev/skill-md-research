# cr-skill-workflow: Iterative Code Review Workflow Framework

> **For agentic workers:** Use superpowers:executing-plans or superpowers:subagent-driven-development to implement the companion plan.

**Goal:** A lightweight experimentation sandbox for iterating on multi-step code review workflows with Gemma 4, tracking F1 improvement over the `cr-local-kg` baseline (per-run F1 = 0.204, union-of-3 F1 = 0.355).

**Philosophy:** The code review process is a DAG. Artefacts flow between nodes. We want to find the optimal DAG topology and prompt structure by running cheap experiments — starting with single-session workflow prompts, escalating to harness-orchestrated multi-call chains. Once a topology converges on good F1, the DAG collapses back into a single `SKILL.md` prompt (or structured skill chain). Python/LangGraph is a later option if types 1 and 2 are insufficient.

**Tech stack:** bash, TypeScript (npx tsx), aictrl CLI, Jinja2-style template substitution (implemented in the harness), existing `score-relaxed.ts` and `sync-sheet.ts` from `cr-local-kg`.

---

## Constraint: no oracle leakage

Prompts must never reference known bugs, golden-set findings, or `answer-key.json` content. The answer key is scoring-only. This is a hard constraint for all experiments.

---

## Experiment types

### Type 1 — workflow-in-prompt

One `aictrl run` call. The SKILL.md encodes the DAG as numbered workflow steps. Artefacts live in the model's context window — no file I/O, no external orchestration.

Example structure for a multi-step SKILL.md:

```markdown
## Workflow

**Step 1 — Scan**: Read the code. Produce a scratch JSON block of candidate findings.

**Step 2 — KG enrichment**: For each candidate call `aictrl_query_context`
(callers + impact). Annotate the scratch block with blast-radius notes.

**Step 3 — Filter**: Drop candidates with zero callers or confidence < 5.
Promote severity for candidates with many callers.

**Step 4 — Output**: Emit surviving findings as the final JSON array.
```

This is the cheapest hypothesis to test. No new infrastructure. Uses the existing `run-aictrl.sh` harness — just swap the experiment's `SKILL.md` and `aictrl.jsonc`.

### Type 2 — harness-orchestrated DAG

Multiple `aictrl run` calls, chained by `run-workflow.sh`. Each node produces a structured artefact (JSON); the harness renders the next node's prompt template with `{{node.artefact}}` substitution before spawning the next call.

```
run-workflow.sh:
  aictrl run pass1.md           → pass1-findings.json
  render pass2.md.j2            with {{ pass1.findings }}
  aictrl run pass2-rendered.md  → final findings.json
```

The shell script is the orchestrator. No native aictrl subagent tool required. If aictrl adds native task dispatch in future, type-2 experiments can upgrade to let the model trigger sub-calls directly.

---

## Experiment definition

### Type 1: single SKILL.md

```
experiments/cr-skill-workflow/experiments/exp-001-multistep-prompt/
  SKILL.md          ← workflow instructions (multi-step, single session)
  aictrl.jsonc      ← optional config override (default: shared aictrl-workflow.jsonc)
```

Run with:
```bash
scripts/run-workflow.sh --exp exp-001-multistep-prompt --rep 1
```

### Type 2: dag.yaml + prompt templates

```
experiments/cr-skill-workflow/experiments/exp-002-two-pass/
  dag.yaml
  prompts/
    pass1.md
    pass2.md.j2     ← uses {{ pass1.findings }}
```

`dag.yaml` schema:

```yaml
id: exp-002-two-pass
hypothesis: "Second pass sees first-pass findings and hunts for what was missed"
reps: 3          # default rep count; --rep N on CLI runs a single rep
nodes:
  pass1:
    prompt: prompts/pass1.md
    inputs: [code]           # code = task source files injected by harness
    outputs: [findings]      # findings = JSON array [{file,line,severity,title,description}]
  pass2:
    prompt: prompts/pass2.md.j2
    inputs: [code, pass1.findings]
    outputs: [findings]
output: pass2    # node whose findings.json becomes the task's final result
```

Run with:
```bash
scripts/run-workflow.sh --exp exp-002-two-pass --rep 1
```

---

## Template injection (`{{node.artefact}}`)

For type-2 prompts, `.j2` files use `{{ node_id.output_name }}` placeholders. The harness resolves these before passing the prompt to `aictrl run`.

Example `pass2.md.j2`:

```markdown
You are reviewing the same code for defects that a first pass may have missed.

## First-pass findings (already reported — do NOT repeat these)

```json
{{ pass1.findings }}
```

Focus on: defects the first pass missed, interactions between findings,
and issues in code paths the first pass did not examine.

--- FILE: {{ task.path }} ---
{{ task.code }}
```

The harness substitutes `{{ pass1.findings }}` with the JSON array written by the `pass1` node, renders the template to a temp file, and passes it as the prompt to the second `aictrl run` call.

Script nodes (future): a node with `type: script` and `run: scripts/kg-prefetch.ts` receives code file paths as CLI args and writes JSON artefact files. The harness injects them the same way.

---

## Directory structure

```
experiments/cr-skill-workflow/
  experiments/
    exp-001-multistep-prompt/
      SKILL.md
    exp-002-two-pass/
      dag.yaml
      prompts/
        pass1.md
        pass2.md.j2
  scripts/
    run-workflow.sh         ← main harness: type 1 wraps run-aictrl.sh;
                               type 2 executes dag.yaml node-by-node
    score.ts                ← thin wrapper calling cr-local-kg/score-relaxed.ts
    sync-experiment.ts      ← appends one row to Google Sheet per experiment run
  aictrl-workflow.jsonc     ← shared aictrl config (gemma4, MCP enabled)
  tasks → ../cr-local-kg/tasks              (symlink)
  answer-key.json → ../cr-local-kg/answer-key.json  (symlink)
  task-files → ../cr-local-kg/task-files    (symlink)
  results/
    exp-001/
      rep-1/treatment/files/PR-101.findings.json
      rep-1/treatment/modules/PR-201.findings.json
      scores.json           ← written by score.ts after all reps
    exp-002/
      …
```

Results use the same directory layout as `cr-local-kg/results/raw/` so `score-relaxed.ts` works with `--results-dir results/exp-NNN` unchanged.

---

## Harness: `run-workflow.sh`

Accepts `--exp <id> --rep <N> [--task <id>]`.

**Type 1 path** (no `dag.yaml`): delegates directly to `run-aictrl.sh` with `--config experiments/<id>/aictrl.jsonc` (or shared config) and `--results-dir results/<id>`. The experiment's `SKILL.md` is loaded via the `skills.paths` entry in the aictrl config.

**Type 2 path** (has `dag.yaml`): for each task, executes nodes in declaration order (topological sort for future branching):
1. Render prompt template (substitute `{{node.artefact}}` from previous node outputs)
2. Write rendered prompt to a temp file
3. Run `aictrl run --format json <rendered-prompt>` → session JSON
4. Run `parse-session.ts` → `artefact.json` in scratch dir
5. Repeat for next node
6. Copy final output node's `findings.json` to `results/<id>/rep-<N>/treatment/<class>/PR-<id>.findings.json`

Failure in one task never stops the sweep (same behaviour as existing harness).

---

## Scoring and tracking

After all reps complete:

```bash
npx tsx scripts/score.ts --results-dir results/exp-NNN
# → prints F1 table, writes results/exp-NNN/scores.json

npx tsx scripts/sync-experiment.ts --exp exp-NNN
# → appends row to Google Sheet
```

Google Sheet row columns:

| exp-id | hypothesis | F1 per-run | F1 union-3 | ΔF1 vs baseline | TP | FP | FN | avg s/task | type | notes |
|---|---|---|---|---|---|---|---|---|---|---|

Baseline for ΔF1: `cr-local-kg` treatment — per-run F1 = 0.204, union-of-3 F1 = 0.355.

`sync-experiment.ts` reads `scores.json` + `dag.yaml` (or `SKILL.md` header) for hypothesis text, emits Google Sheets MCP cells via the existing `sync-sheet.ts` pattern.

---

## First two experiments to run

**exp-001 — multi-step workflow prompt (type 1)**
Hypothesis: a structured 4-step SKILL.md (scan → KG enrich → filter → output) produces higher F1 than the current "verify with KG first" instruction by making the filtering step explicit.

**exp-002 — two-pass chain (type 2)**
Hypothesis: a second `aictrl run` that sees first-pass findings and is explicitly tasked with finding what was missed increases recall without hurting precision.

---

## Success criteria

An experiment is considered a positive signal if:
- Per-run F1 ≥ 0.220 (>+0.016 vs baseline), **or**
- Union-of-3 F1 ≥ 0.380 (>+0.025 vs baseline), **or**
- TP count increases without FP count increasing proportionally

Negative results are equally valuable — they rule out hypotheses and narrow the search space.
