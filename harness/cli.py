"""
CLI Interface for StreamAppExpert: Deterministic Multi-Agent Harness for Streaming Applications.
Allows initializing, inspecting, building JIT prompts, stepping state transitions,
and executing streaming-specific compliance linters.
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from harness.schemas import TaskFrame, TaskStatus, SystemState, TaskBudget, StrictLevel, StreamingDomain
from harness.task_stack import TaskStackManager
from harness.state_machine import DeterministicStateMachine
from harness.prompt_builder import PromptOnDemandBuilder
from harness.verifier import DeterministicVerifier
from harness.streaming_rules import StreamingRulesEngine


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="stream-harness",
        description="StreamAppExpert: Deterministic Multi-Agent Harness for Streaming & OTT Applications",
    )
    parser.add_argument(
        "--stack-file",
        default="stack.json",
        help="Path to stack.json file (default: stack.json)",
    )
    parser.add_argument(
        "--strict-level",
        choices=["lenient", "strict", "hardcore"],
        default="strict",
        help="Enforcement level for Strict/Opinionated Mode (default: strict)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. init
    init_parser = subparsers.add_parser("init", help="Initialize a new root streaming task onto the stack")
    init_parser.add_argument("--task-id", default="STREAM-001", help="ID of root task")
    init_parser.add_argument("--title", required=True, help="Title of root task")
    init_parser.add_argument("--desc", default="", help="Description or acceptance criteria")
    init_parser.add_argument(
        "--domain",
        choices=["exoplayer", "mobile_touch", "tv_leanback", "scraper_resolver", "backend_gateway", "apk_optimization", "general"],
        default="general",
        help="Streaming architectural domain",
    )
    init_parser.add_argument("--agent", default="stream_mobile_agent", help="Initial agent (default: stream_mobile_agent)")
    init_parser.add_argument(
        "--allowed-files",
        nargs="*",
        default=[],
        help="List of allowed files for strict boundary checking (Hyper-Disciplined Stack Hygiene)",
    )
    init_parser.add_argument(
        "--max-lines",
        type=int,
        default=200,
        help="Max lines changed for atomic blast radius (default: 200)",
    )

    # 2. status
    subparsers.add_parser("status", help="Print current status and Top of Stack")

    # 3. build-prompt
    prompt_parser = subparsers.add_parser("build-prompt", help="Build JIT prompt on demand for Top of Stack")
    prompt_parser.add_argument("--agent", default=None, help="Override target agent")
    prompt_parser.add_argument("--output", default=None, help="Save generated prompt to file")

    # 4. transition
    trans_parser = subparsers.add_parser("transition", help="Apply agent structured output to advance state")
    trans_parser.add_argument(
        "--input",
        required=True,
        help="Raw output text or JSON string from agent, or path to file containing output",
    )

    # 5. verify
    subparsers.add_parser("verify", help="Run deterministic ground-truth verification on current top artifacts")

    # 6. inspect-stack
    subparsers.add_parser("inspect-stack", help="Display visual stack and history in JSON format")

    # 7. streaming-lint
    lint_parser = subparsers.add_parser("streaming-lint", help="Scan codebase or specific files for streaming bug anti-patterns")
    lint_parser.add_argument(
        "--files",
        nargs="*",
        default=[],
        help="Specific file paths to inspect (defaults to scanning recent git modified files or entire repo)",
    )

    # 8. doctor
    subparsers.add_parser("doctor", help="Check system environment, Git repository, and streaming health diagnostics")

    args = parser.parse_args()

    strict_lvl = StrictLevel(args.strict_level)
    stack_mgr = TaskStackManager(file_path=args.stack_file, strict_level=strict_lvl)
    fsm = DeterministicStateMachine(stack_mgr)

    if args.command == "init":
        domain = StreamingDomain(args.domain)
        root_task = TaskFrame(
            task_id=args.task_id,
            title=args.title,
            description=args.desc,
            assigned_agent=args.agent,
            domain=domain,
            status=TaskStatus.PENDING,
            allowed_files=list(args.allowed_files),
            max_lines_changed=args.max_lines,
        )
        stack_mgr.set_strict_level(strict_lvl)
        stack_mgr.push(root_task)
        initial_state = fsm.state_for_agent(args.agent)
        stack_mgr.set_system_state(initial_state)
        print(f"🎬 [StreamAppExpert] Initialized task stack with root task '{args.task_id}'.")
        print(f"System State:   {initial_state.value}")
        print(f"Domain:         {domain.value.upper()}")
        print(f"Strict Level:   {strict_lvl.value.upper()}")
        print(f"Top Agent:      {args.agent}")
        if args.allowed_files:
            print(f"Allowed Files:  {', '.join(args.allowed_files)}")

    elif args.command == "status":
        print("=" * 65)
        print(f"🎬 StreamAppExpert Control Plane Status")
        print(f"⚡ SYSTEM STATE: {stack_mgr.current_state.value}")
        print(f"🛡️ STRICT LEVEL: {stack_mgr.strict_level.value.upper()}")
        print(f"📁 STACK DEPTH:  {len(stack_mgr.stack)}")
        print(f"🔑 SESSION ID:   {stack_mgr.session_id}")
        print("=" * 65)

        top = stack_mgr.peek()
        if top:
            print(f"🎯 TOP OF STACK (Active Task):")
            print(f"  - Task ID:        {top.task_id}")
            print(f"  - Title:          {top.title}")
            print(f"  - Domain:         {top.domain.value}")
            print(f"  - Assigned Agent: {top.assigned_agent}")
            print(f"  - Status:         {top.status.value}")
            print(f"  - Allowed Files:  {', '.join(top.allowed_files) if top.allowed_files else '(unrestricted)'}")
            print(f"  - Max Blast (L):  {top.max_lines_changed}")
            print(f"  - Artifacts:      {', '.join(top.artifacts) if top.artifacts else '(none)'}")
            print(f"  - Retries:        {top.budget.current_retries} / {top.budget.max_retries}")
            print(f"  - Tokens Used:    {top.budget.used_tokens} / {top.budget.max_tokens}")
        else:
            print("Stack is empty (IDLE / COMPLETED).")

        if stack_mgr.history:
            last_hist = stack_mgr.history[-1]
            receipt = last_hist.get("verification_receipt")
            if receipt:
                print("\n🧾 LATEST VERIFICATION RECEIPT:")
                print(f"  - Gate Type:        {receipt.get('gate_type')}")
                print(f"  - Status:           {receipt.get('status')} (Exit Code: {receipt.get('exit_code')})")
                print(f"  - Verified Files:   {', '.join(receipt.get('verified_files', []))}")
                if receipt.get("streaming_checks"):
                    print(f"  - Streaming Checks: {', '.join(receipt.get('streaming_checks', []))}")

    elif args.command == "build-prompt":
        top = stack_mgr.peek()
        if not top:
            print("❌ Cannot build prompt: Task stack is empty.", file=sys.stderr)
            sys.exit(1)

        builder = PromptOnDemandBuilder()
        prompt = builder.build_prompt(top, target_agent=args.agent, strict_level=stack_mgr.strict_level)

        if args.output:
            out_path = Path(args.output)
            out_path.write_text(prompt, encoding="utf-8")
            print(f"✅ Prompt saved to {out_path} ({len(prompt)} chars).")
        else:
            print(prompt)

    elif args.command == "transition":
        input_data = args.input
        input_path = Path(input_data)
        if input_path.exists() and input_path.is_file():
            input_data = input_path.read_text(encoding="utf-8")

        res = fsm.step_with_raw_output(input_data)
        print("=" * 65)
        print(f"Transition Result: {'✅ SUCCESS' if res.success else '❌ REJECTED / BLOCKED'}")
        print(f"State Change:      {res.previous_state.value} -> {res.new_state.value}")
        print(f"Next Agent:        {res.next_agent or '(none)'}")
        print(f"Message:           {res.message}")
        if res.rejection_feedback:
            print(f"Feedback/Reason:   {res.rejection_feedback}")
        if res.verification_receipt:
            print(f"Receipt Generated: {res.verification_receipt.status} (Gate: {res.verification_receipt.gate_type})")
        print("=" * 65)
        if not res.success:
            sys.exit(1)

    elif args.command == "verify":
        top = stack_mgr.peek()
        if not top:
            print("❌ Stack is empty.", file=sys.stderr)
            sys.exit(1)

        verifier = DeterministicVerifier()
        v_res = verifier.verify_artifacts(top.artifacts)
        print(v_res.summary())
        if not v_res.passed:
            for err in v_res.errors:
                print(f"  - ❌ {err}")
            sys.exit(1)
        for warn in v_res.warnings:
            print(f"  - ⚠️ {warn}")

    elif args.command == "inspect-stack":
        print(json.dumps(stack_mgr.to_dict(), indent=2, ensure_ascii=False))

    elif args.command == "streaming-lint":
        engine = StreamingRulesEngine()
        target_files = args.files

        if not target_files:
            # If no files specified, search git status or search all .kt / .kts files
            cmd = ["git", "status", "--porcelain"]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, check=False)
                git_files = [line[3:].strip() for line in res.stdout.splitlines() if line.strip()]
                target_files = [f for f in git_files if f.endswith((".kt", ".kts", ".java", ".xml"))]
            except Exception:
                target_files = []

        if not target_files:
            # Fallback: scan current directory recursively for kotlin files
            target_files = [str(p) for p in Path(".").rglob("*.kt")] + [str(p) for p in Path(".").rglob("*.kts")]

        print(f"🔍 Scanning {len(target_files)} file(s) for streaming domain anti-patterns...")
        violations = engine.run_all_checks(target_files)

        if not violations:
            print("✅ Streaming Lint Passed: No streaming anti-patterns detected!")
        else:
            errors = [v for v in violations if v.severity == "ERROR"]
            warnings = [v for v in violations if v.severity == "WARNING"]
            print(f"⚠️ Found {len(violations)} issue(s): {len(errors)} error(s), {len(warnings)} warning(s):")
            for v in violations:
                symbol = "❌" if v.severity == "ERROR" else "⚠️"
                loc = f":{v.line_number}" if v.line_number else ""
                print(f"{symbol} [{v.rule_id}] {v.file_path}{loc}")
                print(f"    Message: {v.message}")
                print(f"    Fix:     {v.recommendation}\n")

            if errors:
                sys.exit(1)

    elif args.command == "doctor":
        print("🩺 Running StreamAppExpert Doctor Diagnostics...")
        print(f"Python:       {sys.version.split()[0]} ({sys.executable})")
        print(f"Working Dir:  {Path('.').resolve()}")

        # Check git
        try:
            git_ver = subprocess.run(["git", "--version"], capture_output=True, text=True, check=False)
            print(f"Git:          {git_ver.stdout.strip()}")
        except Exception:
            print("Git:          ⚠️ Git CLI not found or not in PATH")

        # Check stack.json
        stack_p = Path(args.stack_file)
        if stack_p.exists():
            print(f"Stack File:   ✅ Found ({stack_p.resolve()}, {stack_p.stat().st_size} bytes)")
        else:
            print(f"Stack File:   ℹ️ No active {args.stack_file} (Run 'init' to create one)")

        # Check skills directory
        skills_p = Path(".agents/skills")
        if skills_p.exists():
            count = len(list(skills_p.iterdir()))
            print(f"Skills Store: ✅ Found {count} specialized skills in {skills_p}")
        else:
            print(f"Skills Store: ℹ️ .agents/skills directory not found locally")


if __name__ == "__main__":
    main()
