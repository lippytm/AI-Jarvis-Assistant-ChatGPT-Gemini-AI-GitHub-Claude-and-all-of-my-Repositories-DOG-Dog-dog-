#!/usr/bin/env python3
"""Check control-plane files for credential patterns without printing their values.

This small preflight check covers every regular file under .jarvis and .github.
It is a pattern check, not a replacement for repository-wide secret scanning or
provider-side credential validation. Missing/unreadable paths and symlinks fail
the check rather than silently reducing coverage.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import stat
import sys


CONTROL_DIRECTORIES = (".jarvis", ".github")
RULES = (
    (
        "model_api_key",
        re.compile(rb"(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{20,}(?![A-Za-z0-9_-])"),
    ),
    (
        "google_api_key",
        re.compile(rb"(?<![A-Za-z0-9_-])AIza[A-Za-z0-9_-]{30,}(?![A-Za-z0-9_-])"),
    ),
    (
        "aws_access_key_id",
        re.compile(rb"(?<![A-Z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])"),
    ),
    (
        "github_token",
        re.compile(rb"(?<![A-Za-z0-9_])gh[pousr]_[A-Za-z0-9]{36,}(?![A-Za-z0-9_])"),
    ),
    (
        "github_fine_grained_token",
        re.compile(rb"(?<![A-Za-z0-9_])github_pat_[A-Za-z0-9_]{40,}(?![A-Za-z0-9_])"),
    ),
    (
        "private_key_header",
        re.compile(rb"-----BEGIN (?:(?:RSA|EC|DSA|OPENSSH|ENCRYPTED) )?PRIVATE KEY-----"),
    ),
)


class ScanError(Exception):
    """A coverage failure with safe metadata only."""

    def __init__(self, path: Path, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(reason)


def _file_kind(path: Path) -> int:
    try:
        mode = path.lstat().st_mode
    except OSError:
        raise ScanError(path, "missing_or_unreadable_path") from None
    if stat.S_ISLNK(mode):
        raise ScanError(path, "symlink_not_allowed")
    return mode


def _files(directory: Path):
    try:
        entries = sorted(directory.iterdir())
    except OSError:
        raise ScanError(directory, "unreadable_directory") from None
    for path in entries:
        mode = _file_kind(path)
        if stat.S_ISDIR(mode):
            yield from _files(path)
        elif stat.S_ISREG(mode):
            yield path
        else:
            raise ScanError(path, "unsupported_file_type")


def scan(repository: Path) -> list[dict[str, str | int]]:
    """Return metadata for candidate credentials; never return matched content."""
    findings = []
    for name in CONTROL_DIRECTORIES:
        directory = repository / name
        if not stat.S_ISDIR(_file_kind(directory)):
            raise ScanError(directory, "required_directory_missing")
        for path in _files(directory):
            try:
                content = path.read_bytes()
            except OSError:
                raise ScanError(path, "unreadable_file") from None
            for rule, pattern in RULES:
                for match in pattern.finditer(content):
                    findings.append({
                        "path": path.relative_to(repository).as_posix(),
                        "line": content.count(b"\n", 0, match.start()) + 1,
                        "rule": rule,
                    })
    return sorted(findings, key=lambda finding: (finding["path"], finding["line"], finding["rule"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        findings = scan(args.repository)
    except ScanError as exc:
        try:
            path = exc.path.relative_to(args.repository).as_posix()
        except ValueError:
            path = str(exc.path)
        print(json.dumps({"path": path, "error": exc.reason}), file=sys.stderr)
        return 2
    for finding in findings:
        print(json.dumps(finding, sort_keys=True))
    if findings:
        print(f"Credential scan failed: {len(findings)} potential credential pattern(s). Values omitted.", file=sys.stderr)
        return 1
    print("Credential scan passed for .jarvis and .github.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
