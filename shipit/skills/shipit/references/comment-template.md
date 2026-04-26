# ADO Work Item Comment Templates

ADO work item comments render HTML, not Markdown. Convert before POSTing to `/wit/workitems/{id}/comments?api-version=7.1-preview.4`.

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
<h4>Phased changes</h4>
<ol>
  <li><b>Phase 1 — {{title}}:</b> {{files / behaviour}}</li>
  <li><b>Phase 2 — {{title}}:</b> {{files / behaviour}}</li>
</ol>
<h4>Test strategy</h4>
<ul>
  <li>Coverage target: ≥ 60% line coverage on changed code</li>
  <li>{{test type / framework}}</li>
</ul>
<h4>Risks</h4>
<ul>
  <li>{{risk + mitigation}}</li>
</ul>
```

## 3. Summary (Step 7)

```html
<h3>Shipped (shipit)</h3>
<p><b>PR:</b> <a href="{{pr_url}}">{{pr_title}}</a></p>
<p><b>Branch:</b> <code>{{branch_name}}</code> &nbsp; <b>Commit:</b> <code>{{commit_sha}}</code></p>
<h4>Changes</h4>
<ul>
  <li>{{group of files / module}}</li>
</ul>
<h4>Tests</h4>
<p>{{n}} tests, {{coverage}}% line coverage on changed code.</p>
<h4>Deviations from plan</h4>
<ul>
  <li>{{deviation or "None"}}</li>
</ul>
```

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
