package main

import (
	"bufio"
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"mime/multipart"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/yuin/goldmark"
	"github.com/yuin/goldmark/extension"
	"github.com/yuin/goldmark/renderer/html"
)

// VoiceResponse is returned to the frontend for voice requests
type VoiceResponse struct {
	Transcript  string `json:"transcript"`
	Response    string `json:"response"`
	AudioURL    string `json:"audio_url,omitempty"`
	AudioBase64 string `json:"audio_base64,omitempty"`
}

// ChatRequest for text chat
type ChatRequest struct {
	Message   string `json:"message"`
	SessionID string `json:"session_id,omitempty"`
}

// ChatResponse for text chat
type ChatResponse struct {
	Response    string `json:"response"`
	AudioURL    string `json:"audio_url,omitempty"`
	AudioBase64 string `json:"audio_base64,omitempty"`
}

// STTResponse from Demeterics STT API
type STTResponse struct {
	Text string `json:"text"`
}

// TTSRequest to Demeterics TTS API
type TTSRequest struct {
	Input    string `json:"input"`
	Model    string `json:"model,omitempty"`
	Voice    string `json:"voice,omitempty"`
	Format   string `json:"format,omitempty"`
	Provider string `json:"provider,omitempty"`
}

// TTSResponse from Demeterics TTS API
type TTSResponse struct {
	AudioURL    string `json:"audio_url,omitempty"`
	AudioBase64 string `json:"audio_base64,omitempty"`
}

// ClawdbotCLIResponse from openclaw agent --json command
type ClawdbotCLIResponse struct {
	RunID   string `json:"runId"`
	Status  string `json:"status"`
	Summary string `json:"summary"`
	Result  struct {
		Payloads []struct {
			Text     string `json:"text"`
			MediaURL string `json:"mediaUrl"`
		} `json:"payloads"`
		Meta struct {
			DurationMs int `json:"durationMs"`
			AgentMeta  struct {
				SessionID string `json:"sessionId"`
				Provider  string `json:"provider"`
				Model     string `json:"model"`
				Usage     struct {
					Input      int `json:"input"`
					Output     int `json:"output"`
					CacheRead  int `json:"cacheRead"`
					CacheWrite int `json:"cacheWrite"`
					Total      int `json:"total"`
				} `json:"usage"`
			} `json:"agentMeta"`
		} `json:"meta"`
	} `json:"result"`
}

// voiceStreamHandler handles voice requests: STT then creates an async job (same as text chat)
func voiceStreamHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Set SSE headers
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("X-Accel-Buffering", "no") // Disable nginx buffering

	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "Streaming not supported", http.StatusInternalServerError)
		return
	}

	// Helper to send SSE events
	sendEvent := func(event string, data interface{}) {
		jsonData, _ := json.Marshal(data)
		fmt.Fprintf(w, "event: %s\ndata: %s\n\n", event, jsonData)
		flusher.Flush()
	}

	// Parse multipart form (10MB max)
	if err := r.ParseMultipartForm(10 << 20); err != nil {
		sendEvent("error", map[string]string{"error": "Failed to parse form"})
		return
	}

	file, _, err := r.FormFile("audio")
	if err != nil {
		sendEvent("error", map[string]string{"error": "Audio file required"})
		return
	}
	defer file.Close()

	audioData, err := io.ReadAll(file)
	if err != nil {
		sendEvent("error", map[string]string{"error": "Failed to read audio"})
		return
	}

	email, _, _ := getSessionUser(r)
	log.Printf("Voice stream request from %s, audio size: %d bytes", email, len(audioData))

	// Step 1: Speech-to-Text (cloud, with local fallback)
	transcript, err := callSTT(audioData)
	if err != nil {
		log.Printf("Cloud STT error: %v — trying local Whisper", err)
		logWarning("Cloud STT failed, trying local Whisper fallback", "voice", "")
		transcript, err = callSTTLocal(audioData)
		if err != nil {
			log.Printf("Local STT also failed: %v", err)
			sendEvent("error", map[string]string{"error": "Speech recognition failed: " + err.Error()})
			return
		}
		logInfo("Local Whisper STT succeeded", "voice", "")
	}
	log.Printf("STT transcript: %s", transcript)

	// Send transcript immediately
	sendEvent("transcript", map[string]string{"transcript": transcript})

	// Step 2: Create async job — same path as text chat
	sessionID := r.FormValue("session_id")
	if active := getActiveJobForThread(sessionID, email); active != nil {
		logWarning("Voice: job already running for thread: "+active.ID, "voice", sessionID)
		sendEvent("job", map[string]string{"job_id": active.ID, "status": active.Status})
		sendEvent("done", map[string]string{"transcript": transcript, "job_id": active.ID})
		return
	}

	job := startJob(sessionID, email, transcript)
	logInfo("Voice: created job "+job.ID+" for thread "+sessionID, "voice", sessionID)

	// Send job ID so frontend can poll (same as text chat)
	sendEvent("job", map[string]string{"job_id": job.ID})
	sendEvent("done", map[string]string{"transcript": transcript, "job_id": job.ID})
}

func voiceHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Parse multipart form (10MB max)
	if err := r.ParseMultipartForm(10 << 20); err != nil {
		log.Printf("Failed to parse form: %v", err)
		http.Error(w, "Failed to parse form", http.StatusBadRequest)
		return
	}

	file, _, err := r.FormFile("audio")
	if err != nil {
		log.Printf("Failed to get audio file: %v", err)
		http.Error(w, "Audio file required", http.StatusBadRequest)
		return
	}
	defer file.Close()

	audioData, err := io.ReadAll(file)
	if err != nil {
		log.Printf("Failed to read audio: %v", err)
		http.Error(w, "Failed to read audio", http.StatusInternalServerError)
		return
	}

	// Get session user for context
	email, _, _ := getSessionUser(r)
	log.Printf("Voice request from %s, audio size: %d bytes", email, len(audioData))

	// Get session ID from form if provided
	sessionID := r.FormValue("session_id")

	// Step 1: Speech-to-Text via Demeterics
	transcript, err := callSTT(audioData)
	if err != nil {
		log.Printf("STT error: %v", err)
		jsonError(w, "Speech recognition failed: "+err.Error(), http.StatusInternalServerError)
		return
	}
	log.Printf("STT transcript: %s", transcript)

	// Step 2: LLM via Clawdbot; fall back to Groq fallback LLM on failure
	llmResponse, err := callClawdbot(transcript, email, sessionID)
	if err != nil {
		log.Printf("Clawdbot error: %v", err)
		logWarning("Voice (non-stream): falling back to Groq fallback LLM", "voice", sessionID)
		llmResponse, err = callFallbackLLM(transcript)
		if err != nil {
			log.Printf("Groq fallback also failed: %v", err)
			jsonError(w, "AI processing failed: all backends unavailable", http.StatusInternalServerError)
			return
		}
	}
	log.Printf("Clawdbot response: %s", truncate(llmResponse, 100))

	// Step 3: Text-to-Speech (strip markdown, truncate, with local fallback)
	plainText := stripMarkdown(llmResponse)
	if len(plainText) > 2800 {
		plainText = plainText[:2800] + "..."
	}
	audioURL, audioBase64, err := callTTS(plainText)
	if err != nil {
		log.Printf("Cloud TTS error: %v — trying local espeak-ng", err)
		audioBase64, err = callTTSLocal(plainText)
		if err != nil {
			log.Printf("Local TTS also failed: %v", err)
			// Return response without audio
			jsonResponse(w, VoiceResponse{
				Transcript: transcript,
				Response:   markdownToHTML(llmResponse),
			})
			return
		}
		audioURL = ""
	}

	jsonResponse(w, VoiceResponse{
		Transcript:  transcript,
		Response:    markdownToHTML(llmResponse),
		AudioURL:    audioURL,
		AudioBase64: audioBase64,
	})
}

func chatHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req ChatRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		jsonError(w, "Invalid request", http.StatusBadRequest)
		return
	}

	email, _, _ := getSessionUser(r)
	log.Printf("Chat request from %s: %s", email, truncate(req.Message, 100))
	logInfo("Chat request: "+truncate(req.Message, 100), "chat", req.SessionID)

	// Check for already running job on this thread
	if active := getActiveJobForThread(req.SessionID, email); active != nil {
		logWarning("Job already running for thread: "+active.ID, "chat", req.SessionID)
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"job_id": active.ID,
			"status": active.Status,
		})
		return
	}

	// Start async job — returns immediately
	job := startJob(req.SessionID, email, req.Message)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"job_id": job.ID,
		"status": job.Status,
	})
}

func callSTT(audioData []byte) (string, error) {
	// Create multipart form
	var buf bytes.Buffer
	writer := multipart.NewWriter(&buf)

	part, err := writer.CreateFormFile("file", "audio.webm")
	if err != nil {
		return "", fmt.Errorf("create form file: %w", err)
	}
	part.Write(audioData)

	// Add model parameter — turbo is ~6x faster with same quality
	writer.WriteField("model", "whisper-large-v3-turbo")
	writer.Close()

	// Call Demeterics STT API
	url := cfg.DemetericsBaseURL + "/audio/v1/transcriptions"
	req, err := http.NewRequest("POST", url, &buf)
	if err != nil {
		return "", fmt.Errorf("create request: %w", err)
	}

	req.Header.Set("Authorization", "Bearer "+cfg.DemetericsAPIKey)
	req.Header.Set("Content-Type", writer.FormDataContentType())

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("STT request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("STT error %d: %s", resp.StatusCode, string(body))
	}

	var sttResp STTResponse
	if err := json.NewDecoder(resp.Body).Decode(&sttResp); err != nil {
		return "", fmt.Errorf("decode response: %w", err)
	}

	return sttResp.Text, nil
}

func callClawdbot(message, userEmail, sessionID string) (string, error) {
	// Use provided session ID or fall back to sanitized user email
	// OpenClaw rejects session IDs containing @ and other special chars
	if sessionID == "" {
		safe := strings.NewReplacer("@", "_at_", ".", "_").Replace(userEmail)
		sessionID = "openclaw-voice-" + safe
	}

	// Retry once if the gateway was restarted mid-request (token refresh).
	// Wait for the new container to be ready before retrying.
	const maxAttempts = 2
	const retryDelay = 15 * time.Second

	for attempt := 1; attempt <= maxAttempts; attempt++ {
		result, err := callClawdbotOnce(message, sessionID)
		if err == nil {
			return result, nil
		}

		// Only retry on fast failures (container gone / restarting), not timeouts or API errors
		if attempt < maxAttempts && !strings.Contains(err.Error(), "timed out") {
			log.Printf("Clawdbot attempt %d failed: %v — retrying in %s", attempt, err, retryDelay)
			logWarning(fmt.Sprintf("Gateway may be restarting, retrying in %s", retryDelay), "clawdbot", sessionID)
			time.Sleep(retryDelay)
			continue
		}

		return "", err
	}
	return "", fmt.Errorf("clawdbot: all attempts failed")
}

func callClawdbotOnce(message, sessionID string) (string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 43200*time.Second) // 12 hours
	defer cancel()
	cmd := exec.CommandContext(ctx,
		cfg.ClawdbotCLI,
		"agent",
		"--session-id", sessionID,
		"--message", message,
		"--thinking", "medium",
		"--json",
	)

	start := time.Now()
	logInfo(fmt.Sprintf("Clawdbot call: session=%s, message=%s", sessionID, truncate(message, 80)), "clawdbot", sessionID)

	// Capture both stdout and stderr via pipes for reliable logging
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err := cmd.Run()
	elapsed := time.Since(start)

	if err != nil {
		stderrStr := strings.TrimSpace(stderr.String())
		logError(fmt.Sprintf("Clawdbot failed after %s: %v | stderr: %s", elapsed.Round(time.Millisecond), err, truncate(stderrStr, 500)), "clawdbot", sessionID)
		log.Printf("Clawdbot stderr (%s): %s", elapsed.Round(time.Millisecond), stderrStr)
		if ctx.Err() == context.DeadlineExceeded {
			return "", fmt.Errorf("clawdbot timed out after %s", elapsed.Round(time.Second))
		}
		if stderrStr != "" {
			return "", fmt.Errorf("clawdbot error: %s", stderrStr)
		}
		return "", fmt.Errorf("clawdbot exec: %w", err)
	}

	output := stdout.Bytes()
	logDebug(fmt.Sprintf("Clawdbot completed in %s (%d bytes)", elapsed.Round(time.Millisecond), len(output)), "clawdbot", sessionID)

	log.Printf("Clawdbot raw output length: %d bytes", len(output))

	var resp ClawdbotCLIResponse
	if err := json.Unmarshal(output, &resp); err != nil {
		log.Printf("Clawdbot JSON parse error: %v, output: %s", err, string(output[:min(500, len(output))]))
		return "", fmt.Errorf("parse clawdbot response: %w", err)
	}

	log.Printf("Clawdbot payloads: %d", len(resp.Result.Payloads))

	// Log detailed response info
	meta := resp.Result.Meta
	logInfo(fmt.Sprintf("AI response: model=%s, duration=%dms, tokens=%d (in:%d out:%d cache:%d)",
		meta.AgentMeta.Model,
		meta.DurationMs,
		meta.AgentMeta.Usage.Total,
		meta.AgentMeta.Usage.Input,
		meta.AgentMeta.Usage.Output,
		meta.AgentMeta.Usage.CacheRead,
	), "clawdbot", sessionID)

	// Extract thinking blocks from session file
	go extractThinkingFromSession(sessionID)

	if len(resp.Result.Payloads) == 0 {
		return "", fmt.Errorf("clawdbot returned no response")
	}

	// Concatenate all text payloads (agent may split response across multiple payloads)
	var parts []string
	for _, p := range resp.Result.Payloads {
		if p.Text != "" {
			parts = append(parts, p.Text)
		}
	}
	if len(parts) == 0 {
		return "", fmt.Errorf("clawdbot returned no text response")
	}

	return strings.Join(parts, "\n\n"), nil
}

// callFallbackLLM calls Groq compound model directly as a fallback when OpenClaw is down
func callFallbackLLM(message string) (string, error) {
	if cfg.GroqAPIKey == "" {
		return "", fmt.Errorf("GROQ_API_KEY not configured")
	}

	reqBody := map[string]any{
		"model": "groq/compound",
		"messages": []map[string]string{
			{"role": "system", "content": "You are ATHENA, a helpful AI assistant. Be concise, friendly, and helpful. Note: you are running in fallback mode with limited capabilities (no web browsing, no tools). Let the user know if their request needs tools you don't have."},
			{"role": "user", "content": message},
		},
	}

	body, err := json.Marshal(reqBody)
	if err != nil {
		return "", fmt.Errorf("marshal request: %w", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		"https://api.groq.com/openai/v1/chat/completions", bytes.NewReader(body))
	if err != nil {
		return "", fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+cfg.GroqAPIKey)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		respBody, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("Demeterics API error %d: %s", resp.StatusCode, string(respBody))
	}

	var chatResp struct {
		Choices []struct {
			Message struct {
				Content   string `json:"content"`
				Reasoning string `json:"reasoning"`
			} `json:"message"`
		} `json:"choices"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&chatResp); err != nil {
		return "", fmt.Errorf("decode response: %w", err)
	}

	if len(chatResp.Choices) == 0 {
		return "", fmt.Errorf("empty response from fallback LLM")
	}

	content := chatResp.Choices[0].Message.Content
	if content == "" {
		// OSS 120B may put output in reasoning field
		content = chatResp.Choices[0].Message.Reasoning
	}
	if content == "" {
		return "", fmt.Errorf("empty response from fallback LLM")
	}

	return content, nil
}

// extractThinkingFromSession reads the session JSONL file and extracts thinking blocks
func extractThinkingFromSession(sessionID string) {
	if sessionID == "" {
		return
	}

	// Session files are in the gateway's dotopenclaw volume, mounted at /opt/openclaw/vault/../dotopenclaw
	// but that's not accessible from the web container. Use the vault's parent if available.
	dotopenclaw := os.Getenv("DOTOPENCLAW_DIR")
	if dotopenclaw == "" {
		// Not mounted — skip silently
		return
	}
	sessionFile := filepath.Join(dotopenclaw, "agents", "main", "sessions", sessionID+".jsonl")

	file, err := os.Open(sessionFile)
	if err != nil {
		log.Printf("Could not open session file %s: %v", sessionFile, err)
		return
	}
	defer file.Close()

	// Read last 50KB to get recent messages
	stat, _ := file.Stat()
	startPos := int64(0)
	if stat.Size() > 50000 {
		startPos = stat.Size() - 50000
	}
	file.Seek(startPos, 0)

	scanner := bufio.NewScanner(file)
	scanner.Buffer(make([]byte, 1024*1024), 1024*1024) // 1MB buffer

	var thinkingBlocks []string
	for scanner.Scan() {
		line := scanner.Text()
		if !strings.Contains(line, `"type":"thinking"`) && !strings.Contains(line, `"type": "thinking"`) {
			continue
		}

		var entry struct {
			Type    string `json:"type"`
			Message struct {
				Content []struct {
					Type     string `json:"type"`
					Thinking string `json:"thinking"`
				} `json:"content"`
			} `json:"message"`
		}

		if err := json.Unmarshal([]byte(line), &entry); err != nil {
			continue
		}

		// Extract thinking from message content
		if entry.Type == "message" {
			for _, c := range entry.Message.Content {
				if c.Type == "thinking" && c.Thinking != "" {
					thinkingBlocks = append(thinkingBlocks, c.Thinking)
				}
			}
		}
	}

	// Store thinking blocks in log store
	for _, thinking := range thinkingBlocks {
		logStore.AddThinking(sessionID, thinking)
		// Also log a truncated version
		preview := thinking
		if len(preview) > 200 {
			preview = preview[:200] + "..."
		}
		logDebug("Thinking: "+preview, "thinking", sessionID)
	}

	if len(thinkingBlocks) > 0 {
		logInfo(fmt.Sprintf("Extracted %d thinking blocks", len(thinkingBlocks)), "thinking", sessionID)
	}
}

// ttsHandler provides a standalone TTS endpoint for voice responses
func ttsHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Text string `json:"text"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		jsonError(w, "Invalid request", http.StatusBadRequest)
		return
	}
	if req.Text == "" {
		jsonError(w, "text is required", http.StatusBadRequest)
		return
	}

	// Strip markdown and truncate for TTS
	plainText := stripMarkdown(req.Text)
	const maxTTSChars = 2800
	if len(plainText) > maxTTSChars {
		plainText = plainText[:maxTTSChars] + "..."
	}

	audioURL, audioBase64, err := callTTS(plainText)
	if err != nil {
		log.Printf("Cloud TTS error: %v — trying local espeak-ng", err)
		audioBase64, err = callTTSLocal(plainText)
		if err != nil {
			log.Printf("Local TTS also failed: %v", err)
			jsonError(w, "TTS failed: "+err.Error(), http.StatusInternalServerError)
			return
		}
		audioURL = ""
		logInfo("Local espeak-ng TTS used as fallback", "tts", "")
	}

	jsonResponse(w, map[string]string{
		"audio_url":    audioURL,
		"audio_base64": audioBase64,
	})
}

// stripMarkdown converts markdown to plain text suitable for TTS
func stripMarkdown(md string) string {
	lines := strings.Split(md, "\n")
	var result []string
	inCodeBlock := false

	for _, line := range lines {
		// Skip code blocks
		if strings.HasPrefix(strings.TrimSpace(line), "```") {
			inCodeBlock = !inCodeBlock
			continue
		}
		if inCodeBlock {
			continue
		}

		// Remove headers
		line = strings.TrimLeft(line, "# ")

		// Remove bold/italic markers
		for strings.Contains(line, "**") {
			line = strings.Replace(line, "**", "", 2)
		}
		for strings.Contains(line, "__") {
			line = strings.Replace(line, "__", "", 2)
		}
		line = strings.ReplaceAll(line, "*", "")
		line = strings.ReplaceAll(line, "_", " ")

		// Remove inline code
		for strings.Contains(line, "`") {
			line = strings.Replace(line, "`", "", 2)
		}

		// Convert links [text](url) → text
		for {
			start := strings.Index(line, "[")
			mid := strings.Index(line, "](")
			end := strings.Index(line, ")")
			if start >= 0 && mid > start && end > mid {
				linkText := line[start+1 : mid]
				line = line[:start] + linkText + line[end+1:]
			} else {
				break
			}
		}

		// Remove image syntax ![alt](url)
		for strings.Contains(line, "![") {
			start := strings.Index(line, "![")
			end := strings.Index(line[start:], ")")
			if end > 0 {
				line = line[:start] + line[start+end+1:]
			} else {
				break
			}
		}

		// Remove horizontal rules
		trimmed := strings.TrimSpace(line)
		if trimmed == "---" || trimmed == "***" || trimmed == "___" {
			continue
		}

		// Convert list markers to natural speech
		if strings.HasPrefix(trimmed, "- ") {
			line = strings.Replace(line, "- ", "", 1)
		}

		// Remove HTML tags
		for {
			start := strings.Index(line, "<")
			end := strings.Index(line, ">")
			if start >= 0 && end > start {
				line = line[:start] + line[end+1:]
			} else {
				break
			}
		}

		if strings.TrimSpace(line) != "" {
			result = append(result, strings.TrimSpace(line))
		}
	}

	return strings.Join(result, ". ")
}

// callSTTLocal runs local Whisper via the gateway container as a fallback
func callSTTLocal(audioData []byte) (string, error) {
	// Write audio to shared vault volume (accessible by both containers)
	tmpName := fmt.Sprintf(".tmp_stt_%d.webm", time.Now().UnixNano())
	vaultDir := os.Getenv("VAULT_DIR")
	if vaultDir == "" {
		vaultDir = "/opt/openclaw/vault"
	}
	tmpPath := filepath.Join(vaultDir, tmpName)

	if err := os.WriteFile(tmpPath, audioData, 0644); err != nil {
		return "", fmt.Errorf("write temp audio: %w", err)
	}
	defer os.Remove(tmpPath)

	// Map to gateway container path
	gatewayAudioPath := "/home/openclaw/.openclaw/workspace/vault/" + tmpName

	ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, "docker", "exec", "openclaw-gateway",
		"/opt/ai/venv/bin/python3",
		"/home/openclaw/.openclaw/workspace/skills/local-ai/local_ai.py",
		"transcribe",
		"--audio", gatewayAudioPath,
		"--model", "small",
	)

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("local whisper: %v (stderr: %s)", err, stderr.String())
	}

	transcript := strings.TrimSpace(stdout.String())
	if transcript == "" {
		return "", fmt.Errorf("local whisper returned empty transcript")
	}

	return transcript, nil
}

// callTTSLocal tries Kokoro (ultra-fast neural TTS on a local GPU),
// then falls back to espeak-ng if Kokoro is unreachable.
func callTTSLocal(text string) (string, error) {
	// Try Kokoro first (~50-500ms per sentence, high quality)
	b64, err := callTTSKokoro(text)
	if err == nil {
		return b64, nil
	}
	log.Printf("Kokoro TTS unavailable: %v — falling back to espeak-ng", err)

	// Final fallback: espeak-ng (robotic but always available)
	return callTTSEspeak(text)
}

// callTTSKokoro calls the Kokoro-82M TTS server running on the host (port 5175)
func callTTSKokoro(text string) (string, error) {
	if len(text) > 5000 {
		text = text[:5000]
	}

	reqBody, _ := json.Marshal(map[string]interface{}{
		"text":  text,
		"voice": "am_adam",
		"speed": 1.0,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	kokoroURL := os.Getenv("KOKORO_TTS_URL")
	if kokoroURL == "" {
		kokoroURL = "http://host.docker.internal:5175"
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		kokoroURL+"/synthesize", bytes.NewReader(reqBody))
	if err != nil {
		return "", fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("kokoro request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("kokoro error %d: %s", resp.StatusCode, string(body))
	}

	// Kokoro returns raw WAV — convert to MP3 via ffmpeg pipe
	wavData, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("read wav: %w", err)
	}

	// WAV → MP3 via ffmpeg
	cmd := exec.CommandContext(ctx, "ffmpeg", "-y", "-i", "pipe:0",
		"-codec:a", "libmp3lame", "-b:a", "64k", "-f", "mp3", "pipe:1")
	cmd.Stdin = bytes.NewReader(wavData)
	var mp3Buf, stderrBuf bytes.Buffer
	cmd.Stdout = &mp3Buf
	cmd.Stderr = &stderrBuf

	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("ffmpeg wav→mp3: %v", err)
	}

	return base64.StdEncoding.EncodeToString(mp3Buf.Bytes()), nil
}

// callTTSEspeak uses espeak-ng as the last-resort TTS fallback
func callTTSEspeak(text string) (string, error) {
	if len(text) > 3000 {
		text = text[:3000]
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	tmpWav := fmt.Sprintf("/tmp/tts_%d.wav", time.Now().UnixNano())
	defer os.Remove(tmpWav)

	cmd := exec.CommandContext(ctx, "espeak-ng", "-v", "en-us", "-s", "160", "-p", "50", "-w", tmpWav)
	cmd.Stdin = strings.NewReader(text)
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("espeak-ng: %v (stderr: %s)", err, stderr.String())
	}

	tmpMp3 := tmpWav + ".mp3"
	defer os.Remove(tmpMp3)

	cmd2 := exec.CommandContext(ctx, "ffmpeg", "-y", "-i", tmpWav, "-codec:a", "libmp3lame", "-b:a", "64k", "-f", "mp3", tmpMp3)
	cmd2.Stderr = &stderr
	if err := cmd2.Run(); err != nil {
		return "", fmt.Errorf("ffmpeg wav→mp3: %v", err)
	}

	mp3Data, err := os.ReadFile(tmpMp3)
	if err != nil {
		return "", fmt.Errorf("read mp3: %w", err)
	}

	return base64.StdEncoding.EncodeToString(mp3Data), nil
}

func callTTS(text string) (audioURL, audioBase64 string, err error) {
	reqBody := TTSRequest{
		Input:    text,
		Provider: "murf",
		Model:    "FALCON",
		Voice:    "en-US-miles",
		Format:   "mp3",
	}

	body, _ := json.Marshal(reqBody)
	url := cfg.DemetericsBaseURL + "/tts/v1/generate"

	req, err := http.NewRequest("POST", url, bytes.NewReader(body))
	if err != nil {
		return "", "", fmt.Errorf("create request: %w", err)
	}

	req.Header.Set("Authorization", "Bearer "+cfg.DemetericsAPIKey)
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return "", "", fmt.Errorf("TTS request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		respBody, _ := io.ReadAll(resp.Body)
		return "", "", fmt.Errorf("TTS error %d: %s", resp.StatusCode, string(respBody))
	}

	// Check content type - could be JSON or raw audio
	contentType := resp.Header.Get("Content-Type")
	if contentType == "application/json" || contentType == "application/json; charset=utf-8" {
		var ttsResp TTSResponse
		if err := json.NewDecoder(resp.Body).Decode(&ttsResp); err != nil {
			return "", "", fmt.Errorf("decode response: %w", err)
		}
		return ttsResp.AudioURL, ttsResp.AudioBase64, nil
	}

	// Raw audio response - encode as base64
	audioData, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", "", fmt.Errorf("read audio: %w", err)
	}
	return "", base64.StdEncoding.EncodeToString(audioData), nil
}

func jsonResponse(w http.ResponseWriter, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(data)
}

func jsonError(w http.ResponseWriter, message string, code int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(map[string]string{"error": message})
}

func truncate(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen] + "..."
}

// markdownToHTML converts markdown text to HTML
func markdownToHTML(md string) string {
	converter := goldmark.New(
		goldmark.WithExtensions(extension.GFM),
		goldmark.WithRendererOptions(
			html.WithHardWraps(),
			html.WithXHTML(),
		),
	)

	var buf bytes.Buffer
	if err := converter.Convert([]byte(md), &buf); err != nil {
		log.Printf("Markdown conversion error: %v", err)
		return md // Return original on error
	}
	return buf.String()
}
