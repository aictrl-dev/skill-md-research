# Experiment Harness: Ready to Run

## Verification Complete ✓

```bash
# Single run - DRY RUN
./scripts/run-decomposition-experiment.sh \
  --task outline_crud_001_word_count \
  --decomposition stack \
  --artifacts full \
  --rep 1 \
  --dry-run

# Output:
# Running: outline_crud_001_word_count/stack_full/rep_1
# Model: claude-3-5-haiku@20241022
# [DRY RUN] Would execute...
```

## Sample Prompt Generated

```
results/sample/prompt_sample.md
  Lines: 700
  Words: 1,953
```

## Experiment Sizes

| Mode | Runs | Description |
|------|------|-------------|
| Single | 1 | One task, one condition |
| Pilot | 3 | All models on first task |
| Full | 432 | All tasks × decomps × formats × models × reps |

## Commands

```bash
# Change to harness directory
cd research/task-decomposition/experiment-harness

# Run single experiment
./scripts/run-decomposition-experiment.sh \
  --task outline_crud_001_word_count \
  --decomposition stack \
  --artifacts full \
  --rep 1

# Run pilot (test all models)
./scripts/run-decomposition-experiment.sh --pilot

# Run full experiment
./scripts/run-decomposition-experiment.sh --full

# Generate sample prompt
./scripts/generate-sample-prompt.sh

# Evaluate results
python scripts/evaluate.py \
  --run-dir results/outline_crud_001_word_count/stack_full/rep_1
```

## Output Structure

```
results/
├── sample/
│   └── prompt_sample.md           # Generated sample
│
├── outline_crud_001_word_count/
│   ├── stack_nl/
│   │   ├── rep_1/
│   │   │   ├── prompt.md
│   │   │   ├── output.md
│   │   │   └── metrics.json
│   │   ├── rep_2/
│   │   └── rep_3/
│   ├── stack_gherkin/
│   ├── stack_gherkin_api/
│   ├── stack_full/
│   ├── domain_nl/
│   ├── ...
│   └── journey_full/
│
├── outline_workflow_001_approval/
├── outline_integration_001_slack/
└── outline_uiflow_001_wizard/
```

## Estimated Costs

| Model | Cost per 1K tokens | Est. per run | Pilot cost | Full cost |
|-------|-------------------|--------------|------------|-----------|
| Haiku | $0.25/$1.25 | ~$0.50 | $1.50 | $216 |
| Opus | $15/$75 | ~$5.00 | $15.00 | $2,160 |
| GLM-4-Flash | ~$0.10 | ~$0.20 | $0.60 | $86 |
| **Total** | | | **~$17** | **~$2,462** |

## Next Steps

1. **Run pilot** to verify setup
   ```bash
   ./scripts/run-decomposition-experiment.sh --pilot
   ```

2. **Evaluate pilot results**
   ```bash
   python scripts/evaluate.py --run-dir results/outline_crud_001_word_count/stack_full/rep_1
   ```

3. **Decide on full experiment scope**
   - Full 432 runs?
   - Reduced design (e.g., 2 models, 2 reps)?

4. **Run and analyze**
