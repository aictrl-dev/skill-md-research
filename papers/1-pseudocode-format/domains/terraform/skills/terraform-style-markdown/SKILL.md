---
name: terraform-style
description: Write Terraform configurations following AWS best practices for naming, structure, security, and maintainability. Use when generating HCL infrastructure-as-code.
---

# Terraform Style Compliance

Write production-quality Terraform configurations following HashiCorp best practices and AWS Well-Architected conventions.

## Core Principle

Every Terraform configuration should be modular, readable, and safe to apply. Variables parameterize, outputs expose, tags identify, and IAM policies enforce least privilege.

## 1. Naming Convention

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

## 2. Variable Descriptions

Every variable must include a `description` attribute explaining what it controls:

```hcl
variable "bucket_name" {
  description = "Name of the S3 bucket for application storage"
  type        = string
}
```

A variable without a description is incomplete. Descriptions appear in `terraform plan` output and documentation.

## 3. Variable Types

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

## 4. Outputs

Every configuration must define sufficient `output` blocks exposing key resource attributes. The number of outputs depends on the task — typically at least 3-4 for complex configurations:

```hcl
output "cluster_endpoint" {
  description = "Endpoint of the EKS cluster"
  value       = aws_eks_cluster.main.endpoint
}

output "replication_role_arn" {
  description = "ARN of the S3 replication IAM role"
  value       = aws_iam_role.replication_role.arn
}
```

Outputs are how consumers of the module access created resources.

## 5. Tags

All taggable resources must include a `tags` block. Use a common set of tags for consistency, preferably via `locals`:

```hcl
resource "aws_s3_bucket" "app_bucket" {
  bucket = var.bucket_name
  tags   = local.common_tags
}
```

## 6. Lifecycle on Stateful Resources

Stateful resources **must** include `lifecycle { prevent_destroy = true }` to prevent accidental destruction. Stateful resources include: `aws_s3_bucket`, `aws_db_instance`, `aws_efs_file_system`, `aws_dynamodb_table`, `aws_kms_key`, `aws_secretsmanager_secret`, `aws_eks_cluster`.

```hcl
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
```

## 7. Locals for Tags

Define a `locals` block for common tags and reference `local.*` in at least 50% of taggable resources. This reduces repetition and ensures tag consistency:

```hcl
locals {
  common_tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }

  name_prefix = "${var.project_name}-${var.environment}"
}

resource "aws_vpc" "main_vpc" {
  cidr_block = var.vpc_cidr
  tags       = local.common_tags
}

resource "aws_security_group" "app_sg" {
  name   = "${local.name_prefix}-app-sg"
  vpc_id = aws_vpc.main_vpc.id
  tags   = merge(local.common_tags, { Name = "${local.name_prefix}-app-sg" })
}
```

## 8. No Hardcoded IDs

Never hardcode AWS-specific identifiers directly in resource blocks:

| Bad | Good |
|-----|------|
| `ami = "ami-0c55b159cbfafe1f0"` | `ami = data.aws_ami.amazon_linux.id` |
| `account_id = "123456789012"` | `account_id = data.aws_caller_identity.current.account_id` |
| `region = "us-east-1"` in a resource | `region = var.aws_region` |

Use variables, data sources, or locals instead. Region strings inside the `provider` block are acceptable.

## 9. Provider Configuration

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

## 10. Backend with State Locking

Configure a remote backend with DynamoDB state locking:

```hcl
terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "project/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-locks"
    encrypt        = true
  }
}
```

The `dynamodb_table` attribute is mandatory — it prevents concurrent state modifications. Create a corresponding `aws_dynamodb_table` resource with `LockID` as the hash key.

## 11. IAM Least Privilege

IAM policies must follow least privilege — no wildcards in `Action` or `Resource`:

```hcl
resource "aws_iam_role_policy" "replication_policy" {
  name = "s3-replication-policy"
  role = aws_iam_role.replication_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetReplicationConfiguration",
          "s3:ListBucket",
          "s3:GetObjectVersionForReplication",
          "s3:ReplicateObject",
          "s3:ReplicateDelete"
        ]
        Resource = [
          aws_s3_bucket.source_bucket.arn,
          "${aws_s3_bucket.source_bucket.arn}/*",
          aws_s3_bucket.destination_bucket.arn,
          "${aws_s3_bucket.destination_bucket.arn}/*"
        ]
      }
    ]
  })
}
```

Forbidden patterns:
- `Action = "*"` or `Action = ["*"]`
- `Resource = "*"` or `Resource = ["*"]`
- Service wildcards: `s3:*`, `ec2:*`, `iam:*`

## 12. Security Group Ingress

Security group ingress rules must be port-specific. Never allow `0.0.0.0/0` on non-HTTP/HTTPS ports. Use security-group-to-security-group references for internal communication:

```hcl
resource "aws_security_group" "cluster_sg" {
  name   = "${local.name_prefix}-cluster-sg"
  vpc_id = var.vpc_id
  tags   = local.common_tags
}

resource "aws_security_group_rule" "cluster_api" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = [var.management_cidr]
  security_group_id = aws_security_group.cluster_sg.id
  description       = "Kubernetes API access from management network"
}

resource "aws_security_group_rule" "node_from_cluster" {
  type                     = "ingress"
  from_port                = 0
  to_port                  = 65535
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.cluster_sg.id
  security_group_id        = aws_security_group.node_sg.id
  description              = "All traffic from cluster control plane"
}
```

Forbidden: `cidr_blocks = ["0.0.0.0/0"]` on ports other than 80 or 443.

## 13. Sensitive Values

Variables and outputs with names containing sensitive keywords (`password`, `secret`, `token`, `key`, `connection_string`) must have `sensitive = true`:

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

## 14. Resource Coverage

Configurations must include at least 70% of the required resource types specified for the task. Missing core resources indicates an incomplete implementation.

## 15. Data Sources

Every configuration must include at least one `data` block for dynamic lookups:

```hcl
data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

data "tls_certificate" "eks_oidc" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer
}
```

Data sources keep configurations portable across accounts and regions.

## Quick Checklist

Before submitting, verify:
- [ ] 1. Resource names use `snake_case` with descriptive prefixes
- [ ] 2. All variables have `description` attribute
- [ ] 3. All variables have `type` constraint
- [ ] 4. Sufficient `output` blocks defined (task-specific minimum)
- [ ] 5. Tags on all taggable resources
- [ ] 6. `lifecycle { prevent_destroy = true }` on all stateful resources
- [ ] 7. `locals` block with common tags, >=50% of taggable resources reference `local.*`
- [ ] 8. No hardcoded AMI IDs, account numbers, or region strings in resources
- [ ] 9. Provider version pinned in `required_providers`
- [ ] 10. Backend configured with `dynamodb_table` for state locking
- [ ] 11. IAM policies follow least privilege (no wildcards)
- [ ] 12. Security group ingress port-specific (no 0.0.0.0/0 on non-80/443)
- [ ] 13. Sensitive values marked with `sensitive = true`
- [ ] 14. >=70% of required resource types present
- [ ] 15. At least one `data` source block defined
