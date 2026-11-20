"""Collect check findings and print them for humans, agents and GitHub Actions."""
from __future__ import annotations

import os
import sys


def _escape(msg: str) -> str:
    return msg.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


class Report:
    def __init__(self, check: str):
        self.check = check
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.notes: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def note(self, msg: str) -> None:
        self.notes.append(msg)

    @property
    def ok(self) -> bool:
        return not self.errors

    def emit(self, stream=None) -> int:
        stream = stream or sys.stdout
        in_actions = os.environ.get("GITHUB_ACTIONS") == "true"
        status = "PASS" if self.ok else "FAIL"
        print(f"[{self.check}] {status}", file=stream)
        for e in self.errors:
            print(f"::error title={self.check}::{_escape(e)}" if in_actions else f"  ERROR: {e}", file=stream)
        for w in self.warnings:
            print(f"::warning title={self.check}::{_escape(w)}" if in_actions else f"  WARN:  {w}", file=stream)
        for n in self.notes:
            print(f"  note: {n}", file=stream)

        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as fh:
                icon = "✅" if self.ok else "❌"
                fh.write(f"### {icon} {self.check}\n\n")
                for e in self.errors:
                    fh.write(f"- **Error:** {e}\n")
                for w in self.warnings:
                    fh.write(f"- **Warning:** {w}\n")
                for n in self.notes:
                    fh.write(f"- {n}\n")
                if self.ok and not (self.warnings or self.notes):
                    fh.write("All checks passed.\n")
                fh.write("\n")
        return 0 if self.ok else 1
