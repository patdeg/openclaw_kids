# Printer — Network Printing via IPP

Print documents, images, and text to the network printer (configured via PRINTER_IP env var).

## Configuration

- `PRINTER_IP` — Printer IP address (configured via PRINTER_IP env var)
- `PRINTER_PORT` — IPP port (default: `631`)
- `PRINTER_PATH` — IPP endpoint path (default: `/ipp/print`)

No credentials required — the printer accepts jobs on the local network.

## Quick Reference

All commands use `print.py` in the skill directory:

```bash
python3 /home/openclaw/.openclaw/workspace/skills/printer/print.py <command> [args]
```

## Commands

### Status — Check if printer is ready

```bash
python3 /home/openclaw/.openclaw/workspace/skills/printer/print.py status
```

Returns: printer name, model, state (idle/processing/stopped), and any issues.

**Always run `status` first** before printing, to confirm the printer is online and ready.

### Print — Print a file

```bash
python3 /home/openclaw/.openclaw/workspace/skills/printer/print.py print /path/to/file.pdf
python3 /home/openclaw/.openclaw/workspace/skills/printer/print.py print /path/to/photo.jpg --copies 2
python3 /home/openclaw/.openclaw/workspace/skills/printer/print.py print /path/to/document.pdf --no-color
```

Supported formats:
- **PDF** (`.pdf`) — documents, reports, articles
- **JPEG** (`.jpg`, `.jpeg`) — photos, images
- **PNG** (`.png`) — screenshots, graphics
- **Text** (`.txt`) — automatically converted to PDF for clean formatting

Options:
- `--copies N` — Print N copies (default: 1)
- `--no-color` — Print in monochrome (saves ink)

### Text — Print text content directly

```bash
python3 /home/openclaw/.openclaw/workspace/skills/printer/print.py text "Shopping list:\n- Milk\n- Eggs\n- Bread"
python3 /home/openclaw/.openclaw/workspace/skills/printer/print.py text "Meeting notes from today..." --copies 2
```

Text is rendered to PDF with monospace font (Courier) for clean, readable output. Long lines wrap at 90 characters. Multi-page text is handled automatically.

Use `-` to read from stdin:

```bash
echo "Hello world" | python3 /home/openclaw/.openclaw/workspace/skills/printer/print.py text -
```

### Queue — Show active print jobs

```bash
python3 /home/openclaw/.openclaw/workspace/skills/printer/print.py queue
```

Returns: job ID, name, state, and submitting user for each active job.

### Cancel — Cancel a print job

```bash
python3 /home/openclaw/.openclaw/workspace/skills/printer/print.py cancel 42
```

Use the job ID from the `queue` command.

## Decision Patterns

### User asks to print something

1. Run `status` to confirm printer is online
2. If printing a vault file → use `print` with the vault file path
3. If printing text content → use `text` with the content
4. If printing a generated document → save to temp file first, then `print`
5. Report success with job ID

### User asks about the printer

1. Run `status` to check state
2. Report: idle (ready), processing (busy), or stopped (error)
3. If stopped, report the reason (paper jam, out of ink, etc.)

### User wants to cancel printing

1. Run `queue` to show active jobs
2. Confirm which job to cancel
3. Run `cancel` with the job ID

### Printing vault files

Files in the vault are at `~/.openclaw/workspace/vault/files/`. Example:

```bash
# Print a PDF from the vault
python3 ~/skills/printer/print.py print ~/.openclaw/workspace/vault/files/receipts/receipt.pdf

# Print a photo from the vault
python3 ~/skills/printer/print.py print ~/.openclaw/workspace/vault/files/personal/photo.jpg
```

## Common Use Cases

- **Shopping lists**: Generate text → `text` command
- **Recipes**: Research via tavily → format → `text` command
- **Documents**: Vault PDFs → `print` command
- **Photos**: Vault images → `print` command
- **School work**: Print assignments or reports
- **Notes/memos**: Quick text → `text` command
