---
name: terraform-style-pseudocode
description: Write Terraform configurations following AWS best practices for naming, structure, security, and maintainability.
---

# Terraform Style (Pseudocode)

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal
import re

# -----------------------------------------------------------------------------
# CORE TYPES
# -----------------------------------------------------------------------------

class ResourceCategory(Enum):
    COMPUTE   = "compute"       # aws_instance, aws_ecs_service, aws_lambda_function
    STORAGE   = "storage"       # aws_s3_bucket, aws_db_instance, aws_efs_file_system
    NETWORK   = "network"       # aws_vpc, aws_subnet, aws_security_group, aws_lb
    IAM       = "iam"           # aws_iam_role, aws_iam_policy
    SECRETS   = "secrets"       # aws_secretsmanager_secret, aws_ssm_parameter
    LOGGING   = "logging"       # aws_cloudwatch_log_group

# Resources that support tags in AWS
TAGGABLE_RESOURCES = {
    "aws_instance", "aws_s3_bucket", "aws_vpc", "aws_subnet",
    "aws_security_group", "aws_lb", "aws_ecs_cluster", "aws_db_instance",
    "aws_ecs_service", "aws_ecs_task_definition", "aws_cloudwatch_log_group",
    "aws_eip", "aws_nat_gateway", "aws_internet_gateway", "aws_route_table",
    "aws_lb_target_group", "aws_secretsmanager_secret", "aws_iam_role",
}

# Resources where data loss is catastrophic — lifecycle blocks recommended
STATEFUL_RESOURCES = {
    "aws_s3_bucket", "aws_db_instance", "aws_efs_file_system",
    "aws_dynamodb_table", "aws_kms_key", "aws_secretsmanager_secret",
}

# Valid Terraform variable types
VALID_VAR_TYPES = {
    "string", "number", "bool", "list", "map", "set", "object", "tuple", "any",
}

# -----------------------------------------------------------------------------
# DATA STRUCTURES
# -----------------------------------------------------------------------------

@dataclass
class Variable:
    """A Terraform variable block."""
    name: str                   # e.g. "bucket_name"
    description: str | None     # Rule 2: MUST be non-empty
    type: str | None            # Rule 3: MUST be present (string, number, list(string), etc.)
    sensitive: bool = False     # Rule 12: Must be True for passwords, secrets, keys
    default: str | None = None

@dataclass
class Output:
    """A Terraform output block."""
    name: str                   # e.g. "vpc_id"
    value: str                  # e.g. "aws_vpc.main_vpc.id"
    description: str | None = None
    sensitive: bool = False

@dataclass
class Resource:
    """A Terraform resource block."""
    type: str                   # e.g. "aws_s3_bucket"
    name: str                   # e.g. "app_bucket" — Rule 1: snake_case, descriptive prefix
    has_tags: bool = False      # Rule 5: MUST be True for TAGGABLE_RESOURCES
    has_lifecycle: bool = False # Rule 6: Recommended for STATEFUL_RESOURCES

@dataclass
class DataSource:
    """A Terraform data block."""
    type: str                   # e.g. "aws_ami"
    name: str                   # e.g. "amazon_linux"

@dataclass
class ProviderConfig:
    """Provider and terraform block."""
    provider: str               # e.g. "aws"
    version_constraint: str | None  # Rule 10: MUST be present, e.g. "~> 5.0"
    required_version: str | None    # e.g. ">= 1.5"

@dataclass
class BackendConfig:
    """Backend configuration."""
    backend_type: str | None    # Rule 11: e.g. "s3", "gcs", "azurerm"

@dataclass
class LocalsBlock:
    """A locals block with shared values."""
    entries: dict[str, str]     # Rule 14: At least one entry expected

# -----------------------------------------------------------------------------
# TERRAFORM CONFIGURATION — all fields mandatory
# -----------------------------------------------------------------------------

@dataclass
class TerraformConfig:
    provider: ProviderConfig
    backend: BackendConfig
    variables: list[Variable]
    outputs: list[Output]
    resources: list[Resource]
    data_sources: list[DataSource] = field(default_factory=list)
    locals: LocalsBlock | None = None

# -----------------------------------------------------------------------------
# VALIDATION RULES — 14-rule checklist
# -----------------------------------------------------------------------------

# NAMING (1 rule)

def check_rule_1_naming(config: TerraformConfig) -> tuple[bool, str]:
    """Rule 1: snake_case resource names with descriptive prefix.
    Bad: sg1, vpc1, role1, main (alone for non-obvious resources).
    Good: app_security_group, main_vpc, ecs_task_execution_role."""
    BAD_NAMES = re.compile(r'^[a-z]{1,3}\d*$')  # sg1, vpc1, r1, a
    violations = []
    for r in config.resources:
        if not re.match(r'^[a-z][a-z0-9_]*$', r.name):
            violations.append(f"{r.type}.{r.name}: not snake_case")
        elif BAD_NAMES.match(r.name):
            violations.append(f"{r.type}.{r.name}: too generic")
    if violations:
        return False, "; ".join(violations)
    return True, "all resource names are descriptive snake_case"

# VARIABLES (2 rules)

def check_rule_2_var_description(config: TerraformConfig) -> tuple[bool, str]:
    """Rule 2: All variables have a description attribute."""
    missing = [v.name for v in config.variables if not v.description]
    if missing:
        return False, f"missing description: {missing}"
    return True, f"all {len(config.variables)} variables have descriptions"

def check_rule_3_var_type(config: TerraformConfig) -> tuple[bool, str]:
    """Rule 3: All variables have a type constraint."""
    missing = [v.name for v in config.variables if not v.type]
    if missing:
        return False, f"missing type: {missing}"
    return True, f"all {len(config.variables)} variables have types"

# OUTPUTS (1 rule)

def check_rule_4_outputs(config: TerraformConfig) -> tuple[bool, str]:
    """Rule 4: At least one output block defined."""
    if len(config.outputs) == 0:
        return False, "no outputs defined"
    return True, f"{len(config.outputs)} outputs defined"

# TAGS (1 rule)

def check_rule_5_tags(config: TerraformConfig) -> tuple[bool, str]:
    """Rule 5: Tags on all taggable resources."""
    missing = [
        f"{r.type}.{r.name}"
        for r in config.resources
        if r.type in TAGGABLE_RESOURCES and not r.has_tags
    ]
    if missing:
        return False, f"missing tags: {missing}"
    return True, "all taggable resources have tags"

# LIFECYCLE (1 rule)

def check_rule_6_lifecycle(config: TerraformConfig) -> tuple[bool, str]:
    """Rule 6: lifecycle blocks on stateful resources. MANUAL CHECK."""
    # Always needs human review — lifecycle is a recommendation, not strict
    return True, "needs_review"

# STRUCTURE (2 rules)

def check_rule_7_var_separation(tf_text: str) -> tuple[bool, str]:
    """Rule 7: Variables grouped together, not scattered between resources.
    SEMI — heuristic: check if variable blocks appear between resource blocks."""
    # Best-effort: look for resource...variable...resource pattern
    blocks = re.findall(r'^\s*(resource|variable)\b', tf_text, re.MULTILINE)
    saw_resource = False
    saw_var_after_resource = False
    saw_resource_after_var_after_resource = False
    for b in blocks:
        if b == "resource":
            if saw_var_after_resource:
                saw_resource_after_var_after_resource = True
            saw_resource = True
        elif b == "variable":
            if saw_resource:
                saw_var_after_resource = True
    if saw_resource_after_var_after_resource:
        return False, "variables scattered between resource blocks"
    return True, "variables appear grouped"

def check_rule_8_file_structure(tf_text: str) -> tuple[bool, str]:
    """Rule 8: Module file structure mentioned (main.tf/variables.tf/outputs.tf).
    SEMI — check if output mentions file names or multi-file structure."""
    file_markers = ["main.tf", "variables.tf", "outputs.tf", "data.tf", "locals.tf"]
    found = [f for f in file_markers if f in tf_text]
    if found:
        return True, f"file structure mentioned: {found}"
    return True, "needs_review (single file output)"

# VALUES (1 rule)

def check_rule_9_no_hardcoded_ids(tf_text: str) -> tuple[bool, str]:
    """Rule 9: No hardcoded AMI IDs, account numbers, or region strings in resources.
    - ami-[0-9a-f]{8,17} — hardcoded AMI
    - 12-digit number — AWS account ID
    - Region string like "us-east-1" outside provider block"""
    violations = []
    if re.search(r'ami-[0-9a-f]{8,17}', tf_text):
        violations.append("hardcoded AMI ID (ami-*)")
    if re.search(r'(?<!\d)\d{12}(?!\d)', tf_text):
        violations.append("possible hardcoded AWS account ID (12 digits)")
    # Region in resource blocks (not provider): find "us-east-1" etc. in resource context
    # This is best-effort — region in provider block is acceptable
    if violations:
        return False, "; ".join(violations)
    return True, "no hardcoded IDs found"

# PROVIDER (1 rule)

def check_rule_10_provider_pinned(config: TerraformConfig) -> tuple[bool, str]:
    """Rule 10: Provider version pinned in required_providers block."""
    if not config.provider.version_constraint:
        return False, "provider version not pinned"
    return True, f"provider version: {config.provider.version_constraint}"

# BACKEND (1 rule)

def check_rule_11_backend(config: TerraformConfig) -> tuple[bool, str]:
    """Rule 11: Backend configured (terraform { backend "..." {} })."""
    if not config.backend.backend_type:
        return False, "no backend configured"
    return True, f"backend: {config.backend.backend_type}"

# SENSITIVE (1 rule — conditional)

def check_rule_12_sensitive(config: TerraformConfig, task_requires: bool) -> tuple[bool, str]:
    """Rule 12: Sensitive values marked with sensitive = true.
    Only checked when the task requires sensitive handling."""
    if not task_requires:
        return True, "n/a (task does not require sensitive values)"
    sensitive_vars = [v.name for v in config.variables if v.sensitive]
    sensitive_outputs = [o.name for o in config.outputs if o.sensitive]
    if not sensitive_vars and not sensitive_outputs:
        return False, "task requires sensitive values but none marked sensitive"
    return True, f"sensitive vars: {sensitive_vars}, outputs: {sensitive_outputs}"

# DATA SOURCES (1 rule — conditional)

def check_rule_13_data_sources(config: TerraformConfig, task_requires: bool) -> tuple[bool, str]:
    """Rule 13: Data sources used for lookups when task requires them."""
    if not task_requires:
        return True, "n/a (task does not require data sources)"
    if len(config.data_sources) == 0:
        return False, "task requires data sources but none defined"
    return True, f"{len(config.data_sources)} data sources defined"

# LOCALS (1 rule)

def check_rule_14_locals(config: TerraformConfig) -> tuple[bool, str]:
    """Rule 14: Locals block present for shared/computed values."""
    if config.locals is None or len(config.locals.entries) == 0:
        return False, "no locals block defined"
    return True, f"locals defined: {list(config.locals.entries.keys())}"

# -----------------------------------------------------------------------------
# COMPLETE VALIDATION
# -----------------------------------------------------------------------------

def validate_terraform(config: TerraformConfig, tf_text: str, task: dict) -> list[tuple[str, bool, str]]:
    """Run all 14 rules. Returns list of (rule_name, passed, detail)."""
    requires_sensitive = task.get("requirements", {}).get("sensitive_values", False)
    requires_data = task.get("requirements", {}).get("data_sources", False)

    return [
        ("rule_1_naming",           *check_rule_1_naming(config)),
        ("rule_2_var_description",  *check_rule_2_var_description(config)),
        ("rule_3_var_type",         *check_rule_3_var_type(config)),
        ("rule_4_outputs",          *check_rule_4_outputs(config)),
        ("rule_5_tags",             *check_rule_5_tags(config)),
        ("rule_6_lifecycle",        *check_rule_6_lifecycle(config)),
        ("rule_7_var_separation",   *check_rule_7_var_separation(tf_text)),
        ("rule_8_file_structure",   *check_rule_8_file_structure(tf_text)),
        ("rule_9_no_hardcoded_ids", *check_rule_9_no_hardcoded_ids(tf_text)),
        ("rule_10_provider_pinned", *check_rule_10_provider_pinned(config)),
        ("rule_11_backend",         *check_rule_11_backend(config)),
        ("rule_12_sensitive",       *check_rule_12_sensitive(config, requires_sensitive)),
        ("rule_13_data_sources",    *check_rule_13_data_sources(config, requires_data)),
        ("rule_14_locals",          *check_rule_14_locals(config)),
    ]

# -----------------------------------------------------------------------------
# 14-RULE CHECKLIST SUMMARY
# -----------------------------------------------------------------------------

# NAMING (1)
#  1. snake_case resource names with descriptive prefix (not sg1, vpc1)

# VARIABLES (2)
#  2. All variables have description attribute
#  3. All variables have type constraint

# OUTPUTS (1)
#  4. At least one output block defined

# TAGS (1)
#  5. Tags on all taggable resources (aws_instance, aws_vpc, aws_s3_bucket, etc.)

# LIFECYCLE (1)
#  6. lifecycle blocks on stateful resources (MANUAL — always needs_review)

# STRUCTURE (2)
#  7. Variables grouped together, not scattered between resources (SEMI)
#  8. File structure mentioned — main.tf/variables.tf/outputs.tf (SEMI)

# VALUES (1)
#  9. No hardcoded AMI IDs (ami-*), account numbers (12-digit), region strings

# PROVIDER (1)
# 10. Provider version pinned in required_providers block

# BACKEND (1)
# 11. Backend configured (terraform { backend "..." {} })

# SENSITIVE (1 — conditional)
# 12. Sensitive values marked sensitive = true (when task requires it)

# DATA SOURCES (1 — conditional)
# 13. Data sources used for lookups (when task requires them)

# LOCALS (1)
# 14. Locals block present for shared/computed values
```

## Usage

1. Construct `TerraformConfig` with **all** fields from the generated HCL
2. Call `validate_terraform(config, tf_text, task)` to check all 14 rules
3. Empty violations list = fully compliant
4. Rule 6 always returns `needs_review` (requires human judgment)
5. Rules 7, 8 are semi-automatable (heuristic checks)
6. Rules 12, 13 are conditional (only checked when task requires them)
