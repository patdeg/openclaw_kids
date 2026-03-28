package main

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
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

// voiceStreamHandler — voice feature removed
func voiceStreamHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusNotImplemented)
	json.NewEncoder(w).Encode(map[string]string{"error": "Voice feature not available"})
}

// voiceHandler — voice feature removed
func voiceHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusNotImplemented)
	json.NewEncoder(w).Encode(map[string]string{"error": "Voice feature not available"})
}

// ttsHandler — voice feature removed
func ttsHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusNotImplemented)
	json.NewEncoder(w).Encode(map[string]string{"error": "Voice feature not available"})
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

// callFallbackLLM is a stub — fallback LLM not configured
func callFallbackLLM(message string) (string, error) {
	return "", fmt.Errorf("fallback LLM not configured")
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

// stripMarkdown converts markdown to plain text
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

		// Convert links [text](url) -> text
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
