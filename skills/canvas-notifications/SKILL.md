# Canvas Notifications — Grade Alerts via Discord

Monitors Canvas LMS for grade changes and missing work, pushes alerts
to Discord. Designed to run via cron.

## Usage

```
exec: python3 ~/skills/canvas-notifications/canvas_notify.py check
exec: python3 ~/skills/canvas-notifications/canvas_notify.py digest [--period daily|weekly]
```

## Commands

- `check` — Check for new grades and missing work since last check.
  Returns a summary of changes. Designed to be called by cron and have
  results posted to Discord.
- `digest` — Generate a daily or weekly grade summary across all courses.

## Environment Variables

- `CANVAS_API_KEY` — Canvas LMS bearer token (required)
- `CANVAS_BASE_URL` — Canvas instance URL (default: YOUR_SCHOOL.instructure.com)

## Cron Setup

Add to cron jobs in openclaw config:
- Daily at 4 PM PT: `canvas-notifications check` (catch new grades after school)
- Weekly Sunday 6 PM: `canvas-notifications digest --period weekly`

## Notes

- Uses the same Canvas API as the school skill.
- State file at workspace/canvas_last_check.json tracks what's been seen.
- Missing work is flagged with high priority.
- Grade drops are flagged for attention.
