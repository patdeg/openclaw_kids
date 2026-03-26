# School — Canvas LMS Monitoring

Monitor student grades, assignments, submissions, and announcements from Canvas LMS.

> **Multi-instance:** Dad's instance sees all observed students. Each kid's instance sees only themselves (their token has no observees).

## Setup

Only `CANVAS_API_KEY` is required. **Setup is automatic** — if any command is run and the context file is missing or empty, the skill auto-discovers students and courses before proceeding. No manual setup step needed.

You can also run setup explicitly:

```bash
python3 school.py setup
```

This queries the Canvas API to find:
1. The authenticated user (parent/observer or student)
2. Observed students (for parent accounts) or self (for student accounts)
3. Active courses for each student

Results are written to `SCHOOL_CONTEXT.md` in the workspace. Re-run at the start of each semester to refresh, or just delete the file and the next command will re-discover automatically.

## Credentials

| Variable | Required | Description |
|----------|----------|-------------|
| `CANVAS_API_KEY` | Yes | Canvas Bearer token (Canvas: Account > Settings > New Access Token) |
| `CANVAS_BASE_URL` | No | API base URL (default: `https://YOUR_SCHOOL.instructure.com/api/v1`) |

No course IDs or student IDs needed — `setup` discovers them automatically.

## CLI Commands

```bash
# First-time setup (or run any command — setup happens automatically)
python3 school.py setup

# Course info
python3 school.py courses
python3 school.py courses --course 184467

# Student profile
python3 school.py profile
python3 school.py profile --student 136421

# Current grades (primary use case)
python3 school.py grades
python3 school.py grades --course 184467 --student 136421

# Assignments
python3 school.py assignments
python3 school.py assignments --course 184467 --bucket upcoming
python3 school.py assignments --bucket overdue

# Submissions (graded work)
python3 school.py submissions --since 7d
python3 school.py submissions --course 184467 --student 136421 --since 2w
python3 school.py submissions --state graded

# Missing/overdue work
python3 school.py missing
python3 school.py missing --student 136421

# Upcoming assignments (what's due soon)
python3 school.py upcoming
python3 school.py upcoming --course 184467

# Announcements
python3 school.py announcements
python3 school.py announcements --since 7d
```

## Date Syntax

The `--since` flag accepts:

| Format | Meaning | Example |
|--------|---------|---------|
| `7d` | 7 days ago | `--since 7d` |
| `2w` | 2 weeks ago | `--since 2w` |
| `1m` | 1 month ago | `--since 1m` |
| ISO date | Specific date | `--since 2026-02-01` |

## Assignment Buckets

The `--bucket` flag for `assignments` accepts:

| Bucket | Meaning |
|--------|---------|
| `past` | Past due date |
| `overdue` | Past due, not submitted |
| `undated` | No due date set |
| `ungraded` | Submitted but not graded |
| `unsubmitted` | Not yet submitted |
| `upcoming` | Due soon |
| `future` | Due in the future |

## SCHOOL_CONTEXT.md

The `setup` command writes a `SCHOOL_CONTEXT.md` file to the workspace containing:
- Authenticated account info
- Student table (ID, name)
- Course table (ID, name, student, term)

This file serves dual purpose:
1. **Machine-readable** — school.py parses the tables to know which students/courses to query
2. **AI-readable** — OpenClaw can read it to understand who the students are and what courses they take

## Natural Language Mapping

| User Says | Command |
|-----------|---------|
| "How are the kids doing in school?" | `grades` |
| "What are Student A's grades?" | `grades --student {student_a_id}` |
| "Any missing homework?" | `missing` |
| "What's due this week?" | `upcoming` |
| "Show me recent grades" | `submissions --since 7d --state graded` |
| "What assignments are overdue?" | `assignments --bucket overdue` |
| "Any school announcements?" | `announcements --since 7d` |
| "How did Student B do on their math test?" | `submissions --student {student_b_id} --course {math_id}` |

## Response Formatting

When presenting grades, use markdown tables:

```markdown
**Current Grades**
| Course | Student | Score | Grade |
|--------|---------|-------|-------|
| Math 8 | Student A | 92.5 | A- |
| English 8 | Student A | 88.0 | B+ |
| Math 8 | Student B | 95.0 | A |

**Missing Work** (2 items)
| Student | Assignment | Course | Due |
|---------|-----------|--------|-----|
| Student A | Ch. 5 Worksheet | Math 8 | Feb 18 |
| Student B | Essay Draft | English 8 | Feb 15 |
```

When reporting submissions:

```markdown
**Recent Submissions** (last 7 days)
| Student | Assignment | Score | Status |
|---------|-----------|-------|--------|
| Student A | Quiz 12 | 18/20 (90%) | Graded |
| Student B | Lab Report | 45/50 (90%) | Graded |
| Student A | Homework 8 | -- | Submitted |
```
