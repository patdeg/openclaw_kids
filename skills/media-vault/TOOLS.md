# Media Vault - Clawdbot Governance

This document teaches Clawdbot how to effectively use the Media Vault skill.

## Core Principle

**The vault is your external memory.** Use it to:
1. Store things users want to keep
2. Retrieve things users have stored
3. Save your own generated content for users
4. Build context about the user over time

---

## Quick Command Decision Guide

**Use this to pick the right command for each task:**

### "I need to understand the vault structure"
| Situation | Command |
|-----------|---------|
| What topics exist? | `tree` (visual) or `topics --counts` (data) |
| What's in a topic? | `list --topic X` or read that topic's VAULT.md |
| What changed recently? | `recent --limit 20` |
| Overall stats? | `stats` |

### "I need to find something"
| Situation | Command |
|-----------|---------|
| Know the filename pattern | `find --pattern "*.pdf"` or `find --pattern "invoice*"` |
| Know keywords to search | `search --query "keywords"` |
| Need to search file contents with context | `grep --pattern "regex" -C 3` |
| User references `RE: [topic/file]` | `read --topic X --filename Y` |

### "I need to read/examine a file"
| Situation | Command |
|-----------|---------|
| Know topic + filename | `read --topic X --filename Y` (includes content for text) |
| Know the ID | `get --id mv_xxx` (metadata only) |
| File is huge, need just the start | `head --id mv_xxx -n 50` |
| File is huge, need just the end | `tail --id mv_xxx -n 50` |
| Need dimensions/duration/page count | `info --id mv_xxx` |
| Need word/line count | `wc --id mv_xxx` |

### "I need to compare or analyze"
| Situation | Command |
|-----------|---------|
| Compare two versions | `diff --id1 mv_xxx --id2 mv_yyy -u` |
| Find pattern across files | `grep --pattern "TODO" --topic code` |
| Get image dimensions | `info --id mv_xxx` → `image_info` |
| Get audio/video duration | `info --id mv_xxx` → `audio_info` or `video_info` |
| Get PDF page count | `info --id mv_xxx` → `pdf_info` |

### "I need to modify something"
| Situation | Command |
|-----------|---------|
| Fix description/tags | `update --id mv_xxx --description "..." --tags "..."` |
| Move to different topic | `move --id mv_xxx --topic newtopic` |
| Rename a file | `rename --id mv_xxx --filename newname.md` |
| Delete a file | `delete --id mv_xxx` |

### Common Patterns

**Answering "what do I have about X?"**
```bash
# 1. Check VAULT.md first for context
vault.py get-vault-md --topic relevant-topic

# 2. Then search
vault.py search --query "X"
```

**Answering "show me the details of this file"**
```bash
# Get comprehensive info
vault.py info --id mv_xxx
# Returns: file_info + type-specific info (image_info, audio_info, etc.)
```

**Answering "what does this file say about Y?"**
```bash
# Search within specific file(s) with context
vault.py grep --pattern "Y" --topic topic-name -C 3
```

**Working with large text files**
```bash
# Don't read entire file - use head/tail
vault.py head --id mv_xxx -n 100   # First 100 lines
vault.py tail --id mv_xxx -n 50    # Last 50 lines
vault.py wc --id mv_xxx            # How big is it?
```

---

## CRITICAL: Never Bypass vault.py

**All vault operations MUST go through `vault.py` commands. Never manipulate files directly.**

### What Happens When You Bypass vault.py

| Bad Action | Consequence |
|------------|-------------|
| `mkdir ~/clawd/vault/files/newtopic` | Topic not in database, UI shows "None" |
| `mv` or `cp` files directly | Database points to wrong location |
| Create .md files with echo/cat | File exists but not searchable |
| `rm` files directly | Database still shows deleted item |
| Edit files without updating metadata | Search results become stale |

### Correct vs Wrong

```bash
# WRONG - Creating files directly
mkdir ~/clawd/vault/files/trips
echo "Trip info" > ~/clawd/vault/files/trips/SWITZERLAND.md

# RIGHT - Use vault.py store
python3 ~/clawd/skills/media-vault/vault.py store \
  --type document --topic trips \
  --original-filename "SWITZERLAND.md" \
  --stored-filename "20260131_SWITZERLAND.md" \
  --description "Switzerland trip itinerary" \
  --content-text "Trip info..."
```

### Allowed Exceptions (In-Place Transforms)

Some operations can be done directly when:
1. File is already indexed in vault
2. Operation doesn't change location or identity
3. User explicitly requests quick transformation

**Allowed:**
- Rotate image in-place: `convert photo.jpg -rotate 90 photo.jpg`
- Compress in-place: `convert photo.jpg -quality 80 photo.jpg`
- Generate thumbnail to thumbs/

**Not allowed (even if "quick"):**
- Moving files between topics → `vault.py move`
- Renaming files → `vault.py rename`
- Creating new files → `vault.py store`
- Deleting files → `vault.py delete`

---

## Vault File References: `RE: [topic/filename]`

When a user message starts with `RE: [topic/filename]`, they are explicitly referencing an existing vault file. **This is a critical pattern you MUST recognize and handle correctly.**

### Pattern Recognition

```
RE: [trips/SWITZERLAND_FEB_2026.md] Can you update the dates?
     ↑                            ↑
     topic                        filename
```

### Mandatory Handling

When you see this pattern:

1. **FIRST**: Read the referenced file using vault.py
   ```bash
   python3 ~/clawd/skills/media-vault/vault.py read --topic {topic} --filename {filename}
   ```
   This returns:
   - File metadata (id, description, tags, etc.)
   - **File content** for text files (.md, .txt, .json, .yaml, .csv)
   - File path for binary files

2. **THEN**: Process the user's request with full file context

3. **NEVER**: Say "I don't have that file" or "Let me create one" without reading first

### Why This Matters

Users expect you to know what's in the file they're referencing. Ignoring this pattern and saying "I'll create a new file" is a critical failure that destroys user trust.

### Example - Correct Handling

```
User: RE: [trips/SWITZERLAND_FEB_2026.md] Can you move the ski days from Feb 13-17 to Feb 14-18?

1. Read: python3 vault.py read --topic trips --filename SWITZERLAND_FEB_2026.md
   → Returns JSON with "content" field containing the markdown text
2. Parse: Understand current itinerary structure from content
3. Modify: Update the dates as requested
4. Save: Write updated content back to file (for .md files, direct edit is allowed)
5. Respond: "Updated the ski days in your Switzerland trip. Now Feb 14-18 instead of Feb 13-17."
```

### Example - WRONG Handling

```
User: RE: [trips/SWITZERLAND_FEB_2026.md] Can you update the dates?

WRONG: "I don't have an existing trip file, so I'll create one..."
```

This response shows you ignored the explicit file reference. Never do this.

### File Types

The `vault.py read` command works with any vault file:

| Extension | `vault.py read` returns |
|-----------|-------------------------|
| `.md`, `.txt`, `.json`, `.yaml`, `.csv` | Full content in `content` field |
| `.pdf`, images, audio | Metadata + `full_path` (read content_text for transcripts) |

For text files, you get the content directly and can modify.
For binary files, use `content_text` field for any extracted text (OCR, transcripts).

### When User Says "RE:" Without Brackets

If user types just `RE: filename` or `RE: topic`, treat it as a vault reference:
```
RE: Switzerland trip → search vault for Switzerland-related files
RE: my insurance docs → search vault for insurance
```

---

## VAULT.md - Mandatory Pre-Operation Requirement

> **This is non-negotiable. ALWAYS read VAULT.md before ANY vault operation.**

**Before doing ANYTHING with vault data, you MUST read the relevant VAULT.md file.**

### What is VAULT.md?

Every topic folder (and the root) has an auto-generated VAULT.md file that provides:
- Summary of contents
- Key files and their purposes
- Organization patterns
- Cross-references to related topics
- Guidance on using the contents

### Always Read VAULT.md First - No Exceptions

```
User asks about vault contents OR any vault operation
    ↓
FIRST: Read VAULT.md for that topic/root
    ↓
THEN: Use context to answer OR search for specifics
    ↓
NEVER: Skip the VAULT.md step
```

**Every single vault operation requires this.** This includes:
- Searching
- Listing
- Storing new content
- Updating metadata
- Answering questions about what's stored

### How to Read VAULT.md

**Via API (recommended):**
```bash
# Get raw content for a topic
curl /api/vault/vault-md/governance?raw=1

# Get root VAULT.md
curl /api/vault/vault-md/root?raw=1
```

**Via CLI:**
```bash
python3 ~/clawd/skills/media-vault/vault.py get-vault-md --topic governance
python3 ~/clawd/skills/media-vault/vault.py get-vault-md  # root
```

### When to Read Which VAULT.md

| User Question | Read This |
|---------------|-----------|
| "What's in my vault?" | Root VAULT.md |
| "Tell me about my [topic] files" | Topic VAULT.md |
| "What governance docs do I have?" | governance VAULT.md |
| Any vault search | Relevant topic VAULT.md first |

### Example Flow

```
User: "What governance documents do I have?"

1. Read /api/vault/vault-md/governance?raw=1
   → Returns: "Contains 3 chapters covering Clawdbot identity,
      skill integration patterns, and family context..."

2. Now you understand the context without searching

3. If user wants specifics, search with informed context:
   python3 vault.py search --query "chapter" --topic governance
```

### VAULT.md is User-Editable

Users can edit VAULT.md through the Files UI to:
- Add custom notes or organization preferences
- Correct AI-generated descriptions
- Add cross-references to other topics

**Respect user edits** - don't regenerate unless asked.

---

## When to Search the Vault

**Always search before saying "I don't know":**

| User says | Action |
|-----------|--------|
| "Find my..." | Search vault |
| "What did I save about..." | Search vault |
| "Show me the..." | Search vault |
| "Where's that..." | Search vault |
| "Do I have any..." | Search vault |
| "What's my..." (insurance, VIN, etc.) | Search vault |

**Search command:**
```bash
python3 ~/clawd/skills/media-vault/vault.py search --query "user's keywords"
```

## When to Store in the Vault

### User-Initiated Storage

When user uploads media via the web UI, it's automatically processed and stored. Confirm with:
```
Saved [type] to "[topic]" - [description]. ID: [mv_id]
```

### Clawdbot-Initiated Storage

**You should store content you create for the user:**

1. **Generated images** - When you create images for the user
2. **Research documents** - When you compile research results
3. **Plans and lists** - Meal plans, shopping lists, project plans
4. **Summaries** - Meeting summaries, book summaries
5. **Reference material** - Anything the user might want again

**How to store your generated content:**

```bash
# 1. Write content to temp file
echo "Your generated content here" > /tmp/generated_doc.txt

# 2. Copy to vault files directory (vault.py store requires file to exist)
cp /tmp/generated_doc.txt ~/clawd/vault/files/generated/$(date +%Y%m%d)_filename.txt

# 3. Index in database with vault.py
python3 ~/clawd/skills/media-vault/vault.py store \
  --type document \
  --topic generated \
  --original-filename "filename.txt" \
  --stored-filename "$(date +%Y%m%d)_filename.txt" \
  --description "Description of what this is" \
  --tags "generated,category" \
  --content-text "Full searchable text content"

# Note: Steps 2+3 MUST be done together. Never do step 2 without step 3!
```

## Returning Media to Users

**Always use markdown links with the API path:**

```markdown
Here's what I found: [Receipt from Olive Garden](/api/vault/file/mv_abc123)
```

For images, use image syntax so they display inline:
```markdown
![Volleyball tournament photo](/api/vault/file/mv_xyz789)
```

For multiple results:
```markdown
Found 3 receipts:
1. [Chipotle - $12.50](/api/vault/file/mv_001) (Jan 5)
2. [Panera - $15.80](/api/vault/file/mv_002) (Jan 12)
3. [Subway - $9.25](/api/vault/file/mv_003) (Jan 20)
```

## Search Strategies

### Broad to Narrow
Start broad, then filter:
```bash
# First, broad search
python3 vault.py search --query "volleyball"

# If too many results, narrow by type
python3 vault.py search --query "volleyball" --type image

# Or by date
python3 vault.py search --query "volleyball" --from-date 2025-01-01
```

### Cross-Topic Discovery
When user asks about a person or topic, search without type filter to find all related items:
```bash
# Find everything about a specific person or topic
python3 vault.py search --query "Alex"
# Might return: photos, voice memos about them, documents mentioning them
```

### Use Wildcards
FTS5 supports prefix matching:
```bash
# Find all volleyball-related
python3 vault.py search --query "volley*"
```

## Topic Management

### Default Topics
- `receipts` - Financial documents, receipts
- `medical` - Health records, prescriptions, insurance
- `family` - Family photos, events, memories
- `ideas` - Voice memos, brainstorms, notes
- `work` - Work-related documents
- `documents` - General documents
- `generated` - Content Clawdbot created
- `volleyball` - Kids' volleyball activities

### Creating New Topics
Topics are created automatically when storing. Choose descriptive, lowercase, hyphenated names:
- Good: `home-improvement`, `car-maintenance`, `school-2025`
- Bad: `Misc`, `stuff`, `temp`

### List Available Topics
```bash
python3 vault.py topics
```

## Metadata Best Practices

### Descriptions
Write descriptions that will help future searches:
- **Good**: "Restaurant receipt from Olive Garden, family dinner, $47.82"
- **Bad**: "receipt" or "image001"

### Tags
Use consistent, searchable tags:
- People: use first names of family members
- Categories: `receipt`, `medical`, `school`, `sports`
- Events: `birthday`, `tournament`, `vacation`

### Content Text
For audio and documents, the full transcript/text is stored in `content_text`. This is searchable. Reference it when the user asks about the content.

## Integration Patterns

### With Family Calendars
```
User: What photos do I have from the tournament last Saturday?
1. Check family-calendars for the event date
2. Search vault with date range and "tournament"
3. Return matching photos with links
```

### With Twilio
```
User: Send Mom the photo I took yesterday
1. Search vault for recent images
2. Get the file URL
3. Send via Twilio MMS (if image) or include link in SMS
```

### With Email (himalaya)
```
User: Email me the insurance documents
1. Search vault for insurance
2. Get file paths
3. Compose email with attachments or links
```

## Error Handling

### No Results Found
```
I searched the vault for "unicorn photos" but didn't find anything.
Would you like me to search for something else, or would you like to
save something new?
```

### File Not Found
If a stored ID returns "not found", the file may have been moved or deleted:
```
The file mv_abc123 seems to be missing from storage.
I found the metadata: "Olive Garden receipt from Jan 15"
but the actual file isn't available.
```

## Privacy & Security

1. **All vault data is private** - Only accessible to authenticated users
2. **Soft delete** - Files are hidden, not permanently deleted
3. **Local storage** - All files stored on local server, not cloud
4. **Session isolation** - Each session has its own ID for tracking

## Command Reference

### Reading & Viewing
| Command | Use Case |
|---------|----------|
| `read --topic X --filename Y` | Read file by topic/filename (returns content for text files) |
| `get --id mv_xxx` | Get full details by ID |
| `head --id mv_xxx -n 20` | First N lines of a text file |
| `tail --id mv_xxx -n 20` | Last N lines of a text file |
| `info --id mv_xxx` | Comprehensive file info (dimensions, duration, word count) |

### Searching & Finding
| Command | Use Case |
|---------|----------|
| `search --query "text"` | Full-text search in metadata/content |
| `grep --pattern "regex" -C 3` | Search file contents with context lines |
| `grep --pattern "TODO" -A 2 -B 1` | Context: 1 line before, 2 after |
| `find --pattern "*.pdf"` | Find files by glob pattern |
| `find --pattern "invoice*" --topic receipts` | Find in specific topic |

### Browsing & Listing
| Command | Use Case |
|---------|----------|
| `list --type image` | Browse recent images |
| `list --topic receipts` | Browse a topic |
| `recent --limit 10` | Recently modified files |
| `tree` | Visual directory structure |
| `tree --json` | Directory structure as JSON |
| `topics --counts` | All topics with file counts |

### File Statistics
| Command | Use Case |
|---------|----------|
| `wc --id mv_xxx` | Word/line/character count |
| `info --id mv_xxx` | File stats + type-specific info |
| `stats` | Overall vault statistics |
| `diff --id1 mv_xxx --id2 mv_yyy` | Compare two files |
| `diff --id1 X --id2 Y -u` | Unified diff format |

### File Management
| Command | Use Case |
|---------|----------|
| `update --id mv_xxx` | Fix description/tags |
| `move --id mv_xxx --topic Y` | Move to different topic |
| `rename --id mv_xxx --filename Y` | Rename a file |
| `delete --id mv_xxx` | Remove an item |

### `info` Command Output by Type

**Images** (`image_info`):
```json
{"width": 3840, "height": 2160, "format": "JPEG", "depth": "8", "colorspace": "sRGB"}
```

**Audio** (`audio_info`):
```json
{"duration_seconds": 125.5, "duration_human": "2m 5s", "codec": "aac", "sample_rate": 44100}
```

**Video** (`video_info`):
```json
{"duration_seconds": 300, "width": 1920, "height": 1080, "fps": 30, "video_codec": "h264"}
```

**PDF** (`pdf_info`):
```json
{"pages": 12, "title": "Document", "author": "John"}
```

**Text** (`text_info`):
```json
{"lines": 150, "words": 2500, "characters": 15000}
```

### `grep` Examples

```bash
# Find all mentions of "ski" with 2 lines context
vault.py grep --pattern "ski" --topic trips -C 2

# Case-insensitive search for TODO/FIXME
vault.py grep --pattern "TODO|FIXME" -i

# Find function definitions in documents
vault.py grep --pattern "^def |^function " --type document
```

## Examples of Good Responses

### When user uploads media:
```
Saved your receipt to "receipts" - Target shopping trip, $127.43.
I extracted the items: household supplies, kids clothing.
Tagged: receipt, target, shopping

[View receipt](/api/vault/file/mv_abc123)
```

### When user searches:
```
Found 3 volleyball photos from last month:

![Alex's tournament](/api/vault/file/mv_001)
Alex at club tournament, Jan 20

![Team practice](/api/vault/file/mv_002)
Team practice, Jan 15

![Jordan's game](/api/vault/file/mv_003)
Jordan's club match, Jan 18
```

### When suggesting storage:
```
I just created a meal plan for you. Would you like me to save it
to your vault so you can reference it later?

[Save to vault] [Just show me]
```

### When building context:
```
I noticed you've saved several volleyball tournament photos.
Would you like me to create a "tournaments-2025" topic to
organize them separately from practice photos?
```
