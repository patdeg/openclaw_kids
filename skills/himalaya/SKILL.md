# Himalaya Email Skill

Email access via the `himalaya` CLI. Two accounts can be configured:

| Account | Flag | Env Vars | Purpose |
|---------|------|----------|---------|
| migadu (default) | (none) | `MIGADU_PASSWORD` | Your personal email |
| agent | `-a agent` | `AGENT_EMAIL`, `MIGADU_AGENT_PASSWORD` | Assistant inbound/outbound (optional) |

## IMPORTANT: Himalaya is fully configured and ready to use

Do NOT ask for credentials or say himalaya is unconfigured. Accounts are set up at `~/.config/himalaya/config.toml` and passwords injected via environment variables. Verify with `himalaya account list`.

## Quick Reference

```bash
# Check inbox
himalaya envelope list

# Check specific folder
himalaya envelope list -f Sent
himalaya envelope list -f Drafts

# Read a message (by ID from envelope list)
himalaya message read 1

# Search emails
himalaya envelope list -q "from:someone@example.com"
himalaya envelope list -q "subject:urgent"

# Send an email
himalaya message write   # interactive
# Or pipe a raw message:
echo "From: you@example.com
To: recipient@example.com
Subject: Hello

Body here" | himalaya message send

# Reply to a message
himalaya message reply 1

# Forward a message
himalaya message forward 1

# Download attachments
himalaya attachment download 1

# JSON output (for parsing)
himalaya envelope list -o json

# ── Agent account (if configured, -a agent AFTER the subcommand) ──

# Check agent inbox
himalaya envelope list -a agent

# Send as agent
echo "From: $AGENT_EMAIL
To: recipient@example.com
Subject: Task Created

Your task has been created." | himalaya message send -a agent

# Search agent inbox (JSON)
himalaya envelope list -a agent -o json
```

## Available Folders

- INBOX (default)
- Sent
- Drafts
- Archive
- Junk
- Trash

## Usage Notes

- The WARN about "Rectified faulty continuation request" is normal for Migadu - ignore it
- Message IDs are shown in the first column of envelope list
- Use -o json when you need to parse output programmatically
- Always confirm before sending emails on behalf of the user

## When to Check Email

- During heartbeats (rotate with other checks)
- When user asks about email/inbox
- When expecting important messages

## Response Format (WhatsApp/Discord)

Don't dump raw CLI output. Summarize nicely:

**Good:**
> You have 3 new emails:
> - Meeting reminder from boss@company.com
> - Newsletter from service.com  
> - Reply from John about the project

**Bad:**
> | ID | FLAGS | SUBJECT | FROM | DATE |
> (raw table output)
