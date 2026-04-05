#!/usr/bin/env python3
"""Tasks skill — manage tasks in the OpenClaw SQLite database.

Usage:
    python3 tasks.py list [--status STATUS] [--priority PRIORITY] [--limit N]
    python3 tasks.py create "title" [--description TEXT] [--priority low|medium|high|urgent] [--due DATE] [--source SOURCE]
    python3 tasks.py get <task_id>
    python3 tasks.py update <task_id> [--title TEXT] [--status STATUS] [--priority PRIORITY] [--due DATE] [--description TEXT]
    python3 tasks.py comment <task_id> "body" [--source user|assistant|system|email]
    python3 tasks.py link <task_id> --file <vault_file_id>
    python3 tasks.py unlink <task_id> --file <vault_file_id>
    python3 tasks.py delete <task_id>
    python3 tasks.py overdue
    python3 tasks.py due-today
    python3 tasks.py summary
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, date


def get_db_path():
    vault_dir = os.environ.get("VAULT_DIR", "/opt/openclaw/vault")
    # Also check workspace vault (gateway container layout)
    if not os.path.isdir(vault_dir):
        alt = os.path.expanduser("~/.openclaw/workspace/vault")
        if os.path.isdir(alt):
            vault_dir = alt
    for name in ("openclaw.db",):
        path = os.path.join(vault_dir, name)
        if os.path.exists(path):
            return path
    return os.path.join(vault_dir, "openclaw.db")


def get_db():
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(json.dumps({"error": f"Database not found: {db_path}"}))
        sys.exit(1)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Ensure tables exist
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            user_email TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            priority TEXT NOT NULL DEFAULT 'medium',
            due_date TEXT,
            thread_id TEXT,
            source TEXT NOT NULL DEFAULT 'web',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS task_comments (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            user_email TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'user',
            body TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS task_files (
            task_id TEXT NOT NULL,
            file_id TEXT NOT NULL,
            linked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (task_id, file_id)
        );
    """)
    return conn


# Default user email — read from ALLOWED_EMAIL env var (set per-device in web.env)
DEFAULT_EMAIL = os.environ.get("ALLOWED_EMAIL", "user@example.com")


def gen_id(prefix):
    return f"{prefix}_{int(time.time() * 1000)}"


def cmd_list(args):
    conn = get_db()
    query = "SELECT * FROM tasks WHERE user_email = ?"
    params = [DEFAULT_EMAIL]

    if args.status:
        query += " AND status = ?"
        params.append(args.status)
    if args.priority:
        query += " AND priority = ?"
        params.append(args.priority)

    query += " ORDER BY CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END, updated_at DESC"
    query += f" LIMIT {args.limit}"

    rows = conn.execute(query, params).fetchall()
    tasks = [dict(r) for r in rows]

    # Add counts
    for t in tasks:
        t["comment_count"] = conn.execute(
            "SELECT COUNT(*) FROM task_comments WHERE task_id = ?", (t["id"],)
        ).fetchone()[0]
        t["file_count"] = conn.execute(
            "SELECT COUNT(*) FROM task_files WHERE task_id = ?", (t["id"],)
        ).fetchone()[0]

    print(json.dumps({"tasks": tasks, "count": len(tasks)}, indent=2, default=str))


def cmd_create(args):
    conn = get_db()
    task_id = gen_id("task")
    conn.execute(
        """INSERT INTO tasks (id, user_email, title, description, priority, due_date, source)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (task_id, DEFAULT_EMAIL, args.title, args.description or "",
         args.priority, args.due or None, args.source),
    )
    conn.commit()
    print(json.dumps({"success": True, "id": task_id, "title": args.title}))


def cmd_get(args):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM tasks WHERE id = ? AND user_email = ?",
        (args.task_id, DEFAULT_EMAIL),
    ).fetchone()
    if not row:
        print(json.dumps({"error": "Task not found"}))
        sys.exit(1)
    task = dict(row)

    comments = [dict(r) for r in conn.execute(
        "SELECT * FROM task_comments WHERE task_id = ? ORDER BY created_at ASC",
        (args.task_id,),
    ).fetchall()]
    task["comments"] = comments

    files = [dict(r) for r in conn.execute(
        "SELECT * FROM task_files WHERE task_id = ? ORDER BY linked_at DESC",
        (args.task_id,),
    ).fetchall()]
    task["files"] = files

    print(json.dumps(task, indent=2, default=str))


def cmd_update(args):
    conn = get_db()
    sets = ["updated_at = CURRENT_TIMESTAMP"]
    params = []

    if args.title:
        sets.append("title = ?")
        params.append(args.title)
    if args.status:
        sets.append("status = ?")
        params.append(args.status)
    if args.priority:
        sets.append("priority = ?")
        params.append(args.priority)
    if args.due is not None:
        if args.due == "":
            sets.append("due_date = NULL")
        else:
            sets.append("due_date = ?")
            params.append(args.due)
    if args.description is not None:
        sets.append("description = ?")
        params.append(args.description)

    params.extend([args.task_id, DEFAULT_EMAIL])
    query = f"UPDATE tasks SET {', '.join(sets)} WHERE id = ? AND user_email = ?"
    result = conn.execute(query, params)
    conn.commit()

    if result.rowcount == 0:
        print(json.dumps({"error": "Task not found"}))
        sys.exit(1)

    # Add system comment for status changes
    if args.status:
        conn.execute(
            "INSERT INTO task_comments (id, task_id, user_email, source, body) VALUES (?, ?, ?, 'system', ?)",
            (gen_id("comment"), args.task_id, DEFAULT_EMAIL, f"Status changed to **{args.status}**"),
        )
        conn.commit()

    print(json.dumps({"success": True, "id": args.task_id}))


def cmd_comment(args):
    conn = get_db()
    # Verify task exists
    row = conn.execute("SELECT 1 FROM tasks WHERE id = ? AND user_email = ?",
                       (args.task_id, DEFAULT_EMAIL)).fetchone()
    if not row:
        print(json.dumps({"error": "Task not found"}))
        sys.exit(1)

    comment_id = gen_id("comment")
    conn.execute(
        "INSERT INTO task_comments (id, task_id, user_email, source, body) VALUES (?, ?, ?, ?, ?)",
        (comment_id, args.task_id, DEFAULT_EMAIL, args.source, args.body),
    )
    conn.execute("UPDATE tasks SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (args.task_id,))
    conn.commit()
    print(json.dumps({"success": True, "id": comment_id}))


def cmd_link(args):
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO task_files (task_id, file_id) VALUES (?, ?)",
        (args.task_id, args.file),
    )
    conn.execute("UPDATE tasks SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (args.task_id,))
    conn.commit()
    print(json.dumps({"success": True}))


def cmd_unlink(args):
    conn = get_db()
    conn.execute(
        "DELETE FROM task_files WHERE task_id = ? AND file_id = ?",
        (args.task_id, args.file),
    )
    conn.execute("UPDATE tasks SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (args.task_id,))
    conn.commit()
    print(json.dumps({"success": True}))


def cmd_delete(args):
    conn = get_db()
    result = conn.execute("DELETE FROM tasks WHERE id = ? AND user_email = ?",
                          (args.task_id, DEFAULT_EMAIL))
    if result.rowcount == 0:
        print(json.dumps({"error": "Task not found"}))
        sys.exit(1)
    conn.execute("DELETE FROM task_comments WHERE task_id = ?", (args.task_id,))
    conn.execute("DELETE FROM task_files WHERE task_id = ?", (args.task_id,))
    conn.commit()
    print(json.dumps({"success": True, "id": args.task_id}))


def cmd_overdue(args):
    conn = get_db()
    today = date.today().isoformat()
    rows = conn.execute(
        """SELECT id, title, priority, due_date, status FROM tasks
           WHERE user_email = ? AND due_date < ? AND status NOT IN ('done', 'archived')
           ORDER BY due_date ASC""",
        (DEFAULT_EMAIL, today),
    ).fetchall()
    tasks = [dict(r) for r in rows]
    print(json.dumps({"overdue": tasks, "count": len(tasks)}, indent=2, default=str))


def cmd_due_today(args):
    conn = get_db()
    today = date.today().isoformat()
    rows = conn.execute(
        """SELECT id, title, priority, due_date, status FROM tasks
           WHERE user_email = ? AND due_date = ? AND status NOT IN ('done', 'archived')
           ORDER BY priority ASC""",
        (DEFAULT_EMAIL, today),
    ).fetchall()
    tasks = [dict(r) for r in rows]
    print(json.dumps({"due_today": tasks, "count": len(tasks)}, indent=2, default=str))


def cmd_summary(args):
    conn = get_db()
    counts = {}
    for status in ["pending", "started", "done", "archived"]:
        counts[status] = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_email = ? AND status = ?",
            (DEFAULT_EMAIL, status),
        ).fetchone()[0]

    today = date.today().isoformat()
    overdue = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_email = ? AND due_date < ? AND status NOT IN ('done', 'archived')",
        (DEFAULT_EMAIL, today),
    ).fetchone()[0]
    due_today = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_email = ? AND due_date = ? AND status NOT IN ('done', 'archived')",
        (DEFAULT_EMAIL, today),
    ).fetchone()[0]

    print(json.dumps({
        "summary": counts,
        "overdue": overdue,
        "due_today": due_today,
        "total_active": counts["pending"] + counts["started"],
    }, indent=2))


def main():
    parser = argparse.ArgumentParser(description="OpenClaw task management skill")
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    p = sub.add_parser("list", help="List tasks")
    p.add_argument("--status", choices=["pending", "started", "done", "archived"])
    p.add_argument("--priority", choices=["low", "medium", "high", "urgent"])
    p.add_argument("--limit", type=int, default=50)

    # create
    p = sub.add_parser("create", help="Create a task")
    p.add_argument("title", help="Task title")
    p.add_argument("--description", default="")
    p.add_argument("--priority", default="medium", choices=["low", "medium", "high", "urgent"])
    p.add_argument("--due", help="Due date (YYYY-MM-DD)")
    p.add_argument("--source", default="skill")

    # get
    p = sub.add_parser("get", help="Get task details")
    p.add_argument("task_id")

    # update
    p = sub.add_parser("update", help="Update a task")
    p.add_argument("task_id")
    p.add_argument("--title")
    p.add_argument("--status", choices=["pending", "started", "done", "archived"])
    p.add_argument("--priority", choices=["low", "medium", "high", "urgent"])
    p.add_argument("--due")
    p.add_argument("--description")

    # comment
    p = sub.add_parser("comment", help="Add a comment")
    p.add_argument("task_id")
    p.add_argument("body")
    p.add_argument("--source", default="assistant", choices=["user", "assistant", "system", "email"])

    # link
    p = sub.add_parser("link", help="Link a vault file")
    p.add_argument("task_id")
    p.add_argument("--file", required=True)

    # unlink
    p = sub.add_parser("unlink", help="Unlink a vault file")
    p.add_argument("task_id")
    p.add_argument("--file", required=True)

    # delete
    p = sub.add_parser("delete", help="Delete a task")
    p.add_argument("task_id")

    # overdue
    sub.add_parser("overdue", help="List overdue tasks")

    # due-today
    sub.add_parser("due-today", help="List tasks due today")

    # summary
    sub.add_parser("summary", help="Task summary stats")

    args = parser.parse_args()

    commands = {
        "list": cmd_list,
        "create": cmd_create,
        "get": cmd_get,
        "update": cmd_update,
        "comment": cmd_comment,
        "link": cmd_link,
        "unlink": cmd_unlink,
        "delete": cmd_delete,
        "overdue": cmd_overdue,
        "due-today": cmd_due_today,
        "summary": cmd_summary,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
