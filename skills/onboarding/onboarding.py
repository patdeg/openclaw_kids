#!/usr/bin/env python3
"""Onboarding skill — first-run questionnaire that builds PROFILE.md."""

import argparse
import json
import os
import sys

WORKSPACE = os.path.expanduser("~/workspace")
PROFILE_PATH = os.path.join(WORKSPACE, "PROFILE.md")

PROFILE_FIELDS = [
    ("nickname", "Nickname"),
    ("grade", "Grade"),
    ("favorite_subjects", "Favorite Subjects"),
    ("least_favorite", "Least Favorite"),
    ("interests", "Interests"),
    ("games", "Games"),
    ("minecraft_username", "Minecraft Username"),
    ("sports", "Sports"),
    ("music", "Music"),
    ("pets", "Pets"),
    ("wants_to_improve", "Wants to Improve"),
    ("study_style", "Study Style"),
    ("homework_time", "Homework Time"),
    ("needs_help_with", "Needs Help With"),
]


def cmd_check(_args):
    """Check if profile exists."""
    exists = os.path.isfile(PROFILE_PATH)
    print(json.dumps({
        "exists": exists,
        "path": PROFILE_PATH,
        "message": "Profile exists." if exists else (
            "No profile found. Please start the onboarding questionnaire "
            "by asking the user the questions listed in SKILL.md, then call "
            "'onboarding save --json' with their answers."
        ),
    }))


def cmd_save(args):
    """Save profile answers to PROFILE.md."""
    try:
        data = json.loads(args.json)
    except (json.JSONDecodeError, TypeError) as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}))
        sys.exit(1)

    name = data.get("nickname", data.get("name", "User"))

    os.makedirs(WORKSPACE, exist_ok=True)

    lines = [f"# Profile: {name}", ""]
    for key, label in PROFILE_FIELDS:
        value = data.get(key, "")
        if value:
            lines.append(f"- **{label}**: {value}")

    # Allow extra fields not in the standard list
    standard_keys = {k for k, _ in PROFILE_FIELDS}
    standard_keys.add("name")
    for key, value in data.items():
        if key not in standard_keys and value:
            label = key.replace("_", " ").title()
            lines.append(f"- **{label}**: {value}")

    lines.append("")

    with open(PROFILE_PATH, "w") as f:
        f.write("\n".join(lines))

    print(json.dumps({
        "success": True,
        "path": PROFILE_PATH,
        "message": f"Profile saved for {name}.",
    }))


def cmd_show(_args):
    """Display the current profile."""
    if not os.path.isfile(PROFILE_PATH):
        print(json.dumps({
            "error": "No profile found. Run onboarding first.",
        }))
        sys.exit(1)

    with open(PROFILE_PATH, "r") as f:
        content = f.read()

    print(json.dumps({
        "path": PROFILE_PATH,
        "content": content,
    }))


def main():
    parser = argparse.ArgumentParser(description="Onboarding skill")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("check", help="Check if profile exists")

    save_parser = subparsers.add_parser("save", help="Save profile")
    save_parser.add_argument("--json", required=True, help="JSON answers")

    subparsers.add_parser("show", help="Show current profile")

    args = parser.parse_args()

    if args.command == "check":
        cmd_check(args)
    elif args.command == "save":
        cmd_save(args)
    elif args.command == "show":
        cmd_show(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
