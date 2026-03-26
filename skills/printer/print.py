#!/usr/bin/env python3
"""OpenClaw Printer Skill — Print to a network printer via IPP."""

import argparse
import http.client
import os
import struct
import sys
import tempfile
import textwrap

# ── Configuration ──

PRINTER_IP = os.environ.get("PRINTER_IP", "192.168.1.200")
PRINTER_PORT = int(os.environ.get("PRINTER_PORT", "631"))
PRINTER_PATH = os.environ.get("PRINTER_PATH", "/ipp/print")
PRINTER_URI = f"ipp://{PRINTER_IP}:{PRINTER_PORT}{PRINTER_PATH}"

# ── IPP Constants ──

IPP_PRINT_JOB = 0x0002
IPP_CANCEL_JOB = 0x0008
IPP_GET_JOBS = 0x000A
IPP_GET_PRINTER_ATTRS = 0x000B

TAG_OPERATION = 0x01
TAG_JOB = 0x02
TAG_END = 0x03
TAG_PRINTER = 0x04

VT_INTEGER = 0x21
VT_BOOLEAN = 0x22
VT_ENUM = 0x23
VT_TEXT = 0x41
VT_NAME = 0x42
VT_KEYWORD = 0x44
VT_URI = 0x45
VT_CHARSET = 0x47
VT_LANGUAGE = 0x48
VT_MIME = 0x49

PRINTER_STATES = {3: "idle", 4: "processing", 5: "stopped"}
JOB_STATES = {
    3: "pending", 4: "pending-held", 5: "processing",
    6: "processing-stopped", 7: "canceled", 8: "aborted", 9: "completed",
}

MIME_MAP = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".txt": "text/plain",
    ".text": "text/plain",
    ".ps": "application/postscript",
}


# ── IPP Protocol ──

def _encode_attr(value_tag, name, value):
    """Encode a single IPP attribute."""
    name_bytes = name.encode("ascii") if name else b""
    if value_tag in (VT_INTEGER, VT_ENUM):
        val_bytes = struct.pack(">i", value)
    elif value_tag == VT_BOOLEAN:
        val_bytes = bytes([1 if value else 0])
    else:
        val_bytes = value.encode("utf-8") if isinstance(value, str) else value
    return (
        struct.pack(">b", value_tag)
        + struct.pack(">H", len(name_bytes))
        + name_bytes
        + struct.pack(">H", len(val_bytes))
        + val_bytes
    )


def _encode_request(operation, request_id, op_attrs, job_attrs=None, document=None):
    """Build a complete IPP request."""
    data = struct.pack(">HHI", 0x0200, operation, request_id)

    # Operation attributes group (always required)
    data += struct.pack(">b", TAG_OPERATION)
    data += _encode_attr(VT_CHARSET, "attributes-charset", "utf-8")
    data += _encode_attr(VT_LANGUAGE, "attributes-natural-language", "en")
    data += _encode_attr(VT_URI, "printer-uri", PRINTER_URI)
    for vt, name, val in op_attrs:
        data += _encode_attr(vt, name, val)

    # Job attributes group (optional)
    if job_attrs:
        data += struct.pack(">b", TAG_JOB)
        for vt, name, val in job_attrs:
            data += _encode_attr(vt, name, val)

    data += struct.pack(">b", TAG_END)

    if document is not None:
        data += document

    return data


def _decode_response(data):
    """Decode an IPP response into status and attribute groups."""
    if len(data) < 8:
        return {"status": -1, "groups": []}

    status = struct.unpack(">H", data[2:4])[0]
    groups = []
    current_attrs = {}
    current_name = None
    offset = 8

    while offset < len(data):
        tag = data[offset]
        offset += 1

        if tag in (TAG_OPERATION, TAG_JOB, TAG_PRINTER):
            if current_attrs:
                groups.append(current_attrs)
            current_attrs = {}
            continue

        if tag == TAG_END:
            if current_attrs:
                groups.append(current_attrs)
            break

        # Value tag — read name and value
        if offset + 2 > len(data):
            break
        name_len = struct.unpack(">H", data[offset:offset + 2])[0]
        offset += 2

        if name_len > 0:
            current_name = data[offset:offset + name_len].decode("ascii", errors="replace")
        offset += name_len

        if offset + 2 > len(data):
            break
        val_len = struct.unpack(">H", data[offset:offset + 2])[0]
        offset += 2

        raw = data[offset:offset + val_len]
        offset += val_len

        # Decode value
        if tag in (VT_INTEGER, VT_ENUM) and len(raw) == 4:
            value = struct.unpack(">i", raw)[0]
        elif tag == VT_BOOLEAN and len(raw) == 1:
            value = raw[0] != 0
        else:
            value = raw.decode("utf-8", errors="replace")

        if current_name:
            if current_name in current_attrs:
                existing = current_attrs[current_name]
                if isinstance(existing, list):
                    existing.append(value)
                else:
                    current_attrs[current_name] = [existing, value]
            else:
                current_attrs[current_name] = value

    return {"status": status, "groups": groups}


def _send_ipp(operation, op_attrs=None, job_attrs=None, document=None):
    """Send an IPP request and return the decoded response."""
    op_attrs = op_attrs or []
    req_data = _encode_request(operation, 1, op_attrs, job_attrs, document)
    try:
        conn = http.client.HTTPConnection(PRINTER_IP, PRINTER_PORT, timeout=15)
        conn.request(
            "POST", PRINTER_PATH,
            body=req_data,
            headers={"Content-Type": "application/ipp"},
        )
        resp = conn.getresponse()
        resp_data = resp.read()
        conn.close()
        return _decode_response(resp_data)
    except Exception as e:
        print(f"ERROR: Could not reach printer at {PRINTER_IP}:{PRINTER_PORT}: {e}",
              file=sys.stderr)
        sys.exit(1)


# ── Text to PDF ──

def _text_to_pdf(text):
    """Convert plain text to a multi-page PDF using matplotlib."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    # Wrap long lines and split into pages
    wrapped_lines = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            wrapped_lines.append("")
        else:
            wrapped_lines.extend(textwrap.fill(paragraph, width=90).split("\n"))

    lines_per_page = 55
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)

    try:
        with PdfPages(tmp.name) as pdf:
            for page_start in range(0, max(len(wrapped_lines), 1), lines_per_page):
                page_lines = wrapped_lines[page_start:page_start + lines_per_page]
                page_text = "\n".join(page_lines)

                fig, ax = plt.subplots(figsize=(8.5, 11))
                ax.text(
                    0.05, 0.95, page_text,
                    transform=ax.transAxes,
                    fontsize=10,
                    verticalalignment="top",
                    fontfamily="monospace",
                )
                ax.axis("off")
                fig.subplots_adjust(left=0.08, right=0.95, top=0.95, bottom=0.05)
                pdf.savefig(fig)
                plt.close(fig)

        with open(tmp.name, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp.name)


# ── Commands ──

def cmd_status(_args):
    """Show printer status."""
    resp = _send_ipp(IPP_GET_PRINTER_ATTRS)

    if resp["status"] != 0:
        print(f"ERROR: Printer returned IPP status 0x{resp['status']:04x}", file=sys.stderr)
        sys.exit(1)

    attrs = {}
    for g in resp["groups"]:
        attrs.update(g)

    state = attrs.get("printer-state", "unknown")
    state_str = PRINTER_STATES.get(state, str(state))
    reasons = attrs.get("printer-state-reasons", "none")
    name = attrs.get("printer-name", "Epson WF-7820")
    make = attrs.get("printer-make-and-model", "Epson WF-7820")

    if isinstance(reasons, list):
        reasons = ", ".join(str(r) for r in reasons)

    print(f"Printer:  {name}")
    print(f"Model:    {make}")
    print(f"State:    {state_str}")
    print(f"Reasons:  {reasons}")
    print(f"Address:  {PRINTER_IP}")


def cmd_print_file(args):
    """Print a file (PDF, JPEG, PNG, or text)."""
    filepath = args.file
    if not os.path.isfile(filepath):
        print(f"ERROR: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    mime = MIME_MAP.get(os.path.splitext(filepath)[1].lower(), "application/octet-stream")

    # For text files, convert to PDF for reliable rendering
    if mime == "text/plain":
        with open(filepath, "r") as f:
            text = f.read()
        doc_data = _text_to_pdf(text)
        mime = "application/pdf"
    else:
        with open(filepath, "rb") as f:
            doc_data = f.read()

    job_name = os.path.basename(filepath)
    copies = args.copies or 1

    op_attrs = [
        (VT_NAME, "job-name", job_name),
        (VT_MIME, "document-format", mime),
        (VT_NAME, "requesting-user-name", "clawdbot"),
    ]
    job_attrs = []
    if copies > 1:
        job_attrs.append((VT_INTEGER, "copies", copies))
    if args.color is False:
        job_attrs.append((VT_KEYWORD, "print-color-mode", "monochrome"))

    resp = _send_ipp(IPP_PRINT_JOB, op_attrs, job_attrs or None, doc_data)

    if resp["status"] != 0:
        msg = ""
        for g in resp["groups"]:
            if "status-message" in g:
                msg = f" — {g['status-message']}"
        print(f"ERROR: Print failed (IPP status 0x{resp['status']:04x}{msg})", file=sys.stderr)
        sys.exit(1)

    job_id = None
    for g in resp["groups"]:
        if "job-id" in g:
            job_id = g["job-id"]
            break

    print(f"Print job submitted: {job_name}")
    print(f"Format:  {mime}")
    print(f"Copies:  {copies}")
    if job_id:
        print(f"Job ID:  {job_id}")


def cmd_print_text(args):
    """Print text content (converted to PDF)."""
    text = args.text
    if text == "-":
        text = sys.stdin.read()

    pdf_data = _text_to_pdf(text)
    copies = args.copies or 1

    op_attrs = [
        (VT_NAME, "job-name", "text-document"),
        (VT_MIME, "document-format", "application/pdf"),
        (VT_NAME, "requesting-user-name", "clawdbot"),
    ]
    job_attrs = []
    if copies > 1:
        job_attrs.append((VT_INTEGER, "copies", copies))
    if args.color is False:
        job_attrs.append((VT_KEYWORD, "print-color-mode", "monochrome"))

    resp = _send_ipp(IPP_PRINT_JOB, op_attrs, job_attrs or None, pdf_data)

    if resp["status"] != 0:
        print(f"ERROR: Print failed (IPP status 0x{resp['status']:04x})", file=sys.stderr)
        sys.exit(1)

    job_id = None
    for g in resp["groups"]:
        if "job-id" in g:
            job_id = g["job-id"]
            break

    print(f"Text printed ({len(text)} chars, {len(pdf_data)} bytes PDF)")
    if job_id:
        print(f"Job ID:  {job_id}")


def cmd_queue(_args):
    """Show print queue."""
    resp = _send_ipp(IPP_GET_JOBS)

    if resp["status"] != 0:
        print(f"ERROR: Could not get jobs (IPP status 0x{resp['status']:04x})", file=sys.stderr)
        sys.exit(1)

    job_groups = [g for g in resp["groups"] if "job-id" in g]
    if not job_groups:
        print("No active print jobs.")
        return

    for g in job_groups:
        jid = g.get("job-id", "?")
        name = g.get("job-name", "unknown")
        state = g.get("job-state", 0)
        state_str = JOB_STATES.get(state, str(state))
        user = g.get("job-originating-user-name", "")
        print(f"  Job {jid}: {name} [{state_str}] (user: {user})")


def cmd_cancel(args):
    """Cancel a print job."""
    op_attrs = [
        (VT_INTEGER, "job-id", args.job_id),
        (VT_NAME, "requesting-user-name", "clawdbot"),
    ]
    resp = _send_ipp(IPP_CANCEL_JOB, op_attrs)

    if resp["status"] != 0:
        print(f"ERROR: Cancel failed (IPP status 0x{resp['status']:04x})", file=sys.stderr)
        sys.exit(1)

    print(f"Job {args.job_id} cancelled.")


# ── CLI ──

def main():
    parser = argparse.ArgumentParser(description="Print to Epson WF-7820 via IPP")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show printer status")

    p_print = sub.add_parser("print", help="Print a file (PDF, JPEG, PNG)")
    p_print.add_argument("file", help="Path to file")
    p_print.add_argument("--copies", type=int, default=1, help="Number of copies")
    p_print.add_argument("--no-color", dest="color", action="store_false",
                         default=True, help="Print in monochrome")

    p_text = sub.add_parser("text", help="Print text content (converted to PDF)")
    p_text.add_argument("text", help="Text to print (use '-' for stdin)")
    p_text.add_argument("--copies", type=int, default=1, help="Number of copies")
    p_text.add_argument("--no-color", dest="color", action="store_false",
                         default=True, help="Print in monochrome")

    sub.add_parser("queue", help="Show print queue")

    p_cancel = sub.add_parser("cancel", help="Cancel a print job")
    p_cancel.add_argument("job_id", type=int, help="Job ID to cancel")

    args = parser.parse_args()
    cmds = {
        "status": cmd_status,
        "print": cmd_print_file,
        "text": cmd_print_text,
        "queue": cmd_queue,
        "cancel": cmd_cancel,
    }
    cmds[args.command](args)


if __name__ == "__main__":
    main()
