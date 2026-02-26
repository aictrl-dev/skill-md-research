# Outcome Measurement Results

**Task**: Document Approval Workflow  
**Model**: GLM-4.7
**Date**: 2026-02-23

---

## Executive Summary

| Approach | Code Generated | Integration | Outcome |
|----------|----------------|-------------|---------|
| **One-shot** | ✓ Yes (8 files) | ✗ **OVERWROTE** existing files | ✗ BROKEN |
| **Two-phase** | ✓ Yes (4 files) | ✗ Wrong directory | ✗ NOT APPLIED |

**Neither approach produced working code.**

---

## Detailed Findings

### One-Shot Approach

**What happened:**
- Generated 8 code blocks
- Applied 4 files to codebase
- **Critical bug**: OVERWROTE `server/models/Document.ts`

**Before (original):**
```typescript
// 1384 lines of complex Document model with:
// - 50+ decorators
// - 20+ relationships
// - Complex scopes and hooks
```

**After (generated):**
```typescript
// 50 lines - completely new file
export class Document extends Model {
  async submitForApproval(actorId: string) { ... }
  async approve(actorId: string) { ... }
  async reject(actorId: string) { ... }
}
```

**Result**: Lost all existing Document model code. Codebase broken.

---

### Two-Phase Approach

**What happened:**
- Phase 1: Generated artifacts ✓
- Phase 2: Tool explored wrong directory
- Files written to wrong location

**Files created** (in wrong directory):
```
./server/migrations/20240101000000-add-approval-state.js
./server/models/Document.ts
./server/routes/api/documents/approval.ts
./server/presenters/document.ts
```

**Result**: Files not in codebase, not applied, not testable.

---

## Root Cause Analysis

### One-Shot Failure

| Problem | Cause |
|---------|-------|
| Overwrites existing code | Generates complete files, not patches |
| No integration awareness | Doesn't read existing code before writing |
| Wrong file format | Migration .ts but uses CommonJS syntax |

### Two-Phase Failure

| Problem | Cause |
|---------|-------|
| Wrong directory | Tool explores from CWD, not codebase |
| No file markers | Output format doesn't match extraction regex |
| Lost context | Phase 2 doesn't have codebase context |

---

## Outcome Comparison

| Metric | One-Shot | Two-Phase |
|--------|----------|-----------|
| Code blocks generated | 8 | 0 (wrote files directly) |
| Files applied | 4 | 0 |
| Existing code preserved | ✗ No | N/A |
| Syntactically valid | ⚠ Mixed | N/A |
| **Working outcome** | ✗ **BROKEN** | ✗ **NOT APPLIED** |

---

## Key Insight

**Neither approach works for real codebase integration.**

Why:
1. LLMs generate complete files, not patches
2. No awareness of existing code structure
3. No verification before write

---

## What Would Be Needed

To actually measure outcomes, need:

1. **Patch generation** - Generate diffs, not full files
2. **Context injection** - Read existing files before generating
3. **Safe apply** - Check if code integrates correctly
4. **Rollback** - Undo if compilation fails

---

## Conclusion

### Current Evidence

| Claim | Evidence |
|-------|----------|
| "Artifacts help" | No evidence |
| "Two-phase better" | No evidence |
| "Either works" | ✗ Both failed |

### Honest Answer

**We still cannot determine if artifacts improve outcomes.**

Both approaches produced code that:
- Doesn't integrate with existing codebase
- Would break the system if applied
- Cannot be verified

---

## Next Steps

To get real evidence:

1. **Use a sandbox** - Fresh codebase with no existing code
2. **Generate patches** - Not complete files
3. **Or**: Accept that outcome measurement requires different infrastructure

---

## Files Modified (One-Shot)

```
M server/models/Document.ts    - OVERWRITTEN (1384 → 50 lines)
M server/presenters/document.ts - OVERWRITTEN
A server/migrations/20240101000000-add-approval-state.ts
A server/routes/api/documents/approval.ts
```

## Files Created (Two-Phase, wrong dir)

```
./server/migrations/20240101000000-add-approval-state.js
./server/models/Document.ts
./server/presenters/document.ts
./server/routes/api/documents/approval.ts
```

---

## Recommendation

For aictrl.dev:
1. **Never let LLM write complete files** to existing codebases
2. **Generate patches/diffs only**
3. **Validate before applying**
4. **Always have rollback**
