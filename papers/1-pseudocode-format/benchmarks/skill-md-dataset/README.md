# Skill-MD: A Benchmark for LLM Skill-Instruction Formats

Skill-MD evaluates how different instruction formats (plain prose, Markdown, pseudocode) affect LLM code-generation quality. Each domain provides structured tasks, format-specific skill files, and a rubric for automated scoring.

## Structure

```
skill-md-dataset/
  chart/
    skills/          2 SKILL.md files (markdown, pseudocode)
    tasks/           3 task JSONs (Economist/FT-style chart generation)
  dockerfile/
    skills/          2 SKILL.md files
    tasks/           3 task JSONs (production Dockerfile generation)
    rubric.md        13 automatable + 1 manual rule
  sql-query/
    skills/          2 SKILL.md files
    tasks/           3 task JSONs (dbt-style analytical SQL pipelines)
    rubric.md        14 automatable rules
  terraform/
    skills/          2 SKILL.md files
    tasks/           3 task JSONs (AWS infrastructure modules)
    rubric.md        14 automatable rules
```

The chart domain's rubric (15 rules) is embedded in its evaluator (`scripts/evaluate_deep.py`) rather than a separate file.

## Task Format

Each task is a JSON file with:

```json
{
  "task_id": "1",
  "domain": "dockerfile",
  "description": "Write a production Dockerfile for ..."
}
```

The `description` field is the prompt sent to the LLM.

## Skill Formats

Each domain has two skill variants under `skills/`:

| Directory suffix | Format |
|-----------------|--------|
| `*-markdown/SKILL.md` | Structured Markdown (headers, lists, tables) |
| `*-pseudocode/SKILL.md` | Pseudocode (IF/THEN rules, indented blocks) |

A third condition (**none**) sends only the task description with no skill file.

## Evaluation

Each domain's evaluator parses the LLM output, extracts the artifact (Dockerfile, SQL, HCL, or chart JSON), and checks it against 13-15 binary rules. The `auto_score` is the count of passing rules.

## Summary Statistics

| Dimension | Count |
|-----------|-------|
| Domains | 4 |
| Skill formats | 2 (+ none baseline) |
| Tasks per domain | 3 |
| Total tasks | 12 |
| Rubric rules per domain | 13-15 |

## License

CC-BY-4.0. See [`../LICENSE-DATA`](../LICENSE-DATA).

## Citation

If you use Skill-MD, please cite:

```bibtex
@article{skillmd2026,
  title={Pseudocode Beats Prose: Structured Skill Instructions Improve LLM Code Generation},
  year={2026}
}
```
