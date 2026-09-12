"""Cut a release, git-flow style, in one command.

    python3 scripts/release.py              # next build of the current Tesseract
    python3 scripts/release.py --dry-run    # show the plan, change nothing

From a clean, pushed develop whose build-windows and build-macos runs are
green: release branch -> master (--no-ff), annotated tag
tesseract-<version>-pdfmcp<n> on master, master merged back into develop,
then master, develop and the tag pushed. The tag starts release.yml, which
rebuilds, checks, attests and publishes the zips.

Safe to rerun: every check runs before anything changes, the tag must be
new locally and on GitHub, all merges and the tag are made locally first,
any failure rolls them back, and one atomic push publishes all three refs
or none.

<version> is the Tesseract version named in release.yml's notes, so the tag
and the release page cannot disagree; <n> counts up from the last tag for
that version, starting at 1.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELEASE_YML = ROOT / ".github" / "workflows" / "release.yml"
BUILD_WORKFLOWS = ("build-windows", "build-macos")


def run(*cmd: str, capture: bool = True) -> str:
    result = subprocess.run(
        cmd, cwd=ROOT, check=True, text=True, capture_output=capture
    )
    return (result.stdout or "").strip()


def fail(message: str) -> None:
    sys.exit(f"release: {message}")


def tesseract_version() -> str:
    m = re.search(r"\(Tesseract (\d+\.\d+\.\d+),", RELEASE_YML.read_text("utf-8"))
    if not m:
        fail("release.yml's notes no longer name a Tesseract version")
    return m.group(1)


def next_tag(version: str, existing: list[str]) -> str:
    builds = [
        int(m.group(1))
        for t in existing
        if (m := re.fullmatch(rf"tesseract-{re.escape(version)}-pdfmcp(\d+)", t))
    ]
    return f"tesseract-{version}-pdfmcp{max(builds, default=0) + 1}"


def check_ready() -> dict[str, str]:
    """Every precondition, before anything changes. Returns the SHAs that a
    rollback restores."""
    run("gh", "auth", "status")
    if run("git", "branch", "--show-current") != "develop":
        fail("run this from develop")
    if run("git", "status", "--porcelain", "--untracked-files=no"):
        fail("develop has uncommitted changes")
    run("git", "fetch", "-q", "--tags", "origin")
    head = run("git", "rev-parse", "develop")
    if head != run("git", "rev-parse", "origin/develop"):
        fail("develop and origin/develop differ; pull or push first")
    if run("git", "rev-list", "--count", "develop..origin/master") != "0":
        fail("master has commits develop lacks; merge master into develop first")
    for workflow in BUILD_WORKFLOWS:
        runs = json.loads(
            run(
                "gh", "run", "list", "--workflow", f"{workflow}.yml",
                "--commit", head, "--json", "status,conclusion",
            )
        )
        if not any(r["conclusion"] == "success" for r in runs):
            state = runs[0]["status"] if runs else "no run"
            fail(f"{workflow} is not green on develop {head[:7]} ({state})")
    return {
        "develop": head,
        "master": run("git", "rev-parse", "origin/master"),
    }


def tag_is_free(tag: str) -> None:
    if run("git", "tag", "-l", tag) or run(
        "git", "ls-remote", "--tags", "origin", f"refs/tags/{tag}"
    ):
        fail(f"tag {tag} already exists")


def rollback(start: dict[str, str], tag: str, branch: str) -> None:
    """Undo the local steps; nothing was pushed, so this is all of it."""
    subprocess.run(["git", "merge", "--abort"], cwd=ROOT, capture_output=True)
    run("git", "checkout", "-q", "--force", "develop")
    run("git", "reset", "-q", "--hard", start["develop"])
    run("git", "branch", "-f", "master", start["master"])
    for cmd in (["git", "tag", "-d", tag], ["git", "branch", "-D", branch]):
        subprocess.run(cmd, cwd=ROOT, capture_output=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true", help="skip the prompt")
    args = parser.parse_args(argv)

    start = check_ready()
    version = tesseract_version()
    tag = next_tag(version, run("git", "tag", "-l", "tesseract-*").split())
    tag_is_free(tag)
    branch = f"release/{tag.removeprefix('tesseract-')}"
    build = tag.rsplit("pdfmcp", 1)[1]
    local = [
        ["git", "branch", "-f", "master", start["master"]],
        ["git", "checkout", "-q", "master"],
        ["git", "branch", branch, "develop"],
        ["git", "merge", "-q", "--no-ff", branch, "-m", f"Merge branch '{branch}'"],
        ["git", "tag", "-a", tag, "-m", f"Tesseract {version}, pdf-mcp build {build}"],
        ["git", "checkout", "-q", "develop"],
        ["git", "merge", "-q", "--no-ff", "master", "-m",
         f"Merge tag '{tag}' into develop"],
        ["git", "branch", "-q", "-d", branch],
    ]
    # One atomic push: master, develop and the tag land together or not at
    # all, so a rejected push cannot leave a tag without its master commit.
    push = ["git", "push", "--atomic", "-q", "origin", "master", "develop", tag]
    print(f"Release {tag} from develop {start['develop'][:7]} (both builds green):")
    for step in local + [push]:
        print("  " + " ".join(step))
    if args.dry_run:
        print("dry run: nothing changed")
        return 0
    if not args.yes:
        try:
            answer = input(f"Publish {tag}? [y/N] ")
        except EOFError:  # no terminal: never publish by default
            answer = ""
        if answer.strip().lower() != "y":
            print("aborted: nothing changed (pass --yes when there is no terminal)")
            return 1
    try:
        for step in local:
            run(*step)
    except subprocess.CalledProcessError as exc:
        rollback(start, tag, branch)
        fail(f"{' '.join(exc.cmd)} failed; rolled back, nothing pushed\n{exc.stderr}")
    try:
        run(*push)
    except subprocess.CalledProcessError as exc:
        rollback(start, tag, branch)
        fail(f"push rejected; rolled back, nothing published\n{exc.stderr}")
    print(f"Pushed {tag}; release.yml is building and publishing it:")
    print(f"  gh run list --workflow release.yml --branch {tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
