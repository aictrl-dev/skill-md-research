---
name: terraform-style-pseudocode-examples
description: Write Terraform configurations following AWS best practices for naming, structure, security, and maintainability.
---

# Terraform Style (Pseudocode + Examples)

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
    "aws_eks_cluster", "aws_eks_node_group", "aws_kms_key",
    "aws_dynamodb_table", "aws_lambda_function", "aws_api_gateway_stage",
    "aws_wafv2_web_acl",
}

# Resources where lifecycle { prevent_destroy = true } is REQUIRED
STATEFUL_RESOURCES = {
    "aws_s3_bucket", "aws_db_instance", "aws_efs_file_system",
    "aws_dynamodb_table", "aws_kms_key", "aws_secretsmanager_secret",
    "aws_eks_cluster",
}

# Keywords in variable/output names that require sensitive = true
SENSITIVE_KEYWORDS = {
    "password", "secret", "token", "key", "connection_string",
    "private_key", "api_key", "credentials",
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
    """A Terraform variable block.

    Example HCL:
        variable "bucket_name" {
          description = "Name of the S3 bucket for application storage"
          type        = string
        }

        variable "db_password" {
          description = "Database master password"
          type        = string
          sensitive   = true
        }
    """
    name: str                   # e.g. "bucket_name"
    description: str | None     # Rule 2: MUST be non-empty
    type: str | None            # Rule 3: MUST be present (string, number, list(string), etc.)
    sensitive: bool = False     # Rule 13: Must be True if name contains SENSITIVE_KEYWORDS
    default: str | None = None

@dataclass
class Output:
    """A Terraform output block.

    Example HCL:
        output "cluster_endpoint" {
          description = "Endpoint of the EKS cluster"
          value       = aws_eks_cluster.main.endpoint
        }

        output "replication_role_arn" {
          description = "ARN of the S3 replication IAM role"
          value       = aws_iam_role.replication_role.arn
        }
    """
    name: str                   # e.g. "vpc_id"
    value: str                  # e.g. "aws_vpc.main_vpc.id"
    description: str | None = None
    sensitive: bool = False     # Rule 13: Must be True if name contains SENSITIVE_KEYWORDS

@dataclass
class Resource:
    """A Terraform resource block.

    Example HCL (with tags, lifecycle, and local.* tags):
        resource "aws_s3_bucket" "app_bucket" {
          bucket = var.bucket_name
          tags   = local.common_tags

          lifecycle {
            prevent_destroy = true
          }
        }

        resource "aws_dynamodb_table" "terraform_locks" {
          name         = "terraform-state-locks"
          billing_mode = "PAY_PER_REQUEST"
          hash_key     = "LockID"

          attribute {
            name = "LockID"
            type = "S"
          }

          tags = local.common_tags

          lifecycle {
            prevent_destroy = true
          }
        }
    """
    type: str                   # e.g. "aws_s3_bucket"
    name: str                   # e.g. "app_bucket" — Rule 1: snake_case, descriptive prefix
    has_tags: bool = False      # Rule 5: MUST be True for TAGGABLE_RESOURCES
    uses_local_tags: bool = False  # Rule 7: Should reference local.* for tags
    has_lifecycle: bool = False # Rule 6: MUST be True for STATEFUL_RESOURCES

@dataclass
class IamPolicy:
    """An IAM policy document (from aws_iam_role_policy or aws_iam_policy).

    Example HCL (scoped policy — GOOD):
        resource "aws_iam_role_policy" "replication_policy" {
          name = "s3-replication-policy"
          role = aws_iam_role.replication_role.id

          policy = jsonencode({
            Version = "2012-10-17"
            Statement = [{
              Effect = "Allow"
              Action = [
                "s3:GetReplicationConfiguration",
                "s3:ListBucket",
                "s3:GetObjectVersionForReplication",
                "s3:ReplicateObject",
                "s3:ReplicateDelete"
              ]
              Resource = [
                aws_s3_bucket.source.arn,
                "${aws_s3_bucket.source.arn}/*"
              ]
            }]
          })
        }

    FORBIDDEN patterns:
        Action   = "*"          # wildcard action
        Action   = ["s3:*"]     # service wildcard
        Resource = "*"          # wildcard resource
        Resource = ["*"]        # wildcard resource
    """
    resource_name: str          # e.g. "replication_policy"
    actions: list[str]          # e.g. ["s3:GetObject", "s3:ListBucket"]
    resources: list[str]        # e.g. ["arn:aws:s3:::bucket/*"]
    has_wildcard_action: bool = False   # Rule 11: MUST be False
    has_wildcard_resource: bool = False # Rule 11: MUST be False
    has_service_wildcard: bool = False  # Rule 11: MUST be False (e.g. "s3:*")

@dataclass
class SecurityGroupRule:
    """A security group ingress/egress rule.

    Example HCL (port-specific, CIDR-restricted — GOOD):
        resource "aws_security_group_rule" "cluster_api" {
          type              = "ingress"
          from_port         = 443
          to_port           = 443
          protocol          = "tcp"
          cidr_blocks       = [var.management_cidr]
          security_group_id = aws_security_group.cluster_sg.id
          description       = "K8s API from management network"
        }

    Example HCL (SG-to-SG reference — GOOD):
        resource "aws_security_group_rule" "node_from_cluster" {
          type                     = "ingress"
          from_port                = 0
          to_port                  = 65535
          protocol                 = "tcp"
          source_security_group_id = aws_security_group.cluster_sg.id
          security_group_id        = aws_security_group.node_sg.id
          description              = "All traffic from cluster control plane"
        }

    FORBIDDEN: cidr_blocks = ["0.0.0.0/0"] on ports other than 80 or 443.
    """
    sg_name: str                # Parent security group name
    direction: str              # "ingress" or "egress"
    from_port: int
    to_port: int
    cidr_blocks: list[str]      # e.g. ["10.0.0.0/8"]
    source_sg_id: str | None = None  # SG-to-SG reference

@dataclass
class DataSource:
    """A Terraform data block.

    Example HCL:
        data "aws_caller_identity" "current" {}

        data "tls_certificate" "eks_oidc" {
          url = aws_eks_cluster.main.identity[0].oidc[0].issuer
        }
    """
    type: str                   # e.g. "aws_ami"
    name: str                   # e.g. "amazon_linux"

@dataclass
class ProviderConfig:
    """Provider and terraform block.

    Example HCL:
        terraform {
          required_version = ">= 1.5"

          required_providers {
            aws = {
              source  = "hashicorp/aws"
              version = "~> 5.0"
            }
          }
        }

        provider "aws" {
          region = var.aws_region
        }
    """
    provider: str               # e.g. "aws"
    version_constraint: str | None  # Rule 9: MUST be present, e.g. "~> 5.0"
    required_version: str | None    # e.g. ">= 1.5"

@dataclass
class BackendConfig:
    """Backend configuration with state locking.

    Example HCL:
        terraform {
          backend "s3" {
            bucket         = "my-terraform-state"
            key            = "project/terraform.tfstate"
            region         = "us-east-1"
            dynamodb_table = "terraform-state-locks"
            encrypt        = true
          }
        }
    """
    backend_type: str | None    # Rule 10: e.g. "s3", "gcs", "azurerm"
    lock_table: str | None      # Rule 10: DynamoDB table name for state locking

@dataclass
class LocalsBlock:
    """A locals block with shared values.

    Example HCL:
        locals {
          common_tags = {
            Environment = var.environment
            Project     = var.project_name
            ManagedBy   = "terraform"
          }

          name_prefix = "${var.project_name}-${var.environment}"
        }
    """
    entries: dict[str, str]     # Rule 7: Must include common_tags or similar

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
    iam_policies: list[IamPolicy] = field(default_factory=list)
    sg_rules: list[SecurityGroupRule] = field(default_factory=list)
    data_sources: list[DataSource] = field(default_factory=list)
    locals: LocalsBlock | None = None

# -----------------------------------------------------------------------------
# VALIDATION RULES — 15-rule checklist (zero free points)
# -----------------------------------------------------------------------------

# STYLE (5 rules)

def check_rule_1_naming(config: TerraformConfig) -> tuple[bool, str]:
    """Rule 1: snake_case resource names with descriptive prefix (>3 chars).
    Bad:  sg1, vpc1, role1.
    Good: app_security_group, main_vpc, ecs_task_execution_role.

    Example HCL (good naming):
        resource "aws_vpc" "main_vpc" { ... }
        resource "aws_security_group" "app_security_group" { ... }
        resource "aws_iam_role" "ecs_task_execution_role" { ... }
    """
    BAD_NAMES = re.compile(r'^[a-z]{1,3}\d*$')
    violations = []
    for r in config.resources:
        if not re.match(r'^[a-z][a-z0-9_]*$', r.name):
            violations.append(f"{r.type}.{r.name}: not snake_case")
        elif BAD_NAMES.match(r.name):
            violations.append(f"{r.type}.{r.name}: too generic")
    if violations:
        return False, "; ".join(violations)
    return True, "all resource names are descriptive snake_case"

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

def check_rule_4_outputs(config: TerraformConfig, min_outputs: int) -> tuple[bool, str]:
    """Rule 4: At least N outputs defined (N from task JSON)."""
    if len(config.outputs) < min_outputs:
        return False, f"{len(config.outputs)} outputs, need >={min_outputs}"
    return True, f"{len(config.outputs)} outputs defined (need >={min_outputs})"

def check_rule_5_tags(config: TerraformConfig) -> tuple[bool, str]:
    """Rule 5: Tags on all taggable resources.

    Example HCL:
        resource "aws_vpc" "main_vpc" {
          cidr_block = var.vpc_cidr
          tags       = local.common_tags
        }

        resource "aws_security_group" "app_sg" {
          name   = "${local.name_prefix}-app-sg"
          vpc_id = aws_vpc.main_vpc.id
          tags   = merge(local.common_tags, { Name = "${local.name_prefix}-app-sg" })
        }
    """
    missing = [
        f"{r.type}.{r.name}"
        for r in config.resources
        if r.type in TAGGABLE_RESOURCES and not r.has_tags
    ]
    if missing:
        return False, f"missing tags: {missing}"
    return True, "all taggable resources have tags"

# STRUCTURE (3 rules)

def check_rule_6_lifecycle_stateful(config: TerraformConfig) -> tuple[bool, str]:
    """Rule 6: prevent_destroy = true on every stateful resource.

    Example HCL:
        resource "aws_s3_bucket" "app_bucket" {
          bucket = var.bucket_name
          tags   = local.common_tags

          lifecycle {
            prevent_destroy = true
          }
        }

        resource "aws_dynamodb_table" "terraform_locks" {
          name         = "terraform-state-locks"
          billing_mode = "PAY_PER_REQUEST"
          hash_key     = "LockID"

          attribute {
            name = "LockID"
            type = "S"
          }

          tags = local.common_tags

          lifecycle {
            prevent_destroy = true
          }
        }
    """
    missing = [
        f"{r.type}.{r.name}"
        for r in config.resources
        if r.type in STATEFUL_RESOURCES and not r.has_lifecycle
    ]
    if missing:
        return False, f"missing lifecycle prevent_destroy: {missing}"
    return True, "all stateful resources have prevent_destroy = true"

def check_rule_7_locals_for_tags(config: TerraformConfig) -> tuple[bool, str]:
    """Rule 7: locals block exists AND >=50% of taggable resources reference local.*.

    Example HCL:
        locals {
          common_tags = {
            Environment = var.environment
            Project     = var.project_name
            ManagedBy   = "terraform"
          }
        }

        resource "aws_vpc" "main_vpc" {
          cidr_block = var.vpc_cidr
          tags       = local.common_tags       # references local.*
        }
    """
    if config.locals is None or len(config.locals.entries) == 0:
        return False, "no locals block defined"
    taggable = [r for r in config.resources if r.type in TAGGABLE_RESOURCES]
    if not taggable:
        return True, "locals present, no taggable resources"
    using_local = sum(1 for r in taggable if r.uses_local_tags)
    pct = using_local / len(taggable) * 100
    if pct >= 50:
        return True, f"{using_local}/{len(taggable)} use local.* tags ({pct:.0f}%)"
    return False, f"only {using_local}/{len(taggable)} use local.* tags ({pct:.0f}%), need >=50%"

def check_rule_8_no_hardcoded_ids(tf_text: str) -> tuple[bool, str]:
    """Rule 8: No hardcoded AMI IDs, account numbers, or region strings in resources.

    Bad:  ami = "ami-0c55b159cbfafe1f0"
    Good: ami = data.aws_ami.amazon_linux.id

    Bad:  account_id = "123456789012"
    Good: account_id = data.aws_caller_identity.current.account_id
    """
    violations = []
    if re.search(r'ami-[0-9a-f]{8,17}', tf_text):
        violations.append("hardcoded AMI ID")
    if re.search(r'(?<!\d)\d{12}(?!\d)', tf_text):
        violations.append("possible hardcoded AWS account ID")
    if violations:
        return False, "; ".join(violations)
    return True, "no hardcoded IDs found"

# PROVIDER & STATE (2 rules)

def check_rule_9_provider_pinned(config: TerraformConfig) -> tuple[bool, str]:
    """Rule 9: Provider version pinned in required_providers block."""
    if not config.provider.version_constraint:
        return False, "provider version not pinned"
    return True, f"provider version: {config.provider.version_constraint}"

def check_rule_10_backend_with_locking(config: TerraformConfig) -> tuple[bool, str]:
    """Rule 10: Backend configured AND dynamodb_table for state locking.

    Example HCL:
        terraform {
          backend "s3" {
            bucket         = "my-terraform-state"
            key            = "project/terraform.tfstate"
            region         = "us-east-1"
            dynamodb_table = "terraform-state-locks"
            encrypt        = true
          }
        }
    """
    if not config.backend.backend_type:
        return False, "no backend configured"
    if not config.backend.lock_table:
        return False, f"backend {config.backend.backend_type} but no dynamodb_table for locking"
    return True, f"backend {config.backend.backend_type} with lock table {config.backend.lock_table}"

# SECURITY (3 rules)

def check_rule_11_iam_least_privilege(config: TerraformConfig) -> tuple[bool, str]:
    """Rule 11: No '*' in Action or Resource. No service wildcards (s3:*).

    Example HCL (scoped policy — GOOD):
        resource "aws_iam_role_policy" "lambda_logging" {
          name = "lambda-logging"
          role = aws_iam_role.lambda_role.id

          policy = jsonencode({
            Version = "2012-10-17"
            Statement = [{
              Effect   = "Allow"
              Action   = [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
              ]
              Resource = aws_cloudwatch_log_group.lambda_logs.arn
            }]
          })
        }

    FORBIDDEN:
        Action   = "*"
        Action   = ["s3:*"]
        Resource = "*"
    """
    if not config.iam_policies:
        return False, "no IAM policies found"
    violations = []
    for p in config.iam_policies:
        if p.has_wildcard_action:
            violations.append(f"{p.resource_name}: Action = '*'")
        if p.has_wildcard_resource:
            violations.append(f"{p.resource_name}: Resource = '*'")
        if p.has_service_wildcard:
            violations.append(f"{p.resource_name}: service wildcard (e.g. s3:*)")
    if violations:
        return False, "; ".join(violations)
    return True, f"all {len(config.iam_policies)} IAM policies follow least privilege"

def check_rule_12_sg_no_open_ingress(config: TerraformConfig) -> tuple[bool, str]:
    """Rule 12: No 0.0.0.0/0 on non-80/443 ports.

    Example HCL (port-specific — GOOD):
        resource "aws_security_group_rule" "vpc_endpoint_https" {
          type              = "ingress"
          from_port         = 443
          to_port           = 443
          protocol          = "tcp"
          cidr_blocks       = [var.vpc_cidr]
          security_group_id = aws_security_group.vpce_sg.id
        }

    FORBIDDEN:
        cidr_blocks = ["0.0.0.0/0"] on port 22, 3306, 5432, etc.
    """
    violations = []
    for rule in config.sg_rules:
        if rule.direction == "ingress" and "0.0.0.0/0" in rule.cidr_blocks:
            if rule.from_port not in (80, 443):
                violations.append(f"{rule.sg_name}: 0.0.0.0/0 on port {rule.from_port}")
    if violations:
        return False, "; ".join(violations)
    return True, "all SG ingress rules pass"

def check_rule_13_sensitive_marked(config: TerraformConfig) -> tuple[bool, str]:
    """Rule 13: Variables/outputs with sensitive keywords must have sensitive = true.
    Keywords: password, secret, token, key, connection_string.

    Example HCL:
        variable "db_password" {
          description = "Database master password"
          type        = string
          sensitive   = true
        }

        output "db_connection_string" {
          description = "Database connection string"
          value       = "postgres://..."
          sensitive   = true
        }
    """
    violations = []
    for v in config.variables:
        if any(kw in v.name.lower() for kw in SENSITIVE_KEYWORDS):
            if not v.sensitive:
                violations.append(f"var.{v.name}")
    for o in config.outputs:
        if any(kw in o.name.lower() for kw in SENSITIVE_KEYWORDS):
            if not o.sensitive:
                violations.append(f"output.{o.name}")
    if violations:
        return False, f"missing sensitive = true: {violations}"
    return True, "all sensitive-named vars/outputs marked sensitive"

# SEMANTIC CORRECTNESS (2 rules)

def check_rule_14_resource_coverage(config: TerraformConfig, expected: list[str]) -> tuple[bool, str]:
    """Rule 14: >=70% of required resource types present."""
    if not expected:
        return True, "no expected resources"
    actual = {r.type for r in config.resources}
    found = [r for r in expected if r in actual]
    pct = len(found) / len(expected) * 100
    if pct >= 70:
        return True, f"{len(found)}/{len(expected)} resources ({pct:.0f}%)"
    return False, f"only {len(found)}/{len(expected)} resources ({pct:.0f}%), need >=70%"

def check_rule_15_data_sources_used(config: TerraformConfig) -> tuple[bool, str]:
    """Rule 15: At least one data block defined.

    Example HCL:
        data "aws_caller_identity" "current" {}

        data "tls_certificate" "eks_oidc" {
          url = aws_eks_cluster.main.identity[0].oidc[0].issuer
        }
    """
    if len(config.data_sources) == 0:
        return False, "no data sources defined"
    return True, f"{len(config.data_sources)} data sources defined"

# -----------------------------------------------------------------------------
# COMPLETE VALIDATION
# -----------------------------------------------------------------------------

def validate_terraform(config: TerraformConfig, tf_text: str, task: dict) -> list[tuple[str, bool, str]]:
    """Run all 15 rules. Returns list of (rule_name, passed, detail)."""
    min_outputs = task.get("min_outputs", 1)
    expected_resources = task.get("resources", [])

    return [
        ("rule_1_naming",              *check_rule_1_naming(config)),
        ("rule_2_var_description",     *check_rule_2_var_description(config)),
        ("rule_3_var_type",            *check_rule_3_var_type(config)),
        ("rule_4_outputs",             *check_rule_4_outputs(config, min_outputs)),
        ("rule_5_tags",                *check_rule_5_tags(config)),
        ("rule_6_lifecycle_stateful",  *check_rule_6_lifecycle_stateful(config)),
        ("rule_7_locals_for_tags",     *check_rule_7_locals_for_tags(config)),
        ("rule_8_no_hardcoded_ids",    *check_rule_8_no_hardcoded_ids(tf_text)),
        ("rule_9_provider_pinned",     *check_rule_9_provider_pinned(config)),
        ("rule_10_backend_with_locking", *check_rule_10_backend_with_locking(config)),
        ("rule_11_iam_least_privilege", *check_rule_11_iam_least_privilege(config)),
        ("rule_12_sg_no_open_ingress", *check_rule_12_sg_no_open_ingress(config)),
        ("rule_13_sensitive_marked",   *check_rule_13_sensitive_marked(config)),
        ("rule_14_resource_coverage",  *check_rule_14_resource_coverage(config, expected_resources)),
        ("rule_15_data_sources_used",  *check_rule_15_data_sources_used(config)),
    ]

# -----------------------------------------------------------------------------
# 15-RULE CHECKLIST SUMMARY
# -----------------------------------------------------------------------------

# STYLE (5)
#  1. snake_case resource names with descriptive prefix (>3 chars)
#  2. All variables have description attribute
#  3. All variables have type constraint
#  4. At least N outputs defined (N from task)
#  5. Tags on all taggable resources

# STRUCTURE (3)
#  6. lifecycle { prevent_destroy = true } on all stateful resources
#  7. locals block + >=50% taggable resources reference local.* for tags
#  8. No hardcoded AMI IDs, account numbers, region strings

# PROVIDER & STATE (2)
#  9. Provider version pinned in required_providers
# 10. Backend configured with dynamodb_table for state locking

# SECURITY (3)
# 11. IAM least privilege — no wildcards in Action/Resource
# 12. SG ingress — no 0.0.0.0/0 on non-80/443 ports
# 13. Sensitive vars/outputs with keyword names marked sensitive = true

# SEMANTIC CORRECTNESS (2)
# 14. >=70% of required resource types present
# 15. At least one data source block defined
```

## Usage

1. Construct `TerraformConfig` with **all** fields from the generated HCL
2. Call `validate_terraform(config, tf_text, task)` to check all 15 rules
3. Empty violations list = fully compliant
4. All 15 rules are fully automated — no manual review needed
5. All rules count toward `auto_score` — no exclusions
