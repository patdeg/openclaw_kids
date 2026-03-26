#!/usr/bin/env python3
"""Canvas Notifications — grade change and missing work alerts."""

import argparse
import json
import os
import sys
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError

WORKSPACE = os.path.expanduser("~/workspace")
STATE_FILE = os.path.join(WORKSPACE, "canvas_last_check.json")

API_KEY = os.environ.get("CANVAS_API_KEY", "")
BASE_URL = os.environ.get("CANVAS_BASE_URL", "https://myschool.instructure.com/api/v1")


def canvas_get(endpoint, params=None):
    """Make a GET request to the Canvas API."""
    if not API_KEY:
        return {"error": "CANVAS_API_KEY not set"}

    url = f"{BASE_URL}{endpoint}"
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query}"

    req = Request(url)
    req.add_header("Authorization", f"Bearer {API_KEY}")
    req.add_header("Accept", "application/json")

    try:
        with urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except URLError as e:
        return {"error": str(e)}


def load_state():
    """Load last check state."""
    if os.path.isfile(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_check": None, "known_grades": {}}


def save_state(state):
    """Save state to disk."""
    os.makedirs(WORKSPACE, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def cmd_check(_args):
    """Check for new grades and missing work."""
    if not API_KEY:
        print(json.dumps({"error": "CANVAS_API_KEY must be set"}))
        sys.exit(1)

    state = load_state()

    # Get enrolled courses
    courses = canvas_get("/courses", {"enrollment_state": "active", "per_page": "50"})
    if isinstance(courses, dict) and "error" in courses:
        print(json.dumps(courses))
        sys.exit(1)

    alerts = []
    new_grades = {}

    for course in courses:
        if not isinstance(course, dict):
            continue
        course_id = course.get("id")
        course_name = course.get("name", "Unknown")

        # Check for missing assignments
        assignments = canvas_get(
            f"/courses/{course_id}/assignments",
            {"per_page": "50", "order_by": "due_at", "bucket": "unsubmitted"}
        )
        if isinstance(assignments, list):
            for a in assignments:
                if a.get("due_at") and not a.get("has_submitted_submissions"):
                    alerts.append({
                        "type": "missing",
                        "course": course_name,
                        "assignment": a.get("name"),
                        "due_at": a.get("due_at"),
                        "points_possible": a.get("points_possible"),
                    })

        # Check for new/changed grades
        enrollments = canvas_get(
            f"/courses/{course_id}/enrollments",
            {"type[]": "StudentEnrollment", "per_page": "10"}
        )
        if isinstance(enrollments, list):
            for e in enrollments:
                grades = e.get("grades", {})
                current = grades.get("current_score")
                prev = state.get("known_grades", {}).get(str(course_id))

                if current is not None:
                    new_grades[str(course_id)] = current
                    if prev is not None and current != prev:
                        change = current - prev
                        alerts.append({
                            "type": "grade_change",
                            "course": course_name,
                            "previous": prev,
                            "current": current,
                            "change": round(change, 1),
                            "direction": "up" if change > 0 else "down",
                        })

    # Update state
    state["last_check"] = datetime.now().isoformat()
    state["known_grades"].update(new_grades)
    save_state(state)

    print(json.dumps({
        "checked_at": state["last_check"],
        "courses_checked": len(courses) if isinstance(courses, list) else 0,
        "alerts": alerts,
        "alert_count": len(alerts),
        "missing_count": sum(1 for a in alerts if a["type"] == "missing"),
        "grade_changes": sum(1 for a in alerts if a["type"] == "grade_change"),
    }))


def cmd_digest(args):
    """Generate a grade summary."""
    if not API_KEY:
        print(json.dumps({"error": "CANVAS_API_KEY must be set"}))
        sys.exit(1)

    period = args.period or "daily"

    courses = canvas_get("/courses", {"enrollment_state": "active", "per_page": "50"})
    if isinstance(courses, dict) and "error" in courses:
        print(json.dumps(courses))
        sys.exit(1)

    summary = []
    for course in courses:
        if not isinstance(course, dict):
            continue
        course_id = course.get("id")
        course_name = course.get("name", "Unknown")

        enrollments = canvas_get(
            f"/courses/{course_id}/enrollments",
            {"type[]": "StudentEnrollment", "per_page": "10"}
        )
        if isinstance(enrollments, list):
            for e in enrollments:
                grades = e.get("grades", {})
                summary.append({
                    "course": course_name,
                    "current_score": grades.get("current_score"),
                    "current_grade": grades.get("current_grade"),
                })

    print(json.dumps({
        "period": period,
        "generated_at": datetime.now().isoformat(),
        "grades": summary,
    }))


def main():
    parser = argparse.ArgumentParser(description="Canvas Notifications")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("check", help="Check for new grades and missing work")

    digest_p = subparsers.add_parser("digest", help="Grade summary")
    digest_p.add_argument("--period", choices=["daily", "weekly"], default="daily")

    args = parser.parse_args()

    if args.command == "check":
        cmd_check(args)
    elif args.command == "digest":
        cmd_digest(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
