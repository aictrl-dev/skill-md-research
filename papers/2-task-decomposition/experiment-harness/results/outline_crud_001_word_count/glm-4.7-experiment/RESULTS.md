# GLM-4.7 Experiment Results

**Date**: 2026-02-22
**Model**: zai-coding-plan/glm-4.7
**Task**: outline_crud_001_word_count

---

## Experiment Design

| Phase | Purpose | Prompt Type |
|-------|---------|-------------|
| Phase 1 | Generate artifacts | Strict format enforcement |
| Phase 2 | Implement code | Stack decomposition |

---

## Phase 1: Artifact Generation

### Prompt Strategy
Used **strict prompt** with explicit requirements:
- "You MUST output all 3 artifacts"
- "You MUST NOT explore codebase"
- "Output ONLY the 3 artifacts"

### Results

| Artifact | Generated | Quality |
|----------|-----------|---------|
| **Gherkin** | ✓ | 3 scenarios (basic) |
| **OpenAPI** | ✓ | Complete spec with schemas |
| **SQL** | ✓ | Migration + index |

### Gherkin Scenarios (3)
1. Word count auto-calculates on content change
2. Filtering by word_count
3. Sorting by word_count

### OpenAPI Spec
- GET/POST /documents
- GET/PUT /documents/{id}
- Document schema with word_count field
- Query params: word_count_min, word_count_max, sort_by

### SQL Migration
```sql
ALTER TABLE documents ADD COLUMN word_count INTEGER NOT NULL DEFAULT 0;
CREATE INDEX idx_documents_word_count ON documents(word_count);
```

---

## Phase 2: Implementation

### Discovery
GLM-4.7 explored the codebase and found the feature **already implemented** from a previous experiment.

### Existing Implementation (verified)
| Component | File | Status |
|-----------|------|--------|
| Migration | `20260222000000-add-word-count-to-documents.js` | ✓ Complete |
| Model field | `Document.ts:371-374` | ✓ wordCount field |
| Calculation | `Document.ts:99-117` | ✓ calculateWordCount() |
| Hook | `Document.ts:572-586` | ✓ BeforeSave hook |
| Presenter | `document.ts:66` | ✓ wordCount in response |
| Revision | `Revision.ts` + presenter | ✓ Also implemented |

---

## Comparison: One-Shot vs Two-Phase

| Metric | One-Shot (Haiku) | One-Shot (GLM-4.5) | Two-Phase (GLM-4.7) |
|--------|------------------|--------------------|---------------------|
| Gherkin | ✗ None | ✗ None | ✓ 3 scenarios |
| OpenAPI | ✗ None | ✗ None | ✓ Full spec |
| SQL | ⚠ Mentioned | ⚠ Mentioned | ✓ Complete |
| Code | Summary only | Diffs (incomplete) | N/A (already done) |
| Score | 32/100 | 47/100 | **Artifacts: 100%** |

---

## Key Findings

### 1. Strict Prompts Work
- Explicit "MUST" requirements force artifact generation
- "You MUST NOT explore" prevents context switching

### 2. Two-Phase Better Than One-Shot
| Approach | Artifacts Generated |
|----------|---------------------|
| One-shot | 0/3 (skipped) |
| Two-phase | 3/3 (complete) |

### 3. GLM Models Can Write Files
- Previous GLM-4.5-Flash run actually modified codebase
- Files persisted: migration, model, presenter

---

## Implications for aictrl.dev

### For Planning Tool
1. **Use two-phase prompting**:
   - Phase 1: Generate Gherkin + OpenAPI + SQL
   - Phase 2: Implement from artifacts
2. **Strict prompt format** to prevent skipping
3. **Validate artifacts** before proceeding to implementation

### For Validation Tool
- Gherkin → Run as tests
- OpenAPI → Schema validation
- SQL → Migration dry-run

---

## Artifact Examples

### Gherkin (abbreviated)
```gherkin
Feature: Word Count
  Scenario: Word count auto-calculates when document content changes
    Given a document exists with content "Hello world"
    When the document content is updated to "Hello world this is a test"
    Then the word_count field should be 7
```

### OpenAPI (abbreviated)
```yaml
components:
  schemas:
    Document:
      properties:
        word_count:
          type: integer
          description: Number of words in the document content
          readOnly: true
```

### SQL (complete)
```sql
-- Up
ALTER TABLE documents ADD COLUMN word_count INTEGER NOT NULL DEFAULT 0;
CREATE INDEX idx_documents_word_count ON documents(word_count);

-- Down
DROP INDEX IF EXISTS idx_documents_word_count;
ALTER TABLE documents DROP COLUMN word_count;
```

---

## Next Steps

1. Run on other task types (workflow, integration, UI)
2. Compare decomposition strategies (stack vs domain vs journey)
3. Measure implementation correctness (apply patches, run tests)
