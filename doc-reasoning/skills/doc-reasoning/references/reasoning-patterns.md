# Reasoning Patterns

Common document analysis patterns with example prompts and expected outputs.

## 1. Gap Analysis (Template vs. Actual)

**When:** You have a template/specification document and a target document that should follow it.

**How:**
1. Parse the template's heading structure to identify expected sections
2. For each template section, check if a corresponding section exists in the target
3. For partial matches, compare content coverage depth
4. Categorize gaps: Missing, Partial, Different

**Expected output:**
```markdown
# Gap Analysis: [Template] vs [Target]

## Coverage Summary
- **Fully covered:** 12/20 sections (60%)
- **Partially covered:** 5/20 sections (25%)
- **Missing:** 3/20 sections (15%)

## Missing Sections
### Section: Architecture Overview
**Template expects:** High-level system diagram and component description
**Target has:** Not present

### Section: Security Considerations
...

## Partial Coverage
### Section: Deployment Guide
**Template expects:** Step-by-step deployment with rollback plan
**Target has:** Deployment steps listed but no rollback plan
**Gap:** Rollback procedure missing

## Recommendations
1. Add Architecture Overview section before Deployment Guide
2. ...
```

## 2. Cross-Document Synthesis

**When:** Information on a topic is spread across multiple documents.

**How:**
1. Identify the synthesis topic/question
2. Extract relevant information from each document
3. Note which document each piece of info comes from
4. Resolve conflicts, note corroborating evidence
5. Present a unified view with citations

**Expected output:**
```markdown
# Synthesis: [Topic]

## Consensus Findings
- **Finding 1:** ...  *(Source: doc-A.md §3.2, doc-B.md §1.4)*
- **Finding 2:** ...  *(Source: doc-C.md §5)*

## Conflicts
- doc-A.md states X, but doc-B.md states Y
- **Resolution:** ...

## Unique Contributions
- doc-A.md provides specific detail on ...
- doc-B.md covers the historical context ...
```

## 3. Compliance Checking

**When:** Checking a document against a standard, policy, or regulation.

**How:**
1. Extract requirements from the standard document
2. For each requirement, check if the target document addresses it
3. Rate compliance: Compliant, Partially Compliant, Non-Compliant, Not Applicable
4. Quote specific evidence from both documents

**Expected output:**
```markdown
# Compliance Report: [Document] vs [Standard]

| Requirement | Status | Evidence |
|-------------|--------|----------|
| R1: Data encryption at rest | ✅ Compliant | Doc §4.2: "All data encrypted using AES-256" |
| R2: Access logging | ⚠️ Partial | Doc §5.1: Mentions logging but no retention period |
| R3: Penetration testing | ❌ Not addressed | No mention found |
```

## 4. Data Extraction and Summarization

**When:** Extracting structured data from documents (especially from spreadsheets).

**How:**
1. Identify the data points to extract
2. For each document, pull the relevant data tables
3. Normalize and combine the data
4. Present as a unified table or structured summary

**Expected output:**
```markdown
# Data Summary: [Topic]

| Metric | doc-A | doc-B | doc-C |
|--------|-------|-------|-------|
| Metric 1 | 100 | 150 | 120 |
| Metric 2 | 3.2 | 2.8 | 3.1 |

## Key Insights
- ...
```

## 5. Document Comparison (Full Diff)

**When:** Two versions of the same document or two similar documents.

**How:**
1. Identify structural differences (sections added/removed/reordered)
2. Identify content differences within matching sections
3. Summarize at section level, then drill into significant content changes

**Expected output:**
```markdown
# Comparison: [Doc X] vs [Doc Y]

## Structural Changes
- Section "Background" removed
- New section "Motivation" added after Introduction
- Section "Results" split into "Results" and "Discussion"

## Content Changes by Section
### Introduction
- Paragraph 2: Changed methodology description from "qualitative" to "mixed-methods"
...
```

## General Tips

- **Prefer tables** for comparisons, compliance, and structured summaries
- **Always cite sources** — include document name and section reference
- **Be specific** about gaps — quote what's missing, not just "it's different"
- **Recommend next steps** — what should the user do with this analysis?
- **Handle ambiguity** — if a match is unclear, note it rather than forcing a binary match/mismatch
