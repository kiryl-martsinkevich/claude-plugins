# ADO Work Item Comment Templates

ADO work item comments render HTML, not Markdown. Convert before POSTing to `/wit/workitems/{id}/comments?api-version=7.1-preview.4`.

## 0. Clarification Request (Step 1.4 — terminates the run)

Used when requirements are unclear. After posting, the shipit run STOPS. The user re-invokes `/shipit` once the work item is updated.

```html
<h3>Clarification needed (shipit)</h3>
<p>The shipit workflow has been paused — the requirements below are not concrete enough to plan or implement against. Please answer the questions, then re-run <code>/shipit {{workitem_id}}</code>.</p>
<h4>Questions</h4>
<ol>
  <li>{{specific question 1 — point to the ambiguous wording}}</li>
  <li>{{specific question 2}}</li>
</ol>
<h4>What would unblock the run</h4>
<ul>
  <li>{{e.g. "Concrete acceptance criterion for empty-input case"}}</li>
  <li>{{e.g. "Confirmation of which repos are in scope: A, B, both?"}}</li>
</ul>
<p><i>Run halted at Step 1. No comments, plan, or code have been produced.</i></p>
```

Each question must reference a specific gap (a missing acceptance criterion, an undefined data shape, an unspecified repo, a contradiction). Generic prompts like "please clarify" are not acceptable.

## 1. Clarified Requirements (Step 2)

```html
<h3>Clarified requirements (shipit)</h3>
<p><b>Source:</b> brainstorming session, {{date}}</p>
<h4>Scope</h4>
<p>{{one-paragraph scope}}</p>
<h4>Acceptance criteria</h4>
<ul>
  <li>{{criterion 1}}</li>
  <li>{{criterion 2}}</li>
</ul>
<h4>Assumptions</h4>
<ul>
  <li>{{assumption}}</li>
</ul>
<h4>Out of scope</h4>
<ul>
  <li>{{exclusion}}</li>
</ul>
```

Skip the `<h4>Assumptions</h4>` and `<h4>Out of scope</h4>` blocks if empty.

## 2. Implementation Plan (Step 3)

```html
<h3>Implementation plan (shipit)</h3>
<h4>Approach</h4>
<p>{{one-paragraph summary}}</p>
<h4>Repos in scope</h4>
<ul>
  <li><code>{{repo_a}}</code> — independent</li>
  <li><code>{{repo_b}}</code> — depends on {{repo_a}} (consumer)</li>
</ul>
<h4>Phased changes</h4>
<ol>
  <li><b>Phase 1 — {{repo_a}}:</b> {{files / behaviour}}</li>
  <li><b>Phase 2 — {{repo_b}}:</b> {{files / behaviour}}</li>
</ol>
<h4>Test strategy</h4>
<ul>
  <li>Coverage target: ≥ 60% line coverage on changed code, per repo</li>
  <li>Post-implementation: <code>simplify</code> runs on changed files and tests are re-validated</li>
  <li>{{test type / framework}}</li>
</ul>
<h4>Risks</h4>
<ul>
  <li>{{risk + mitigation}}</li>
</ul>
```

Drop the "Repos in scope" section when the work touches a single repo.

## 3. Summary (Step 7)

```html
<h3>Shipped across {{N}} repo(s) (shipit)</h3>

<h4>{{repo_a}}</h4>
<p><b>PR:</b> <a href="{{pr_url_a}}">{{pr_title_a}}</a></p>
<p><b>Branch:</b> <code>{{branch_name_a}}</code> &nbsp; <b>Commit:</b> <code>{{commit_sha_a}}</code></p>
<ul>
  <li>{{file group}}</li>
</ul>
<p>{{n}} tests, {{coverage}}% line coverage. Simplify pass: {{summary or "no changes"}}.</p>

<h4>{{repo_b}}</h4>
<p><b>PR:</b> <a href="{{pr_url_b}}">{{pr_title_b}}</a></p>
<p><b>Branch:</b> <code>{{branch_name_b}}</code> &nbsp; <b>Commit:</b> <code>{{commit_sha_b}}</code></p>
<ul>
  <li>{{file group}}</li>
</ul>
<p>{{n}} tests, {{coverage}}% line coverage. Simplify pass: {{summary or "no changes"}}.</p>

<h4>Merge order</h4>
<p>{{e.g. "Merge {{repo_a}} first; {{repo_b}} consumes its new API." or "Independent — any order."}}</p>

<h4>Deviations from plan</h4>
<ul>
  <li>{{deviation or "None"}}</li>
</ul>
```

Collapse to a single repo section (and drop "Merge order") when only one PR was created.

## Helper: convert text to a JSON-safe POST body

```bash
# $HTML holds the rendered HTML for the comment.
BODY=$(python3 -c 'import json,sys; print(json.dumps({"text": sys.stdin.read()}))' <<<"$HTML")
curl -sS -f -X POST \
  -H "Authorization: Basic $AUTH" \
  -H "Content-Type: application/json" \
  -d "$BODY" \
  "$BASE/wit/workitems/${WORKITEM_ID}/comments?api-version=7.1-preview.4"
```

`$AUTH` and `$BASE` follow the patterns in the `azure-devops:ado-operations` skill.
