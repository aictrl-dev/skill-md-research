---
name: dockerfile-style-pseudocode
description: Write production-ready Dockerfiles following security, caching, and size best practices.
---

# Dockerfile Style (Pseudocode)

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

# -----------------------------------------------------------------------------
# CORE TYPES
# -----------------------------------------------------------------------------

class BaseImageVariant(Enum):
    ALPINE = "alpine"       # Smallest, for Node.js / Go
    SLIM = "slim"           # Minimal Debian, for Python
    DISTROLESS = "distroless"  # Google distroless, no shell

class ExecForm(Enum):
    JSON_ARRAY = "exec"     # ["node", "server.js"]  — REQUIRED
    SHELL = "shell"         # node server.js          — FORBIDDEN

@dataclass
class FromInstruction:
    image: str              # e.g. "node"
    tag: str                # e.g. "20-alpine" — MUST be specific, never "latest"
    alias: str | None = None  # e.g. "builder" for multi-stage AS

    def is_valid_tag(self) -> bool:
        """Tag must be specific: not 'latest', not empty."""
        return bool(self.tag) and self.tag != "latest"

@dataclass
class HealthCheck:
    endpoint: str           # "/health"
    port: int               # 3000
    interval_s: int = 30
    timeout_s: int = 3
    start_period_s: int = 5
    retries: int = 3

# -----------------------------------------------------------------------------
# VALIDATION RULES (14-item checklist)
# -----------------------------------------------------------------------------

@dataclass
class TagRules:
    """Rule 1: Every FROM must have a specific version tag."""
    from_instructions: list[FromInstruction] = field(default_factory=list)

    def violations(self) -> list[str]:
        v = []
        for f in self.from_instructions:
            if not f.is_valid_tag():
                v.append(f"FROM {f.image}: tag '{f.tag}' is not specific")
        return v

@dataclass
class SecurityRules:
    """Rules 2-3: Non-root user, no secrets."""
    has_user_directive: bool = False       # Rule 2: USER with non-root
    non_root_user: str = ""                # e.g. "appuser"
    env_values: list[str] = field(default_factory=list)  # Rule 3: no secrets
    arg_values: list[str] = field(default_factory=list)

    SECRET_PATTERNS = ["password", "secret", "token", "api_key", "apikey",
                       "private_key", "credential", "aws_secret"]

    def violations(self) -> list[str]:
        v = []
        # Rule 2: non-root user
        if not self.has_user_directive or self.non_root_user in ("", "root"):
            v.append("Must include USER with non-root user")
        # Rule 3: no secrets in ENV/ARG
        for val in self.env_values + self.arg_values:
            for pattern in self.SECRET_PATTERNS:
                if pattern in val.lower():
                    v.append(f"Secret-like value in ENV/ARG: {val}")
        return v

@dataclass
class StructureRules:
    """Rules 4-5: Multi-stage build, WORKDIR before COPY/RUN."""
    from_count: int = 0           # Rule 4: must be >= 2
    workdir_before_copy: bool = False  # Rule 5: WORKDIR before first COPY/RUN

    def violations(self) -> list[str]:
        v = []
        if self.from_count < 2:
            v.append(f"Multi-stage required: found {self.from_count} FROM (need >= 2)")
        if not self.workdir_before_copy:
            v.append("WORKDIR must appear before first COPY or RUN")
        return v

@dataclass
class CacheRules:
    """Rule 6: Dependency files COPY'd before source."""
    deps_before_source: bool = False  # package.json before COPY . .

    def violations(self) -> list[str]:
        v = []
        if not self.deps_before_source:
            v.append("COPY dependency files (package.json/requirements.txt/go.mod) before source")
        return v

@dataclass
class LayerRules:
    """Rules 7-8: Combined RUN, apt best practices."""
    max_adjacent_runs: int = 0    # Rule 7: must be <= 2
    apt_has_no_recommends: bool = True   # Rule 8: --no-install-recommends
    apt_has_cache_cleanup: bool = True   # Rule 8: rm -rf /var/lib/apt/lists/*

    def violations(self) -> list[str]:
        v = []
        if self.max_adjacent_runs > 2:
            v.append(f"Too many adjacent RUN lines: {self.max_adjacent_runs} (max 2)")
        if not self.apt_has_no_recommends:
            v.append("apt-get install missing --no-install-recommends")
        if not self.apt_has_cache_cleanup:
            v.append("apt-get missing cache cleanup: rm -rf /var/lib/apt/lists/*")
        return v

@dataclass
class HealthRules:
    """Rule 9: HEALTHCHECK present."""
    has_healthcheck: bool = False

    def violations(self) -> list[str]:
        if not self.has_healthcheck:
            return ["Missing HEALTHCHECK instruction"]
        return []

@dataclass
class DocRules:
    """Rules 10-11: EXPOSE and LABEL documented."""
    has_expose: bool = False       # Rule 10
    has_label: bool = False        # Rule 11

    def violations(self) -> list[str]:
        v = []
        if not self.has_expose:
            v.append("Missing EXPOSE instruction")
        if not self.has_label:
            v.append("Missing LABEL metadata")
        return v

@dataclass
class EntryRules:
    """Rule 12: CMD/ENTRYPOINT in exec form (JSON array)."""
    cmd_form: ExecForm = ExecForm.JSON_ARRAY
    entrypoint_form: ExecForm = ExecForm.JSON_ARRAY

    def violations(self) -> list[str]:
        v = []
        if self.cmd_form == ExecForm.SHELL:
            v.append("CMD must use exec form: [\"cmd\", \"arg\"]")
        if self.entrypoint_form == ExecForm.SHELL:
            v.append("ENTRYPOINT must use exec form: [\"cmd\", \"arg\"]")
        return v

@dataclass
class CopyRules:
    """Rule 13: No ADD when COPY suffices."""
    has_unnecessary_add: bool = False  # ADD without tar extraction or URL

    def violations(self) -> list[str]:
        if self.has_unnecessary_add:
            return ["Use COPY instead of ADD (ADD only for tar extraction or URLs)"]
        return []

@dataclass
class IgnoreRules:
    """Rule 14: .dockerignore considered (MANUAL — cannot verify from Dockerfile)."""
    # This rule always needs manual review
    def violations(self) -> list[str]:
        return []  # Cannot be auto-checked

# -----------------------------------------------------------------------------
# COMPLETE SPEC
# -----------------------------------------------------------------------------

@dataclass
class DockerfileSpec:
    tags: TagRules
    security: SecurityRules
    structure: StructureRules
    cache: CacheRules
    layers: LayerRules
    health: HealthRules
    docs: DocRules
    entry: EntryRules
    copy: CopyRules
    ignore: IgnoreRules

    def validate(self) -> list[str]:
        """Returns violations. Empty = compliant."""
        v = []
        v.extend(self.tags.violations())
        v.extend(self.security.violations())
        v.extend(self.structure.violations())
        v.extend(self.cache.violations())
        v.extend(self.layers.violations())
        v.extend(self.health.violations())
        v.extend(self.docs.violations())
        v.extend(self.entry.violations())
        v.extend(self.copy.violations())
        v.extend(self.ignore.violations())
        return v

    def is_compliant(self) -> bool:
        return len(self.validate()) == 0

# -----------------------------------------------------------------------------
# BASE IMAGE SELECTION
# -----------------------------------------------------------------------------

def select_base(runtime: str) -> tuple[str, str]:
    """Select base image and tag by runtime."""
    BASES = {
        "node": ("node", "20-alpine"),
        "python": ("python", "3.11-slim"),
        "go": ("golang", "1.22-alpine"),
        "rust": ("rust", "1.77-slim"),
        "java": ("eclipse-temurin", "21-jre-alpine"),
    }
    if runtime not in BASES:
        raise ValueError(f"Unknown runtime: {runtime}")
    return BASES[runtime]

# FINAL STAGE: always use smallest base (alpine/slim/distroless)

# -----------------------------------------------------------------------------
# LAYER ORDERING
# -----------------------------------------------------------------------------

def optimal_layer_order() -> list[str]:
    """Layers ordered by change frequency (least -> most)."""
    return [
        "FROM base",           # Rarely changes
        "RUN apt-get/apk",     # System deps change rarely
        "COPY deps files",     # package.json, requirements.txt, go.mod
        "RUN install deps",    # Cached unless deps files change
        "COPY model/assets",   # Large files, change occasionally
        "COPY source",         # Changes most frequently
        "RUN build",           # Rebuilds on source change
    ]

# -----------------------------------------------------------------------------
# 14-RULE CHECKLIST
# -----------------------------------------------------------------------------

# BASE (1)
#  1. Specific image tag (no :latest, no untagged)

# SECURITY (2)
#  2. Non-root USER directive
#  3. No secrets in ENV/ARG

# STRUCTURE (2)
#  4. Multi-stage build (>= 2 FROM)
#  5. WORKDIR before first COPY/RUN

# CACHE (1)
#  6. Dependency files COPY'd before source

# LAYERS (2)
#  7. RUN commands combined with && (max 2 adjacent RUNs)
#  8. apt-get --no-install-recommends + cache cleanup

# HEALTH (1)
#  9. HEALTHCHECK instruction present

# DOCS (2)
# 10. EXPOSE documented
# 11. LABEL metadata present

# ENTRY (1)
# 12. CMD/ENTRYPOINT in exec form (JSON array)

# COPY (1)
# 13. No ADD when COPY suffices

# IGNORE (1 — MANUAL)
# 14. .dockerignore considered
```

## Usage

1. Construct `DockerfileSpec` from parsed Dockerfile lines
2. Call `spec.validate()` -> empty list = compliant
3. Generate Dockerfile text following layer ordering from `optimal_layer_order()`
4. Verify 14-rule checklist passes
