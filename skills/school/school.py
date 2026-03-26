#!/usr/bin/env python3
"""
School (Canvas LMS) — Student grades, assignments, and submissions.

Monitor school data for one or more students across configured courses.
Auto-discovers students and courses on first run from the Canvas API key.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests


# ============================================================================
# Configuration
# ============================================================================

DEFAULT_BASE_URL = os.environ.get("CANVAS_BASE_URL", "https://myschool.instructure.com/api/v1")
CONTEXT_FILENAME = "SCHOOL_CONTEXT.md"

# Workspace path: ~/.openclaw/workspace/ (writable volume in container)
WORKSPACE_DIR = Path(os.environ.get(
    "CANVAS_WORKSPACE",
    os.path.expanduser("~/.openclaw/workspace"),
))


def get_api_config():
    """Load API key and base URL from env vars."""
    api_key = os.environ.get("CANVAS_API_KEY")
    if not api_key:
        print(json.dumps({"error": "CANVAS_API_KEY must be set"}))
        sys.exit(1)

    base_url = os.environ.get("CANVAS_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    return {"api_key": api_key, "base_url": base_url}


def get_context_path():
    """Return path to SCHOOL_CONTEXT.md in the workspace."""
    return WORKSPACE_DIR / CONTEXT_FILENAME


def load_context():
    """Load student/course IDs from SCHOOL_CONTEXT.md. Returns dict with students and courses lists."""
    path = get_context_path()
    if not path.exists():
        return {"students": [], "courses": []}

    text = path.read_text()
    students = []
    courses = []

    # Parse student table: | id | name | ... |
    in_students = False
    in_courses = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Students"):
            in_students = True
            in_courses = False
            continue
        if stripped.startswith("## Courses"):
            in_courses = True
            in_students = False
            continue
        if stripped.startswith("## "):
            in_students = False
            in_courses = False
            continue

        # Parse table rows (skip header and separator)
        if not stripped.startswith("|") or stripped.startswith("| ---") or stripped.startswith("|---"):
            continue

        cells = [c.strip() for c in stripped.split("|")[1:-1]]
        if not cells or not cells[0].isdigit():
            continue

        if in_students and len(cells) >= 2:
            students.append({"id": cells[0], "name": cells[1]})
        elif in_courses and len(cells) >= 3:
            courses.append({"id": cells[0], "name": cells[1], "student_id": cells[2] if len(cells) > 2 else ""})

    return {"students": students, "courses": courses}


def get_config():
    """Load full config: API creds + discovered students/courses from context file."""
    api = get_api_config()
    ctx = load_context()

    return {
        "api_key": api["api_key"],
        "base_url": api["base_url"],
        "students": [s["id"] for s in ctx["students"]],
        "courses": [c["id"] for c in ctx["courses"]],
        "student_names": {s["id"]: s["name"] for s in ctx["students"]},
        "course_names": {c["id"]: c["name"] for c in ctx["courses"]},
    }


def get_headers(config):
    """Get API headers with Bearer token."""
    return {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }


# ============================================================================
# Helpers
# ============================================================================

def paginated_get(url, headers, params=None):
    """Follow Canvas Link header pagination, returning all results."""
    results = []
    params = params or {}

    while url:
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
        except requests.exceptions.RequestException as e:
            return {"error": f"Network error: {e}"}

        if resp.status_code != 200:
            try:
                err_body = resp.json()
            except (ValueError, requests.exceptions.JSONDecodeError):
                err_body = resp.text[:200] or resp.status_code
            return {"error": err_body}

        try:
            data = resp.json()
        except (ValueError, requests.exceptions.JSONDecodeError):
            return {"error": f"Invalid JSON response (HTTP {resp.status_code})"}

        if isinstance(data, list):
            results.extend(data)
        else:
            return data  # single object, no pagination

        # Follow next page
        url = None
        params = {}  # params are in the Link URL after first request
        link_header = resp.headers.get("Link", "")
        for part in link_header.split(","):
            if 'rel="next"' in part:
                match = re.search(r"<([^>]+)>", part)
                if match:
                    url = match.group(1)

    return results


def parse_date(value):
    """Parse ISO date string or relative shorthand (7d, 2w, 1m) into ISO format."""
    if not value:
        return None

    # Relative shorthand: 7d, 2w, 1m
    match = re.match(r"^(\d+)([dwm])$", value)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        now = datetime.utcnow()
        if unit == "d":
            dt = now - timedelta(days=amount)
        elif unit == "w":
            dt = now - timedelta(weeks=amount)
        elif unit == "m":
            dt = now - timedelta(days=amount * 30)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Already ISO or date string — return as-is
    return value


def resolve_courses(config, args):
    """Return list of course IDs from --course flag or all configured."""
    if hasattr(args, "course") and args.course:
        return [args.course]
    return config["courses"]


def resolve_students(config, args):
    """Return list of student IDs from --student flag or all configured."""
    if hasattr(args, "student") and args.student:
        return [args.student]
    return config["students"]


def run_setup():
    """Discover observed students and their courses, write SCHOOL_CONTEXT.md.

    Returns the result dict on success, or None on failure.
    Called automatically when context file is missing/empty.
    """
    api = get_api_config()
    headers = get_headers(api)
    base = api["base_url"]

    # Step 1: Who am I?
    me = paginated_get(f"{base}/users/self/profile", headers)
    if isinstance(me, dict) and "error" in me:
        return None

    my_name = me.get("name", "Unknown")
    my_id = me.get("id", "?")
    print(f"[school] Auto-setup: authenticated as {my_name} (ID: {my_id})", file=sys.stderr)

    # Step 2: Discover observed students (parent/observer account)
    observees = paginated_get(f"{base}/users/self/observees", headers)
    students = []
    if isinstance(observees, list) and observees:
        for o in observees:
            students.append({
                "id": str(o.get("id")),
                "name": o.get("name", "Unknown"),
                "short_name": o.get("short_name", ""),
            })
        print(f"[school] Found {len(students)} observed student(s)", file=sys.stderr)
    else:
        # Not an observer — the token owner IS the student
        students.append({
            "id": str(my_id),
            "name": my_name,
            "short_name": me.get("short_name", ""),
        })
        print("[school] No observees found — using self as student", file=sys.stderr)

    # Step 3: Discover active courses for each student
    all_courses = []
    seen_course_ids = set()
    for student in students:
        sid = student["id"]
        courses = paginated_get(
            f"{base}/users/{sid}/courses",
            headers,
            {"enrollment_state": "active", "include[]": ["term"], "per_page": 50},
        )
        if isinstance(courses, dict) and "error" in courses:
            # Fallback: try listing courses visible to the authenticated user
            courses = paginated_get(
                f"{base}/courses",
                headers,
                {"enrollment_state": "active", "include[]": ["term"], "per_page": 50},
            )
            if isinstance(courses, dict) and "error" in courses:
                print(f"[school]   Could not list courses for student {sid}", file=sys.stderr)
                continue

        for c in courses:
            cid = str(c.get("id"))
            if cid not in seen_course_ids:
                seen_course_ids.add(cid)
                term = c.get("term", {})
                all_courses.append({
                    "id": cid,
                    "name": c.get("name", "Unknown"),
                    "course_code": c.get("course_code", ""),
                    "term": term.get("name", "") if term else "",
                    "student_id": sid,
                    "student_name": student["name"],
                })
        print(f"[school]   {student['name']}: {len(courses)} active course(s)", file=sys.stderr)

    # Step 4: Write SCHOOL_CONTEXT.md
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# School (Canvas LMS) Context",
        f"",
        f"Auto-generated by `school.py setup` on {now}.",
        f"Re-run setup to refresh (new semester, new courses).",
        f"",
        f"**Account:** {my_name} (ID: {my_id})",
        f"**Base URL:** {api['base_url']}",
        f"",
        f"## Students",
        f"",
        f"| ID | Name | Short Name |",
        f"|---|---|---|",
    ]
    for s in students:
        lines.append(f"| {s['id']} | {s['name']} | {s['short_name']} |")

    lines += [
        f"",
        f"## Courses",
        f"",
        f"| ID | Name | Student ID | Term | Code |",
        f"|---|---|---|---|---|",
    ]
    for c in all_courses:
        lines.append(f"| {c['id']} | {c['name']} | {c['student_id']} | {c['term']} | {c['course_code']} |")

    lines += [
        f"",
        f"## Notes",
        f"",
        f"- Dad's instance sees all students listed above.",
        f"- Each kid's instance should only have their own student ID.",
        f"- Run `school.py setup` at the start of each semester to refresh.",
    ]

    context_path = get_context_path()
    context_path.parent.mkdir(parents=True, exist_ok=True)
    context_path.write_text("\n".join(lines) + "\n")

    return {
        "status": "setup_complete",
        "context_file": str(context_path),
        "account": {"id": my_id, "name": my_name},
        "students": students,
        "courses": [{"id": c["id"], "name": c["name"], "student": c["student_name"]} for c in all_courses],
    }


def ensure_context():
    """Load config, auto-running setup if context file is missing or empty.

    Every subcommand calls this instead of get_config() directly.
    """
    config = get_config()

    # If we have students and courses, we're good
    if config["students"] and config["courses"]:
        return config

    # Context missing or empty — auto-run setup
    print("[school] Context file missing or empty, running auto-setup...", file=sys.stderr)
    result = run_setup()
    if result is None:
        print(json.dumps({"error": "Auto-setup failed. Check that CANVAS_API_KEY is valid."}))
        sys.exit(1)

    # Reload config from the freshly written context file
    return get_config()


# ============================================================================
# Setup — auto-discover students and courses
# ============================================================================

def cmd_setup(args):
    """Discover observed students and their courses, write SCHOOL_CONTEXT.md."""
    result = run_setup()
    if result is None:
        print(json.dumps({"error": "Failed to get self profile. Check CANVAS_API_KEY."}))
        return
    print(json.dumps(result, indent=2))


# ============================================================================
# Subcommands
# ============================================================================

def cmd_courses(args):
    """List discovered courses with live details from API."""
    config = ensure_context()
    headers = get_headers(config)
    course_ids = resolve_courses(config, args)

    courses = []
    for cid in course_ids:
        data = paginated_get(f"{config['base_url']}/courses/{cid}", headers)
        if isinstance(data, dict) and "error" in data:
            courses.append({"course_id": cid, "error": data["error"]})
            continue
        courses.append({
            "id": data.get("id"),
            "name": data.get("name"),
            "course_code": data.get("course_code"),
            "term": data.get("term", {}).get("name") if data.get("term") else None,
            "start_at": data.get("start_at"),
            "end_at": data.get("end_at"),
            "workflow_state": data.get("workflow_state"),
        })

    print(json.dumps({"courses": courses, "count": len(courses)}, indent=2))


def cmd_profile(args):
    """Get student profile info."""
    config = ensure_context()
    headers = get_headers(config)
    student_ids = resolve_students(config, args)

    profiles = []
    for sid in student_ids:
        data = paginated_get(f"{config['base_url']}/users/{sid}/profile", headers)
        if isinstance(data, dict) and "error" in data:
            profiles.append({"student_id": sid, "error": data["error"]})
            continue
        profiles.append({
            "id": data.get("id"),
            "name": data.get("name"),
            "short_name": data.get("short_name"),
            "login_id": data.get("login_id"),
            "email": data.get("primary_email"),
            "avatar_url": data.get("avatar_url"),
        })

    print(json.dumps({"profiles": profiles, "count": len(profiles)}, indent=2))


def cmd_grades(args):
    """Get current scores and letter grades per course."""
    config = ensure_context()
    headers = get_headers(config)
    course_ids = resolve_courses(config, args)
    student_ids = resolve_students(config, args)

    grades = []
    for cid in course_ids:
        for sid in (student_ids or [None]):
            params = {"type[]": "StudentEnrollment", "per_page": 50}
            if sid:
                params["user_id"] = sid
            data = paginated_get(f"{config['base_url']}/courses/{cid}/enrollments", headers, params)
            if isinstance(data, dict) and "error" in data:
                grades.append({"course_id": cid, "error": data["error"]})
                continue

            for enrollment in data:
                uid = str(enrollment.get("user_id", ""))
                if student_ids and uid not in student_ids:
                    continue
                g = enrollment.get("grades", {})
                grades.append({
                    "course_id": cid,
                    "course_name": config["course_names"].get(cid, cid),
                    "student_id": uid,
                    "student_name": enrollment.get("user", {}).get("name")
                        or config["student_names"].get(uid, uid),
                    "current_score": g.get("current_score"),
                    "current_grade": g.get("current_grade"),
                    "final_score": g.get("final_score"),
                    "final_grade": g.get("final_grade"),
                    "enrollment_state": enrollment.get("enrollment_state"),
                })

    print(json.dumps({"grades": grades, "count": len(grades)}, indent=2))


def cmd_assignments(args):
    """List assignments, optionally filtered by bucket."""
    config = ensure_context()
    headers = get_headers(config)
    course_ids = resolve_courses(config, args)

    all_assignments = []
    for cid in course_ids:
        params = {"per_page": 50, "order_by": "due_at"}
        if hasattr(args, "bucket") and args.bucket:
            params["bucket"] = args.bucket
        data = paginated_get(f"{config['base_url']}/courses/{cid}/assignments", headers, params)
        if isinstance(data, dict) and "error" in data:
            all_assignments.append({"course_id": cid, "error": data["error"]})
            continue

        for a in data:
            all_assignments.append({
                "id": a.get("id"),
                "course_id": cid,
                "course_name": config["course_names"].get(cid, cid),
                "name": a.get("name"),
                "due_at": a.get("due_at"),
                "points_possible": a.get("points_possible"),
                "submission_types": a.get("submission_types"),
                "workflow_state": a.get("workflow_state"),
                "has_submitted_submissions": a.get("has_submitted_submissions"),
            })

    print(json.dumps({"assignments": all_assignments, "count": len(all_assignments)}, indent=2))


def cmd_submissions(args):
    """Get graded/submitted work for students."""
    config = ensure_context()
    headers = get_headers(config)
    course_ids = resolve_courses(config, args)
    student_ids = resolve_students(config, args)

    since = parse_date(args.since) if hasattr(args, "since") and args.since else None

    all_submissions = []
    for cid in course_ids:
        params = {
            "per_page": 50,
            "include[]": ["assignment", "user"],
            "student_ids[]": student_ids if student_ids else ["all"],
        }
        if since:
            params["submitted_since"] = since
        if hasattr(args, "state") and args.state:
            params["workflow_state"] = args.state

        data = paginated_get(
            f"{config['base_url']}/courses/{cid}/students/submissions",
            headers, params,
        )
        if isinstance(data, dict) and "error" in data:
            all_submissions.append({"course_id": cid, "error": data["error"]})
            continue

        for s in data:
            assignment = s.get("assignment", {})
            all_submissions.append({
                "id": s.get("id"),
                "course_id": cid,
                "course_name": config["course_names"].get(cid, cid),
                "assignment_id": s.get("assignment_id"),
                "assignment_name": assignment.get("name") if assignment else None,
                "student_id": s.get("user_id"),
                "student_name": s.get("user", {}).get("name") if s.get("user") else None,
                "score": s.get("score"),
                "grade": s.get("grade"),
                "points_possible": assignment.get("points_possible") if assignment else None,
                "submitted_at": s.get("submitted_at"),
                "graded_at": s.get("graded_at"),
                "workflow_state": s.get("workflow_state"),
                "late": s.get("late"),
                "missing": s.get("missing"),
            })

    print(json.dumps({"submissions": all_submissions, "count": len(all_submissions)}, indent=2))


def cmd_missing(args):
    """Get missing/overdue submissions for students."""
    config = ensure_context()
    headers = get_headers(config)
    student_ids = resolve_students(config, args)

    all_missing = []
    for sid in student_ids:
        params = {"per_page": 50, "include[]": ["course"]}
        course_ids = resolve_courses(config, args)
        if course_ids:
            params["course_ids[]"] = course_ids

        data = paginated_get(
            f"{config['base_url']}/users/{sid}/missing_submissions",
            headers, params,
        )
        if isinstance(data, dict) and "error" in data:
            all_missing.append({"student_id": sid, "error": data["error"]})
            continue

        for a in data:
            all_missing.append({
                "student_id": sid,
                "student_name": config["student_names"].get(sid, sid),
                "assignment_id": a.get("id"),
                "name": a.get("name"),
                "course_id": a.get("course_id"),
                "due_at": a.get("due_at"),
                "points_possible": a.get("points_possible"),
                "submission_types": a.get("submission_types"),
            })

    print(json.dumps({"missing": all_missing, "count": len(all_missing)}, indent=2))


def cmd_upcoming(args):
    """Get upcoming assignments (due soon)."""
    config = ensure_context()
    headers = get_headers(config)
    course_ids = resolve_courses(config, args)

    all_upcoming = []
    for cid in course_ids:
        params = {"per_page": 50, "bucket": "upcoming", "order_by": "due_at"}
        data = paginated_get(f"{config['base_url']}/courses/{cid}/assignments", headers, params)
        if isinstance(data, dict) and "error" in data:
            all_upcoming.append({"course_id": cid, "error": data["error"]})
            continue

        for a in data:
            all_upcoming.append({
                "id": a.get("id"),
                "course_id": cid,
                "course_name": config["course_names"].get(cid, cid),
                "name": a.get("name"),
                "due_at": a.get("due_at"),
                "points_possible": a.get("points_possible"),
                "submission_types": a.get("submission_types"),
            })

    print(json.dumps({"upcoming": all_upcoming, "count": len(all_upcoming)}, indent=2))


def cmd_announcements(args):
    """Get course announcements."""
    config = ensure_context()
    headers = get_headers(config)
    course_ids = resolve_courses(config, args)

    since = parse_date(args.since) if hasattr(args, "since") and args.since else None

    params = {
        "context_codes[]": [f"course_{cid}" for cid in course_ids],
        "per_page": 20,
    }
    if since:
        params["start_date"] = since

    data = paginated_get(f"{config['base_url']}/announcements", headers, params)
    if isinstance(data, dict) and "error" in data:
        print(json.dumps(data))
        return

    announcements = []
    for a in data:
        announcements.append({
            "id": a.get("id"),
            "title": a.get("title"),
            "message": a.get("message"),
            "posted_at": a.get("posted_at"),
            "context_code": a.get("context_code"),
            "author": a.get("author", {}).get("display_name") if a.get("author") else None,
        })

    print(json.dumps({"announcements": announcements, "count": len(announcements)}, indent=2))


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="School (Canvas LMS) CLI — Student grades, assignments, and submissions"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # setup (auto-discover)
    subparsers.add_parser("setup", help="Discover students and courses, write SCHOOL_CONTEXT.md")

    # courses
    courses_parser = subparsers.add_parser("courses", help="List courses with details")
    courses_parser.add_argument("--course", help="Single course ID override")

    # profile
    profile_parser = subparsers.add_parser("profile", help="Get student profile")
    profile_parser.add_argument("--student", help="Single student ID override")

    # grades
    grades_parser = subparsers.add_parser("grades", help="Current scores and letter grades")
    grades_parser.add_argument("--course", help="Single course ID")
    grades_parser.add_argument("--student", help="Single student ID")

    # assignments
    assignments_parser = subparsers.add_parser("assignments", help="List assignments")
    assignments_parser.add_argument("--course", help="Single course ID")
    assignments_parser.add_argument("--bucket", choices=["past", "overdue", "undated", "ungraded", "unsubmitted", "upcoming", "future"],
                                    help="Filter by bucket")

    # submissions
    submissions_parser = subparsers.add_parser("submissions", help="Graded/submitted work")
    submissions_parser.add_argument("--course", help="Single course ID")
    submissions_parser.add_argument("--student", help="Single student ID")
    submissions_parser.add_argument("--since", help="Date filter: ISO date or shorthand (7d, 2w, 1m)")
    submissions_parser.add_argument("--state", help="Workflow state filter (submitted, graded, pending_review)")

    # missing
    missing_parser = subparsers.add_parser("missing", help="Missing/overdue submissions")
    missing_parser.add_argument("--student", help="Single student ID")
    missing_parser.add_argument("--course", help="Single course ID")

    # upcoming
    upcoming_parser = subparsers.add_parser("upcoming", help="Assignments due soon")
    upcoming_parser.add_argument("--course", help="Single course ID")

    # announcements
    announcements_parser = subparsers.add_parser("announcements", help="Course announcements")
    announcements_parser.add_argument("--course", help="Single course ID")
    announcements_parser.add_argument("--since", help="Date filter: ISO date or shorthand (7d, 2w, 1m)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        "setup": cmd_setup,
        "courses": cmd_courses,
        "profile": cmd_profile,
        "grades": cmd_grades,
        "assignments": cmd_assignments,
        "submissions": cmd_submissions,
        "missing": cmd_missing,
        "upcoming": cmd_upcoming,
        "announcements": cmd_announcements,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
