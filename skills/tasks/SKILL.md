# Tasks Skill

Manage tasks in the SQLite database. Tasks can be created from the web UI, chat, or automation scripts.

## Quick Reference

```bash
# List tasks
python3 skills/tasks/tasks.py list
python3 skills/tasks/tasks.py list --status pending --priority high

# Create a task
python3 skills/tasks/tasks.py create "Book Florida hotels" --priority high --due 2026-04-15
python3 skills/tasks/tasks.py create "Review quarterly report" --description "Check Q1 numbers"

# Get task details (with comments and linked files)
python3 skills/tasks/tasks.py get task_1711555200000

# Update a task
python3 skills/tasks/tasks.py update task_1711555200000 --status started
python3 skills/tasks/tasks.py update task_1711555200000 --status done
python3 skills/tasks/tasks.py update task_1711555200000 --priority urgent --due 2026-04-01

# Add a comment
python3 skills/tasks/tasks.py comment task_1711555200000 "Found good rates at Marriott Bonvoy"
python3 skills/tasks/tasks.py comment task_1711555200000 "Booked via email confirmation" --source email

# Link/unlink vault files
python3 skills/tasks/tasks.py link task_1711555200000 --file vault_file_uuid
python3 skills/tasks/tasks.py unlink task_1711555200000 --file vault_file_uuid

# Delete a task
python3 skills/tasks/tasks.py delete task_1711555200000

# Monitoring commands (for heartbeat)
python3 skills/tasks/tasks.py overdue        # List overdue tasks
python3 skills/tasks/tasks.py due-today      # Tasks due today
python3 skills/tasks/tasks.py summary        # Stats: pending, started, done, overdue counts
```

## Task Fields

| Field | Values | Default |
|-------|--------|---------|
| status | pending, started, done, archived | pending |
| priority | low, medium, high, urgent | medium |
| due_date | YYYY-MM-DD or empty | none |
| source | web, email, alfred, skill | skill |

## When to Use

- **"add a task"**, **"remind me to"**, **"I need to"** → create
- **"what's on my list"**, **"what do I need to do"** → list --status pending
- **"mark X as done"**, **"finished X"** → update --status done
- **"what's overdue"** → overdue
- **"task summary"**, **"how am I doing on tasks"** → summary

## Database

Tasks are stored in `/opt/openclaw/vault/openclaw.db` (same SQLite database as chat threads). No encryption needed. The web UI at `/tasks` reads from the same database.
