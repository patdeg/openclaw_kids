# Local AI — On-Device Intelligence

Run AI models locally on the Orange Pi's GPU (Immortalis-G720), NPU, and CPU — no cloud API calls, no latency, no cost per token.

## Capabilities

- **Speech-to-Text** — Whisper (small/medium) transcribes audio files locally
- **LLM Chat** — Qwen2.5-7B via llama.cpp with Vulkan GPU acceleration
- **Object Detection** — YOLOX-M identifies objects in images (80 COCO classes)
- **List Models** — Show what's available on this machine

## Credentials

None required — all models run locally.

## Runtime

The script uses a dedicated Python venv at `/opt/ai/venv/` with onnxruntime, torch, transformers, and opencv.
LLM chat uses `/usr/share/cix/bin/llama-cli-vulkan` (or CPU fallback) with GGUF models in `/opt/ai/models/gguf/`.

```bash
# Run any command:
/opt/ai/venv/bin/python3 local_ai.py <command> [args]

# Or directly (shebang points to venv):
./local_ai.py <command> [args]
```

## Commands

### Transcribe Audio (Whisper)

Convert speech in an audio file to text. Supports WAV, MP3, FLAC, OGG, M4A.

```bash
/opt/ai/venv/bin/python3 local_ai.py transcribe --audio /path/to/audio.wav
```

Use `--model medium` for higher accuracy (slower), default is `small`:

```bash
python3 local_ai.py transcribe --audio /path/to/audio.wav --model medium
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--audio` | string | required | Path to the audio file |
| `--model` | enum | `small` | `tiny`, `small`, or `medium` |

Output: plain text transcription to stdout.

### Local LLM Chat

Ask a question to the local Qwen2.5-7B model. Runs on the Vulkan GPU — no API key needed. Good for quick tasks, offline fallback, or privacy-sensitive queries.

```bash
python3 local_ai.py chat --prompt "Summarize the key points of the family calendar for this week"
```

Control output length and creativity:

```bash
python3 local_ai.py chat --prompt "Write a haiku about coding" --max-tokens 100 --temperature 0.9
```

Use a system prompt for role-playing:

```bash
python3 local_ai.py chat --prompt "What should I buy?" --system "You are a helpful investment advisor"
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--prompt` | string | required | The user message / question |
| `--system` | string | `""` | Optional system prompt |
| `--max-tokens` | int | `512` | Maximum tokens to generate |
| `--temperature` | float | `0.7` | Sampling temperature (0.0-2.0) |
| `--model` | string | auto | Path to GGUF model (auto-detects installed models) |

Output: generated text to stdout.

### Detect Objects in Images

Identify objects in a photo using YOLOX-M. Returns a JSON list of detected objects with labels, confidence scores, and bounding boxes.

```bash
python3 local_ai.py detect --image /path/to/photo.jpg
```

Adjust confidence threshold:

```bash
python3 local_ai.py detect --image /path/to/photo.jpg --confidence 0.5
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--image` | string | required | Path to the image file |
| `--confidence` | float | `0.3` | Minimum confidence threshold (0.0-1.0) |
| `--save` | string | `""` | Path to save annotated image (optional) |

Output: JSON array of detections:
```json
[
  {"label": "person", "confidence": 0.92, "bbox": [100, 50, 300, 400]},
  {"label": "dog", "confidence": 0.87, "bbox": [320, 200, 500, 450]}
]
```

### List Available Models

Show what local AI models are installed and ready to use:

```bash
python3 local_ai.py models
```

Output: table of installed models with type, size, and status.

## When To Use

| User intent | Command |
|-------------|---------|
| "Transcribe this voice message" | `transcribe --audio <file>` |
| "What did I say in this recording?" | `transcribe --audio <file>` |
| "Ask the local AI to..." | `chat --prompt "..."` |
| "Without using the cloud, ..." | `chat --prompt "..."` |
| "What objects are in this photo?" | `detect --image <file>` |
| "Tag this image" | `detect --image <file>` |
| "What local models do we have?" | `models` |

## Response Format

### Good
> Transcription of your voice message:
> "Hey, can you pick up milk on the way home? Also, don't forget your kid's practice is at 4pm."

### Bad
> [50258, 50260, 50359, 50363, 1230, ...] decoder output tokens raw array

### Good
> I found 3 objects in the photo:
> - **Person** (92% confidence) — center of frame
> - **Dog** (87% confidence) — right side
> - **Bicycle** (74% confidence) — background

### Bad
> [[0.92, 100, 50, 300, 400, 0], [0.87, 320, 200, 500, 450, 16]]

## Notes

- Whisper transcription runs on CPU/NPU. A 1-minute audio clip takes ~10-15 seconds with `small`, ~25-30 seconds with `medium`.
- LLM chat uses Vulkan GPU acceleration. Expect ~8-12 tokens/second for the 7B model.
- Object detection runs on CPU via ONNX Runtime. Processing takes 2-5 seconds per image.
- All processing is fully local — nothing leaves the device.
