---
name: dockerfile-style
description: Write production-ready Dockerfiles following security, caching, and size best practices. Use when creating Dockerfiles for any service that needs to be deployed in containers.
---

# Dockerfile Style Compliance

Write production-ready Dockerfiles that are secure, small, cache-friendly, and well-documented.

## Core Principle

Every Dockerfile should produce the smallest possible image with no unnecessary tools, no secrets, and deterministic builds. A good Dockerfile is one where rebuilds after a code change only re-run the minimum layers.

## Base Image Rules

### Image Tags
Always pin to a specific version tag. Never use `:latest` or leave the tag empty.

| Pattern | Verdict | Example |
|---------|---------|---------|
| Specific tag | GOOD | `FROM node:20-alpine` |
| Slim variant | GOOD | `FROM python:3.11-slim` |
| Latest tag | BAD | `FROM node:latest` |
| No tag | BAD | `FROM ubuntu` |

### Image Selection
- Use Alpine or slim variants when possible
- Prefer official images from Docker Hub
- Use `*-slim` for Python, `*-alpine` for Node.js
- For multi-stage builds, the final stage should use the smallest suitable base

## Security

### Non-Root User
Every production Dockerfile must run as a non-root user. Create a dedicated user and switch to it before CMD:

```dockerfile
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser
```

### No Secrets in Build
Never put passwords, tokens, API keys, or credentials in ENV or ARG instructions. These are baked into image layers and visible to anyone with image access.

- BAD: `ENV DATABASE_PASSWORD=secret123`
- BAD: `ARG API_TOKEN=sk-abc123`
- GOOD: Pass secrets at runtime via environment variables or mounted secrets

## Build Structure

### Multi-Stage Builds
Use multi-stage builds to separate build dependencies from runtime. The Dockerfile must contain at least two FROM statements:

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS production
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
```

### WORKDIR Before COPY/RUN
Always set WORKDIR before your first COPY or RUN instruction. Never COPY into an implicit directory.

## Cache Optimization

### Dependency Files First
Copy dependency manifests before the full source code. This ensures dependency installation is cached when only application code changes:

1. COPY dependency files (package.json, requirements.txt, go.mod)
2. RUN install dependencies
3. COPY full source code
4. RUN build

```dockerfile
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
```

## Layer Management

### Combine RUN Commands
Merge related RUN instructions using `&&` to reduce image layers. Never have more than 2 adjacent separate RUN lines:

```dockerfile
# GOOD: combined
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# BAD: separate
RUN apt-get update
RUN apt-get install -y curl
RUN rm -rf /var/lib/apt/lists/*
```

### APT Best Practices
When using apt-get, always include `--no-install-recommends` and clean up the cache:

```dockerfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends <packages> && \
    rm -rf /var/lib/apt/lists/*
```

## Health Checks

### HEALTHCHECK Instruction
Include a HEALTHCHECK instruction so the container runtime can monitor health:

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1
```

For Alpine images without curl, use wget:

```dockerfile
HEALTHCHECK CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1
```

## Documentation

### EXPOSE
Document the port(s) your application listens on:

```dockerfile
EXPOSE 3000
```

### LABEL Metadata
Include at least one LABEL with image metadata:

```dockerfile
LABEL maintainer="team@example.com"
LABEL org.opencontainers.image.source="https://github.com/org/repo"
LABEL org.opencontainers.image.description="Node.js API service"
```

## Entry Point

### Exec Form for CMD/ENTRYPOINT
Always use the JSON array (exec) form for CMD and ENTRYPOINT. Never use the shell form:

```dockerfile
# GOOD: exec form
CMD ["node", "dist/server.js"]
ENTRYPOINT ["python", "-m", "uvicorn"]

# BAD: shell form
CMD node dist/server.js
ENTRYPOINT python -m uvicorn
```

Exec form ensures proper signal handling (SIGTERM reaches the process directly).

## COPY vs ADD

### Prefer COPY Over ADD
Use COPY for copying files. ADD should only be used when you need to:
- Extract a local tar archive
- Fetch a remote URL (though curl in a RUN is preferred)

```dockerfile
# GOOD
COPY . .

# BAD (unless extracting tar)
ADD . .
```

## .dockerignore

### Always Include .dockerignore
Create a `.dockerignore` file to exclude unnecessary files from the build context:

```
node_modules
.git
.env
*.md
Dockerfile
docker-compose*.yml
.github
dist
__pycache__
```

This reduces build context size and prevents secrets from being copied.

## Quick Checklist

Before submitting, verify:
- [ ] Every FROM has a specific version tag (no :latest, no untagged)
- [ ] Non-root USER directive present
- [ ] No secrets in ENV or ARG
- [ ] Multi-stage build (at least 2 FROM statements)
- [ ] WORKDIR set before first COPY or RUN
- [ ] Dependency files copied before source code
- [ ] RUN commands combined with && (no >2 adjacent RUNs)
- [ ] apt-get uses --no-install-recommends + cache cleanup
- [ ] HEALTHCHECK instruction present
- [ ] EXPOSE documented
- [ ] At least one LABEL present
- [ ] CMD/ENTRYPOINT in exec form (JSON array)
- [ ] No ADD when COPY suffices
- [ ] .dockerignore considered
