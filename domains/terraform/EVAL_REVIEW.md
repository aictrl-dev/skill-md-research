# Terraform Evaluation Script Review

**File:** `evaluate_terraform.py`  
**Rubric:** `evaluation-rubric.md`  
**Reviewer:** Claude  
**Date:** 2026-02-20

## Summary

The Terraform evaluator covers 14 rules with good coverage of AWS best practices. Multi-file concatenation is a nice feature for LLM outputs that split code. Some regex patterns are fragile. Below are issues found.

---

## Issues

### 1. Block Body Extraction - Nested Braces (lines 235-247)

```python
def _extract_block_body(text: str, open_brace_pos: int) -> str:
    for i in range(open_brace_pos, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
```

**Problem:** Fails on nested braces inside strings or expressions:
```hcl
resource "aws_instance" "web" {
  user_data = templatefile("${path.module}/user_data.sh", {
    vars = jsonencode({ key = "value" })  # nested braces
  })
}
```

**Fix:** Parse HCL properly or track string literals separately.

---

### 2. Rule 9 Provider Block Removal (lines 399-404)

```python
text_no_provider = re.sub(
    r'provider\s+"[^"]+"\s*\{[^}]*\}',
    '',
    tf_text,
    flags=re.DOTALL,
)
```

**Problem:** `[^}]*` stops at first `}`, not matching provider blocks with nested content:
```hcl
provider "aws" {
  default_tags {
    tags = { Env = "dev" }  # nested braces
  }
}
```

**Fix:** Use brace-counting logic similar to `_extract_block_body`.

---

### 3. Extraction Pattern - Line Start Only (line 106-109)

```python
hcl_start = re.search(
    r'^(terraform|provider|resource|variable|data|locals|output)\s',
    text_to_search,
    re.MULTILINE,
)
```

**Problem:** Misses indented blocks:
```hcl
  resource "aws_vpc" "main" {  # leading whitespace
```

**Fix:** Change to `r'^\s*(terraform|...)'` to allow leading whitespace.

---

### 4. Multiple Fence Pattern Break (lines 91-98)

```python
for pattern in fence_patterns:
    for match in re.finditer(pattern, text_to_search, re.DOTALL):
        ...
    if all_blocks:
        break  # use the first pattern that matched
```

**Problem:** If output has both ````hcl` and ````terraform` fences, only one type is collected.

**Fix:** Remove the break, collect from all patterns.

---

### 5. Rule 10 Version Location (lines 420-430)

```python
if re.search(r'required_providers\s*\{', tf_text):
    if re.search(r'version\s*=\s*"[^"]*"', tf_text):
```

**Problem:** Matches any `version = "..."` anywhere in the terraform block, not necessarily inside a provider namespace:
```hcl
terraform {
  required_version = "1.5.0"  # This is NOT provider version
  required_providers {
    aws = { source = "hashicorp/aws" }  # Missing version!
  }
}
```

**Fix:** Check for `version` inside a provider block pattern like `aws\s*=\s*\{[^}]*version\s*=`.

---

### 6. TAGGABLE_RESOURCES Accuracy (lines 24-32)

**Problem:** Some listed resources don't actually support tags directly:
- `aws_s3_bucket_versioning` - Tags go on the bucket, not this sub-resource
- `aws_s3_bucket_server_side_encryption_configuration` - Same
- `aws_s3_bucket_public_access_block` - Same
- `aws_s3_bucket_lifecycle_configuration` - Same

These will false-negative on tag checks.

**Fix:** Remove sub-resources from taggable list or note as known limitation.

---

### 7. Rule 1 Naming - Borderline Cases (line 259)

```python
BAD_NAME = re.compile(r'^[a-z]{1,3}\d*$')
```

**Problem:** These pass but are poor names:
- `this` (4 chars, passes)
- `that` (4 chars, passes)
- `main` (4 chars, passes - common and acceptable)
- `app` (3 chars, no digits, passes)

**Fix:** Consider adding a list of known bad short names: `this`, `that`, `temp`, `test`.

---

### 8. Rule 5 Dynamic Tags Not Detected (line 324)

```python
if not re.search(r'\btags\s*=', body):
```

**Problem:** Dynamic blocks don't match:
```hcl
resource "aws_instance" "web" {
  dynamic "tag" {
    for_each = local.tags
    content { ... }
  }
}
```

Rubric acknowledges this limitation. Consider adding check for `dynamic\s+"tag"`.

---

### 9. Rule 7 Variable Separation (lines 343-364)

```python
blocks = re.findall(r'^\s*(resource|variable)\b', tf_text, re.MULTILINE)
```

**Problem:** Only checks `resource` and `variable`, ignoring `data`, `locals`, `output` blocks. This interleaving is also bad:
```hcl
resource "aws_vpc" "main" { ... }
data "aws_ami" "linux" { ... }      # OK by current check
variable "region" { ... }           # Flagged
resource "aws_instance" "web" { ... }
```

**Fix:** Include `data`, `locals`, `output` in the interleaving check.

---

### 10. Rule 11 Backend - Terraform Cloud (line 435)

```python
if re.search(r'backend\s+"[^"]+"\s*\{', tf_text):
```

**Problem:** Doesn't match Terraform Cloud/Enterprise:
```hcl
terraform {
  cloud {
    organization = "my-org"
    workspaces { name = "prod" }
  }
}
```

**Fix:** Add alternative pattern: `cloud\s*\{` as valid backend equivalent.

---

### 11. Rule 4 Outputs - No Validation (lines 304-309)

**Problem:** Only checks output exists, not that it has required attributes:
```hcl
output "vpc_id" {
  # Missing value = ... - invalid Terraform!
}
```

**Fix:** Check for `value\s*=` inside output body.

---

### 12. Unmatched Brace Handling (lines 246-247)

```python
# Unmatched brace — return everything from start
return text[start:]
```

**Problem:** If braces are unmatched, returns entire rest of file. Could cause cascading failures in downstream checks.

**Fix:** Return empty string or log warning, don't silently include rest of file.

---

## Minor Issues

### Rule 2 Empty Description

Empty description `description = ""` passes regex but is poor practice. Consider checking for non-empty content.

### Rule 8 File Structure Check (line 371)

Searches for file names in extracted HCL, but LLM might put file names in markdown outside code fences (e.g., "Save this as main.tf:").

### Comment Stripping (lines 390-391)

Only handles `#` and `//`, not `/* */` block comments.

---

## Strengths

1. **Multi-file concatenation** - Handles LLM output with separate main.tf, variables.tf blocks well
2. **Conditional rules** - Rules 12, 13 gracefully handle task-specific requirements
3. **Outcome checks** - Verifies semantic correctness (resources present) alongside style
4. **Comprehensive rubric** - Clear examples with pass/fail for each rule
5. **Taggable resource list** - Good coverage of common AWS resources

---

## Recommendations

| Priority | Issue | Action |
|----------|-------|--------|
| High | Block body extraction | Use brace-counting with string awareness |
| High | Rule 10 version location | Check inside provider namespace |
| Medium | Rule 9 provider block regex | Use brace-counting |
| Medium | Taggable sub-resources | Remove or document limitation |
| Low | Extraction leading whitespace | Allow `^\s*` |
| Low | Terraform Cloud backend | Add `cloud {}` pattern |

---

## Files Reviewed

- `evaluate_terraform.py` (724 lines)
- `evaluation-rubric.md` (417 lines)
