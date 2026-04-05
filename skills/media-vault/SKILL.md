# Media Vault Skill

Store, retrieve, search, and serve media files (images, audio, documents) with AI-powered classification and full-text search.

> **Before ANY vault operation, you MUST read the relevant VAULT.md file(s).**
> See [VAULT.md Context Files](#vaultmd-context-files) section below.

## Overview

The Media Vault is your personal media database with:
- **Auto-classification**: Images analyzed with Groq Vision, audio transcribed with Groq Whisper
- **Full-text search**: SQLite FTS5 indexes descriptions, transcripts, and extracted text
- **Topic organization**: Auto-assigned or custom topics for browsing
- **Web serving**: Files served via the web UI at `/api/vault/file/{id}`

## Storage

- **Database**: `~/clawd/vault/vault.db` (SQLite with FTS5)
- **Files**: `~/clawd/vault/files/{topic}/{YYYYMMDD}_{filename}.{ext}`

## VAULT.md Context Files

> **This is a mandatory requirement, not optional.**

Each topic (and the root) has an auto-generated **VAULT.md** file that provides AI-readable context about its contents.

### Pre-Operation Requirement

**Before executing ANY vault command** (search, list, store, get, update, delete), you MUST:

1. Fetch the relevant VAULT.md: `/api/vault/vault-md/{topic}?raw=1` or root
2. Read and understand the context
3. Use that context to guide your operation

This applies to ALL vault operations without exception.

### Purpose

VAULT.md files serve as:
- **Quick context** - Understand what's in a topic without searching
- **Organization guide** - How files are categorized and related
- **AI memory** - Persistent context across conversations
- **Decision guidance** - Where to store, how to categorize

### Commands

#### get-vault-md
Get the VAULT.md content for a topic (or root).

```bash
python3 vault.py get-vault-md --topic governance
python3 vault.py get-vault-md  # Root VAULT.md
```

#### generate-vault-md
Generate or regenerate VAULT.md for a topic.

```bash
python3 vault.py generate-vault-md --topic governance
python3 vault.py generate-vault-md  # Root VAULT.md
```

#### save-vault-md
Save edited VAULT.md content.

```bash
python3 vault.py save-vault-md --topic governance --content "# Governance\n\n..."
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/vault/vault-md/{topic}?raw=1` | GET | Get raw VAULT.md content |
| `/api/vault/vault-md/{topic}` | GET | Get VAULT.md as HTML preview |
| `/api/vault/vault-md/{topic}/generate` | POST | Regenerate VAULT.md |
| `/api/vault/vault-md/{topic}` | PUT | Save edited VAULT.md |

Use `root` as the topic for the root-level VAULT.md.

---

## Commands

### store
Save a new media item (called by the assistant after processing).

```bash
python3 vault.py store \
  --type image \
  --topic receipts \
  --original-filename "IMG_4532.jpg" \
  --stored-filename "20250130_IMG_4532.jpg" \
  --description "Restaurant receipt from Olive Garden" \
  --tags "receipt,restaurant,olive-garden" \
  --content-text "Olive Garden... Total: $47.82" \
  --content-json '{"total": 47.82, "vendor": "Olive Garden"}'
```

Returns: `{"id": "mv_abc123", "topic": "receipts", "file_path": "receipts/20250130_IMG_4532.jpg"}`

### get
Retrieve a media item by ID.

```bash
python3 vault.py get --id mv_abc123
python3 vault.py get --id mv_abc123 --include-file
```

### search
Full-text search across all media.

```bash
python3 vault.py search --query "restaurant receipts"
python3 vault.py search --query "volleyball practice" --type image
python3 vault.py search --query "dentist appointment" --from-date 2025-01-01
```

### list
List recent items with optional filters.

```bash
python3 vault.py list
python3 vault.py list --type audio --limit 10
python3 vault.py list --topic medical
```

### topics
List existing topics for classification.

```bash
python3 vault.py topics
```

### update
Update metadata for an item.

```bash
python3 vault.py update --id mv_abc123 --description "Updated description"
```

### delete
Permanently delete an item from the database and disk.

```bash
python3 vault.py delete --id mv_abc123
```

---

## Media Processing API

The web app provides endpoints for processing media files. These can be called directly or through natural language commands.

### Convert Documents

Convert documents between formats using pandoc.

**Endpoint:** `POST /api/media/convert`

```json
{
  "source_id": "mv_abc123",
  "target_format": "pdf",
  "options": {}
}
```

**Supported conversions:**
- Markdown → PDF, HTML, DOCX
- HTML → PDF, Markdown
- Text → PDF, HTML
- DOCX → PDF, Markdown, HTML

**Natural language examples:**
- "Convert my notes document to PDF"
- "Turn that markdown file into HTML"
- "Make a PDF from the meeting notes"

### Process Images/Videos

Apply transformations to images and videos.

**Endpoint:** `POST /api/media/process`

```json
{
  "source_id": "mv_abc123",
  "operation": "resize",
  "options": {"width": "800", "height": "600"}
}
```

**Operations:**
| Operation | Options | Description |
|-----------|---------|-------------|
| `resize` | `width`, `height` | Resize maintaining aspect ratio |
| `crop` | `geometry` (e.g., "100x100+10+10") | Crop to specific area |
| `rotate` | `degrees` (90, 180, 270) | Rotate image/video |
| `compress` | `quality` (1-100) | Compress to reduce size |
| `thumbnail` | `size` (e.g., "200x200") | Generate thumbnail |
| `grayscale` | - | Convert to grayscale |
| `optimize` | - | Strip metadata + compress |
| `trim` | `start`, `end`, `duration` | Trim video |

**Natural language examples:**
- "Resize that image to 800 pixels wide"
- "Make a thumbnail of the video"
- "Compress the photo to reduce file size"
- "Rotate the image 90 degrees"
- "Trim the video to the first 30 seconds"

### Extract Media

Extract audio or thumbnails from video files.

**Endpoint:** `POST /api/media/extract`

```json
{
  "source_id": "mv_abc123",
  "extract": "audio",
  "options": {"format": "mp3"}
}
```

**Extract types:**
| Type | Options | Description |
|------|---------|-------------|
| `audio` | `format` (mp3, wav, aac, ogg) | Extract audio track |
| `thumbnail` | `timestamp` (e.g., "00:00:05") | Extract single frame |
| `frames` | `interval` (seconds between frames) | Extract multiple frames |

**Natural language examples:**
- "Extract the audio from this video"
- "Get a thumbnail from the video at 10 seconds"
- "Pull out the audio as an MP3"
- "Grab frames from the video every 5 seconds"

### Natural Language Command Parsing

Clawdbot can parse natural language commands and call the appropriate API:

```
User: "Convert the meeting notes to a PDF"
→ Clawdbot searches vault for "meeting notes"
→ Calls POST /api/media/convert with source_id and target_format: "pdf"
→ Returns: "Converted meeting notes to PDF: [download](/api/vault/file/mv_newid)"

User: "Resize that photo to 1200 pixels"
→ Clawdbot uses the recently referenced image
→ Calls POST /api/media/process with operation: "resize", options: {width: "1200"}
→ Returns: "Resized image saved: [view](/api/vault/file/mv_newid)"

User: "Extract audio from the volleyball video"
→ Clawdbot searches vault for "volleyball video"
→ Calls POST /api/media/extract with extract: "audio"
→ Returns: "Audio extracted as MP3: [listen](/api/vault/file/mv_newid)"
```

---

## 20 Use Cases with Examples

### Category 1: Receipt & Expense Tracking

**1. Store a restaurant receipt**
User uploads photo of restaurant bill.
```
User: [uploads receipt photo]
Clawdbot: Saved receipt to "receipts" - Olive Garden dinner, $47.82. Tagged: receipt, restaurant, dining.
```

**2. Find receipts for reimbursement**
```
User: Find my work lunch receipts from January
Clawdbot: [searches] Found 3 lunch receipts from January:
- mv_abc123: Chipotle $12.50 (Jan 5)
- mv_def456: Panera $15.80 (Jan 12)
- mv_ghi789: Subway $9.25 (Jan 20)
Total: $37.55. Want me to export these?
```

**3. Track a specific expense**
```
User: How much did I spend at Target last month?
Clawdbot: [searches "Target" in receipts] Found 2 Target receipts:
- Jan 8: $127.43 (household items)
- Jan 22: $45.99 (kids clothes)
Total: $173.42
```

### Category 2: Medical Records

**4. Store a prescription label**
```
User: [uploads prescription photo] Save this prescription
Clawdbot: Saved to "medical" - Amoxicillin 500mg prescription from CVS. Refills: 2. Expires: 2025-06-15.
```

**5. Find vaccination records**
```
User: When was Alex's last tetanus shot?
Clawdbot: [searches "Alex tetanus"] Found vaccination record from 2023-08-15 - Alex's Tdap booster at the doctor's office.
```

**6. Insurance card reference**
```
User: What's our dental insurance info?
Clawdbot: [searches "dental insurance"] Found insurance card image - Delta Dental, Group: 12345, Member: DG789012.
```

### Category 3: Voice Memos & Ideas

**7. Record a quick idea**
```
User: [records audio] I had an idea for the backyard...
Clawdbot: Saved voice memo to "ideas" - Backyard project: build raised garden beds near the fence, use cedar wood. Duration: 45 seconds.
```

**8. Capture meeting notes**
```
User: [records audio] Notes from school meeting...
Clawdbot: Saved to "family" - School meeting notes: your child needs math tutor, parent-teacher conference March 15. Duration: 2 min.
```

**9. Find a past idea**
```
User: What was that idea I had about the garage?
Clawdbot: [searches "garage"] Found voice memo from Jan 10: "Garage organization - install pegboard, add bike hooks, build workbench."
```

### Category 4: Family & Events

**10. Store event photos**
```
User: [uploads photo] This is from Alex's volleyball tournament
Clawdbot: Saved to "volleyball" - Alex at tournament, team huddle with coaches. Tagged: volleyball, alex, tournament.
```

**11. Find photos by person**
```
User: Show me recent photos of your child
Clawdbot: [searches "your child"] Found 5 images:
- [mv_xxx1](/api/vault/file/mv_xxx1) Volleyball practice (Jan 25)
- [mv_xxx2](/api/vault/file/mv_xxx2) Birthday dinner (Jan 15)
... Want to see them?
```

**12. Event documentation**
```
User: What photos do I have from Christmas?
Clawdbot: [searches "Christmas 2024"] Found 12 images in "family" topic - gift opening, dinner, family group photo...
```

### Category 5: Documents & Reference

**13. Store important documents**
```
User: [uploads PDF] Save this car insurance policy
Clawdbot: Saved to "documents" - State Farm auto policy, Policy #: 123-456-789, expires 2025-07-01. Coverage: $100k/$300k.
```

**14. Quick reference lookup**
```
User: What's my car VIN number?
Clawdbot: [searches "VIN"] Found in car registration document: VIN 1HGBH41JXMN109186
```

**15. Find a saved document**
```
User: Where's that home warranty info?
Clawdbot: [searches "home warranty"] Found PDF from "documents" - American Home Shield warranty, claim phone: 1-800-XXX-XXXX.
```

### Category 6: Clawdbot-Generated Content

**16. Save generated images for user**
When Clawdbot generates an image for the user:
```
User: Create an image of a sunset over mountains
Clawdbot: [generates image, stores in vault]
Here's your sunset image: [mv_sunset1](/api/vault/file/mv_sunset1)
Saved to "generated" topic for future reference.
```

**17. Store research results**
```
User: Research the best dishwashers and save it
Clawdbot: [researches, creates summary document, stores]
Saved research document to "documents" - Top 5 dishwashers 2025 comparison. ID: mv_dishwasher_research
```

**18. Archive conversation artifacts**
```
Clawdbot: I created a meal plan for next week. Saving to vault for easy access...
Saved to "family" - Weekly meal plan Jan 27-Feb 2. [mv_mealplan](/api/vault/file/mv_mealplan)
```

### Category 7: Search & Discovery

**19. Cross-topic search**
```
User: Find anything about "dentist"
Clawdbot: Found across topics:
- medical: Dental insurance card
- medical: Dr. Smith appointment notes (audio)
- receipts: Dentist copay receipt $25
```

**20. Browse by topic**
```
User: What's in my ideas folder?
Clawdbot: [lists ideas topic] You have 8 items in "ideas":
- Backyard raised beds (voice memo)
- App idea for volleyball scheduling (voice memo)
- Kitchen remodel notes (document)
...
```

---

## Response Format

When returning media to users, **always include clickable links**:

**Good:**
```markdown
Found your receipt: [Olive Garden receipt](/api/vault/file/mv_abc123)
- Amount: $47.82
- Date: January 15, 2025
```

**Bad:**
```
Found receipt mv_abc123 in the vault.
```

## Best Practices

1. **Always confirm saves**: Tell user what was saved, topic, and key metadata
2. **Include links**: Use markdown `[description](/api/vault/file/{id})` format
3. **Search before giving up**: If user asks about something, search the vault first
4. **Suggest organization**: If user saves many items, suggest topic organization
5. **Cross-reference**: Link related items (e.g., "This matches the receipt you saved last week")

## Integration with Other Skills

- **Family Calendars**: Cross-reference events with saved photos/documents
- **Twilio**: "Send Agnes the photo I saved yesterday" - retrieve and send
- **Email**: Attach vault items to outgoing emails

---

## OCR, Thumbnails & Deduplication

### OCR (Optical Character Recognition)

Extract text from images using tesseract.

**On store:**
```bash
python3 vault.py store --type image --topic receipts ... --ocr
```

**On existing image:**
```bash
python3 vault.py ocr --id mv_abc123
python3 vault.py ocr --id mv_abc123 --append  # Append to existing content
```

The extracted text is added to `content_text` for full-text search.

### Thumbnails

Thumbnails are automatically generated for images, videos, and PDFs.

**API endpoint:** `GET /api/vault/thumb/{id}`
- Returns 300x300 JPEG thumbnail
- Generated on-demand if not exists
- Cached for 24 hours

**Manual generation:**
```bash
python3 vault.py thumbnail --id mv_abc123
python3 vault.py get-thumbnail --id mv_abc123
python3 vault.py generate-all-thumbnails  # Batch generate
```

### Deduplication

Files are hashed (SHA-256) on upload to detect duplicates.

**Check before upload:**
```bash
python3 vault.py check-duplicate --file /path/to/file.jpg
```

Returns:
```json
{
  "is_duplicate": true,
  "file_hash": "abc123...",
  "existing_id": "mv_abc123",
  "existing_topic": "receipts"
}
```

**Store with duplicate handling:**
```bash
# Will return duplicate info instead of storing
python3 vault.py store --type image ... --check-duplicate

# Force store even if duplicate
python3 vault.py store --type image ... --allow-duplicate
```

---

## Technical Notes

- IDs are prefixed with `mv_` (media vault)
- Delete is permanent (removes from database and disk)
- FTS5 search supports prefix matching: `volley*` matches "volleyball"
- Images analyzed with Groq Vision (Llama 4 Maverick)
- Audio transcribed with Groq Whisper (whisper-large-v3-turbo)
- Documents: PDF text extracted via pdftotext
- Media processing: ImageMagick (convert), ffmpeg, pandoc
- OCR: tesseract-ocr with English language pack
- Thumbnails stored in: `~/clawd/vault/thumbs/{id}.jpg`
- File deduplication via SHA-256 hash stored in database
