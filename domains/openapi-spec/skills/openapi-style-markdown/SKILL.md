---
name: openapi-style
description: Design production-grade OpenAPI 3.0 specifications following enterprise API standards including RFC 7807 errors, cursor pagination, rate-limit headers, and idempotency.
---

# Enterprise OpenAPI Style Guide

Generate production-grade OpenAPI 3.0 specifications that follow enterprise API standards. Every endpoint, schema, and response must be precise, consistent, and self-documenting.

## Path Design

### Rule 1: Plural Nouns for Collections

Use plural nouns for collection resources:

| Correct | Incorrect |
|---------|-----------|
| `/users` | `/user` |
| `/products` | `/product` |
| `/orders` | `/order` |
| `/webhooks` | `/webhook` |

### Rule 2: Kebab-Case Path Segments

Use kebab-case for multi-word path segments. No camelCase, no underscores.

| Correct | Incorrect |
|---------|-----------|
| `/user-profiles` | `/userProfiles` |
| `/payment-methods` | `/payment_methods` |
| `/order-items` | `/OrderItems` |

### Rule 3: No Verbs in Paths

Paths represent resources, not actions. HTTP methods convey the action.

**Blacklisted verbs**: get, create, delete, update, fetch, remove, add, list, search, find, retrieve, modify, put, post, patch

| Correct | Incorrect |
|---------|-----------|
| `GET /users` | `GET /getUsers` |
| `POST /users` | `POST /createUser` |
| `DELETE /users/{userId}` | `DELETE /deleteUser/{userId}` |
| `GET /users?q=term` | `GET /searchUsers` |

## Operations

### Rule 4: Operation ID (Required)

Every operation must have a unique `operationId`. Use camelCase and follow the pattern `verbNoun`:

```yaml
paths:
  /users:
    get:
      operationId: listUsers
    post:
      operationId: createUser
  /users/{userId}:
    get:
      operationId: getUser
    put:
      operationId: updateUser
    delete:
      operationId: deleteUser
```

### Rule 5: Summary or Description (Required)

Every operation must have at least a `summary` or `description` field:

```yaml
get:
  operationId: listUsers
  summary: List all users
  description: Returns a paginated list of all user accounts. Supports filtering by role and status.
```

## Schema Property Names

### Rule 6: camelCase Property Names

ALL property names must be camelCase. Regex: `^[a-z][a-zA-Z0-9]*$`

| Correct | Incorrect |
|---------|-----------|
| `userId` | `user_id` |
| `createdAt` | `created_at` |
| `isActive` | `is_active` |
| `stockCount` | `stock_count` |

## API Contact Info

### Rule 7: info.contact Required

`info.contact` MUST include `email` or `url`:

```yaml
info:
  title: My API
  version: "1.0.0"
  contact:
    email: api-team@example.com
    url: https://api-docs.example.com
```

## RFC 7807 Problem Details

### Rule 8: ProblemDetail Schema for All Errors

ALL error responses (4xx, 5xx) must use the RFC 7807 Problem Details schema. Define a `ProblemDetail` schema with fields: `type` (string, URI), `title` (string), `status` (integer), `detail` (string). Reference it from all error responses.

```yaml
components:
  schemas:
    ProblemDetail:
      type: object
      required: [type, title, status, detail]
      properties:
        type:
          type: string
          format: uri
          example: "https://api.example.com/errors/not-found"
        title:
          type: string
          example: "Resource Not Found"
        status:
          type: integer
          example: 404
        detail:
          type: string
          example: "The requested user with ID 123 was not found."

# Usage in responses:
responses:
  '400':
    description: Bad request
    content:
      application/problem+json:
        schema:
          $ref: '#/components/schemas/ProblemDetail'
  '404':
    description: Resource not found
    content:
      application/problem+json:
        schema:
          $ref: '#/components/schemas/ProblemDetail'
  '500':
    description: Internal server error
    content:
      application/problem+json:
        schema:
          $ref: '#/components/schemas/ProblemDetail'
```

## Cursor Pagination

### Rule 9: Pagination Envelope on List Endpoints

List endpoints must wrap responses in a pagination envelope. Required fields: `data` (array), `nextCursor` (string, nullable), `hasMore` (boolean).

```yaml
# For each list endpoint, define a paginated response:
ListUsersResponse:
  type: object
  required: [data, hasMore]
  properties:
    data:
      type: array
      items:
        $ref: '#/components/schemas/User'
    nextCursor:
      type: string
      nullable: true
      example: "eyJpZCI6MTAwfQ=="
    hasMore:
      type: boolean
      example: true

# Accept cursor parameter:
parameters:
  - name: cursor
    in: query
    schema:
      type: string
  - name: limit
    in: query
    schema:
      type: integer
      default: 20
```

## Rate-Limit Headers

### Rule 10: Rate-Limit Headers on All Success Responses

ALL success responses (2xx) must document these headers:

```yaml
headers:
  X-RateLimit-Limit:
    description: Maximum requests per window
    schema:
      type: integer
      example: 100
  X-RateLimit-Remaining:
    description: Requests remaining in current window
    schema:
      type: integer
      example: 95
  X-RateLimit-Reset:
    description: Seconds until rate limit resets
    schema:
      type: integer
      example: 3600
```

## Idempotency-Key Header

### Rule 11: Idempotency-Key on POST and PUT

POST and PUT operations must accept an `Idempotency-Key` request header:

```yaml
parameters:
  - name: Idempotency-Key
    in: header
    required: false
    description: Unique key for idempotent requests
    schema:
      type: string
      format: uuid
      example: "550e8400-e29b-41d4-a716-446655440000"
```

## Example Values

### Rule 12: Example on Every Schema Property

EVERY schema property must have an `example` field:

```yaml
properties:
  id:
    type: string
    format: uuid
    example: "550e8400-e29b-41d4-a716-446655440000"
  email:
    type: string
    format: email
    example: "alice@example.com"
  createdAt:
    type: string
    format: date-time
    example: "2024-01-15T09:30:00Z"
```

## Security

### Rule 13: Security Scheme Definition (When Auth Required)

When the API requires authentication, define a security scheme in `components/securitySchemes`:

```yaml
# Bearer JWT
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

# OAuth2 client credentials
components:
  securitySchemes:
    oauth2:
      type: oauth2
      flows:
        clientCredentials:
          tokenUrl: /oauth/token
          scopes:
            read: Read access
            write: Write access
```

### Rule 14: Security Applied (When Auth Required)

Security schemes must be applied either globally or per-operation. Do not define a scheme without using it:

```yaml
# Global (applies to all operations)
security:
  - bearerAuth: []

# Per-operation
paths:
  /users:
    get:
      security:
        - bearerAuth: []
```

## Quick Checklist

Before submitting, verify all 14 rules:

1. Plural nouns for collections
2. Kebab-case path segments
3. No verbs in paths
4. `operationId` on all operations
5. `summary` or `description` on all operations
6. camelCase property names
7. `info.contact` with email or url
8. RFC 7807 `ProblemDetail` schema for all error responses
9. Cursor pagination envelope (`data`, `nextCursor`, `hasMore`) on list endpoints
10. Rate-limit headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`) on success responses
11. `Idempotency-Key` header on POST and PUT operations
12. `example` values on all schema properties
13. Security scheme defined (when auth required)
14. Security applied to operations (when auth required)
