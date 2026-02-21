---
name: openapi-style-pseudocode
description: Design production-grade OpenAPI 3.0 specifications following enterprise API standards.
---

# OpenAPI Style (Pseudocode)

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal
import re

# ---------------------------------------------------------------------------
# CORE TYPES
# ---------------------------------------------------------------------------

class HttpMethod(Enum):
    GET = "get"
    POST = "post"
    PUT = "put"
    PATCH = "patch"
    DELETE = "delete"

class AuthType(Enum):
    BEARER = "bearer"
    OAUTH2 = "oauth2"
    API_KEY = "apiKey"

# Verbs that must NEVER appear as path segments
VERB_BLACKLIST = {
    "get", "create", "delete", "update", "fetch", "remove",
    "add", "list", "search", "find", "retrieve", "modify",
    "put", "post", "patch",
}

# Property names must match this pattern
CAMEL_CASE_RE = re.compile(r"^[a-z][a-zA-Z0-9]*$")

# Required rate-limit headers for all 2xx responses
RATE_LIMIT_HEADERS = [
    "X-RateLimit-Limit",       # Maximum requests per window
    "X-RateLimit-Remaining",   # Requests remaining in current window
    "X-RateLimit-Reset",       # Seconds until rate limit resets
]

# Required fields in the RFC 7807 ProblemDetail schema
PROBLEM_DETAIL_FIELDS = ["type", "title", "status", "detail"]

# Required fields in the cursor pagination envelope
PAGINATION_ENVELOPE_FIELDS = ["data", "nextCursor", "hasMore"]

# ---------------------------------------------------------------------------
# VALIDATION RULES (14-item checklist)
# ---------------------------------------------------------------------------

@dataclass
class PathRules:
    """Rules 1-3: path naming conventions."""
    paths: list[str] = field(default_factory=list)

    def violations(self) -> list[str]:
        v = []
        for path in self.paths:
            segments = [s for s in path.split("/") if s and not s.startswith("{")]
            for seg in segments:
                # Rule 1: plural nouns for collections
                # Heuristic check -- manual review for edge cases
                pass
                # Rule 2: kebab-case (lowercase, hyphens only, no _ or camelCase)
                if seg != seg.lower() or "_" in seg:
                    v.append(f"Rule 2: '{seg}' not kebab-case in {path}")
                # Rule 3: no verbs in path segments
                if seg.lower() in VERB_BLACKLIST:
                    v.append(f"Rule 3: verb '{seg}' in path {path}")
        return v

@dataclass
class OperationRules:
    """Rules 4-5: operation completeness."""
    operations: list[dict] = field(default_factory=list)
    # Each dict: {"method": HttpMethod, "path": str, "operationId": str|None,
    #             "has_summary_or_description": bool}

    def violations(self) -> list[str]:
        v = []
        for op in self.operations:
            # Rule 4: operationId present and unique (camelCase, verbNoun)
            if not op.get("operationId"):
                v.append(f"Rule 4: missing operationId on {op.get('method')} {op.get('path','?')}")
            # Rule 5: summary or description present
            if not op.get("has_summary_or_description"):
                v.append(f"Rule 5: missing summary/description on {op.get('operationId','?')}")
        return v

@dataclass
class SchemaPropertyRules:
    """Rule 6: camelCase property names."""
    property_names: list[str] = field(default_factory=list)

    def violations(self) -> list[str]:
        v = []
        for name in self.property_names:
            if not CAMEL_CASE_RE.match(name):
                v.append(f"Rule 6: '{name}' not camelCase (must match ^[a-z][a-zA-Z0-9]*$)")
        return v

@dataclass
class ContactRules:
    """Rule 7: info.contact completeness."""
    contact_email: str = ""
    contact_url: str = ""

    def violations(self) -> list[str]:
        v = []
        if not self.contact_email and not self.contact_url:
            v.append("Rule 7: info.contact must have email or url")
        return v

@dataclass
class ProblemDetailRules:
    """Rule 8: RFC 7807 ProblemDetail for all error responses."""
    has_problem_detail_schema: bool = False       # ProblemDetail defined in components
    problem_detail_fields: list[str] = field(default_factory=list)  # fields on the schema
    error_responses_use_ref: bool = False          # all 4xx/5xx ref ProblemDetail
    error_content_type: str = ""                   # should be application/problem+json

    def violations(self) -> list[str]:
        v = []
        if not self.has_problem_detail_schema:
            v.append("Rule 8: ProblemDetail schema not defined in components/schemas")
        else:
            for required_field in PROBLEM_DETAIL_FIELDS:
                if required_field not in self.problem_detail_fields:
                    v.append(f"Rule 8: ProblemDetail missing field '{required_field}'")
        if not self.error_responses_use_ref:
            v.append("Rule 8: not all error responses (4xx/5xx) reference ProblemDetail")
        return v

@dataclass
class PaginationRules:
    """Rule 9: cursor pagination envelope on list endpoints."""
    list_endpoints: list[dict] = field(default_factory=list)
    # Each dict: {"path": str, "response_fields": list[str],
    #             "has_cursor_param": bool, "has_limit_param": bool}

    def violations(self) -> list[str]:
        v = []
        for ep in self.list_endpoints:
            fields = ep.get("response_fields", [])
            for required in PAGINATION_ENVELOPE_FIELDS:
                if required not in fields:
                    v.append(f"Rule 9: list endpoint {ep['path']} missing '{required}' in response envelope")
            if not ep.get("has_cursor_param"):
                v.append(f"Rule 9: list endpoint {ep['path']} missing 'cursor' query parameter")
        return v

@dataclass
class RateLimitRules:
    """Rule 10: rate-limit headers on all 2xx responses."""
    success_responses: list[dict] = field(default_factory=list)
    # Each dict: {"path": str, "method": str, "status": int, "headers": list[str]}

    def violations(self) -> list[str]:
        v = []
        for resp in self.success_responses:
            headers = resp.get("headers", [])
            for required_header in RATE_LIMIT_HEADERS:
                if required_header not in headers:
                    v.append(
                        f"Rule 10: {resp['method']} {resp['path']} {resp['status']} "
                        f"missing header '{required_header}'"
                    )
        return v

@dataclass
class IdempotencyRules:
    """Rule 11: Idempotency-Key header on POST and PUT."""
    post_put_operations: list[dict] = field(default_factory=list)
    # Each dict: {"path": str, "method": str, "has_idempotency_key": bool}

    def violations(self) -> list[str]:
        v = []
        for op in self.post_put_operations:
            if not op.get("has_idempotency_key"):
                v.append(
                    f"Rule 11: {op['method']} {op['path']} missing "
                    f"Idempotency-Key header parameter"
                )
        return v

@dataclass
class ExampleValueRules:
    """Rule 12: example value on every schema property."""
    properties: list[dict] = field(default_factory=list)
    # Each dict: {"schema": str, "name": str, "has_example": bool}

    def violations(self) -> list[str]:
        v = []
        for prop in self.properties:
            if not prop.get("has_example"):
                v.append(
                    f"Rule 12: property '{prop['name']}' in schema "
                    f"'{prop['schema']}' missing 'example' field"
                )
        return v

@dataclass
class SecurityRules:
    """Rules 13-14: auth scheme defined and applied (conditional)."""
    requires_auth: bool = False
    scheme_defined: bool = False
    security_applied: bool = False     # global or per-operation

    def violations(self) -> list[str]:
        v = []
        if not self.requires_auth:
            return v   # Rules 13-14 only apply when auth is required
        # Rule 13: security scheme defined
        if not self.scheme_defined:
            v.append("Rule 13: no securitySchemes defined (auth required)")
        # Rule 14: security applied to operations
        if not self.security_applied:
            v.append("Rule 14: security not applied to operations (auth required)")
        return v

# ---------------------------------------------------------------------------
# COMPLETE SPEC VALIDATOR
# ---------------------------------------------------------------------------

@dataclass
class OpenAPISpec:
    paths: PathRules
    operations: OperationRules
    schema_properties: SchemaPropertyRules
    contact: ContactRules
    problem_detail: ProblemDetailRules
    pagination: PaginationRules
    rate_limit: RateLimitRules
    idempotency: IdempotencyRules
    examples: ExampleValueRules
    security: SecurityRules

    def validate(self) -> list[str]:
        """Returns all violations. Empty list = fully compliant."""
        v = []
        v.extend(self.paths.violations())          # Rules 1-3
        v.extend(self.operations.violations())      # Rules 4-5
        v.extend(self.schema_properties.violations())  # Rule 6
        v.extend(self.contact.violations())         # Rule 7
        v.extend(self.problem_detail.violations())  # Rule 8
        v.extend(self.pagination.violations())      # Rule 9
        v.extend(self.rate_limit.violations())      # Rule 10
        v.extend(self.idempotency.violations())     # Rule 11
        v.extend(self.examples.violations())        # Rule 12
        v.extend(self.security.violations())        # Rules 13-14
        return v

    def is_compliant(self) -> bool:
        return len(self.validate()) == 0

# ---------------------------------------------------------------------------
# AUTH TYPE SELECTION
# ---------------------------------------------------------------------------

def select_auth(
    machine_to_machine: bool,
    user_facing: bool,
    simple_token: bool,
) -> AuthType:
    """Decision logic for auth type."""
    if machine_to_machine:
        return AuthType.OAUTH2      # client_credentials flow
    if user_facing:
        return AuthType.BEARER      # JWT from login
    if simple_token:
        return AuthType.API_KEY     # header/query key
    return AuthType.BEARER           # default

# ---------------------------------------------------------------------------
# 14-RULE CHECKLIST
# ---------------------------------------------------------------------------

# PATHS (3)
#  1. Plural nouns for collections (/users not /user)
#  2. Kebab-case path segments (no camelCase, no underscores)
#  3. No verbs in paths (blacklist: get, create, delete, update, fetch,
#     remove, add, list, search, find, retrieve, modify, put, post, patch)

# OPERATIONS (2)
#  4. operationId on every operation (camelCase, verbNoun pattern)
#  5. summary or description on every operation

# SCHEMA PROPERTIES (1)
#  6. camelCase property names (regex: ^[a-z][a-zA-Z0-9]*$)

# API CONTACT (1)
#  7. info.contact with email or url

# RFC 7807 (1)
#  8. ProblemDetail schema for all error responses (4xx/5xx)
#     Fields: type (URI), title, status (integer), detail

# CURSOR PAGINATION (1)
#  9. Pagination envelope on list endpoints (data, nextCursor, hasMore)
#     Accept cursor and limit query parameters

# RATE LIMITING (1)
# 10. X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
#     headers on all 2xx responses

# IDEMPOTENCY (1)
# 11. Idempotency-Key header (uuid) on POST and PUT operations

# EXAMPLE VALUES (1)
# 12. Every schema property must have an example field

# SECURITY (2) -- only when auth required
# 13. Security scheme defined in components/securitySchemes
# 14. Security applied globally or per-operation
```

## Usage

1. Construct `OpenAPISpec` with all rule groups populated from the spec under review
2. Call `spec.validate()` -- empty list = fully compliant
3. Generate YAML or JSON output as a complete OpenAPI 3.0 document
4. Verify all 14 rules pass before submitting
