#!/usr/bin/env python3
"""
Media Vault CLI - Store, retrieve, and search media files.
Usage: vault.py <command> [options]
"""

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import secrets
import string

# Configuration
VAULT_DIR = Path(os.environ.get('VAULT_DIR', os.path.expanduser('~/clawd/vault')))
DB_PATH = VAULT_DIR / 'vault.db'
FILES_DIR = VAULT_DIR / 'files'
THUMBS_DIR = VAULT_DIR / 'thumbs'

def generate_id():
    """Generate a unique media vault ID."""
    chars = string.ascii_lowercase + string.digits
    return 'mv_' + ''.join(secrets.choice(chars) for _ in range(12))

def get_db():
    """Get database connection, creating schema if needed."""
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    THUMBS_DIR.mkdir(parents=True, exist_ok=True)

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    # Initialize schema if needed
    schema_path = Path(__file__).parent / 'schema.sql'
    if schema_path.exists():
        with open(schema_path) as f:
            db.executescript(f.read())

    # Add file_hash column if not exists (for deduplication)
    try:
        db.execute('ALTER TABLE media_items ADD COLUMN file_hash TEXT')
        db.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists

    return db


def calculate_file_hash(file_path):
    """Calculate SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def run_ocr(image_path):
    """Run OCR on an image using tesseract."""
    try:
        result = subprocess.run(
            ['tesseract', str(image_path), 'stdout', '-l', 'eng'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def generate_thumbnail(source_path, item_id, mime_type):
    """Generate a thumbnail for an image, video, or PDF."""
    thumb_path = THUMBS_DIR / f"{item_id}.jpg"

    if thumb_path.exists():
        return str(thumb_path)

    try:
        if mime_type and mime_type.startswith('image/'):
            # Image thumbnail using ImageMagick
            subprocess.run(
                ['convert', str(source_path), '-thumbnail', '300x300>', '-quality', '85', str(thumb_path)],
                capture_output=True,
                timeout=30
            )
        elif mime_type and mime_type.startswith('video/'):
            # Video thumbnail using ffmpeg
            subprocess.run(
                ['ffmpeg', '-i', str(source_path), '-ss', '00:00:01', '-vframes', '1',
                 '-vf', 'scale=300:-1', '-q:v', '2', '-y', str(thumb_path)],
                capture_output=True,
                timeout=30
            )
        elif mime_type == 'application/pdf':
            # PDF thumbnail using ImageMagick (first page)
            subprocess.run(
                ['convert', '-density', '150', f'{source_path}[0]',
                 '-thumbnail', '300x300>', '-quality', '85', str(thumb_path)],
                capture_output=True,
                timeout=30
            )

        if thumb_path.exists():
            return str(thumb_path)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return None


def find_duplicate_by_hash(db, file_hash):
    """Check if a file with the same hash already exists."""
    if not file_hash:
        return None

    row = db.execute(
        'SELECT id, topic, original_filename, file_path FROM media_items WHERE file_hash = ?',
        (file_hash,)
    ).fetchone()

    if row:
        return dict(row)
    return None

def cmd_store(args):
    """Store a new media item."""
    db = get_db()

    item_id = generate_id()
    now = datetime.utcnow().isoformat() + 'Z'

    # Ensure topic directory exists
    topic_dir = FILES_DIR / args.topic
    topic_dir.mkdir(parents=True, exist_ok=True)

    file_path = f"{args.topic}/{args.stored_filename}"
    full_path = FILES_DIR / file_path

    # Calculate file hash for deduplication
    file_hash = None
    duplicate = None
    if full_path.exists() and getattr(args, 'check_duplicate', True):
        file_hash = calculate_file_hash(full_path)
        duplicate = find_duplicate_by_hash(db, file_hash)

        if duplicate and not getattr(args, 'allow_duplicate', False):
            # Return duplicate info without storing
            print(json.dumps({
                'duplicate': True,
                'existing_id': duplicate['id'],
                'existing_topic': duplicate['topic'],
                'existing_filename': duplicate['original_filename'],
                'file_hash': file_hash
            }))
            return

    # Read content from stdin if requested (avoids "argument list too long")
    import sys
    if getattr(args, 'content_text_stdin', False) and not args.content_text:
        args.content_text = sys.stdin.read()
    if getattr(args, 'content_json_stdin', False) and not args.content_json:
        args.content_json = sys.stdin.read()

    # Run OCR if requested and file is an image
    content_text = args.content_text
    if getattr(args, 'ocr', False) and args.type == 'image' and full_path.exists():
        ocr_text = run_ocr(full_path)
        if ocr_text:
            if content_text:
                content_text = content_text + '\n\n[OCR Text]\n' + ocr_text
            else:
                content_text = ocr_text

    db.execute('''
        INSERT INTO media_items (
            id, type, topic, original_filename, stored_filename, file_path,
            file_size, mime_type, description, tags, content_text, content_json,
            source, session_id, duration_seconds, file_hash, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        item_id, args.type, args.topic, args.original_filename, args.stored_filename,
        file_path, args.file_size, args.mime_type, args.description, args.tags,
        content_text, args.content_json, args.source, args.session_id,
        args.duration_seconds, file_hash, now, now
    ))
    db.commit()

    # Generate thumbnail if applicable
    thumb_path = None
    if full_path.exists() and args.mime_type:
        thumb_path = generate_thumbnail(full_path, item_id, args.mime_type)

    result = {
        'id': item_id,
        'topic': args.topic,
        'file_path': file_path
    }
    if file_hash:
        result['file_hash'] = file_hash
    if thumb_path:
        result['thumbnail'] = thumb_path

    print(json.dumps(result))

def cmd_get(args):
    """Get a media item by ID."""
    db = get_db()

    row = db.execute(
        'SELECT * FROM media_items WHERE id = ?',
        (args.id,)
    ).fetchone()

    if not row:
        print(json.dumps({'error': 'Not found'}))
        sys.exit(1)

    result = dict(row)
    if args.include_file:
        result['full_path'] = str(FILES_DIR / result['file_path'])

    # Parse JSON fields
    if result.get('content_json'):
        try:
            result['content_json'] = json.loads(result['content_json'])
        except:
            pass
    if result.get('tags'):
        result['tags'] = result['tags'].split(',')

    print(json.dumps(result, default=str))

def cmd_read(args):
    """Read a vault file by topic and filename path."""
    db = get_db()

    topic = args.topic
    filename = args.filename

    # Look up file in database by topic and filename
    row = db.execute('''
        SELECT * FROM media_items
        WHERE topic = ? AND (stored_filename = ? OR original_filename = ?)
    ''', (topic, filename, filename)).fetchone()

    if not row:
        # Try partial match on filename
        row = db.execute('''
            SELECT * FROM media_items
            WHERE topic = ? AND (stored_filename LIKE ? OR original_filename LIKE ?)
        ''', (topic, f'%{filename}%', f'%{filename}%')).fetchone()

    if not row:
        print(json.dumps({'error': f'File not found: {topic}/{filename}'}))
        sys.exit(1)

    result = dict(row)
    full_path = FILES_DIR / result['file_path']

    # For text files, include the content
    text_extensions = {'.md', '.txt', '.json', '.yaml', '.yml', '.csv', '.xml', '.html'}
    file_ext = Path(filename).suffix.lower()

    if file_ext in text_extensions and full_path.exists():
        try:
            result['content'] = full_path.read_text(encoding='utf-8')
        except Exception as e:
            result['content_error'] = str(e)

    result['full_path'] = str(full_path)
    result['exists_on_disk'] = full_path.exists()

    # Parse JSON fields
    if result.get('content_json'):
        try:
            result['content_json'] = json.loads(result['content_json'])
        except:
            pass
    if result.get('tags'):
        result['tags'] = result['tags'].split(',')

    print(json.dumps(result, default=str))


def cmd_info(args):
    """Get comprehensive file information (like file + stat + identify)."""
    db = get_db()

    # Find the file
    row = db.execute('SELECT * FROM media_items WHERE id = ?', (args.id,)).fetchone()
    if not row:
        print(json.dumps({'error': 'Not found'}))
        sys.exit(1)

    result = dict(row)
    full_path = FILES_DIR / result['file_path']

    # Basic file stats
    if full_path.exists():
        stat = full_path.stat()
        result['file_info'] = {
            'size_bytes': stat.st_size,
            'size_human': format_size(stat.st_size),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
        }

        # Type-specific info
        mime = result.get('mime_type') or ''
        ext = full_path.suffix.lower()

        if mime.startswith('image/') or ext in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}:
            result['image_info'] = get_image_info(full_path)
        elif mime.startswith('audio/') or ext in {'.mp3', '.wav', '.m4a', '.ogg', '.flac', '.webm'}:
            result['audio_info'] = get_audio_info(full_path)
        elif mime.startswith('video/') or ext in {'.mp4', '.mov', '.avi', '.mkv', '.webm'}:
            result['video_info'] = get_video_info(full_path)
        elif mime == 'application/pdf' or ext == '.pdf':
            result['pdf_info'] = get_pdf_info(full_path)
        elif ext in {'.md', '.txt', '.json', '.yaml', '.yml', '.csv', '.xml', '.html'}:
            result['text_info'] = get_text_info(full_path)
    else:
        result['file_info'] = {'error': 'File not found on disk'}

    result['full_path'] = str(full_path)
    if result.get('tags'):
        result['tags'] = result['tags'].split(',')

    print(json.dumps(result, default=str))


def format_size(size_bytes):
    """Format bytes as human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def parse_frame_rate(rate_str):
    """Safely parse frame rate string like '30/1' or '24000/1001'."""
    if not rate_str or rate_str == '0/0':
        return None
    try:
        if '/' in rate_str:
            num, den = rate_str.split('/')
            den = int(den)
            if den == 0:
                return None
            return round(int(num) / den, 2)
        return float(rate_str)
    except (ValueError, ZeroDivisionError):
        return None


def get_image_info(path):
    """Get image dimensions and format using ImageMagick identify."""
    try:
        result = subprocess.run(
            ['identify', '-format', '%w %h %m %z %[colorspace]', str(path)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split()
            if len(parts) >= 3:
                return {
                    'width': int(parts[0]),
                    'height': int(parts[1]),
                    'format': parts[2],
                    'depth': parts[3] if len(parts) > 3 else None,
                    'colorspace': parts[4] if len(parts) > 4 else None,
                }
    except Exception:
        pass
    return {'error': 'Could not read image info'}


def get_audio_info(path):
    """Get audio duration and format using ffprobe."""
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', str(path)
        ], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            fmt = data.get('format', {})
            streams = data.get('streams', [])
            audio_stream = next((s for s in streams if s.get('codec_type') == 'audio'), {})
            return {
                'duration_seconds': float(fmt.get('duration', 0)),
                'duration_human': format_duration(float(fmt.get('duration', 0))),
                'bitrate': int(fmt.get('bit_rate', 0)) if fmt.get('bit_rate') else None,
                'codec': audio_stream.get('codec_name'),
                'sample_rate': int(audio_stream.get('sample_rate', 0)) if audio_stream.get('sample_rate') else None,
                'channels': audio_stream.get('channels'),
            }
    except Exception:
        pass
    return {'error': 'Could not read audio info'}


def get_video_info(path):
    """Get video duration, resolution, and format using ffprobe."""
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', str(path)
        ], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            fmt = data.get('format', {})
            streams = data.get('streams', [])
            video_stream = next((s for s in streams if s.get('codec_type') == 'video'), {})
            audio_stream = next((s for s in streams if s.get('codec_type') == 'audio'), {})
            return {
                'duration_seconds': float(fmt.get('duration', 0)),
                'duration_human': format_duration(float(fmt.get('duration', 0))),
                'width': video_stream.get('width'),
                'height': video_stream.get('height'),
                'fps': parse_frame_rate(video_stream.get('r_frame_rate')),
                'video_codec': video_stream.get('codec_name'),
                'audio_codec': audio_stream.get('codec_name') if audio_stream else None,
                'bitrate': int(fmt.get('bit_rate', 0)) if fmt.get('bit_rate') else None,
            }
    except Exception:
        pass
    return {'error': 'Could not read video info'}


def get_pdf_info(path):
    """Get PDF page count and metadata using pdfinfo."""
    try:
        result = subprocess.run(['pdfinfo', str(path)], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            info = {}
            for line in result.stdout.split('\n'):
                if ':' in line:
                    key, val = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    info[key] = val.strip()
            return {
                'pages': int(info.get('pages', 0)),
                'title': info.get('title'),
                'author': info.get('author'),
                'creator': info.get('creator'),
                'page_size': info.get('page_size'),
            }
    except Exception:
        pass
    return {'error': 'Could not read PDF info'}


def get_text_info(path):
    """Get text file statistics (lines, words, characters)."""
    try:
        content = path.read_text(encoding='utf-8')
        lines = content.split('\n')
        words = content.split()
        return {
            'lines': len(lines),
            'words': len(words),
            'characters': len(content),
            'encoding': 'utf-8',
        }
    except Exception as e:
        return {'error': str(e)}


def format_duration(seconds):
    """Format seconds as human-readable duration."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def cmd_grep(args):
    """Search file contents with context lines (like grep -A -B -C)."""
    db = get_db()

    pattern = args.pattern
    before = args.before or 0
    after = args.after or 0
    context = args.context or 0
    if context:
        before = after = context

    # Build query
    query = 'SELECT id, topic, original_filename, file_path, content_text FROM media_items WHERE 1=1'
    params = []

    if args.topic:
        query += ' AND topic = ?'
        params.append(args.topic)

    if args.type:
        query += ' AND type = ?'
        params.append(args.type)

    rows = db.execute(query, params).fetchall()

    results = []
    import re
    regex = re.compile(pattern, re.IGNORECASE if args.ignore_case else 0)

    for row in rows:
        # Check content_text first
        content = row['content_text'] or ''

        # For text files, also check actual file content
        full_path = FILES_DIR / row['file_path']
        ext = Path(row['file_path']).suffix.lower()
        if ext in {'.md', '.txt', '.json', '.yaml', '.yml', '.csv', '.xml', '.html'} and full_path.exists():
            try:
                content = full_path.read_text(encoding='utf-8')
            except:
                pass

        if not content:
            continue

        lines = content.split('\n')
        matches = []

        for i, line in enumerate(lines):
            if regex.search(line):
                start = max(0, i - before)
                end = min(len(lines), i + after + 1)
                context_lines = []
                for j in range(start, end):
                    prefix = '>' if j == i else ' '
                    context_lines.append(f"{j+1:4}{prefix} {lines[j]}")
                matches.append({
                    'line_number': i + 1,
                    'line': line.strip(),
                    'context': '\n'.join(context_lines) if (before or after) else None
                })

        if matches:
            results.append({
                'id': row['id'],
                'topic': row['topic'],
                'filename': row['original_filename'],
                'matches': matches[:args.limit] if args.limit else matches
            })

    print(json.dumps(results, default=str))


def cmd_head(args):
    """Read first N lines of a text file."""
    db = get_db()

    row = db.execute('SELECT file_path FROM media_items WHERE id = ?', (args.id,)).fetchone()
    if not row:
        print(json.dumps({'error': 'Not found'}))
        sys.exit(1)

    full_path = FILES_DIR / row['file_path']
    if not full_path.exists():
        print(json.dumps({'error': 'File not found on disk'}))
        sys.exit(1)

    try:
        lines = []
        line_count = 0
        with open(full_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= args.lines:
                    break
                lines.append(line.rstrip('\n'))
                line_count = i + 1
        print(json.dumps({
            'id': args.id,
            'lines': lines,
            'count': len(lines),
            'truncated': line_count >= args.lines
        }))
    except Exception as e:
        print(json.dumps({'error': str(e)}))
        sys.exit(1)


def cmd_tail(args):
    """Read last N lines of a text file."""
    db = get_db()

    row = db.execute('SELECT file_path FROM media_items WHERE id = ?', (args.id,)).fetchone()
    if not row:
        print(json.dumps({'error': 'Not found'}))
        sys.exit(1)

    full_path = FILES_DIR / row['file_path']
    if not full_path.exists():
        print(json.dumps({'error': 'File not found on disk'}))
        sys.exit(1)

    try:
        content = full_path.read_text(encoding='utf-8')
        all_lines = content.split('\n')
        lines = all_lines[-args.lines:] if len(all_lines) > args.lines else all_lines
        print(json.dumps({
            'id': args.id,
            'lines': lines,
            'count': len(lines),
            'total_lines': len(all_lines),
            'truncated': len(all_lines) > args.lines
        }))
    except Exception as e:
        print(json.dumps({'error': str(e)}))
        sys.exit(1)


def cmd_tree(args):
    """Show directory tree structure of vault."""
    db = get_db()

    # Get all topics with counts
    rows = db.execute('''
        SELECT topic, type, COUNT(*) as count, SUM(file_size) as size
        FROM media_items
        GROUP BY topic, type
        ORDER BY topic, type
    ''').fetchall()

    # Build tree structure
    tree = {}
    for row in rows:
        topic = row['topic']
        if topic not in tree:
            tree[topic] = {'files': {}, 'total': 0, 'size': 0}
        tree[topic]['files'][row['type']] = row['count']
        tree[topic]['total'] += row['count']
        tree[topic]['size'] += row['size'] or 0

    # Check for empty folders on disk
    if FILES_DIR.exists():
        for d in FILES_DIR.iterdir():
            if d.is_dir() and d.name not in tree:
                tree[d.name] = {'files': {}, 'total': 0, 'size': 0, 'empty': True}

    # Format output
    if args.json:
        print(json.dumps(tree, default=str))
    else:
        output = ["vault/"]
        topics = sorted(tree.keys())
        for i, topic in enumerate(topics):
            is_last = i == len(topics) - 1
            prefix = "└── " if is_last else "├── "
            info = tree[topic]
            size_str = format_size(info['size']) if info['size'] else '0 B'
            type_counts = ', '.join(f"{v} {k}" for k, v in info['files'].items())
            empty_str = " (empty)" if info.get('empty') else ""
            output.append(f"{prefix}{topic}/ [{info['total']} files, {size_str}]{empty_str}")
            if type_counts and not info.get('empty'):
                child_prefix = "    " if is_last else "│   "
                output.append(f"{child_prefix}({type_counts})")
        print('\n'.join(output))


def cmd_find(args):
    """Find files by name pattern (glob)."""
    db = get_db()
    import fnmatch

    pattern = args.pattern

    query = 'SELECT id, topic, original_filename, stored_filename, type, file_size, created_at FROM media_items'
    params = []

    if args.topic:
        query += ' WHERE topic = ?'
        params.append(args.topic)

    rows = db.execute(query, params).fetchall()

    results = []
    for row in rows:
        # Match against both original and stored filename
        if fnmatch.fnmatch(row['original_filename'].lower(), pattern.lower()) or \
           fnmatch.fnmatch(row['stored_filename'].lower(), pattern.lower()):
            results.append({
                'id': row['id'],
                'topic': row['topic'],
                'filename': row['original_filename'],
                'type': row['type'],
                'size': row['file_size'],
                'created': row['created_at']
            })

    if args.limit:
        results = results[:args.limit]

    print(json.dumps(results, default=str))


def cmd_wc(args):
    """Word count for a file (lines, words, characters)."""
    db = get_db()

    row = db.execute('SELECT file_path, content_text FROM media_items WHERE id = ?', (args.id,)).fetchone()
    if not row:
        print(json.dumps({'error': 'Not found'}))
        sys.exit(1)

    full_path = FILES_DIR / row['file_path']
    content = None

    # Try to read from file first
    ext = full_path.suffix.lower()
    if ext in {'.md', '.txt', '.json', '.yaml', '.yml', '.csv', '.xml', '.html'} and full_path.exists():
        try:
            content = full_path.read_text(encoding='utf-8')
        except:
            pass

    # Fall back to content_text
    if content is None:
        content = row['content_text'] or ''

    lines = content.split('\n')
    words = content.split()

    print(json.dumps({
        'id': args.id,
        'lines': len(lines),
        'words': len(words),
        'characters': len(content),
        'bytes': len(content.encode('utf-8'))
    }))


def cmd_recent(args):
    """Show recently modified files across all topics."""
    db = get_db()

    query = '''
        SELECT id, topic, original_filename, type, file_size, description, updated_at, created_at
        FROM media_items
        ORDER BY updated_at DESC
        LIMIT ?
    '''
    params = [args.limit]

    if args.topic:
        query = '''
            SELECT id, topic, original_filename, type, file_size, description, updated_at, created_at
            FROM media_items
            WHERE topic = ?
            ORDER BY updated_at DESC
            LIMIT ?
        '''
        params = [args.topic, args.limit]

    rows = db.execute(query, params).fetchall()

    results = []
    for row in rows:
        results.append({
            'id': row['id'],
            'topic': row['topic'],
            'filename': row['original_filename'],
            'type': row['type'],
            'size': format_size(row['file_size']) if row['file_size'] else None,
            'description': (row['description'] or '')[:100],
            'updated': row['updated_at'],
            'created': row['created_at']
        })

    print(json.dumps(results, default=str))


def cmd_diff(args):
    """Compare two vault files."""
    db = get_db()

    # Get both files
    row1 = db.execute('SELECT file_path, content_text FROM media_items WHERE id = ?', (args.id1,)).fetchone()
    row2 = db.execute('SELECT file_path, content_text FROM media_items WHERE id = ?', (args.id2,)).fetchone()

    if not row1:
        print(json.dumps({'error': f'File not found: {args.id1}'}))
        sys.exit(1)
    if not row2:
        print(json.dumps({'error': f'File not found: {args.id2}'}))
        sys.exit(1)

    # Read content
    def read_content(row):
        full_path = FILES_DIR / row['file_path']
        ext = full_path.suffix.lower()
        if ext in {'.md', '.txt', '.json', '.yaml', '.yml', '.csv', '.xml', '.html'} and full_path.exists():
            try:
                return full_path.read_text(encoding='utf-8')
            except:
                pass
        return row['content_text'] or ''

    content1 = read_content(row1)
    content2 = read_content(row2)

    # Generate diff
    import difflib
    lines1 = content1.splitlines(keepends=True)
    lines2 = content2.splitlines(keepends=True)

    if args.unified:
        diff = list(difflib.unified_diff(lines1, lines2, fromfile=args.id1, tofile=args.id2))
    else:
        diff = list(difflib.ndiff(lines1, lines2))

    print(json.dumps({
        'id1': args.id1,
        'id2': args.id2,
        'diff': ''.join(diff),
        'lines_added': sum(1 for d in diff if d.startswith('+')),
        'lines_removed': sum(1 for d in diff if d.startswith('-')),
    }))


def cmd_search(args):
    """Search media items."""
    db = get_db()

    query_parts = []
    params = []

    base_query = '''
        SELECT m.* FROM media_items m
        JOIN media_fts f ON m.id = f.id
        WHERE 1=1
    '''

    if args.query:
        query_parts.append('media_fts MATCH ?')
        params.append(args.query)

    if args.type:
        query_parts.append('m.type = ?')
        params.append(args.type)

    if args.topic:
        query_parts.append('m.topic = ?')
        params.append(args.topic)

    if args.from_date:
        query_parts.append('m.created_at >= ?')
        params.append(args.from_date)

    if args.to_date:
        query_parts.append('m.created_at <= ?')
        params.append(args.to_date)

    if query_parts:
        base_query += ' AND ' + ' AND '.join(query_parts)

    base_query += ' ORDER BY m.created_at DESC LIMIT ?'
    params.append(args.limit)

    rows = db.execute(base_query, params).fetchall()

    results = []
    for row in rows:
        item = dict(row)
        if item.get('tags'):
            item['tags'] = item['tags'].split(',')
        results.append(item)

    print(json.dumps(results, default=str))

def cmd_list(args):
    """List recent media items."""
    db = get_db()

    query = 'SELECT * FROM media_items WHERE 1=1'
    params = []

    if args.type:
        query += ' AND type = ?'
        params.append(args.type)

    if args.topic:
        query += ' AND topic = ?'
        params.append(args.topic)

    query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
    params.extend([args.limit, args.offset])

    rows = db.execute(query, params).fetchall()

    results = []
    for row in rows:
        item = dict(row)
        if item.get('tags'):
            item['tags'] = item['tags'].split(',')
        results.append(item)

    print(json.dumps(results, default=str))

def cmd_topics(args):
    """List existing topics with optional counts."""
    db = get_db()

    if args.counts:
        rows = db.execute('''
            SELECT topic,
                   COUNT(*) as count,
                   SUM(file_size) as total_size,
                   MAX(created_at) as last_updated
            FROM media_items
            GROUP BY topic
            ORDER BY topic
        ''').fetchall()

        results = {row['topic']: dict(row) for row in rows}

        # Also include empty directories from filesystem
        if FILES_DIR.exists():
            for d in FILES_DIR.iterdir():
                if d.is_dir() and d.name not in results:
                    results[d.name] = {
                        'topic': d.name,
                        'count': 0,
                        'total_size': 0,
                        'last_updated': None
                    }

        # Sort by topic name
        sorted_results = sorted(results.values(), key=lambda x: x['topic'])
        print(json.dumps(sorted_results, default=str))
    else:
        rows = db.execute(
            'SELECT DISTINCT topic FROM media_items ORDER BY topic'
        ).fetchall()
        topics = set(row['topic'] for row in rows)

        # Also include empty directories from filesystem
        if FILES_DIR.exists():
            for d in FILES_DIR.iterdir():
                if d.is_dir():
                    topics.add(d.name)

        print(json.dumps(sorted(topics)))

def validate_topic_name(name):
    """Validate topic name for security."""
    import re
    if not name or len(name) > 100:
        return False
    # Only allow alphanumeric, hyphens, underscores
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        return False
    # Disallow reserved names
    if name in ('.', '..', 'VAULT.md', 'thumbs'):
        return False
    return True


def validate_filename(name):
    """Validate filename for security - no path traversal."""
    if not name or len(name) > 255:
        return False
    # No path separators
    if '/' in name or '\\' in name:
        return False
    # No parent directory references
    if '..' in name:
        return False
    # No hidden files starting with dot (optional)
    if name.startswith('.'):
        return False
    return True


def cmd_create_topic(args):
    """Create an empty topic (directory)."""
    topic_name = args.name.strip()

    if not topic_name:
        print(json.dumps({'error': 'Topic name is required'}))
        sys.exit(1)

    # Validate topic name with strict rules
    if not validate_topic_name(topic_name):
        print(json.dumps({'error': 'Invalid topic name: use only letters, numbers, hyphens, underscores'}))
        sys.exit(1)

    # Initialize DB to ensure FILES_DIR exists
    get_db()

    topic_dir = FILES_DIR / topic_name
    if topic_dir.exists():
        print(json.dumps({'topic': topic_name, 'created': False, 'reason': 'Already exists'}))
        return

    topic_dir.mkdir(parents=True, exist_ok=True)
    print(json.dumps({'topic': topic_name, 'created': True}))

def cmd_delete_topic(args):
    """Delete a topic with cascade delete of all files."""
    db = get_db()
    topic_name = args.name.strip()
    force = getattr(args, 'force', False)

    # Get all files in topic
    rows = db.execute(
        'SELECT id, file_path FROM media_items WHERE topic = ?',
        (topic_name,)
    ).fetchall()

    file_count = len(rows)

    # If topic has files and not forced, return info for confirmation
    if file_count > 0 and not force:
        print(json.dumps({
            'error': f'Topic has {file_count} files',
            'file_count': file_count,
            'requires_force': True
        }))
        sys.exit(1)

    topic_dir = FILES_DIR / topic_name
    if not topic_dir.exists():
        print(json.dumps({'error': 'Topic not found'}))
        sys.exit(1)

    # Delete all files from database and disk
    for row in rows:
        full_path = FILES_DIR / row['file_path']
        if full_path.exists():
            full_path.unlink()

    # Delete from database
    if file_count > 0:
        db.execute('DELETE FROM media_items WHERE topic = ?', (topic_name,))
        db.commit()

    # Delete VAULT.md if exists
    vault_md_path = topic_dir / 'VAULT.md'
    if vault_md_path.exists():
        vault_md_path.unlink()

    # Delete any remaining files in directory (shouldn't be any)
    try:
        shutil.rmtree(topic_dir)
    except OSError as e:
        print(json.dumps({'error': f'Cannot delete directory: {e}'}))
        sys.exit(1)

    print(json.dumps({
        'topic': topic_name,
        'deleted': True,
        'files_deleted': file_count
    }))

def cmd_update(args):
    """Update a media item."""
    db = get_db()

    updates = []
    params = []

    if args.description is not None:
        updates.append('description = ?')
        params.append(args.description)

    if args.tags is not None:
        updates.append('tags = ?')
        params.append(args.tags)

    if args.topic is not None:
        updates.append('topic = ?')
        params.append(args.topic)

    if not updates:
        print(json.dumps({'error': 'No updates provided'}))
        sys.exit(1)

    updates.append("updated_at = datetime('now')")
    params.append(args.id)

    db.execute(
        f'UPDATE media_items SET {", ".join(updates)} WHERE id = ?',
        params
    )
    db.commit()

    print(json.dumps({'id': args.id, 'updated': True}))

def cmd_delete(args):
    """Hard-delete a media item (removes from DB and disk)."""
    db = get_db()

    # Get file info first
    row = db.execute(
        'SELECT file_path, topic FROM media_items WHERE id = ?',
        (args.id,)
    ).fetchone()

    if not row:
        print(json.dumps({'error': 'Not found'}))
        sys.exit(1)

    file_path = row['file_path']
    topic = row['topic']

    # Delete from database
    db.execute('DELETE FROM media_items WHERE id = ?', (args.id,))
    db.commit()

    # Delete from disk
    full_path = FILES_DIR / file_path
    if full_path.exists():
        full_path.unlink()

    print(json.dumps({'id': args.id, 'deleted': True, 'topic': topic}))

def cmd_move(args):
    """Move a media item to a different topic."""
    db = get_db()

    # Get current file info
    row = db.execute(
        'SELECT file_path, stored_filename, topic FROM media_items WHERE id = ?',
        (args.id,)
    ).fetchone()

    if not row:
        print(json.dumps({'error': 'Not found'}))
        sys.exit(1)

    old_topic = row['topic']
    new_topic = args.topic
    stored_filename = row['stored_filename']

    if old_topic == new_topic:
        print(json.dumps({'id': args.id, 'moved': False, 'reason': 'Same topic'}))
        return

    # Create new topic directory
    new_topic_dir = FILES_DIR / new_topic
    new_topic_dir.mkdir(parents=True, exist_ok=True)

    # Move file
    old_path = FILES_DIR / old_topic / stored_filename
    new_path = new_topic_dir / stored_filename
    new_file_path = f"{new_topic}/{stored_filename}"

    if old_path.exists():
        old_path.rename(new_path)

    # Update database
    db.execute('''
        UPDATE media_items
        SET topic = ?, file_path = ?, updated_at = datetime('now')
        WHERE id = ?
    ''', (new_topic, new_file_path, args.id))
    db.commit()

    print(json.dumps({'id': args.id, 'moved': True, 'from': old_topic, 'to': new_topic}))

def cmd_delete_bulk(args):
    """Bulk hard-delete media items (removes from DB and disk)."""
    db = get_db()

    ids = [id.strip() for id in args.ids.split(',')]
    placeholders = ','.join(['?' for _ in ids])

    # Get file paths first
    rows = db.execute(
        f'SELECT id, file_path, topic FROM media_items WHERE id IN ({placeholders})',
        ids
    ).fetchall()

    topics_affected = set()
    for row in rows:
        topics_affected.add(row['topic'])
        # Delete from disk
        full_path = FILES_DIR / row['file_path']
        if full_path.exists():
            full_path.unlink()

    # Delete from database
    db.execute(f'DELETE FROM media_items WHERE id IN ({placeholders})', ids)
    db.commit()

    print(json.dumps({
        'deleted': ids,
        'count': len(ids),
        'topics_affected': list(topics_affected)
    }))

def cmd_stats(args):
    """Get vault storage statistics."""
    db = get_db()

    row = db.execute('''
        SELECT
            COUNT(*) as total_files,
            SUM(file_size) as total_size,
            SUM(CASE WHEN type = 'image' THEN 1 ELSE 0 END) as images,
            SUM(CASE WHEN type = 'audio' THEN 1 ELSE 0 END) as audio,
            SUM(CASE WHEN type = 'document' THEN 1 ELSE 0 END) as documents,
            COUNT(DISTINCT topic) as topics
        FROM media_items
    ''').fetchone()

    print(json.dumps(dict(row), default=str))

def cmd_generate_vault_md(args):
    """Generate or regenerate VAULT.md for a topic or root."""
    db = get_db()
    topic = args.topic if args.topic else None

    # Get files for this topic (or all topics for root)
    if topic:
        rows = db.execute('''
            SELECT id, type, original_filename, description, tags, content_text,
                   file_size, created_at, mime_type
            FROM media_items
            WHERE topic = ?
            ORDER BY created_at DESC
        ''', (topic,)).fetchall()
    else:
        # Root VAULT.md - get overview of all topics
        rows = db.execute('''
            SELECT topic, COUNT(*) as count, SUM(file_size) as total_size,
                   GROUP_CONCAT(DISTINCT type) as types,
                   GROUP_CONCAT(description, ' | ') as descriptions
            FROM media_items
            GROUP BY topic
            ORDER BY topic
        ''').fetchall()

    if not rows and topic:
        # Empty folder - create minimal VAULT.md
        vault_content = f"""# {topic}

This folder is empty. Upload files to automatically generate context.

## Purpose
[To be determined based on uploaded content]
"""
    else:
        # Build context for LLM
        vault_content = generate_vault_content(topic, rows, db)

    # Save VAULT.md
    if topic:
        vault_path = FILES_DIR / topic / 'VAULT.md'
    else:
        vault_path = VAULT_DIR / 'VAULT.md'

    vault_path.parent.mkdir(parents=True, exist_ok=True)
    vault_path.write_text(vault_content)

    print(json.dumps({
        'success': True,
        'topic': topic or 'root',
        'path': str(vault_path),
        'size': len(vault_content)
    }))

def generate_vault_content(topic, rows, db):
    """Generate VAULT.md content using LLM."""
    import requests

    groq_api_key = os.environ.get('GROQ_API_KEY', '')

    if topic:
        # Topic-level VAULT.md
        files_context = []
        for row in rows[:50]:  # Limit to 50 most recent files
            file_info = {
                'filename': row['original_filename'],
                'type': row['type'],
                'description': row['description'] or '',
                'tags': row['tags'] or '',
                'size': row['file_size'],
                'date': row['created_at'][:10] if row['created_at'] else ''
            }
            # Include transcript snippet for audio
            if row['content_text']:
                file_info['content_preview'] = row['content_text'][:500]
            files_context.append(file_info)

        prompt = f"""Generate a VAULT.md file for the "{topic}" folder in a personal media vault.

This file serves as context for AI assistants working with these files. Write it to help future AI understand:
- What this folder contains and its purpose
- Key themes and patterns in the content
- How to handle new files added here
- Any notable items or recurring subjects

Files in this folder ({len(rows)} total):
{json.dumps(files_context, indent=2)}

Guidelines:
- Be concise but comprehensive (aim for 500-2000 words)
- Use markdown formatting
- Focus on actionable insights, not just listing files
- Identify patterns and themes
- Suggest how this folder should be organized
- Include a section for user notes (empty, for manual additions)

Generate the VAULT.md content:"""
    else:
        # Root VAULT.md - overview of all topics
        topics_context = []
        for row in rows:
            topics_context.append({
                'topic': row['topic'],
                'file_count': row['count'],
                'total_size_mb': round((row['total_size'] or 0) / 1024 / 1024, 2),
                'file_types': row['types'],
                'sample_descriptions': (row['descriptions'] or '')[:500]
            })

        prompt = f"""Generate a root VAULT.md file for a personal media vault.

This file serves as the master context for AI assistants. Write it to provide:
- Overview of the entire vault structure
- Purpose and organization principles
- Cross-topic patterns and relationships
- Guidelines for file classification

Topics in vault:
{json.dumps(topics_context, indent=2)}

Guidelines:
- Be comprehensive but organized (aim for 1000-3000 words)
- Use markdown formatting with clear sections
- Describe each topic's purpose
- Explain classification logic
- Include guidelines for handling new uploads
- Include a section for user notes (empty, for manual additions)

Generate the VAULT.md content:"""

    # Call Groq LLM
    if not groq_api_key:
        return f"# {topic or 'Media Vault'}\n\n[VAULT.md generation requires GROQ_API_KEY]\n"

    try:
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {groq_api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'llama-3.3-70b-versatile',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 4000,
                'temperature': 0.7
            },
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return f"# {topic or 'Media Vault'}\n\n[Generation failed: {response.status_code}]\n"
    except Exception as e:
        return f"# {topic or 'Media Vault'}\n\n[Generation error: {str(e)}]\n"

def cmd_get_vault_md(args):
    """Get VAULT.md content for a topic or root."""
    topic = args.topic if args.topic else None

    if topic:
        vault_path = FILES_DIR / topic / 'VAULT.md'
    else:
        vault_path = VAULT_DIR / 'VAULT.md'

    if not vault_path.exists():
        print(json.dumps({'exists': False, 'content': None}))
        return

    content = vault_path.read_text()
    print(json.dumps({
        'exists': True,
        'content': content,
        'path': str(vault_path),
        'size': len(content)
    }))

def cmd_save_vault_md(args):
    """Save edited VAULT.md content."""
    import sys
    topic = args.topic if args.topic else None
    content = args.content
    if getattr(args, 'content_stdin', False) and not content:
        content = sys.stdin.read()
    if not content:
        print(json.dumps({'error': 'No content provided (use --content or --content-stdin)'}))
        sys.exit(1)

    if topic:
        vault_path = FILES_DIR / topic / 'VAULT.md'
    else:
        vault_path = VAULT_DIR / 'VAULT.md'

    vault_path.parent.mkdir(parents=True, exist_ok=True)
    vault_path.write_text(content)

    print(json.dumps({
        'success': True,
        'path': str(vault_path),
        'size': len(content)
    }))

def cmd_scan_vault_md(args):
    """Scan all topics and generate missing VAULT.md files."""
    db = get_db()
    generated = []
    skipped = []

    # Get all topics from database
    rows = db.execute('''
        SELECT DISTINCT topic FROM media_items ORDER BY topic
    ''').fetchall()
    db_topics = set(row['topic'] for row in rows)

    # Also check filesystem for empty folders
    if FILES_DIR.exists():
        for d in FILES_DIR.iterdir():
            if d.is_dir():
                db_topics.add(d.name)

    # Check each topic for VAULT.md
    for topic in db_topics:
        vault_path = FILES_DIR / topic / 'VAULT.md'
        if not vault_path.exists():
            # Generate VAULT.md
            try:
                # Get files for this topic
                topic_rows = db.execute('''
                    SELECT id, type, original_filename, description, tags, content_text,
                           file_size, created_at, mime_type
                    FROM media_items
                    WHERE topic = ?
                    ORDER BY created_at DESC
                ''', (topic,)).fetchall()

                if topic_rows:
                    vault_content = generate_vault_content(topic, topic_rows, db)
                else:
                    vault_content = f"""# {topic}

This folder is empty. Upload files to automatically generate context.

## Purpose
[To be determined based on uploaded content]
"""
                vault_path.parent.mkdir(parents=True, exist_ok=True)
                vault_path.write_text(vault_content)
                generated.append(topic)
            except Exception as e:
                skipped.append({'topic': topic, 'error': str(e)})
        else:
            skipped.append({'topic': topic, 'reason': 'exists'})

    # Also check root VAULT.md
    root_vault = VAULT_DIR / 'VAULT.md'
    if not root_vault.exists():
        try:
            # Get overview of all topics
            overview_rows = db.execute('''
                SELECT topic, COUNT(*) as count, SUM(file_size) as total_size,
                       GROUP_CONCAT(DISTINCT type) as types,
                       GROUP_CONCAT(description, ' | ') as descriptions
                FROM media_items
                GROUP BY topic
                ORDER BY topic
            ''').fetchall()

            if overview_rows:
                vault_content = generate_vault_content(None, overview_rows, db)
            else:
                vault_content = """# Media Vault

This vault is empty. Upload files to automatically generate context.
"""
            root_vault.write_text(vault_content)
            generated.append('root')
        except Exception as e:
            skipped.append({'topic': 'root', 'error': str(e)})

    print(json.dumps({
        'generated': generated,
        'skipped': len([s for s in skipped if isinstance(s, dict) and s.get('reason') == 'exists']),
        'errors': [s for s in skipped if isinstance(s, dict) and s.get('error')]
    }))

def cmd_rename(args):
    """Rename a media item's filename."""
    db = get_db()

    new_filename = args.filename

    # Validate filename for security (prevent path traversal)
    if not validate_filename(new_filename):
        print(json.dumps({'error': 'Invalid filename: no path separators or special characters allowed'}))
        sys.exit(1)

    # Get current file info
    row = db.execute(
        'SELECT file_path, stored_filename, topic FROM media_items WHERE id = ?',
        (args.id,)
    ).fetchone()

    if not row:
        print(json.dumps({'error': 'Not found'}))
        sys.exit(1)

    old_filename = row['stored_filename']
    topic = row['topic']

    # Rename file on disk
    old_path = FILES_DIR / topic / old_filename
    new_path = FILES_DIR / topic / new_filename
    new_file_path = f"{topic}/{new_filename}"

    if old_path.exists():
        old_path.rename(new_path)

    # Update database
    db.execute('''
        UPDATE media_items
        SET stored_filename = ?, file_path = ?, updated_at = datetime('now')
        WHERE id = ?
    ''', (new_filename, new_file_path, args.id))
    db.commit()

    print(json.dumps({'id': args.id, 'renamed': True, 'filename': new_filename}))


def cmd_ocr(args):
    """Run OCR on an existing image and update content_text."""
    db = get_db()

    row = db.execute(
        'SELECT file_path, type, content_text FROM media_items WHERE id = ?',
        (args.id,)
    ).fetchone()

    if not row:
        print(json.dumps({'error': 'Not found'}))
        sys.exit(1)

    if row['type'] != 'image':
        print(json.dumps({'error': 'OCR only works on images'}))
        sys.exit(1)

    full_path = FILES_DIR / row['file_path']
    if not full_path.exists():
        print(json.dumps({'error': 'File not found on disk'}))
        sys.exit(1)

    ocr_text = run_ocr(full_path)
    if not ocr_text:
        print(json.dumps({'error': 'OCR failed or no text found'}))
        sys.exit(1)

    # Append or replace content_text
    existing_text = row['content_text'] or ''
    if args.append and existing_text:
        new_text = existing_text + '\n\n[OCR Text]\n' + ocr_text
    else:
        new_text = ocr_text

    db.execute('''
        UPDATE media_items SET content_text = ?, updated_at = datetime('now') WHERE id = ?
    ''', (new_text, args.id))
    db.commit()

    print(json.dumps({
        'id': args.id,
        'ocr_text': ocr_text[:500] + ('...' if len(ocr_text) > 500 else ''),
        'text_length': len(ocr_text)
    }))


def cmd_thumbnail(args):
    """Generate or regenerate thumbnail for a media item."""
    db = get_db()

    row = db.execute(
        'SELECT file_path, mime_type FROM media_items WHERE id = ?',
        (args.id,)
    ).fetchone()

    if not row:
        print(json.dumps({'error': 'Not found'}))
        sys.exit(1)

    full_path = FILES_DIR / row['file_path']
    if not full_path.exists():
        print(json.dumps({'error': 'File not found on disk'}))
        sys.exit(1)

    # Delete existing thumbnail if regenerating
    existing_thumb = THUMBS_DIR / f"{args.id}.jpg"
    if existing_thumb.exists():
        existing_thumb.unlink()

    thumb_path = generate_thumbnail(full_path, args.id, row['mime_type'])

    if thumb_path:
        print(json.dumps({
            'id': args.id,
            'thumbnail': thumb_path,
            'success': True
        }))
    else:
        print(json.dumps({'error': 'Thumbnail generation failed'}))
        sys.exit(1)


def cmd_get_thumbnail(args):
    """Get thumbnail path for a media item."""
    thumb_path = THUMBS_DIR / f"{args.id}.jpg"

    if thumb_path.exists():
        print(json.dumps({
            'id': args.id,
            'thumbnail': str(thumb_path),
            'exists': True
        }))
    else:
        print(json.dumps({
            'id': args.id,
            'exists': False
        }))


def cmd_check_duplicate(args):
    """Check if a file is a duplicate based on its hash."""
    file_path = Path(args.file)

    if not file_path.exists():
        print(json.dumps({'error': 'File not found'}))
        sys.exit(1)

    file_hash = calculate_file_hash(file_path)
    db = get_db()
    duplicate = find_duplicate_by_hash(db, file_hash)

    if duplicate:
        print(json.dumps({
            'is_duplicate': True,
            'file_hash': file_hash,
            'existing_id': duplicate['id'],
            'existing_topic': duplicate['topic'],
            'existing_filename': duplicate['original_filename'],
            'existing_path': duplicate['file_path']
        }))
    else:
        print(json.dumps({
            'is_duplicate': False,
            'file_hash': file_hash
        }))


def cmd_generate_all_thumbnails(args):
    """Generate thumbnails for all media items that don't have one."""
    db = get_db()

    rows = db.execute('''
        SELECT id, file_path, mime_type FROM media_items
        WHERE type IN ('image', 'video') OR mime_type = 'application/pdf'
    ''').fetchall()

    generated = []
    skipped = []
    failed = []

    for row in rows:
        item_id = row['id']
        thumb_path = THUMBS_DIR / f"{item_id}.jpg"

        if thumb_path.exists():
            skipped.append(item_id)
            continue

        full_path = FILES_DIR / row['file_path']
        if not full_path.exists():
            failed.append({'id': item_id, 'reason': 'file not found'})
            continue

        result = generate_thumbnail(full_path, item_id, row['mime_type'])
        if result:
            generated.append(item_id)
        else:
            failed.append({'id': item_id, 'reason': 'generation failed'})

    print(json.dumps({
        'generated': len(generated),
        'skipped': len(skipped),
        'failed': len(failed),
        'failed_items': failed[:10]  # Limit to first 10
    }))

def main():
    parser = argparse.ArgumentParser(description='Media Vault CLI')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Store command
    store_p = subparsers.add_parser('store', help='Store a new media item')
    store_p.add_argument('--type', required=True, choices=['image', 'audio', 'document', 'video'])
    store_p.add_argument('--topic', required=True)
    store_p.add_argument('--original-filename', required=True)
    store_p.add_argument('--stored-filename', required=True)
    store_p.add_argument('--file-size', type=int)
    store_p.add_argument('--mime-type')
    store_p.add_argument('--description')
    store_p.add_argument('--tags')
    store_p.add_argument('--content-text')
    store_p.add_argument('--content-text-stdin', action='store_true',
                         help='Read content-text from stdin instead of argument')
    store_p.add_argument('--content-json')
    store_p.add_argument('--content-json-stdin', action='store_true',
                         help='Read content-json from stdin instead of argument')
    store_p.add_argument('--source', default='assistant')
    store_p.add_argument('--session-id')
    store_p.add_argument('--duration-seconds', type=int)
    store_p.add_argument('--ocr', action='store_true', help='Run OCR on image')
    store_p.add_argument('--check-duplicate', action='store_true', default=True, help='Check for duplicates')
    store_p.add_argument('--allow-duplicate', action='store_true', help='Allow storing duplicate files')

    # Get command
    get_p = subparsers.add_parser('get', help='Get a media item')
    get_p.add_argument('--id', required=True)
    get_p.add_argument('--include-file', action='store_true')

    # Read command (by topic/filename path)
    read_p = subparsers.add_parser('read', help='Read a vault file by topic and filename')
    read_p.add_argument('--topic', required=True, help='Topic name')
    read_p.add_argument('--filename', required=True, help='Filename (stored or original)')

    # Info command (comprehensive file info)
    info_p = subparsers.add_parser('info', help='Get comprehensive file info (dimensions, duration, etc.)')
    info_p.add_argument('--id', required=True, help='Media item ID')

    # Grep command (search with context)
    grep_p = subparsers.add_parser('grep', help='Search file contents with context lines')
    grep_p.add_argument('--pattern', required=True, help='Regex pattern to search')
    grep_p.add_argument('--topic', help='Limit to topic')
    grep_p.add_argument('--type', choices=['image', 'audio', 'document'], help='Limit to type')
    grep_p.add_argument('-A', '--after', type=int, help='Lines after match')
    grep_p.add_argument('-B', '--before', type=int, help='Lines before match')
    grep_p.add_argument('-C', '--context', type=int, help='Lines before and after match')
    grep_p.add_argument('-i', '--ignore-case', action='store_true', help='Case insensitive')
    grep_p.add_argument('--limit', type=int, default=10, help='Max matches per file')

    # Head command (first N lines)
    head_p = subparsers.add_parser('head', help='Read first N lines of a file')
    head_p.add_argument('--id', required=True, help='Media item ID')
    head_p.add_argument('-n', '--lines', type=int, default=10, help='Number of lines')

    # Tail command (last N lines)
    tail_p = subparsers.add_parser('tail', help='Read last N lines of a file')
    tail_p.add_argument('--id', required=True, help='Media item ID')
    tail_p.add_argument('-n', '--lines', type=int, default=10, help='Number of lines')

    # Tree command (directory structure)
    tree_p = subparsers.add_parser('tree', help='Show vault directory tree')
    tree_p.add_argument('--json', action='store_true', help='Output as JSON')

    # Find command (find by filename glob)
    find_p = subparsers.add_parser('find', help='Find files by name pattern (glob)')
    find_p.add_argument('--pattern', required=True, help='Glob pattern (e.g., "*.pdf", "invoice*")')
    find_p.add_argument('--topic', help='Limit to topic')
    find_p.add_argument('--limit', type=int, help='Max results')

    # Wc command (word count)
    wc_p = subparsers.add_parser('wc', help='Word/line/character count')
    wc_p.add_argument('--id', required=True, help='Media item ID')

    # Recent command (recently modified)
    recent_p = subparsers.add_parser('recent', help='Show recently modified files')
    recent_p.add_argument('--topic', help='Limit to topic')
    recent_p.add_argument('--limit', type=int, default=20, help='Number of files')

    # Diff command (compare files)
    diff_p = subparsers.add_parser('diff', help='Compare two vault files')
    diff_p.add_argument('--id1', required=True, help='First file ID')
    diff_p.add_argument('--id2', required=True, help='Second file ID')
    diff_p.add_argument('-u', '--unified', action='store_true', help='Unified diff format')

    # Search command
    search_p = subparsers.add_parser('search', help='Search media items')
    search_p.add_argument('--query', required=True)
    search_p.add_argument('--type', choices=['image', 'audio', 'document'])
    search_p.add_argument('--topic')
    search_p.add_argument('--from-date')
    search_p.add_argument('--to-date')
    search_p.add_argument('--limit', type=int, default=10)

    # List command
    list_p = subparsers.add_parser('list', help='List media items')
    list_p.add_argument('--type', choices=['image', 'audio', 'document'])
    list_p.add_argument('--topic')
    list_p.add_argument('--limit', type=int, default=20)
    list_p.add_argument('--offset', type=int, default=0)

    # Topics command
    topics_p = subparsers.add_parser('topics', help='List existing topics')
    topics_p.add_argument('--counts', action='store_true', help='Include counts and sizes')

    # Create topic command
    create_topic_p = subparsers.add_parser('create-topic', help='Create an empty topic')
    create_topic_p.add_argument('--name', required=True, help='Topic name')

    # Delete topic command
    delete_topic_p = subparsers.add_parser('delete-topic', help='Delete a topic and all its files')
    delete_topic_p.add_argument('--name', required=True, help='Topic name')
    delete_topic_p.add_argument('--force', action='store_true', help='Force delete even if topic has files')

    # Update command
    update_p = subparsers.add_parser('update', help='Update a media item')
    update_p.add_argument('--id', required=True)
    update_p.add_argument('--description')
    update_p.add_argument('--tags')
    update_p.add_argument('--topic')

    # Delete command
    delete_p = subparsers.add_parser('delete', help='Delete a media item')
    delete_p.add_argument('--id', required=True)

    # Move command
    move_p = subparsers.add_parser('move', help='Move item to different topic')
    move_p.add_argument('--id', required=True)
    move_p.add_argument('--topic', required=True, help='Destination topic')

    # Delete bulk command
    delete_bulk_p = subparsers.add_parser('delete-bulk', help='Bulk delete items')
    delete_bulk_p.add_argument('--ids', required=True, help='Comma-separated IDs')

    # Stats command
    subparsers.add_parser('stats', help='Get vault statistics')

    # Rename command
    rename_p = subparsers.add_parser('rename', help='Rename a file')
    rename_p.add_argument('--id', required=True)
    rename_p.add_argument('--filename', required=True)

    # VAULT.md commands
    gen_vault_p = subparsers.add_parser('generate-vault-md', help='Generate VAULT.md for topic')
    gen_vault_p.add_argument('--topic', help='Topic name (omit for root)')

    get_vault_p = subparsers.add_parser('get-vault-md', help='Get VAULT.md content')
    get_vault_p.add_argument('--topic', help='Topic name (omit for root)')

    save_vault_p = subparsers.add_parser('save-vault-md', help='Save VAULT.md content')
    save_vault_p.add_argument('--topic', help='Topic name (omit for root)')
    save_vault_p.add_argument('--content', help='Markdown content')
    save_vault_p.add_argument('--content-stdin', action='store_true',
                              help='Read content from stdin')

    # Scan for missing VAULT.md files
    subparsers.add_parser('scan-vault-md', help='Scan and generate missing VAULT.md files')

    # OCR command
    ocr_p = subparsers.add_parser('ocr', help='Run OCR on an image')
    ocr_p.add_argument('--id', required=True, help='Media item ID')
    ocr_p.add_argument('--append', action='store_true', help='Append to existing content_text')

    # Thumbnail commands
    thumb_p = subparsers.add_parser('thumbnail', help='Generate thumbnail for a media item')
    thumb_p.add_argument('--id', required=True, help='Media item ID')

    get_thumb_p = subparsers.add_parser('get-thumbnail', help='Get thumbnail path for a media item')
    get_thumb_p.add_argument('--id', required=True, help='Media item ID')

    subparsers.add_parser('generate-all-thumbnails', help='Generate thumbnails for all items')

    # Duplicate check command
    dup_p = subparsers.add_parser('check-duplicate', help='Check if a file is a duplicate')
    dup_p.add_argument('--file', required=True, help='Path to file to check')

    args = parser.parse_args()

    commands = {
        'store': cmd_store,
        'get': cmd_get,
        'read': cmd_read,
        'info': cmd_info,
        'grep': cmd_grep,
        'head': cmd_head,
        'tail': cmd_tail,
        'tree': cmd_tree,
        'find': cmd_find,
        'wc': cmd_wc,
        'recent': cmd_recent,
        'diff': cmd_diff,
        'search': cmd_search,
        'list': cmd_list,
        'topics': cmd_topics,
        'create-topic': cmd_create_topic,
        'delete-topic': cmd_delete_topic,
        'update': cmd_update,
        'delete': cmd_delete,
        'move': cmd_move,
        'delete-bulk': cmd_delete_bulk,
        'stats': cmd_stats,
        'rename': cmd_rename,
        'generate-vault-md': cmd_generate_vault_md,
        'get-vault-md': cmd_get_vault_md,
        'save-vault-md': cmd_save_vault_md,
        'scan-vault-md': cmd_scan_vault_md,
        'ocr': cmd_ocr,
        'thumbnail': cmd_thumbnail,
        'get-thumbnail': cmd_get_thumbnail,
        'generate-all-thumbnails': cmd_generate_all_thumbnails,
        'check-duplicate': cmd_check_duplicate,
    }

    commands[args.command](args)

if __name__ == '__main__':
    main()
