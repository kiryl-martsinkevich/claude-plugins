# Confluence Space Configuration

This file maps Confluence space keys to their purposes. Edit this file to match your organization's actual space structure. The skill uses this mapping to target searches to the most relevant spaces.

## How to Configure

1. Update the space entries below to match your Confluence instance
2. Add new spaces as needed
3. Remove spaces that don't exist in your instance
4. Update search keywords to improve automatic space targeting

## Space Mappings

### ENTARCH — Enterprise Architecture

**Purpose**: Architecture decisions, system design documents, architecture diagrams, technology roadmaps, ADRs (Architecture Decision Records)

**Search this space when**: User asks about system architecture, design patterns, component diagrams, integration architecture, data architecture, technology roadmap, or architecture decisions.

**Common labels**: `architecture`, `adr`, `design`, `system-design`, `integration`

---

### TECHSTD — Technology Standards

**Purpose**: Coding standards, approved technology stack, framework guidelines, development best practices, code review standards

**Search this space when**: User asks about coding standards, approved technologies, framework choices, development guidelines, naming conventions, or technology governance.

**Common labels**: `standards`, `guidelines`, `best-practices`, `governance`, `tech-stack`

---

### SECPOL — Security Policies

**Purpose**: Security requirements, compliance documentation, access control policies, data classification, incident response procedures

**Search this space when**: User asks about security requirements, compliance (SOC2, GDPR, HIPAA), access control, data handling policies, or security best practices.

**Common labels**: `security`, `compliance`, `policy`, `access-control`, `data-classification`

---

### DEVOPS — DevOps & Infrastructure

**Purpose**: CI/CD pipelines, deployment procedures, infrastructure documentation, monitoring setup, environment configurations, runbooks

**Search this space when**: User asks about deployment, CI/CD, infrastructure, Kubernetes, Docker, monitoring, alerting, environment setup, or operational procedures.

**Common labels**: `devops`, `infrastructure`, `deployment`, `ci-cd`, `monitoring`, `runbook`

---

### APIREF — API Documentation

**Purpose**: API specifications, integration guides, API contracts, endpoint documentation, webhook configurations, API versioning

**Search this space when**: User asks about API endpoints, integration documentation, API contracts, REST/GraphQL specifications, or service interfaces.

**Common labels**: `api`, `integration`, `rest`, `graphql`, `swagger`, `openapi`

---

### ONBOARD — Onboarding & Guides

**Purpose**: New hire onboarding, team guides, how-to documentation, development environment setup, process documentation

**Search this space when**: User asks about onboarding, getting started, how-to guides, environment setup, or team processes.

**Common labels**: `onboarding`, `guide`, `how-to`, `setup`, `getting-started`

---

## Adding New Spaces

To add a new space, follow this template:

```markdown
### SPACEKEY — Space Name

**Purpose**: Brief description of what this space contains

**Search this space when**: Describe the queries/topics that should target this space

**Common labels**: `label1`, `label2`, `label3`
```

## Space Selection Logic

When a user's query matches multiple spaces, search in this priority order:

1. **Exact space mentioned** — If user names a space key, use it directly
2. **Topic match** — Match query keywords against the "Search this space when" descriptions
3. **Broad search** — If no clear match, search across all spaces
4. **Attachment search** — Also search attachments when looking for specific documents (BRDs, specs, standards docs)
