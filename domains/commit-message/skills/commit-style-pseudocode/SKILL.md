---
name: commit-style-pseudocode
description: Write commit messages following team conventions including gitmoji, structured body sections, DCO sign-off, and JIRA ticket references.
---

# Commit Style (Pseudocode)

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal
import re

# -----------------------------------------------------------------------------
# CORE TYPES
# -----------------------------------------------------------------------------

class CommitType(Enum):
    FEAT     = "feat"       # New feature or capability
    FIX      = "fix"        # Bug fix
    DOCS     = "docs"       # Documentation only
    STYLE    = "style"      # Formatting, whitespace (no logic change)
    REFACTOR = "refactor"   # Code restructuring, no behavior change
    PERF     = "perf"       # Performance improvement
    TEST     = "test"       # Adding or updating tests only
    BUILD    = "build"      # Build system or dependency changes
    CI       = "ci"         # CI/CD configuration changes
    CHORE    = "chore"      # Maintenance tasks
    REVERT   = "revert"     # Reverting a previous commit

VALID_TYPES = {t.value for t in CommitType}

# Gitmoji shortcode mapped to each commit type
GITMOJI_MAP = {
    "feat":     ":sparkles:",
    "fix":      ":bug:",
    "docs":     ":memo:",
    "style":    ":art:",
    "refactor": ":recycle:",
    "perf":     ":zap:",
    "test":     ":white_check_mark:",
    "build":    ":hammer:",
    "ci":       ":construction_worker:",
    "chore":    ":wrench:",
    "revert":   ":rewind:",
}

# Words that violate imperative mood at the start of description
IMPERATIVE_BLACKLIST = {
    # Past tense
    "added", "fixed", "removed", "updated", "changed", "refactored",
    "deleted", "moved", "renamed", "replaced", "converted", "migrated",
    # Gerund (-ing)
    "adding", "fixing", "removing", "updating", "changing", "refactoring",
    "deleting", "moving", "renaming", "replacing", "converting", "migrating",
    # Third person (-s)
    "adds", "fixes", "removes", "updates", "changes", "refactors",
    "deletes", "moves", "renames", "replaces", "converts", "migrates",
}

MAX_SUBJECT_LENGTH = 50
MAX_BODY_LINE_LENGTH = 72
MIN_BODY_WORDS = 30
MAX_BODY_WORDS = 150

# -----------------------------------------------------------------------------
# DATA STRUCTURES
# -----------------------------------------------------------------------------

@dataclass
class Scope:
    """Required scope in parentheses. Must be from allowed vocabulary, lowercase kebab-case."""
    value: str              # e.g. "auth", "api", "db", "ui", "core"
    allowed: set[str]       # project-specific allowed scopes

    def is_valid(self) -> bool:
        if not self.value:
            return False  # scope is REQUIRED
        if not re.match(r'^[a-z][a-z0-9]*(-[a-z0-9]+)*$', self.value):
            return False
        return self.value in self.allowed

@dataclass
class Subject:
    """The first line: <type>(<scope>)[!]: <gitmoji> <description>"""
    type: str               # "feat", "fix", etc.
    scope: Scope            # Required scope
    breaking: bool          # Whether ! indicator is present
    gitmoji: str            # ":sparkles:", ":bug:", etc.
    description: str        # The text after gitmoji

@dataclass
class Footer:
    """A single footer line in Key: value format."""
    token: str              # "Ticket", "Signed-off-by", "BREAKING CHANGE"
    value: str              # "PROJ-247", "Alice Developer <alice@example.com>", etc.

@dataclass
class CommitMessage:
    subject: Subject
    body_why: str                               # Content under "Why:" header
    body_what: str                              # Content under "What:" header
    footers: list[Footer] = field(default_factory=list)

    def full_subject_line(self) -> str:
        """Reconstruct the full subject line string."""
        parts = [self.subject.type]
        parts.append(f"({self.subject.scope.value})")
        if self.subject.breaking:
            parts.append("!")
        parts.append(f": {self.subject.gitmoji} {self.subject.description}")
        return "".join(parts)

    def body_text(self) -> str:
        """Reconstruct full body with Why: and What: sections."""
        return f"Why:\n{self.body_why}\n\nWhat:\n{self.body_what}"

    def body_word_count(self) -> int:
        """Count words in body (Why + What sections combined)."""
        combined = f"{self.body_why} {self.body_what}"
        return len(combined.split())

# -----------------------------------------------------------------------------
# VALIDATION RULES (14-rule checklist)
# -----------------------------------------------------------------------------

def check_rule_1_valid_type(msg: CommitMessage) -> tuple[bool, str]:
    """Rule 1: Valid type prefix."""
    if msg.subject.type in VALID_TYPES:
        return True, f"valid type: {msg.subject.type}"
    return False, f"invalid type: {msg.subject.type}, must be one of {VALID_TYPES}"

def check_rule_2_separator(raw: str) -> tuple[bool, str]:
    """Rule 2: Correct separator ': ' (colon + space)."""
    match = re.match(r'^[a-z]+\([a-z0-9-]+\)!?:\s', raw)
    if match:
        colon_pos = raw.index(':')
        if raw[colon_pos:colon_pos+2] == ': ':
            return True, "ok"
        return False, f"separator is '{raw[colon_pos:colon_pos+3]}', expected ': '"
    return False, "missing or malformed type(scope): description separator"

def check_rule_3_imperative(msg: CommitMessage) -> tuple[bool, str]:
    """Rule 3: Description uses imperative mood."""
    first_word = msg.subject.description.split()[0].lower() if msg.subject.description else ""
    if first_word in IMPERATIVE_BLACKLIST:
        return False, f"'{first_word}' is not imperative mood"
    return True, f"first word '{first_word}' is ok"

def check_rule_4_no_period(msg: CommitMessage) -> tuple[bool, str]:
    """Rule 4: No trailing period on subject."""
    if msg.subject.description.rstrip().endswith("."):
        return False, "description ends with period"
    return True, "ok"

def check_rule_5_lowercase(msg: CommitMessage) -> tuple[bool, str]:
    """Rule 5: Description starts with lowercase letter (after gitmoji)."""
    desc = msg.subject.description
    if desc and desc[0].isupper():
        return False, f"starts with uppercase '{desc[0]}'"
    return True, "ok"

def check_rule_6_scope(msg: CommitMessage) -> tuple[bool, str]:
    """Rule 6: Scope is from allowed vocabulary, lowercase kebab-case."""
    if msg.subject.scope.is_valid():
        return True, f"scope ok: {msg.subject.scope.value}"
    if not msg.subject.scope.value:
        return False, "scope is required but missing"
    if msg.subject.scope.value not in msg.subject.scope.allowed:
        return False, f"scope '{msg.subject.scope.value}' not in allowed: {msg.subject.scope.allowed}"
    return False, f"invalid scope format: '{msg.subject.scope.value}', must be lowercase kebab-case"

def check_rule_7_gitmoji(msg: CommitMessage) -> tuple[bool, str]:
    """Rule 7: Gitmoji after type matches the commit type."""
    expected = GITMOJI_MAP.get(msg.subject.type)
    if not expected:
        return False, f"no gitmoji mapping for type '{msg.subject.type}'"
    if msg.subject.gitmoji == expected:
        return True, f"gitmoji {msg.subject.gitmoji} matches type {msg.subject.type}"
    return False, f"gitmoji {msg.subject.gitmoji} does not match type {msg.subject.type}, expected {expected}"

def check_rule_8_body_sections(msg: CommitMessage) -> tuple[bool, str]:
    """Rule 8: Body has Why: and What: sections."""
    has_why = bool(msg.body_why and msg.body_why.strip())
    has_what = bool(msg.body_what and msg.body_what.strip())
    if has_why and has_what:
        return True, "body has both Why: and What: sections"
    missing = []
    if not has_why:
        missing.append("Why:")
    if not has_what:
        missing.append("What:")
    return False, f"body missing sections: {', '.join(missing)}"

def check_rule_9_body_word_count(msg: CommitMessage) -> tuple[bool, str]:
    """Rule 9: Body is 30-150 words."""
    count = msg.body_word_count()
    if MIN_BODY_WORDS <= count <= MAX_BODY_WORDS:
        return True, f"body word count {count} is within {MIN_BODY_WORDS}-{MAX_BODY_WORDS}"
    if count < MIN_BODY_WORDS:
        return False, f"body too short: {count} words, minimum is {MIN_BODY_WORDS}"
    return False, f"body too long: {count} words, maximum is {MAX_BODY_WORDS}"

def check_rule_10_footer_format(msg: CommitMessage) -> tuple[bool, str]:
    """Rule 10: All footers use Key: value format."""
    invalid = []
    for f in msg.footers:
        if not re.match(r'^[A-Za-z][A-Za-z0-9 -]*$', f.token):
            invalid.append(f.token)
        if not f.value or not f.value.strip():
            invalid.append(f"{f.token} (empty value)")
    if invalid:
        return False, f"invalid footer format: {invalid}"
    return True, "all footers use Key: value format"

def check_rule_11_signed_off(msg: CommitMessage) -> tuple[bool, str]:
    """Rule 11: Signed-off-by footer present (DCO sign-off)."""
    dco = [f for f in msg.footers if f.token == "Signed-off-by"]
    if not dco:
        return False, "missing Signed-off-by footer"
    # Validate format: "Full Name <email>"
    value = dco[0].value.strip()
    if re.match(r'^.+ <.+@.+>$', value):
        return True, f"DCO sign-off present: {value}"
    return False, f"Signed-off-by format invalid: '{value}', expected 'Full Name <email>'"

def check_rule_12_breaking_footer(msg: CommitMessage, task_breaking: bool) -> tuple[bool, str]:
    """Rule 12: BREAKING CHANGE footer present and correct when applicable."""
    if not task_breaking:
        return True, "n/a (not a breaking change)"
    bc_footers = [f for f in msg.footers if f.token == "BREAKING CHANGE"]
    if not bc_footers:
        return False, "missing BREAKING CHANGE footer"
    footer = bc_footers[0]
    if len(footer.value.strip()) < 10:
        return False, f"BREAKING CHANGE footer too short: '{footer.value.strip()}'"
    return True, f"BREAKING CHANGE footer present ({len(footer.value.strip())} chars)"

def check_rule_13_ticket(msg: CommitMessage, expected_ticket: str) -> tuple[bool, str]:
    """Rule 13: Ticket footer with JIRA-style reference (not GitHub #123)."""
    ticket_footers = [f for f in msg.footers if f.token == "Ticket"]
    if not ticket_footers:
        return False, "missing Ticket footer"
    value = ticket_footers[0].value.strip()
    # Must be JIRA-style: PROJ-123
    if not re.match(r'^[A-Z]+-\d+$', value):
        return False, f"Ticket value '{value}' is not JIRA-style (expected PROJ-123)"
    if expected_ticket and value != expected_ticket:
        return False, f"Ticket '{value}' does not match expected '{expected_ticket}'"
    return True, f"Ticket footer present: {value}"

def check_rule_14_subject_length(msg: CommitMessage) -> tuple[bool, str]:
    """Rule 14: Subject line <= 50 characters."""
    line = msg.full_subject_line()
    length = len(line)
    if length <= MAX_SUBJECT_LENGTH:
        return True, f"length={length} <= {MAX_SUBJECT_LENGTH}"
    return False, f"length={length} > {MAX_SUBJECT_LENGTH}"

# -----------------------------------------------------------------------------
# COMPLETE VALIDATION
# -----------------------------------------------------------------------------

def validate_commit(msg: CommitMessage, raw: str, task: dict) -> list[tuple[str, bool, str]]:
    """Run all 14 rules. Returns list of (rule_name, passed, detail)."""
    task_breaking = task.get("breaking_change", False)
    expected_ticket = task.get("ticket", "")

    return [
        ("rule_1_valid_type",       *check_rule_1_valid_type(msg)),
        ("rule_2_separator",        *check_rule_2_separator(raw)),
        ("rule_3_imperative",       *check_rule_3_imperative(msg)),
        ("rule_4_no_period",        *check_rule_4_no_period(msg)),
        ("rule_5_lowercase",        *check_rule_5_lowercase(msg)),
        ("rule_6_scope",            *check_rule_6_scope(msg)),
        ("rule_7_gitmoji",          *check_rule_7_gitmoji(msg)),
        ("rule_8_body_sections",    *check_rule_8_body_sections(msg)),
        ("rule_9_body_word_count",  *check_rule_9_body_word_count(msg)),
        ("rule_10_footer_format",   *check_rule_10_footer_format(msg)),
        ("rule_11_signed_off",      *check_rule_11_signed_off(msg)),
        ("rule_12_breaking_footer", *check_rule_12_breaking_footer(msg, task_breaking)),
        ("rule_13_ticket",          *check_rule_13_ticket(msg, expected_ticket)),
        ("rule_14_subject_length",  *check_rule_14_subject_length(msg)),
    ]

# -----------------------------------------------------------------------------
# 14-RULE CHECKLIST SUMMARY
# -----------------------------------------------------------------------------

#  1. Valid type prefix (one of CommitType enum values)
#  2. Correct separator ': ' (colon + space)
#  3. Imperative mood (first word not in IMPERATIVE_BLACKLIST)
#  4. No trailing period
#  5. Lowercase start (after gitmoji)
#  6. Scope from allowed vocabulary (required, lowercase kebab-case)
#  7. Gitmoji after type matching the commit type (from GITMOJI_MAP)
#  8. Body has Why: and What: sections
#  9. Body is 30-150 words
# 10. All footers use Key: value format
# 11. Signed-off-by footer present (DCO)
# 12. BREAKING CHANGE footer (when applicable, min 10 chars)
# 13. Ticket footer with JIRA-style reference (PROJ-123)
# 14. Subject line <= 50 characters

# -----------------------------------------------------------------------------
# COMPLIANT EXAMPLES
# -----------------------------------------------------------------------------

# Example 1: Simple bug fix (45 chars subject)
# fix(db): :bug: handle null record in findById
#
# Why:
# UserService.findById() throws a null pointer exception when
# querying for a user ID that does not exist in the database.
# This crashes the request handler silently.
#
# What:
# Add null check after database query and return a proper 404
# response with descriptive error message instead of crashing.
#
# Ticket: PROJ-247
# Signed-off-by: Alice Developer <alice@example.com>

# Example 2: Feature (39 chars subject)
# feat(api): :sparkles: add rate limiting
#
# Why:
# The API has no protection against abuse. A single client can
# make unlimited requests, potentially causing service degradation
# for all users.
#
# What:
# Implement sliding window rate limiter backed by Redis. Default
# config allows 100 requests per 15-minute window. Returns 429
# with Retry-After header when the limit is exceeded.
#
# Ticket: PROJ-312
# Signed-off-by: Alice Developer <alice@example.com>

# Example 3: Breaking change (39 chars subject)
# feat(auth)!: :sparkles: replace jwt lib
#
# Why:
# The jsonwebtoken library has known CVEs and lacks native
# TypeScript types. jose is standards-compliant and provides
# full TS support with zero native dependencies.
#
# What:
# Migrate all token signing from jwt.sign() to jose SignJWT
# builder pattern. Verification now uses jwtVerify() with
# explicit algorithm allowlist.
#
# BREAKING CHANGE: JWT tokens signed with jsonwebtoken are
# incompatible with jose. All active sessions will be
# invalidated. Users must log in again after deployment.
#
# Ticket: PROJ-189
# Signed-off-by: Alice Developer <alice@example.com>
```

## Usage

1. Construct `CommitMessage` from the task context with `Scope(value, allowed_scopes)`, gitmoji from `GITMOJI_MAP`, and separate `body_why`/`body_what` fields
2. Call `validate_commit(msg, raw, task)` to check all 14 rules
3. Empty violations list = fully compliant
4. Ensure `task` dict includes `breaking_change` (bool) and `ticket` (JIRA-style string)
