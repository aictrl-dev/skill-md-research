# Evaluation Rubric

Each task output is scored on 5 dimensions (1-5 scale each, max 25 points).

## Dimensions

### 1. Compilability

| Score | Criteria |
|-------|----------|
| 1 | Does not compile - syntax errors or missing imports |
| 2 | Compiles with significant type errors |
| 3 | Compiles with warnings or minor type issues |
| 4 | Clean compile, 1-2 trivial warnings |
| 5 | Clean compile, zero warnings |

### 2. Completeness

| Score | Criteria |
|-------|----------|
| 1 | Missing major requirements (>50% not addressed) |
| 2 | Several requirements missing or only partially done |
| 3 | All requirements addressed, minor gaps |
| 4 | All requirements fully implemented, edge cases considered |
| 5 | All requirements fully implemented, plus sensible extras (validation, etc.) |

### 3. Pattern Adherence

| Score | Criteria |
|-------|----------|
| 1 | Ignores project conventions entirely |
| 2 | Follows some patterns, significant deviations |
| 3 | Follows most patterns, minor deviations (e.g., different error handling style) |
| 4 | Matches existing patterns closely, 1-2 minor style differences |
| 5 | Perfectly matches existing patterns (logger, error handling, imports, .js extensions, helpers) |

### 4. Type Safety

| Score | Criteria |
|-------|----------|
| 1 | Missing types, uses `any` extensively |
| 2 | Some types present but many `any` or incorrect types |
| 3 | Types present but imprecise (e.g., `string` where union type exists) |
| 4 | Correct types from project's type system, minimal imprecision |
| 5 | Correct types throughout, no `any`, leverages existing type definitions |

### 5. Correctness

| Score | Criteria |
|-------|----------|
| 1 | Logic errors, wrong methods called, would fail at runtime |
| 2 | Major logic issues, some correct paths |
| 3 | Mostly correct logic, edge cases missed |
| 4 | Correct logic, proper error paths, minor edge cases |
| 5 | Correct logic, proper error paths, right StateManager methods, handles all cases |

## Automated Checks (Binary Pass/Fail)

Applied before manual scoring:

| Check | Command | Applies To |
|-------|---------|------------|
| Backend compile | `npm run build` | All tasks |
| Backend lint | `npm run lint` | All tasks |
| UI compile | `cd ui && npm run build` | Task 3 only |
| UI lint | `cd ui && npm run lint` | Task 3 only |

## Scoring Process

1. Apply the generated patch to a clean checkout
2. Run automated checks, record pass/fail
3. Read the generated code and score each dimension
4. Record scores in `analysis/score-quality.md`
5. Calculate totals and per-task deltas
