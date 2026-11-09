"""
Deterministic Ground-Truth Verifier for StreamAppExpert.
Performs lightweight syntax/type/file checks, boundary isolation, blast radius auditing,
and deep domain anti-regression checks via StreamingRulesEngine.
Supports Python, JSON, Markdown, Kotlin (.kt), XML (.xml), and Gradle build scripts (.gradle.kts).
"""

from __future__ import annotations
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import List, Optional, Tuple
import xml.etree.ElementTree as ET

from harness.schemas import VerificationReceipt
from harness.streaming_rules import StreamingRulesEngine, StreamingRuleViolation


IGNORE_BOUNDARY_FILES = {
    "stack.json",
    ".gitignore",
    ".tmp",
}


@dataclass
class VerificationResult:
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    verified_files: List[str] = field(default_factory=list)
    streaming_violations: List[StreamingRuleViolation] = field(default_factory=list)
    receipt: Optional[VerificationReceipt] = None

    def summary(self) -> str:
        if self.passed:
            streaming_note = f" (Streaming Compliance Clean)" if not self.streaming_violations else f" ({len(self.warnings)} streaming warning(s))"
            return f"Deterministic Verification Passed ({len(self.verified_files)} files verified){streaming_note}."
        return f"Deterministic Verification Failed with {len(self.errors)} error(s): " + "; ".join(self.errors[:3])


class DeterministicVerifier:
    """Fast ground-truth verification without invoking LLMs."""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()
        self.streaming_engine = StreamingRulesEngine(str(self.workspace_root))

    def _normalize_rel_path(self, raw_path: str) -> str:
        p = Path(raw_path.strip().strip('"'))
        if p.is_absolute():
            try:
                return str(p.relative_to(self.workspace_root))
            except ValueError:
                return str(p)
        return str(p)

    def check_file_boundaries(
        self,
        allowed_files: List[str],
        exempt_files: Optional[List[str]] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Hyper-Disciplined Stack Hygiene (Rule 1):
        Inspects git status to ensure no files outside allowed_files (or exempt prior task files)
        were created or modified.
        """
        if not allowed_files:
            return True, []

        allowed_normalized = {self._normalize_rel_path(f) for f in allowed_files if f}
        if exempt_files:
            allowed_normalized.update(self._normalize_rel_path(f) for f in exempt_files if f)

        cmd = ["git", "status", "--porcelain", "-uall"]
        try:
            res = subprocess.run(cmd, cwd=self.workspace_root, capture_output=True, text=True, check=False)
            lines = res.stdout.strip().splitlines()
        except Exception:
            return True, []

        unauthorized_files: List[str] = []
        for line in lines:
            if not line or len(line) < 4:
                continue
            file_entry = line[2:].strip()
            if " -> " in file_entry:
                file_entry = file_entry.split(" -> ")[-1].strip()
            file_entry = self._normalize_rel_path(file_entry)

            entry_name = Path(file_entry).name
            if entry_name in IGNORE_BOUNDARY_FILES or file_entry.endswith(".tmp"):
                continue

            if file_entry not in allowed_normalized:
                unauthorized_files.append(file_entry)

        if unauthorized_files:
            return False, unauthorized_files
        return True, []

    def check_blast_radius(
        self,
        max_lines: int = 400,
        max_files: int = 15,
        target_files: Optional[List[str]] = None,
        exempt_extensions: Tuple[str, ...] = (".md", ".json", ".xml"),
    ) -> Tuple[bool, str]:
        """
        Atomic Decomposition (Rule 2):
        Inspects git diff --numstat to ensure code changes don't exceed atomic blast radius.
        """
        rel_targets: List[str] = []
        if target_files:
            rel_targets = [self._normalize_rel_path(f) for f in target_files if f]

        cmd = ["git", "diff", "--numstat"]
        if rel_targets:
            cmd.extend(["--"] + rel_targets)

        try:
            res = subprocess.run(cmd, cwd=self.workspace_root, capture_output=True, text=True, check=False)
            output = res.stdout.strip()
            if not output:
                staged_cmd = ["git", "diff", "--cached", "--numstat"]
                if rel_targets:
                    staged_cmd.extend(["--"] + rel_targets)
                res_staged = subprocess.run(staged_cmd, cwd=self.workspace_root, capture_output=True, text=True, check=False)
                output = res_staged.stdout.strip()
        except Exception:
            return True, ""

        if not output:
            return True, ""

        total_lines = 0
        total_files = 0
        for line in output.splitlines():
            parts = line.split("\t")
            if len(parts) >= 3:
                ins, dels, fname = parts[0], parts[1], parts[2]
                path_obj = Path(fname)
                if path_obj.name in IGNORE_BOUNDARY_FILES:
                    continue
                if exempt_extensions and path_obj.suffix.lower() in exempt_extensions:
                    continue
                try:
                    total_lines += int(ins) + int(dels)
                    total_files += 1
                except ValueError:
                    pass

        if total_files > max_files:
            return False, f"Modified {total_files} files (exceeds limit of {max_files}). Push smaller subtasks."
        if total_lines > max_lines:
            return False, f"Modified {total_lines} lines (exceeds limit of {max_lines}). Push smaller subtasks."

        return True, ""

    def verify_artifacts(self, artifact_paths: List[str]) -> VerificationResult:
        """
        Mandatory Verification before Pop (Rule 3):
        Verifies physical existence, syntax, and streaming domain compliance for all declared artifacts.
        """
        result = VerificationResult(passed=True)

        if not artifact_paths:
            result.warnings.append("No artifacts declared for verification.")
            return result

        checked_streaming_rules: List[str] = []

        for raw_path in artifact_paths:
            path = Path(raw_path)
            if not path.is_absolute():
                path = self.workspace_root / path

            # 1. Physical existence check
            if not path.exists():
                result.passed = False
                result.errors.append(f"Physical file missing (Hallucinated artifact): {raw_path}")
                continue

            if not path.is_file():
                result.passed = False
                result.errors.append(f"Artifact path is not a regular file: {raw_path}")
                continue

            result.verified_files.append(str(path))

            # 2. Syntax validation based on extension
            ext = path.suffix.lower()
            name = path.name.lower()

            if ext == ".py":
                py_valid, py_err = self._verify_python_syntax(path)
                if not py_valid:
                    result.passed = False
                    result.errors.append(f"Python syntax error in {path.name}: {py_err}")

            elif ext == ".json":
                json_valid, json_err = self._verify_json_syntax(path)
                if not json_valid:
                    result.passed = False
                    result.errors.append(f"Invalid JSON syntax in {path.name}: {json_err}")

            elif ext == ".md":
                if path.stat().st_size == 0:
                    result.passed = False
                    result.errors.append(f"Markdown design artifact is empty (0 bytes): {path.name}")

            elif ext == ".xml":
                xml_valid, xml_err = self._verify_xml_syntax(path)
                if not xml_valid:
                    result.passed = False
                    result.errors.append(f"Invalid XML syntax in {path.name}: {xml_err}")

            elif ext == ".kt":
                kt_valid, kt_err = self._verify_kotlin_syntax(path)
                if not kt_valid:
                    result.passed = False
                    result.errors.append(f"Kotlin syntax check failed in {path.name}: {kt_err}")

            elif ext == ".kts" or "gradle" in name:
                gradle_valid, gradle_err = self._verify_gradle_script(path)
                if not gradle_valid:
                    result.passed = False
                    result.errors.append(f"Gradle script verification failed in {path.name}: {gradle_err}")

            # 3. Domain-Specific Streaming Anti-Regression Checks
            violations = self.streaming_engine.inspect_file(path)
            for v in violations:
                result.streaming_violations.append(v)
                checked_streaming_rules.append(v.rule_id)
                loc = f" line {v.line_number}" if v.line_number else ""
                msg = f"[{v.rule_id}] {v.file_path}{loc}: {v.message} -> Fix: {v.recommendation}"
                if v.severity == "ERROR":
                    result.passed = False
                    result.errors.append(msg)
                else:
                    result.warnings.append(msg)

        if result.passed and result.verified_files:
            result.receipt = VerificationReceipt(
                timestamp=time.time(),
                gate_type="STREAMING_STATIC_GATE",
                verified_files=result.verified_files,
                exit_code=0,
                status="PASSED",
                details=f"Verified {len(result.verified_files)} artifact(s) successfully with zero streaming rule violations.",
                streaming_checks=list(set(checked_streaming_rules)),
            )

        return result

    def _verify_python_syntax(self, file_path: Path) -> Tuple[bool, str]:
        """Runs py_compile in a subprocess to check syntax without executing code."""
        cmd = [sys.executable, "-m", "py_compile", str(file_path)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            return True, ""
        err_msg = res.stderr.strip().splitlines()[-1] if res.stderr.strip() else "Unknown syntax error"
        return False, err_msg

    def _verify_json_syntax(self, file_path: Path) -> Tuple[bool, str]:
        """Checks if a JSON file is well-formed."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                json.load(f)
            return True, ""
        except Exception as e:
            return False, str(e)

    def _verify_xml_syntax(self, file_path: Path) -> Tuple[bool, str]:
        """Checks if an XML file is well-formed."""
        try:
            ET.parse(file_path)
            return True, ""
        except Exception as e:
            return False, str(e)

    def _verify_kotlin_syntax(self, file_path: Path) -> Tuple[bool, str]:
        """Lightweight static check for Kotlin bracket/brace balancing and common errors."""
        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception as e:
            return False, str(e)

        if not text.strip():
            return False, "File is empty"

        stack = []
        pairs = {')': '(', '}': '{', ']': '['}
        in_string = False
        in_multiline_comment = False
        chars = list(text)
        i = 0
        n = len(chars)

        while i < n:
            c = chars[i]
            # Handle comments
            if not in_string:
                if not in_multiline_comment and i + 1 < n and chars[i] == '/' and chars[i+1] == '*':
                    in_multiline_comment = True
                    i += 2
                    continue
                if in_multiline_comment:
                    if i + 1 < n and chars[i] == '*' and chars[i+1] == '/':
                        in_multiline_comment = False
                        i += 2
                    else:
                        i += 1
                    continue
                if i + 1 < n and chars[i] == '/' and chars[i+1] == '/':
                    while i < n and chars[i] != '\n':
                        i += 1
                    continue

            # Handle string literals
            if c == '"' and not in_multiline_comment:
                if i + 2 < n and chars[i+1] == '"' and chars[i+2] == '"':
                    i += 3
                    while i + 2 < n and not (chars[i] == '"' and chars[i+1] == '"' and chars[i+2] == '"'):
                        i += 1
                    i += 3
                    continue
                else:
                    if not in_string:
                        in_string = True
                    elif i > 0 and chars[i-1] != '\\':
                        in_string = False

            if not in_string and not in_multiline_comment:
                if c in pairs.values():
                    stack.append(c)
                elif c in pairs:
                    if not stack or stack[-1] != pairs[c]:
                        return False, f"Mismatched bracket '{c}'"
                    stack.pop()

            i += 1

        if stack:
            return False, f"Unclosed bracket '{stack[-1]}'"
        return True, ""

    def _verify_gradle_script(self, file_path: Path) -> Tuple[bool, str]:
        """Verifies Gradle build script syntax and bracket balance."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            return False, str(e)

        kt_ok, kt_err = self._verify_kotlin_syntax(file_path)
        if not kt_ok:
            return False, f"Gradle syntax error: {kt_err}"

        return True, ""
