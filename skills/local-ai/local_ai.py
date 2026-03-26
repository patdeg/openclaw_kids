#!/opt/ai/venv/bin/python3
"""
Local AI skill — on-device inference via llama.cpp (Vulkan GPU) and ONNX models.

Subcommands:
  transcribe  — Speech-to-text via Whisper ONNX
  chat        — LLM generation via llama.cpp with Vulkan backend
  detect      — Object detection via YOLOX-M ONNX
  models      — List available local models
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

# ── Paths ────────────────────────────────────────────────────────────────────
MODEL_HUB = os.environ.get("AI_MODEL_HUB", "/opt/ai/ai_model_hub_25_Q3")
GGUF_DIR = os.environ.get("GGUF_DIR", "/opt/ai/models/gguf")
LLAMA_CLI = os.environ.get("LLAMA_CLI", "/usr/share/cix/bin/llama-cli-vulkan")
LLAMA_SERVER = os.environ.get("LLAMA_SERVER", "/usr/share/cix/bin/llama-server-vulkan")

WHISPER_MODELS = {
    "tiny": os.path.join(MODEL_HUB, "models/Audio/Speech_Recognotion/onnx_whisper_tiny_multi_language"),
    "small": os.path.join(MODEL_HUB, "models/Audio/Speech_Recognotion/onnx_whisper_small_multi_language"),
    "medium": os.path.join(MODEL_HUB, "models/Audio/Speech_Recognotion/onnx_whisper_medium_multilingual"),
}

YOLOX_MODEL = os.path.join(MODEL_HUB, "models/ComputeVision/Object_Detection/onnx_yolox_m/model/yolox_m.onnx")

COCO_CLASSES = (
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
    "truck", "boat", "traffic light", "fire hydrant", "stop sign",
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag",
    "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite",
    "baseball bat", "baseball glove", "skateboard", "surfboard",
    "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon",
    "bowl", "banana", "apple", "sandwich", "orange", "broccoli", "carrot",
    "hot dog", "pizza", "donut", "cake", "chair", "couch", "potted plant",
    "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote",
    "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
    "hair drier", "toothbrush",
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def find_gguf_model(explicit_path=None):
    """Find the best available GGUF model."""
    if explicit_path and os.path.isfile(explicit_path):
        return explicit_path
    if not os.path.isdir(GGUF_DIR):
        return None
    # Prefer larger models, prefer Q4_K_M quantization
    models = sorted(
        [f for f in os.listdir(GGUF_DIR) if f.endswith(".gguf")],
        key=lambda f: os.path.getsize(os.path.join(GGUF_DIR, f)),
        reverse=True,
    )
    if models:
        return os.path.join(GGUF_DIR, models[0])
    return None


def audio_to_wav16k(input_path):
    """Convert any audio file to 16kHz mono WAV via ffmpeg, return temp path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    subprocess.run(
        ["ffmpeg", "-y", "-nostdin", "-threads", "0", "-i", input_path,
         "-ar", "16000", "-ac", "1", "-acodec", "pcm_s16le", tmp.name],
        capture_output=True, check=True,
    )
    return tmp.name


# ── Transcribe (Whisper) ─────────────────────────────────────────────────────

def cmd_transcribe(args):
    """Transcribe audio using Whisper ONNX model."""
    import numpy as np

    model_name = args.model
    model_dir = WHISPER_MODELS.get(model_name)
    if not model_dir or not os.path.isdir(model_dir):
        print(f"Error: Whisper model '{model_name}' not found at {model_dir}", file=sys.stderr)
        sys.exit(1)

    audio_path = args.audio
    if not os.path.isfile(audio_path):
        print(f"Error: Audio file not found: {audio_path}", file=sys.stderr)
        sys.exit(1)

    # Convert to 16kHz WAV
    wav_path = audio_to_wav16k(audio_path)

    try:
        import onnxruntime as ort
        import torch
        import torch.nn.functional as F
        from transformers import WhisperProcessor
        from transformers.generation.logits_process import (
            SuppressTokensLogitsProcessor,
            SuppressTokensAtBeginLogitsProcessor,
        )
        from transformers.generation.stopping_criteria import (
            MaxLengthCriteria,
            EosTokenCriteria,
        )

        # Load audio as float32
        raw = np.fromfile(wav_path, dtype=np.int16).astype(np.float32) / 32768.0

        # Pad or trim to 30 seconds (480000 samples at 16kHz)
        target_len = 480000
        if len(raw) > target_len:
            raw = raw[:target_len]
        elif len(raw) < target_len:
            raw = np.pad(raw, (0, target_len - len(raw)))

        # Log-mel spectrogram
        audio_tensor = torch.from_numpy(raw)
        window = torch.hann_window(400)
        stft = torch.stft(audio_tensor, 400, 160, window=window, return_complex=True)
        magnitudes = stft[..., :-1].abs() ** 2

        filters_path = os.path.join(model_dir, "scripts/filters_16000_80.npy")
        filters = torch.from_numpy(np.load(filters_path))
        mel_spec = filters @ magnitudes
        log_spec = torch.clamp(mel_spec, min=1e-10).log10()
        log_spec = torch.maximum(log_spec, log_spec.max() - 8.0)
        log_spec = (log_spec + 4.0) / 4.0
        audio_input = log_spec.unsqueeze(0).detach().cpu().numpy()

        # Determine model file prefix based on model name
        model_prefix = f"whisper_{model_name}"
        if model_name == "medium":
            model_prefix = "whisper_medium"
        encoder_path = os.path.join(model_dir, f"model/{model_prefix}_multilang_encoder.onnx")
        decoder_path = os.path.join(model_dir, f"model/{model_prefix}_multilang_decoder.onnx")

        # Fallback: search for encoder/decoder ONNX files
        if not os.path.isfile(encoder_path):
            model_files = os.path.join(model_dir, "model")
            for f in os.listdir(model_files):
                if "encoder" in f and f.endswith(".onnx"):
                    encoder_path = os.path.join(model_files, f)
                elif "decoder" in f and f.endswith(".onnx"):
                    decoder_path = os.path.join(model_files, f)

        # Encoder
        encoder_session = ort.InferenceSession(encoder_path)
        input_name = encoder_session.get_inputs()[0].name
        hidden = encoder_session.run(None, {input_name: audio_input})[0]

        # Decoder (autoregressive)
        decoder_session = ort.InferenceSession(decoder_path)
        # Start tokens: <|startoftranscript|><|en|><|transcribe|><|notimestamps|>
        decoder_input_ids = np.array([50258, 50259, 50359, 50363], dtype=np.int64).reshape(1, -1)
        decoder_input_ids = torch.from_numpy(decoder_input_ids)

        # Suppress tokens
        suppress_path = os.path.join(model_dir, "scripts/suppress_tokens.npy")
        attn_mask_path = os.path.join(model_dir, "scripts/attn_mask_decoder.npy")

        begin_suppress = SuppressTokensAtBeginLogitsProcessor([220, 50257], begin_index=4)
        suppress_tokens = SuppressTokensLogitsProcessor(np.load(suppress_path).tolist())
        max_length_criteria = MaxLengthCriteria(max_length=448, max_position_embeddings=None)
        eos_criteria = EosTokenCriteria(eos_token_id=torch.tensor([50257], dtype=torch.int64))

        # Processor for decoding tokens — find the processor directory
        processor_dir = os.path.join(model_dir, f"whisper-{model_name}")
        if not os.path.isdir(processor_dir):
            # Try alternative names (e.g., whisper-tiny-multi)
            for d in os.listdir(model_dir):
                if d.startswith(f"whisper-{model_name}") and os.path.isdir(os.path.join(model_dir, d)):
                    processor_dir = os.path.join(model_dir, d)
                    break
        processor = WhisperProcessor.from_pretrained(processor_dir)

        # Determine decoder sequence length from the ONNX model input shape
        decoder_seq_len = decoder_session.get_inputs()[0].shape[1]
        if isinstance(decoder_seq_len, str) or decoder_seq_len is None:
            decoder_seq_len = 448  # fallback for dynamic shapes
        real_len = decoder_input_ids.shape[1]
        decoder_buf = np.zeros((1, decoder_seq_len), dtype=np.int64)
        decoder_buf[0, :real_len] = decoder_input_ids[0, :].numpy()

        input_dicts = {}
        input_dicts[decoder_session.get_inputs()[1].name] = hidden
        input_dicts[decoder_session.get_inputs()[2].name] = np.load(attn_mask_path)

        while True:
            input_dicts[decoder_session.get_inputs()[0].name] = decoder_buf
            scores = decoder_session.run(None, input_dicts)[0]
            scores = scores[:, real_len - 1, :]
            scores = torch.from_numpy(scores)

            scores = suppress_tokens(decoder_input_ids, scores)
            scores = begin_suppress(decoder_input_ids, scores)
            next_tokens = torch.argmax(scores, dim=-1)
            decoder_input_ids = torch.cat([decoder_input_ids, next_tokens[:, None]], dim=-1)

            is_done = max_length_criteria(decoder_input_ids, scores)
            is_done = is_done | eos_criteria(decoder_input_ids, scores)
            if is_done.max():
                break

            real_len = decoder_input_ids.shape[1]
            if real_len >= 256:
                break
            decoder_buf[0, :real_len] = decoder_input_ids[0, :].numpy()

        transcription = processor.batch_decode(decoder_input_ids, skip_special_tokens=True)
        print(transcription[0].strip())
    finally:
        os.unlink(wav_path)


# ── Chat (llama.cpp) ─────────────────────────────────────────────────────────

def cmd_chat(args):
    """Run LLM inference via llama.cpp with Vulkan backend."""
    model_path = find_gguf_model(args.model)
    if not model_path:
        print("Error: No GGUF model found. Download one to /opt/ai/models/gguf/", file=sys.stderr)
        print("  Example: curl -L -o /opt/ai/models/gguf/qwen2.5-7b-instruct-q4_k_m.gguf \\", file=sys.stderr)
        print("    https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf", file=sys.stderr)
        sys.exit(1)

    if not os.path.isfile(LLAMA_CLI):
        print(f"Error: llama-cli not found at {LLAMA_CLI}", file=sys.stderr)
        sys.exit(1)

    # Build prompt with ChatML template
    if args.system:
        prompt = f"<|im_start|>system\n{args.system}<|im_end|>\n<|im_start|>user\n{args.prompt}<|im_end|>\n<|im_start|>assistant\n"
    else:
        prompt = f"<|im_start|>user\n{args.prompt}<|im_end|>\n<|im_start|>assistant\n"

    # The model echoes the prompt. The last "assistant\n" marks where generation starts.
    sentinel = "assistant\n"

    cmd = [
        LLAMA_CLI,
        "--model", model_path,
        "--ctx-size", "4096",
        "--predict", str(args.max_tokens),
        "--temp", str(args.temperature),
        "--no-conversation",
        "-p", prompt,
    ]

    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, timeout=300,
    )

    raw_output = result.stdout

    # Extract only the assistant response (after the last sentinel)
    if sentinel in raw_output:
        output = raw_output.split(sentinel)[-1].strip()
    else:
        output = raw_output.strip()

    # Remove trailing special tokens and EOS markers
    for token in ["<|im_end|>", "<|endoftext|>", "[end of text]"]:
        if output.endswith(token):
            output = output[: -len(token)].strip()

    print(output)

    if result.returncode != 0 and not output:
        print(f"Error: llama-cli exited with code {result.returncode}", file=sys.stderr)
        if result.stderr:
            for line in result.stderr.split("\n"):
                if "error" in line.lower() or "fail" in line.lower():
                    print(line, file=sys.stderr)
        sys.exit(1)


# ── Detect (YOLOX) ───────────────────────────────────────────────────────────

def cmd_detect(args):
    """Detect objects in an image using YOLOX-M ONNX model."""
    import numpy as np

    if not os.path.isfile(args.image):
        print(f"Error: Image file not found: {args.image}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isfile(YOLOX_MODEL):
        print(f"Error: YOLOX model not found at {YOLOX_MODEL}", file=sys.stderr)
        sys.exit(1)

    try:
        import onnxruntime as ort
        import cv2
    except ImportError as e:
        print(f"Error: Missing dependency: {e}", file=sys.stderr)
        print("Install with: pip install onnxruntime opencv-python-headless", file=sys.stderr)
        sys.exit(1)

    # Load and preprocess image
    img = cv2.imread(args.image)
    if img is None:
        print(f"Error: Could not read image: {args.image}", file=sys.stderr)
        sys.exit(1)

    src_h, src_w = img.shape[:2]
    input_size = (640, 640)

    # Resize preserving aspect ratio, pad with gray (114)
    ratio = min(input_size[0] / src_h, input_size[1] / src_w)
    new_h, new_w = int(src_h * ratio), int(src_w * ratio)
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    padded = np.full((input_size[0], input_size[1], 3), 114, dtype=np.uint8)
    padded[:new_h, :new_w, :] = resized

    # HWC -> NCHW, float32
    data = padded.transpose(2, 0, 1).astype(np.float32)
    data = np.expand_dims(data, axis=0)

    # Run inference
    session = ort.InferenceSession(YOLOX_MODEL)
    input_name = session.get_inputs()[0].name
    output = session.run(None, {input_name: data})

    # Post-process YOLOX output
    predictions = output[0]  # shape: (1, num_boxes, 85)

    # Decode YOLOX grid predictions
    grids = []
    expanded_strides = []
    strides = [8, 16, 32]
    for stride in strides:
        h_grid = input_size[0] // stride
        w_grid = input_size[1] // stride
        xv, yv = np.meshgrid(np.arange(w_grid), np.arange(h_grid))
        grid = np.stack((xv, yv), 2).reshape(1, -1, 2)
        grids.append(grid)
        expanded_strides.append(np.full((*grid.shape[:2], 1), stride))

    grids = np.concatenate(grids, 1)
    expanded_strides = np.concatenate(expanded_strides, 1)
    predictions[..., :2] = (predictions[..., :2] + grids) * expanded_strides
    predictions[..., 2:4] = np.exp(predictions[..., 2:4]) * expanded_strides

    # Extract detections
    conf_threshold = args.confidence
    detections = []

    for i in range(predictions.shape[1]):
        box = predictions[0, i]
        obj_conf = box[4]
        if obj_conf < conf_threshold:
            continue

        class_scores = box[5:] * obj_conf
        class_id = int(np.argmax(class_scores))
        score = float(class_scores[class_id])

        if score < conf_threshold:
            continue

        # Convert from center format to corner format and rescale
        cx, cy, w, h = box[:4]
        x1 = (cx - w / 2) / ratio
        y1 = (cy - h / 2) / ratio
        x2 = (cx + w / 2) / ratio
        y2 = (cy + h / 2) / ratio

        # Clip to image bounds
        x1 = max(0, min(src_w, x1))
        y1 = max(0, min(src_h, y1))
        x2 = max(0, min(src_w, x2))
        y2 = max(0, min(src_h, y2))

        label = COCO_CLASSES[class_id] if class_id < len(COCO_CLASSES) else f"class_{class_id}"
        detections.append({
            "label": label,
            "confidence": round(score, 3),
            "bbox": [int(x1), int(y1), int(x2), int(y2)],
        })

    # NMS — simple greedy NMS by class
    nms_threshold = 0.45
    final = []
    detections.sort(key=lambda d: d["confidence"], reverse=True)
    used = [False] * len(detections)
    for i, det_i in enumerate(detections):
        if used[i]:
            continue
        final.append(det_i)
        for j in range(i + 1, len(detections)):
            if used[j] or detections[j]["label"] != det_i["label"]:
                continue
            # IoU check
            bx1 = max(det_i["bbox"][0], detections[j]["bbox"][0])
            by1 = max(det_i["bbox"][1], detections[j]["bbox"][1])
            bx2 = min(det_i["bbox"][2], detections[j]["bbox"][2])
            by2 = min(det_i["bbox"][3], detections[j]["bbox"][3])
            inter = max(0, bx2 - bx1) * max(0, by2 - by1)
            area_i = (det_i["bbox"][2] - det_i["bbox"][0]) * (det_i["bbox"][3] - det_i["bbox"][1])
            area_j = (detections[j]["bbox"][2] - detections[j]["bbox"][0]) * (detections[j]["bbox"][3] - detections[j]["bbox"][1])
            union = area_i + area_j - inter
            if union > 0 and inter / union > nms_threshold:
                used[j] = True

    # Save annotated image if requested
    if args.save:
        annotated = img.copy()
        for det in final:
            x1, y1, x2, y2 = det["bbox"]
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label_text = f"{det['label']} {det['confidence']:.0%}"
            cv2.putText(annotated, label_text, (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.imwrite(args.save, annotated)

    print(json.dumps(final, indent=2))


# ── Models ───────────────────────────────────────────────────────────────────

def cmd_models(args):
    """List available local AI models."""
    print("=== Local AI Models ===\n")

    # Whisper models
    print("Speech-to-Text (Whisper ONNX):")
    for name, path in sorted(WHISPER_MODELS.items()):
        exists = os.path.isdir(path)
        size = ""
        if exists:
            total = sum(
                os.path.getsize(os.path.join(dp, f))
                for dp, _, files in os.walk(path)
                for f in files
            )
            size = f" ({total / 1e9:.1f} GB)"
        status = "ready" if exists else "NOT FOUND"
        print(f"  {name:8s} [{status}]{size}")

    # GGUF models
    print("\nLLM (llama.cpp + Vulkan GPU):")
    llama_ok = os.path.isfile(LLAMA_CLI)
    print(f"  Runtime: {'ready' if llama_ok else 'NOT FOUND'} ({LLAMA_CLI})")

    if os.path.isdir(GGUF_DIR):
        gguf_files = [f for f in os.listdir(GGUF_DIR) if f.endswith(".gguf")]
        if gguf_files:
            for f in sorted(gguf_files):
                size = os.path.getsize(os.path.join(GGUF_DIR, f))
                print(f"  {f:50s} ({size / 1e9:.1f} GB) [ready]")
        else:
            print("  No GGUF models downloaded")
    else:
        print(f"  Model directory not found: {GGUF_DIR}")

    # YOLOX
    print("\nObject Detection (YOLOX-M ONNX):")
    yolox_ok = os.path.isfile(YOLOX_MODEL)
    if yolox_ok:
        size = os.path.getsize(YOLOX_MODEL)
        print(f"  yolox_m.onnx ({size / 1e6:.0f} MB) [ready]")
    else:
        print(f"  NOT FOUND ({YOLOX_MODEL})")

    # Multimodal models
    print("\nMultiModal (llama.cpp vision):")
    mm_dir = os.path.join(MODEL_HUB, "models/MultiModal")
    if os.path.isdir(mm_dir):
        for f in sorted(os.listdir(mm_dir)):
            if f.endswith(".md"):
                name = f.replace(".md", "")
                print(f"  {name:40s} [docs only — needs GGUF download]")
    else:
        print("  Not available")

    print()


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Local AI — on-device inference",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # transcribe
    p_tr = sub.add_parser("transcribe", help="Transcribe audio to text (Whisper)")
    p_tr.add_argument("--audio", required=True, help="Path to audio file")
    p_tr.add_argument("--model", default="small", choices=["tiny", "small", "medium"],
                       help="Whisper model size (default: small)")

    # chat
    p_ch = sub.add_parser("chat", help="Chat with local LLM (llama.cpp + Vulkan)")
    p_ch.add_argument("--prompt", required=True, help="User message")
    p_ch.add_argument("--system", default="", help="System prompt")
    p_ch.add_argument("--max-tokens", type=int, default=512, help="Max tokens to generate")
    p_ch.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature")
    p_ch.add_argument("--model", default=None, help="Path to GGUF model file")

    # detect
    p_dt = sub.add_parser("detect", help="Detect objects in an image (YOLOX)")
    p_dt.add_argument("--image", required=True, help="Path to image file")
    p_dt.add_argument("--confidence", type=float, default=0.3, help="Confidence threshold")
    p_dt.add_argument("--save", default="", help="Save annotated image to path")

    # models
    sub.add_parser("models", help="List available local AI models")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "transcribe": cmd_transcribe,
        "chat": cmd_chat,
        "detect": cmd_detect,
        "models": cmd_models,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
