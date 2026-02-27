# Pseudocode Beats Prose

Structured pseudocode outperforms both plain prose and Markdown when used as LLM skill instructions — achieving higher rule compliance across six coding domains and four models. [Read the paper](paper/main.pdf).

## Repository Structure

```
domains/           Six evaluation domains, each with skills, tasks, evaluator, and results
  chart/           Economist/FT-style data visualization
  commit-message/  Conventional Commits compliance
  dockerfile/      Production-ready Dockerfiles
  openapi-spec/    OpenAPI 3.1 specification generation
  sql-query/       Analytical SQL queries
  terraform/       AWS infrastructure modules
paper/             LaTeX source, compute_stats.py, and built PDF
scripts/           Experiment runners, figure generation, analysis
prompts/           The three prompt condition templates (none, markdown, pseudocode)
models/            Model configuration (dbt-style layer organisation)
```

## Try it Yourself

Walk through a single evaluation end-to-end using the **Dockerfile** domain.

### 1. Pick a domain and task

Each domain has a `test-data/` folder with task JSON files. Here's task 1:

```bash
cat domains/dockerfile/test-data/task-1-java-dashboard.json
```

```json
{
  "task_id": "1",
  "domain": "dockerfile",
  "description": "Write a production Dockerfile for a Java analytics dashboard..."
}
```

The `description` field is what gets sent to the LLM.

### 2. Build a prompt

Every domain has a `skills/` folder with two skill formats — `*-markdown/SKILL.md` and `*-pseudocode/SKILL.md`. The **none** condition uses no skill at all.

| Condition | What to send |
|-----------|-------------|
| **none** | Just the task description |
| **markdown** | `cat domains/dockerfile/skills/dockerfile-style-markdown/SKILL.md` + task description |
| **pseudocode** | `cat domains/dockerfile/skills/dockerfile-style-pseudocode/SKILL.md` + task description |

The prompt templates in `prompts/` show the exact framing used for each condition:
- `prompts/none.txt` — task description only
- `prompts/md.txt` — markdown skill + task
- `prompts/pc.txt` — pseudocode skill + task

### 3. Send to an LLM

Any LLM works. Example with the Claude CLI:

```bash
# Pseudocode condition
SKILL=$(cat domains/dockerfile/skills/dockerfile-style-pseudocode/SKILL.md)
TASK=$(python3 -c "import json; print(json.load(open('domains/dockerfile/test-data/task-1-java-dashboard.json'))['description'])")

claude -p "$SKILL

$TASK

Write a production Dockerfile. Output ONLY the Dockerfile." --model haiku --output-format text > my_output.txt
```

### 4. Save the output as a result JSON

The evaluator expects a JSON file with at least `run_id` and `raw_output`:

```bash
python3 -c "
import json
output = open('my_output.txt').read()
result = {
    'run_id': 'my_test_haiku_pseudocode_task1_rep1',
    'raw_output': output
}
json.dump(result, open('domains/dockerfile/results/my_test.json', 'w'), indent=2)
"
```

### 5. Evaluate

Run the domain evaluator on your result file:

```bash
python3 domains/dockerfile/evaluate_dockerfile.py domains/dockerfile/results/my_test.json
```

This appends a row to `domains/dockerfile/results/scores.csv` with per-rule pass/fail:

```
run_id, model, condition, task, ..., rule_1_tag_pass, rule_2_user_pass, ..., auto_score
```

Each `rule_N_*_pass` column is `True`/`False`; `auto_score` is the count of passing rules out of 13 automatable checks.

## Reproducing All Paper Results

From the `papers/1-pseudocode-format/` directory:

```bash
# Recompute all statistics reported in the paper
python3 paper/compute_stats.py

# Regenerate all figures
python3 scripts/generate_figures.py

# Rebuild the PDF (requires pdflatex + bibtex)
cd paper && pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

## Reproducibility Artifact

A single script reproduces all CSVs, statistics, and figures from the raw JSON outputs:

```bash
bash benchmarks/run_all_evals.sh
```

See [`benchmarks/README.md`](benchmarks/README.md) for prerequisites and details.

The [`benchmarks/skill-md-dataset/`](benchmarks/skill-md-dataset/) directory packages the Skill-MD evaluation benchmark as a standalone dataset with skills, tasks, and rubrics across four domains.
