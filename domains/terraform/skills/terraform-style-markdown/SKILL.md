---
name: terraform-style
description: Write Terraform configurations following AWS best practices for naming, structure, security, and maintainability. Use when generating HCL infrastructure-as-code.
---

# Terraform Style Compliance

Write production-quality Terraform configurations following HashiCorp best practices and AWS Well-Architected conventions.

## Core Principle

Every Terraform configuration should be modular, readable, and safe to apply. Variables parameterize, outputs expose, and tags identify.

## Naming Convention

Use `snake_case` for all resource names with a descriptive prefix identifying the resource's purpose:

| Good | Bad | Why |
|------|-----|-----|
| `main_vpc` | `vpc1` | Describes purpose |
| `app_security_group` | `sg1` | Identifies role |
| `private_subnet_a` | `subnet2` | Clear function |
| `web_alb` | `alb` | Indicates usage |
| `ecs_task_execution_role` | `role1` | Self-documenting |

Rules:
1. Always use `snake_case` (underscores, not hyphens or camelCase)
2. Prefix with a descriptive word indicating the resource's role
3. Never use single letters, bare numbers, or generic names like `this`, `main` alone for non-obvious resources

## Variables

### Description Attribute (Required)

Every variable must include a `description` attribute explaining what it controls:

```hcl
variable "bucket_name" {
  description = "Name of the S3 bucket for application storage"
  type        = string
}
```

A variable without a description is incomplete. Descriptions appear in `terraform plan` output and documentation.

### Type Constraint (Required)

Every variable must include a `type` constraint:

```hcl
variable "instance_type" {
  description = "EC2 instance type for the web server"
  type        = string
  default     = "t3.micro"
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for the database"
  type        = list(string)
}
```

Valid types: `string`, `number`, `bool`, `list(T)`, `map(T)`, `set(T)`, `object({...})`, `tuple([...])`.

## Outputs

Every configuration must define at least one `output` block exposing key resource attributes:

```hcl
output "vpc_id" {
  description = "ID of the created VPC"
  value       = aws_vpc.main_vpc.id
}

output "alb_dns_name" {
  description = "DNS name of the application load balancer"
  value       = aws_lb.web_alb.dns_name
}
```

Outputs are how consumers of the module access created resources.

## Tags

All taggable resources must include a `tags` block. AWS resources that support tags include: `aws_instance`, `aws_s3_bucket`, `aws_vpc`, `aws_subnet`, `aws_security_group`, `aws_lb`, `aws_ecs_cluster`, `aws_db_instance`, `aws_ecs_service`, `aws_ecs_task_definition`, `aws_cloudwatch_log_group`, `aws_eip`, `aws_nat_gateway`, `aws_internet_gateway`, `aws_route_table`, and others.

Use a common set of tags for consistency:

```hcl
tags = {
  Environment = var.environment
  Project     = var.project_name
  ManagedBy   = "terraform"
}
```

Using `locals` for common tags is recommended:

```hcl
locals {
  common_tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

resource "aws_vpc" "main_vpc" {
  cidr_block = "10.0.0.0/16"
  tags       = local.common_tags
}
```

## Lifecycle Blocks

Stateful resources (databases, S3 buckets, EFS, encryption keys) should include `lifecycle` blocks to prevent accidental destruction:

```hcl
resource "aws_db_instance" "app_database" {
  # ... configuration ...

  lifecycle {
    prevent_destroy = true
  }
}
```

Consider `lifecycle` for any resource where data loss would be catastrophic.

## File Structure

Organize Terraform configurations into separate files by concern:

| File | Contents |
|------|----------|
| `main.tf` | Provider configuration and primary resources |
| `variables.tf` | All variable declarations |
| `outputs.tf` | All output declarations |
| `data.tf` | Data source lookups |
| `locals.tf` | Local value definitions |

Even in a single-file configuration, keep variables grouped together at the top or bottom -- do not scatter variable blocks between resource blocks.

## No Hardcoded IDs

Never hardcode AWS-specific identifiers directly in resource blocks:

| Bad | Good |
|-----|------|
| `ami = "ami-0c55b159cbfafe1f0"` | `ami = data.aws_ami.amazon_linux.id` |
| `account_id = "123456789012"` | `account_id = data.aws_caller_identity.current.account_id` |
| `region = "us-east-1"` in a resource | `region = var.aws_region` |

Use variables, data sources, or locals instead. Region strings inside the `provider` block are acceptable.

## Provider Configuration

Pin the provider version in a `required_providers` block:

```hcl
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
```

Always use version constraints (`~>`, `>=`, `=`) to prevent unexpected provider upgrades.

## Backend Configuration

Configure a remote backend for state storage:

```hcl
terraform {
  backend "s3" {
    bucket = "my-terraform-state"
    key    = "project/terraform.tfstate"
    region = "us-east-1"
  }
}
```

A backend block ensures state is stored remotely and supports locking.

## Sensitive Values

Mark sensitive variables and outputs with `sensitive = true`:

```hcl
variable "db_password" {
  description = "Database master password"
  type        = string
  sensitive   = true
}

output "db_connection_string" {
  description = "Database connection string"
  value       = "postgres://${var.db_username}:${var.db_password}@${aws_db_instance.app_database.endpoint}"
  sensitive   = true
}
```

This prevents values from appearing in CLI output and logs.

## Data Sources

Use data sources to look up dynamic values instead of hardcoding:

```hcl
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

data "aws_caller_identity" "current" {}
```

Data sources keep configurations portable across accounts and regions.

## Locals

Use `locals` blocks to define computed or shared values:

```hcl
locals {
  common_tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }

  name_prefix = "${var.project_name}-${var.environment}"
}
```

Locals reduce repetition and make configurations easier to maintain.

## Quick Checklist

Before submitting, verify:
- [ ] Resource names use `snake_case` with descriptive prefixes
- [ ] All variables have `description` attribute
- [ ] All variables have `type` constraint
- [ ] At least one `output` block defined
- [ ] Tags on all taggable resources
- [ ] `lifecycle` blocks on stateful resources
- [ ] Variables grouped together, not scattered among resources
- [ ] File structure mentioned or organized (main.tf/variables.tf/outputs.tf)
- [ ] No hardcoded AMI IDs, account numbers, or region strings in resources
- [ ] Provider version pinned in `required_providers`
- [ ] Backend configured
- [ ] Sensitive values marked with `sensitive = true` (when applicable)
- [ ] Data sources used for dynamic lookups (when applicable)
- [ ] `locals` block present for shared/computed values
