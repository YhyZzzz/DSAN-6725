"""Grade Lab 01 submissions: clone all student repos, check deliverables and CI.

Given a roster of GitHub usernames, this script:
    1. Clones (or updates) each student's GitHub Classroom repo
    2. Checks that every deliverable file exists
    3. Fetches the CI conclusion for the latest commit on the default branch
    4. Parses results.md to verify a real-data run (row count)
    5. Writes a markdown report table (grades_report.md) and prints a summary

Requires the GitHub CLI (gh) authenticated with access to the org.

Example usage:
    # Roster is a CSV with a github_username column (Classroom roster export works)
    uv run python solutions/grade_lab01.py --roster solutions/roster.csv

    # Custom org/prefix or output location
    uv run python solutions/grade_lab01.py --roster roster.csv \
        --org gu-dsan6725 --prefix fall-2026-lab01-agentic-coding \
        --workdir /tmp/lab01-grading --report grades_report.md
"""

import argparse
import csv
import json
import logging
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,p%(process)s,{%(filename)s:%(lineno)d},%(levelname)s,%(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_ORG: str = "gu-dsan6725"
DEFAULT_ASSIGNMENT: str = "lab01-agentic-coding"
DEFAULT_SEMESTER: str = "fall-2026"
REAL_RUN_MIN_ROWS: int = 1_000_000  # one real month is ~3.5M rows; fixture is 5,010

DELIVERABLES: list[str] = [
    "AGENTS.md",
    "CLAUDE.md",
    "src/pipeline/clean.py",
    "src/pipeline/transform.py",
    "results.md",
    "REFLECTION.md",
]


@dataclass
class StudentResult:
    """Grading result for one student."""

    username: str
    repo: str
    cloned: bool = False
    head_sha: str = ""
    ci_conclusion: str = "unknown"
    missing_files: list[str] = field(default_factory=list)
    results_rows: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def real_run(self) -> bool:
        return self.results_rows >= REAL_RUN_MIN_ROWS

    @property
    def complete(self) -> bool:
        return (
            self.cloned
            and self.ci_conclusion == "success"
            and not self.missing_files
            and self.real_run
        )


def _run(
    cmd: list[str],
    cwd: Path | None = None,
) -> tuple[int, str]:
    """Run a command, returning (returncode, stdout+stderr)."""
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def _read_roster(
    roster_path: Path,
) -> list[str]:
    """Read GitHub usernames from a roster CSV.

    Accepts either a single-column file of usernames or a CSV with a
    github_username column (GitHub Classroom roster export format).
    """
    with open(roster_path, newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        raise ValueError(f"Roster {roster_path} is empty")

    header = [c.strip().lower() for c in rows[0]]
    if "github_username" in header:
        idx = header.index("github_username")
        usernames = [r[idx].strip() for r in rows[1:] if len(r) > idx and r[idx].strip()]
    else:
        usernames = [r[0].strip() for r in rows if r and r[0].strip()]

    logger.info(f"Roster: {len(usernames)} students from {roster_path}")
    if not usernames:
        raise ValueError(
            f"No usernames found in {roster_path}. Expected a github_username "
            "column or one username per line."
        )
    return usernames


def _clone_or_update(
    org: str,
    repo: str,
    dest: Path,
) -> bool:
    """Clone the repo if new, otherwise pull; returns True on success."""
    if dest.exists():
        code, out = _run(["git", "pull", "--ff-only"], cwd=dest)
    else:
        code, out = _run(["gh", "repo", "clone", f"{org}/{repo}", str(dest)])
    if code != 0:
        logger.warning(f"{repo}: clone/update failed: {out.splitlines()[-1] if out else '?'}")
    return code == 0


def _head_sha(
    repo_dir: Path,
) -> str:
    """Return the HEAD commit sha of the cloned repo."""
    code, out = _run(["git", "rev-parse", "HEAD"], cwd=repo_dir)
    return out if code == 0 else ""


def _ci_conclusion(
    org: str,
    repo: str,
    sha: str,
) -> str:
    """Return the combined CI conclusion for a commit via check-runs.

    Returns one of: success, failure, pending, none, unknown.
    """
    code, out = _run(
        ["gh", "api", f"repos/{org}/{repo}/commits/{sha}/check-runs", "--jq", "."]
    )
    if code != 0:
        return "unknown"
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return "unknown"

    runs = data.get("check_runs", [])
    if not runs:
        return "none"
    conclusions = {r.get("conclusion") for r in runs}
    if None in conclusions:
        return "pending"
    if conclusions <= {"success", "neutral", "skipped"}:
        return "success"
    return "failure"


def _parse_results_rows(
    repo_dir: Path,
) -> int:
    """Extract the 'Rows scanned' count from results.md, or 0 if absent."""
    results = repo_dir / "results.md"
    if not results.exists():
        return 0
    match = re.search(r"Rows scanned:\s*([\d,]+)", results.read_text())
    if not match:
        return 0
    return int(match.group(1).replace(",", ""))


def _grade_student(
    username: str,
    org: str,
    assignment: str,
    semester: str,
    workdir: Path,
) -> StudentResult:
    """Clone and evaluate one student's repo.

    Repo naming follows assignment-setup's create_repos.py:
    <assignment>-<username>-<semester>.
    """
    repo = f"{assignment}-{username}-{semester}"
    result = StudentResult(username=username, repo=repo)
    repo_dir = workdir / repo

    result.cloned = _clone_or_update(org, repo, repo_dir)
    if not result.cloned:
        result.notes.append("repo missing or inaccessible")
        return result

    result.head_sha = _head_sha(repo_dir)
    result.ci_conclusion = _ci_conclusion(org, repo, result.head_sha)
    result.missing_files = [d for d in DELIVERABLES if not (repo_dir / d).exists()]
    result.results_rows = _parse_results_rows(repo_dir)

    if result.results_rows and not result.real_run:
        result.notes.append(
            f"results.md shows {result.results_rows:,} rows (fixture-sized, not real data)"
        )
    return result


def _write_report(
    results: list[StudentResult],
    report_path: Path,
) -> None:
    """Write the markdown grading report."""
    lines = [
        "# Lab 01 Grading Report",
        "",
        f"Students: {len(results)} | "
        f"Complete: {sum(r.complete for r in results)} | "
        f"Incomplete: {sum(not r.complete for r in results)}",
        "",
        "| Student | CI | Files missing | Real-data run | Complete | Notes |",
        "|---------|----|---------------|---------------|----------|-------|",
    ]
    for r in sorted(results, key=lambda x: (x.complete, x.username)):
        missing = ", ".join(r.missing_files) if r.missing_files else "-"
        rows = f"yes ({r.results_rows:,} rows)" if r.real_run else "NO"
        notes = "; ".join(r.notes) if r.notes else "-"
        complete = "yes" if r.complete else "NO"
        lines.append(
            f"| {r.username} | {r.ci_conclusion} | {missing} | {rows} | {complete} | {notes} |"
        )
    report_path.write_text("\n".join(lines) + "\n")
    logger.info(f"Report written to {report_path}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Grade Lab 01 submissions across all student repos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
    uv run python solutions/grade_lab01.py --roster solutions/roster.csv
""",
    )
    parser.add_argument("--roster", type=Path, required=True,
                        help="CSV roster with a github_username column (or one username per line)")
    parser.add_argument("--org", default=DEFAULT_ORG,
                        help=f"GitHub organization (default: {DEFAULT_ORG})")
    parser.add_argument("--assignment", default=DEFAULT_ASSIGNMENT,
                        help=f"Assignment name (default: {DEFAULT_ASSIGNMENT})")
    parser.add_argument("--semester", default=DEFAULT_SEMESTER,
                        help=f"Semester label used in repo names (default: {DEFAULT_SEMESTER})")
    parser.add_argument("--workdir", type=Path, default=Path("grading-workdir"),
                        help="Where repos are cloned (default: grading-workdir)")
    parser.add_argument("--report", type=Path, default=Path("grades_report.md"),
                        help="Output report path (default: grades_report.md)")
    return parser.parse_args()


def main() -> None:
    """Orchestrate: read roster, grade each student, write the report."""
    args = _parse_args()

    code, out = _run(["gh", "auth", "status"])
    if code != 0:
        raise SystemExit(f"gh is not authenticated. Run: gh auth login\n{out}")

    usernames = _read_roster(args.roster)
    args.workdir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    results = []
    for i, username in enumerate(usernames, 1):
        logger.info(f"[{i}/{len(usernames)}] {username}")
        results.append(
            _grade_student(username, args.org, args.assignment, args.semester, args.workdir)
        )

    _write_report(results, args.report)

    elapsed_time = time.time() - start_time
    minutes = int(elapsed_time // 60)
    seconds = elapsed_time % 60
    if minutes > 0:
        logger.info(f"Completed in {minutes} minutes and {seconds:.1f} seconds")
    else:
        logger.info(f"Completed in {seconds:.1f} seconds")

    incomplete = [r for r in results if not r.complete]
    if incomplete:
        logger.warning(f"{len(incomplete)} incomplete submission(s); see the report table.")


if __name__ == "__main__":
    main()
