# Lab 01 Grading Runbook

Instructions for grading Lab 01 (agentic coding on the taxi-data pipeline).
This file is written to be handed to Claude Code (or followed by a human TA).
Everything under `solution/` is instructor-only; the assignment-setup tooling
(github.com/dsan-gu/assignment-setup) withholds it when creating student repos.

## What you are grading

The lab is worth 100 points. The mechanical half is checked by script; the
reflection carries half the grade and needs human/agent judgment:

| Deliverable | Points | Checked by |
|-------------|--------|------------|
| Green CI on the latest commit (pytest on the fixture + ruff) | 15 | script |
| `AGENTS.md` and `CLAUDE.md` at the repo root | 15 | script (exists) + Step 3 (quality) |
| `src/pipeline/clean.py` and `src/pipeline/transform.py` | 10 | script (exists) + Step 3 (skim) |
| `results.md` from a run against at least one month of REAL data (a real month is about 3.5M rows; the fixture is only 5,010 -- fixture-sized numbers mean the scale run was skipped) | 10 | script |
| `REFLECTION.md` covering: architecture summary, the AGENTS.md before/after experiment, a proprietary vs open-source tool comparison, one failure case, one rewritten prompt | 50 | Step 3 only |

**REFLECTION.md must be entirely human-written. Per the lab README, a
reflection judged to be AI-written scores 0 for the ENTIRE lab, not just the
reflection.** Signals of AI writing: generic polish with no repo-specific
details, no named prompts or observed failures, hedged both-sides prose,
content that could have been written without doing the lab. Signals of honest
writing: specific prompts quoted, specific diffs rejected, typos, opinions.
When in doubt, do not accuse -- flag it for the instructor with the evidence
and let a human make the call and have the conversation.

## Step 1: Run the sweep script

Prerequisites: `gh` CLI authenticated with access to the gu-dsan6725 org
(`gh auth status` to verify), and a roster CSV. The assignment-setup roster format works
(it has a `github_username` column); a plain file with one
username per line also works. See `roster.example.csv`.

```bash
cd lab01-agentic-coding
uv run python solution/grade_lab01.py --roster solution/roster.csv
```

This clones/updates all 45 repos into `grading-workdir/`, checks CI status for
each student's latest commit, verifies every deliverable file exists, parses
`results.md` for the row count, and writes `grades_report.md` -- a table sorted
with incomplete submissions first.

Re-running is safe and incremental (existing clones are pulled, not recloned).

## Step 2: Interpret the table

| Column | Meaning | Action if bad |
|--------|---------|---------------|
| CI | success / failure / pending / none / unknown | `failure`: open the repo's Actions tab, note which stage failed (ruff vs pytest). `none`: student deleted or never triggered the workflow. `pending`: re-run the script in a few minutes. |
| Files missing | Deliverables absent from the repo | List them in feedback; each missing file is an incomplete deliverable |
| Real-data run | results.md row count >= 1,000,000 | "NO" with a note about fixture-sized numbers means they never ran real data -- ask for a re-run, or mark the deliverable incomplete |
| Complete | All mechanical checks passed | These repos move to Step 3 |

## Step 3: Qualitative review (the part that needs judgment)

For each repo, read three files (in `grading-workdir/<repo>/`):

**AGENTS.md** -- must be specific to this repo, not boilerplate. Check for, at
minimum: uv-only, polars-only/no-pandas, stay-lazy (scan_parquet / no eager
collect), run pytest+ruff before done, tests are read-only. Generic
"be a helpful assistant" content or a copy of the course repo's AGENTS.md
scores as weak.

**REFLECTION.md** -- the before/after section must describe an actual observed
difference (e.g., "it used pandas before, polars after"), and the tool
comparison must name both tools they used and say something non-generic. A
reflection that could have been written without doing the lab is the red flag.

**src/pipeline/clean.py and transform.py** -- skim for: LazyFrame in/out
(no .collect() inside the functions), no pandas import, reasonable polars
idioms. Compare against `solution/reference/` for expected shape (student
code does not need to match it, but wildly different approaches that still
pass tests are fine and worth a look).

Also glance at `git log --oneline` in a few repos: a single giant "done" commit
is worth a gentle note; the lab workflow naturally produces several commits.

## Step 4: Record grades

Score each submission out of 100 using the table above. Mechanical deliverables
score all-or-nothing from the script's columns; AGENTS.md/CLAUDE.md and the
modules can lose partial credit in Step 3 for boilerplate or unreviewed junk;
the reflection is scored 0-50 on specificity and evidence of having done the
work. Borderline cases (green CI but thin reflection) get one resubmission
request via a GitHub issue on the student's repo before losing points.
Suspected AI-written reflections: flag with evidence, instructor decides; if
confirmed, the entire lab scores 0.

When grading with Claude Code: produce a final `grades_final.csv` with columns
`github_username,score,notes` -- start from grades_report.md, apply the Step 3
judgments, and keep notes short and actionable (they may be pasted into
feedback issues).

## Edge cases

- **Student repo missing**: create_repos.py was not run for them, or they were added late;
  contact them directly.
- **CI red only on ruff**: minor -- note it, request a fix, do not fail the lab
  for formatting alone.
- **Tests modified**: `git diff origin/main -- tests/` inside the clone against
  the template's tests, or spot-check test files against this repo. Modified
  tests to force a pass is an academic integrity conversation, not a grading
  note; escalate to the instructor.
- **results.md with 12 months** (~41M rows): fine, that is enthusiasm, not
  an error.
