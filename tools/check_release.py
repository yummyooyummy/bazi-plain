#!/usr/bin/env python3
"""Pre-release checks for bazi-plain. Standard library only.

Checks:
  1. Relative links and images in tracked Markdown files point to files that exist.
  2. SKILL.md frontmatter follows the Agent Skills naming rules.
  3. Public text files do not contain local home-directory paths.
  4. Optional: none of the strings listed in an external private file appear in
     tracked files. Point BAZI_PRIVATE_STRINGS_FILE (or --private-strings) at a
     file OUTSIDE the repository, one string per line. Without it, this check is
     reported as skipped, never as passed.

Exit code 0 when every executed check passes, 1 otherwise.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules"}
TEXT_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".txt", ".toml", ".cfg", ".svg"}
LOCAL_PATH = re.compile(r"(/Users/[A-Za-z0-9._-]+|[A-Za-z]:\\Users\\[A-Za-z0-9._-]+|/home/[a-z][a-z0-9._-]*/)")
MD_LINK = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
HTML_REF = re.compile(r"""(?:src|href)\s*=\s*["']([^"']+)["']""")
NAME_RULE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def tracked_files() -> list[Path]:
    """Files git would publish; falls back to a directory walk outside a repo."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT, capture_output=True, check=True,
        ).stdout.decode("utf-8")
        files = [ROOT / p for p in out.split("\0") if p]
    except (OSError, subprocess.CalledProcessError):
        files = [p for p in ROOT.rglob("*") if p.is_file()]
    return sorted(p for p in files
                  if p.is_file() and not SKIP_DIRS.intersection(p.relative_to(ROOT).parts))


def strip_code(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", text)


def check_links(files: list[Path]) -> list[str]:
    errors = []
    for md in (f for f in files if f.suffix == ".md"):
        text = strip_code(md.read_text(encoding="utf-8"))
        targets = MD_LINK.findall(text) + HTML_REF.findall(text)
        for raw in targets:
            if re.match(r"^[a-z][a-z0-9+.-]*:", raw, re.I) or raw.startswith("#"):
                continue
            path = unquote(raw.split("#", 1)[0].split("?", 1)[0])
            if not path:
                continue
            target = (md.parent / path).resolve()
            if not target.exists():
                errors.append(f"{md.relative_to(ROOT)}: missing link target {raw}")
    return errors


def check_skill() -> list[str]:
    skill = ROOT / "SKILL.md"
    if not skill.exists():
        return ["SKILL.md not found"]
    text = skill.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return ["SKILL.md: missing YAML frontmatter"]
    fields = dict(re.findall(r"^([a-z-]+):\s*(.*)$", m.group(1), re.M))
    errors = []
    name, desc = fields.get("name", ""), fields.get("description", "")
    if not (1 <= len(name) <= 64 and NAME_RULE.match(name)):
        errors.append(f"SKILL.md: name {name!r} must be 1-64 chars of a-z, 0-9 and single hyphens")
    if not (1 <= len(desc) <= 1024):
        errors.append("SKILL.md: description must be 1-1024 characters")
    if name != "bazi-plain":
        errors.append(f"SKILL.md: name is {name!r}; docs and install paths expect 'bazi-plain'")
    if ROOT.name != name:
        print(f"note: local folder is {ROOT.name!r}; installed copies must live in a folder named {name!r}")
    return errors


def check_local_paths(files: list[Path]) -> list[str]:
    errors = []
    for f in files:
        if f.suffix not in TEXT_SUFFIXES or f == Path(__file__).resolve():
            continue
        for no, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            hit = LOCAL_PATH.search(line)
            if hit:
                errors.append(f"{f.relative_to(ROOT)}:{no}: local path {hit.group(0)!r}")
    return errors


def check_private_strings(files: list[Path], source: str | None) -> tuple[list[str], bool]:
    if not source:
        return [], False
    src = Path(source).expanduser().resolve()
    if ROOT in src.parents:
        return [f"private strings file must be outside the repository: {src}"], True
    needles = [s.strip() for s in src.read_text(encoding="utf-8").splitlines()
               if s.strip() and not s.lstrip().startswith("#")]
    errors = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for n in needles:
            if n in text:
                # Do not echo the private string itself.
                errors.append(f"{f.relative_to(ROOT)}: contains an entry from the private list")
                break
    return errors, True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--private-strings", default=os.environ.get("BAZI_PRIVATE_STRINGS_FILE"))
    args = parser.parse_args()

    files = tracked_files()
    failed = False
    for label, errors in [("links", check_links(files)),
                          ("skill name", check_skill()),
                          ("local paths", check_local_paths(files))]:
        print(f"[{'FAIL' if errors else 'ok'}] {label}")
        for e in errors:
            print("   ", e)
        failed |= bool(errors)

    errors, ran = check_private_strings(files, args.private_strings)
    if not ran:
        print("[skip] private strings: set BAZI_PRIVATE_STRINGS_FILE to a list kept outside the repo")
    else:
        print(f"[{'FAIL' if errors else 'ok'}] private strings")
        for e in errors:
            print("   ", e)
        failed |= bool(errors)

    print(f"checked {len(files)} files")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
