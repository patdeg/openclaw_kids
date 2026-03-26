#!/usr/bin/env python3
"""Homework Helper skill — study productivity tools."""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta

WORKSPACE = os.path.expanduser("~/workspace")
POMODORO_FILE = os.path.join(WORKSPACE, "pomodoro.json")
POMODORO_DURATION = 25 * 60  # 25 minutes in seconds
BREAK_DURATION = 5 * 60  # 5 minutes in seconds


def cmd_pomodoro(args):
    """Manage pomodoro study timer."""
    action = args.action

    if action == "start":
        os.makedirs(WORKSPACE, exist_ok=True)
        state = {
            "started_at": datetime.now().isoformat(),
            "ends_at": (datetime.now() + timedelta(seconds=POMODORO_DURATION)).isoformat(),
            "duration_min": 25,
            "break_min": 5,
            "active": True,
        }
        with open(POMODORO_FILE, "w") as f:
            json.dump(state, f)
        print(json.dumps({
            "success": True,
            "message": "Pomodoro started! 25 minutes of focused study. No distractions. You got this.",
            "ends_at": state["ends_at"],
        }))

    elif action == "stop":
        if os.path.isfile(POMODORO_FILE):
            os.remove(POMODORO_FILE)
        print(json.dumps({
            "success": True,
            "message": "Pomodoro stopped. Take a break if you need one.",
        }))

    elif action == "status":
        if not os.path.isfile(POMODORO_FILE):
            print(json.dumps({"active": False, "message": "No active pomodoro session."}))
            return

        with open(POMODORO_FILE) as f:
            state = json.load(f)

        ends_at = datetime.fromisoformat(state["ends_at"])
        now = datetime.now()

        if now >= ends_at:
            os.remove(POMODORO_FILE)
            print(json.dumps({
                "active": False,
                "completed": True,
                "message": "Pomodoro complete! Take a 5-minute break. Stand up, stretch, get water.",
            }))
        else:
            remaining = (ends_at - now).total_seconds()
            mins = int(remaining // 60)
            secs = int(remaining % 60)
            print(json.dumps({
                "active": True,
                "remaining_minutes": mins,
                "remaining_seconds": secs,
                "message": f"{mins}m {secs}s remaining. Stay focused!",
            }))
    else:
        print(json.dumps({"error": f"Unknown action '{action}'. Use: start, stop, status"}))
        sys.exit(1)


def cmd_flashcards(args):
    """Generate flashcard instructions for the AI."""
    topic = " ".join(args.topic)
    count = args.count or 10
    print(json.dumps({
        "action": "generate_flashcards",
        "topic": topic,
        "count": count,
        "instructions": (
            f"Generate {count} study flashcards on the topic: '{topic}'. "
            f"Format each as:\n"
            f"**Q:** [question]\n"
            f"**A:** [answer]\n\n"
            f"Make them progressively harder. Mix recall, application, and "
            f"analysis questions. Adapt to the student's grade from PROFILE.md."
        ),
    }))


def cmd_outline(args):
    """Generate essay outline instructions for the AI."""
    topic = " ".join(args.topic)
    print(json.dumps({
        "action": "generate_outline",
        "topic": topic,
        "instructions": (
            f"Generate an essay outline for the topic: '{topic}'. Include:\n"
            f"1. **Thesis statement** (clear, arguable claim)\n"
            f"2. **Introduction** (hook, context, thesis)\n"
            f"3. **Body paragraphs** (3-4, each with topic sentence, evidence, analysis)\n"
            f"4. **Conclusion** (restate thesis, broader significance)\n"
            f"5. **Suggested sources** to research\n\n"
            f"Adapt complexity to the student's grade from PROFILE.md."
        ),
    }))


def cmd_math(args):
    """Generate step-by-step math solution instructions for the AI."""
    problem = " ".join(args.problem)
    print(json.dumps({
        "action": "solve_math",
        "problem": problem,
        "instructions": (
            f"Solve this math problem step-by-step: '{problem}'\n\n"
            f"IMPORTANT: Show ALL work. Never just give the answer. The goal "
            f"is for the student to LEARN, not just get the answer.\n\n"
            f"Format:\n"
            f"1. State what we're solving for\n"
            f"2. Show each step with explanation\n"
            f"3. Final answer clearly marked\n"
            f"4. Check: verify the answer makes sense\n\n"
            f"If the problem is from CPM (Core Connections), reference that "
            f"curriculum's approach when possible."
        ),
    }))


def cmd_cite(args):
    """Generate citation instructions for the AI."""
    url = args.url
    fmt = args.format or "mla"
    print(json.dumps({
        "action": "generate_citation",
        "url": url,
        "format": fmt.upper(),
        "instructions": (
            f"Generate a {fmt.upper()} citation for: {url}\n\n"
            f"Use the tavily skill to extract the page title, author, "
            f"publication date, and site name. Then format as:\n\n"
            f"MLA: Author. \"Title.\" Site Name, Date, URL.\n"
            f"APA: Author. (Year, Month Day). Title. Site Name. URL\n\n"
            f"If information is missing, note it with [n.d.] or [n.p.]."
        ),
    }))


def main():
    parser = argparse.ArgumentParser(description="Homework Helper")
    subparsers = parser.add_subparsers(dest="command")

    pomo_p = subparsers.add_parser("pomodoro", help="Study timer")
    pomo_p.add_argument("action", help="start, stop, or status")

    flash_p = subparsers.add_parser("flashcards", help="Generate flashcards")
    flash_p.add_argument("topic", nargs="+", help="Topic")
    flash_p.add_argument("--count", type=int, default=10, help="Number of cards")

    outline_p = subparsers.add_parser("outline", help="Essay outline")
    outline_p.add_argument("topic", nargs="+", help="Topic")

    math_p = subparsers.add_parser("math", help="Step-by-step math")
    math_p.add_argument("problem", nargs="+", help="Math problem")

    cite_p = subparsers.add_parser("cite", help="Generate citation")
    cite_p.add_argument("url", help="URL to cite")
    cite_p.add_argument("--format", choices=["mla", "apa"], default="mla", help="Citation format")

    args = parser.parse_args()

    commands = {
        "pomodoro": cmd_pomodoro,
        "flashcards": cmd_flashcards,
        "outline": cmd_outline,
        "math": cmd_math,
        "cite": cmd_cite,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
