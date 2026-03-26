package main

import (
	"bytes"
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
	"strconv"
	"strings"
	"time"
)

// MediaUploadResponse returned after processing
type MediaUploadResponse struct {
	Success  bool         `json:"success"`
	Media    MediaInfo    `json:"media"`
	Response ResponseData `json:"response"`
	Error    string       `json:"error,omitempty"`
}

type MediaInfo struct {
	ID          string   `json:"id"`
	Type        string   `json:"type"`
	Topic       string   `json:"topic"`
	Filename    string   `json:"filename"`
	Description string   `json:"description"`
	Tags        []string `json:"tags"`
}

type ResponseData struct {
	Text string `json:"text"`
	HTML string `json:"html"`
}

// GroqVisionResponse from Groq API
type GroqVisionResponse struct {
	Choices []struct {
		Message struct {
			Content string `json:"content"`
		} `json:"message"`
	} `json:"choices"`
}

// GroqWhisperResponse from Groq Whisper API
type GroqWhisperResponse struct {
	Text string `json:"text"`
}

// VisionAnalysis parsed from LLM response
type VisionAnalysis struct {
	Description   string   `json:"description"`
	ExtractedText string   `json:"extracted_text"`
	Details       any      `json:"details"`
	Tags          []string `json:"tags"`
	Topic         string   `json:"topic"`
}

// mediaUploadHandler handles POST /api/media/upload
func mediaUploadHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Parse multipart form (20MB max for documents)
	if err := r.ParseMultipartForm(20 << 20); err != nil {
		jsonError(w, "Failed to parse form: "+err.Error(), http.StatusBadRequest)
		return
	}

	file, header, err := r.FormFile("file")
	if err != nil {
		jsonError(w, "File required", http.StatusBadRequest)
		return
	}
	defer file.Close()

	mediaType := r.FormValue("type")
	if mediaType == "" {
		// Detect from content type
		contentType := header.Header.Get("Content-Type")
		if strings.HasPrefix(contentType, "image/") {
			mediaType = "image"
		} else if strings.HasPrefix(contentType, "audio/") {
			mediaType = "audio"
		} else {
			mediaType = "document"
		}
	}

	userMessage := r.FormValue("message")
	sessionID := r.FormValue("session_id")
	userTopic := r.FormValue("topic") // User-specified topic override
	email, _, _ := getSessionUser(r)

	log.Printf("Media upload from %s: type=%s, filename=%s, size=%d",
		email, mediaType, header.Filename, header.Size)
	logInfo("Upload: "+header.Filename+" ("+mediaType+")", "media", sessionID)

	// Read file data
	fileData, err := io.ReadAll(file)
	if err != nil {
		jsonError(w, "Failed to read file", http.StatusInternalServerError)
		return
	}

	// Get existing topics for classification
	topics := getExistingTopics()

	// Process based on type
	var analysis VisionAnalysis
	var contentText string

	switch mediaType {
	case "image":
		analysis, err = processImage(fileData, header.Header.Get("Content-Type"), topics)
		if err != nil {
			log.Printf("Image processing error: %v", err)
			jsonError(w, "Image processing failed: "+err.Error(), http.StatusInternalServerError)
			return
		}
		contentText = analysis.ExtractedText

	case "audio":
		transcript, err := callGroqWhisper(fileData, header.Filename)
		if err != nil {
			log.Printf("Audio Groq Whisper error: %v", err)
			jsonError(w, "Audio transcription failed: "+err.Error(), http.StatusInternalServerError)
			return
		}
		log.Printf("Audio transcript (%d chars): %s", len(transcript), truncate(transcript, 100))
		analysis, err = classifyText(transcript, "audio", topics)
		if err != nil {
			log.Printf("Audio classification error: %v", err)
			// Use defaults
			analysis = VisionAnalysis{
				Description: "Voice memo",
				Tags:        []string{"voice-memo"},
				Topic:       "ideas",
			}
		}
		contentText = transcript
		analysis.ExtractedText = transcript

	case "document":
		// Extract text from document
		docText := extractDocumentText(fileData, header.Filename)
		analysis, err = classifyText(docText, "document", topics)
		if err != nil {
			log.Printf("Document classification error: %v", err)
			analysis = VisionAnalysis{
				Description: "Document",
				Tags:        []string{"document"},
				Topic:       "documents",
			}
		}
		contentText = docText
		analysis.ExtractedText = docText
	}

	// Override topic if user specified one
	if userTopic != "" {
		if sanitized, ok := sanitizeTopic(userTopic); !ok {
			jsonError(w, "Invalid topic name", http.StatusBadRequest)
			return
		} else {
			log.Printf("Using user-specified topic: %s (AI suggested: %s)", sanitized, analysis.Topic)
			analysis.Topic = sanitized
		}
	}

	// Generate stored filename with date prefix
	datePrefix := time.Now().Format("20060102")
	storedFilename := datePrefix + "_" + sanitizeFilename(header.Filename)

	// Save file to vault
	filePath, err := saveToVault(fileData, analysis.Topic, storedFilename)
	if err != nil {
		log.Printf("File save error: %v", err)
		jsonError(w, "Failed to save file: "+err.Error(), http.StatusInternalServerError)
		return
	}

	// Replace existing file with same name in same topic
	deleteExistingFile(analysis.Topic, header.Filename)

	// Store metadata via vault CLI
	tagsStr := strings.Join(analysis.Tags, ",")
	detailsJSON, _ := json.Marshal(analysis.Details)

	vaultResult, err := storeInVault(
		mediaType,
		analysis.Topic,
		header.Filename,
		storedFilename,
		header.Size,
		header.Header.Get("Content-Type"),
		analysis.Description,
		tagsStr,
		contentText,
		string(detailsJSON),
		sessionID,
	)
	if err != nil {
		log.Printf("Vault store error: %v", err)
		jsonError(w, "Failed to store metadata: "+err.Error(), http.StatusInternalServerError)
		return
	}

	// Build context for Clawdbot
	context := buildMediaContext(vaultResult["id"].(string), mediaType, analysis, userMessage)

	// Call Clawdbot
	llmResponse, err := callClawdbot(context, email, sessionID)
	if err != nil {
		log.Printf("Clawdbot error: %v", err)
		// Return success with default message
		llmResponse = fmt.Sprintf("Saved %s to %s: %s", mediaType, analysis.Topic, analysis.Description)
	}

	_ = filePath // unused but kept for potential future use

	jsonResponse(w, MediaUploadResponse{
		Success: true,
		Media: MediaInfo{
			ID:          vaultResult["id"].(string),
			Type:        mediaType,
			Topic:       analysis.Topic,
			Filename:    storedFilename,
			Description: analysis.Description,
			Tags:        analysis.Tags,
		},
		Response: ResponseData{
			Text: llmResponse,
			HTML: markdownToHTML(llmResponse),
		},
	})
}

// processImage analyzes an image using Groq vision API
func processImage(imageData []byte, contentType string, existingTopics []string) (VisionAnalysis, error) {
	// Encode image as base64
	base64Image := base64.StdEncoding.EncodeToString(imageData)

	// Build data URL
	if contentType == "" {
		contentType = "image/jpeg"
	}
	dataURL := fmt.Sprintf("data:%s;base64,%s", contentType, base64Image)

	// Build topics string
	topicsStr := "receipts, medical, family, ideas, work, travel, events"
	if len(existingTopics) > 0 {
		topicsStr = strings.Join(existingTopics, ", ")
	}

	prompt := fmt.Sprintf(`Analyze this image and return JSON with:
1. description: Brief description (1-2 sentences)
2. extracted_text: Any visible text (OCR)
3. details: Key details object (dates, amounts, names, locations)
4. tags: Array of 3-5 keyword tags
5. topic: Classify into ONE of these existing topics, or create a new one:
   Existing topics: %s
   If none fit, create a descriptive topic (lowercase, hyphenated if multi-word)

Return ONLY valid JSON, no markdown:
{"description": "...", "extracted_text": "...", "details": {...}, "tags": ["..."], "topic": "..."}`, topicsStr)

	reqBody := map[string]interface{}{
		"model": "meta-llama/llama-4-scout-17b-16e-instruct",
		"messages": []map[string]interface{}{
			{
				"role": "user",
				"content": []map[string]interface{}{
					{"type": "text", "text": prompt},
					{"type": "image_url", "image_url": map[string]string{"url": dataURL}},
				},
			},
		},
		"response_format": map[string]string{"type": "json_object"},
	}

	body, _ := json.Marshal(reqBody)
	req, err := http.NewRequest("POST", "https://api.groq.com/openai/v1/chat/completions", bytes.NewReader(body))
	if err != nil {
		return VisionAnalysis{}, err
	}

	req.Header.Set("Authorization", "Bearer "+cfg.GroqAPIKey)
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{Timeout: 60 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return VisionAnalysis{}, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		respBody, _ := io.ReadAll(resp.Body)
		return VisionAnalysis{}, fmt.Errorf("Groq API error %d: %s", resp.StatusCode, string(respBody))
	}

	var groqResp GroqVisionResponse
	if err := json.NewDecoder(resp.Body).Decode(&groqResp); err != nil {
		return VisionAnalysis{}, err
	}

	if len(groqResp.Choices) == 0 {
		return VisionAnalysis{}, fmt.Errorf("no response from Groq")
	}

	var analysis VisionAnalysis
	if err := json.Unmarshal([]byte(groqResp.Choices[0].Message.Content), &analysis); err != nil {
		return VisionAnalysis{}, fmt.Errorf("failed to parse analysis: %w", err)
	}

	return analysis, nil
}

// classifyText classifies text content (for audio transcripts and documents)
func classifyText(text, mediaType string, existingTopics []string) (VisionAnalysis, error) {
	topicsStr := "receipts, medical, family, ideas, work, travel, events"
	if len(existingTopics) > 0 {
		topicsStr = strings.Join(existingTopics, ", ")
	}

	// Truncate text for classification
	if len(text) > 2000 {
		text = text[:2000]
	}

	prompt := fmt.Sprintf(`Analyze this %s content and return JSON:

Content: "%s"

Existing topics in vault: %s

Return ONLY valid JSON:
{"description": "Brief summary (1 sentence)", "tags": ["tag1", "tag2"], "topic": "existing-topic-or-new-one"}`, mediaType, text, topicsStr)

	reqBody := map[string]interface{}{
		"model": "llama-3.3-70b-versatile",
		"messages": []map[string]interface{}{
			{"role": "user", "content": prompt},
		},
		"response_format": map[string]string{"type": "json_object"},
	}

	body, _ := json.Marshal(reqBody)
	req, err := http.NewRequest("POST", "https://api.groq.com/openai/v1/chat/completions", bytes.NewReader(body))
	if err != nil {
		return VisionAnalysis{}, err
	}

	req.Header.Set("Authorization", "Bearer "+cfg.GroqAPIKey)
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return VisionAnalysis{}, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		respBody, _ := io.ReadAll(resp.Body)
		return VisionAnalysis{}, fmt.Errorf("Groq API error %d: %s", resp.StatusCode, string(respBody))
	}

	var groqResp GroqVisionResponse
	if err := json.NewDecoder(resp.Body).Decode(&groqResp); err != nil {
		return VisionAnalysis{}, err
	}

	if len(groqResp.Choices) == 0 {
		return VisionAnalysis{}, fmt.Errorf("no response from Groq")
	}

	var analysis VisionAnalysis
	if err := json.Unmarshal([]byte(groqResp.Choices[0].Message.Content), &analysis); err != nil {
		return VisionAnalysis{}, fmt.Errorf("failed to parse analysis: %w", err)
	}

	return analysis, nil
}

// callGroqWhisper transcribes audio using Groq's Whisper API
func callGroqWhisper(audioData []byte, filename string) (string, error) {
	// Create multipart form
	var buf bytes.Buffer
	writer := multipart.NewWriter(&buf)

	// Determine file extension for proper handling
	ext := filepath.Ext(filename)
	if ext == "" {
		ext = ".webm"
	}

	part, err := writer.CreateFormFile("file", "audio"+ext)
	if err != nil {
		return "", fmt.Errorf("create form file: %w", err)
	}
	part.Write(audioData)

	// Add model parameter - whisper-large-v3-turbo is faster
	writer.WriteField("model", "whisper-large-v3-turbo")
	writer.Close()

	req, err := http.NewRequest("POST", "https://api.groq.com/openai/v1/audio/transcriptions", &buf)
	if err != nil {
		return "", fmt.Errorf("create request: %w", err)
	}

	req.Header.Set("Authorization", "Bearer "+cfg.GroqAPIKey)
	req.Header.Set("Content-Type", writer.FormDataContentType())

	client := &http.Client{Timeout: 60 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("Groq Whisper request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("Groq Whisper error %d: %s", resp.StatusCode, string(body))
	}

	var whisperResp GroqWhisperResponse
	if err := json.NewDecoder(resp.Body).Decode(&whisperResp); err != nil {
		return "", fmt.Errorf("decode response: %w", err)
	}

	return whisperResp.Text, nil
}

// extractDocumentText extracts text from documents (basic implementation)
func extractDocumentText(data []byte, filename string) string {
	ext := strings.ToLower(filepath.Ext(filename))

	switch ext {
	case ".txt", ".md":
		return string(data)
	case ".pdf":
		// Try pdftotext if available
		tmpFile, err := os.CreateTemp("", "doc-*.pdf")
		if err != nil {
			return ""
		}
		defer os.Remove(tmpFile.Name())
		tmpFile.Write(data)
		tmpFile.Close()

		cmd := exec.Command("pdftotext", tmpFile.Name(), "-")
		output, err := cmd.Output()
		if err != nil {
			return "[PDF - text extraction failed]"
		}
		return string(output)
	default:
		return "[Document]"
	}
}

// getExistingTopics returns list of existing topics from vault
func getExistingTopics() []string {
	cmd := exec.Command("python3", filepath.Join(cfg.VaultDir, "../skills/media-vault/vault.py"), "topics")
	output, err := cmd.Output()
	if err != nil {
		return []string{}
	}

	var topics []string
	json.Unmarshal(output, &topics)
	return topics
}

// saveToVault saves file to vault directory
func saveToVault(data []byte, topic, filename string) (string, error) {
	vaultFilesDir := filepath.Join(cfg.VaultDir, "files")
	topicDir := filepath.Join(vaultFilesDir, topic)

	// Defense-in-depth: ensure resolved path stays within vault
	if !strings.HasPrefix(topicDir, vaultFilesDir+string(os.PathSeparator)) && topicDir != vaultFilesDir {
		return "", fmt.Errorf("invalid topic: path traversal detected")
	}

	if err := os.MkdirAll(topicDir, 0755); err != nil {
		return "", err
	}

	filePath := filepath.Join(topicDir, filename)
	if err := os.WriteFile(filePath, data, 0644); err != nil {
		return "", err
	}

	return filepath.Join(topic, filename), nil
}

// storeInVault stores metadata via vault CLI
func storeInVault(mediaType, topic, originalFilename, storedFilename string,
	fileSize int64, mimeType, description, tags, contentText, contentJSON, sessionID string) (map[string]interface{}, error) {

	args := []string{
		"store",
		"--type", mediaType,
		"--topic", topic,
		"--original-filename", originalFilename,
		"--stored-filename", storedFilename,
	}

	if fileSize > 0 {
		args = append(args, "--file-size", fmt.Sprintf("%d", fileSize))
	}
	if mimeType != "" {
		args = append(args, "--mime-type", mimeType)
	}
	if description != "" {
		args = append(args, "--description", description)
	}
	if tags != "" {
		args = append(args, "--tags", tags)
	}
	// For large content, pipe via stdin to avoid "argument list too long"
	var stdinData string
	if contentText != "" {
		args = append(args, "--content-text-stdin")
		stdinData = contentText
	}
	if contentJSON != "" && contentText == "" {
		args = append(args, "--content-json-stdin")
		stdinData = contentJSON
	} else if contentJSON != "" {
		// Both present: contentText wins stdin, contentJSON stays as arg
		args = append(args, "--content-json", contentJSON)
	}
	if sessionID != "" {
		args = append(args, "--session-id", sessionID)
	}

	cmd := exec.Command("python3", filepath.Join(cfg.VaultDir, "../skills/media-vault/vault.py"))
	cmd.Args = append(cmd.Args, args...)

	if stdinData != "" {
		cmd.Stdin = strings.NewReader(stdinData)
	}

	output, err := cmd.Output()
	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			return nil, fmt.Errorf("vault error: %s", string(exitErr.Stderr))
		}
		return nil, err
	}

	var result map[string]interface{}
	if err := json.Unmarshal(output, &result); err != nil {
		return nil, err
	}

	return result, nil
}

// buildMediaContext builds context string for Clawdbot
func buildMediaContext(mediaID, mediaType string, analysis VisionAnalysis, userMessage string) string {
	var sb strings.Builder

	sb.WriteString(fmt.Sprintf("User uploaded %s (saved as %s in topic: %s).\n\n", mediaType, mediaID, analysis.Topic))
	sb.WriteString("Analysis:\n")
	sb.WriteString(fmt.Sprintf("- Description: %s\n", analysis.Description))

	if analysis.ExtractedText != "" {
		text := analysis.ExtractedText
		if len(text) > 500 {
			text = text[:500] + "..."
		}
		sb.WriteString(fmt.Sprintf("- Extracted text: \"%s\"\n", text))
	}

	if len(analysis.Tags) > 0 {
		sb.WriteString(fmt.Sprintf("- Tags: %s\n", strings.Join(analysis.Tags, ", ")))
	}

	sb.WriteString("\n")

	if userMessage != "" {
		sb.WriteString(fmt.Sprintf("User asks: %s", userMessage))
	} else {
		sb.WriteString("Please acknowledge what was saved and suggest any relevant actions.")
	}

	return sb.String()
}

// sanitizeFilename removes unsafe characters from filename
func sanitizeFilename(name string) string {
	// Replace spaces with underscores
	name = strings.ReplaceAll(name, " ", "_")

	// Remove or replace unsafe characters
	unsafe := []string{"/", "\\", ":", "*", "?", "\"", "<", ">", "|"}
	for _, char := range unsafe {
		name = strings.ReplaceAll(name, char, "_")
	}

	return name
}

// deleteExistingFile removes any existing vault entry with the same original_filename in the same topic.
// This enables clean replace-on-upload semantics. Best-effort: upload proceeds even if this fails.
func deleteExistingFile(topic, originalFilename string) {
	vaultPy := filepath.Join(cfg.VaultDir, "..", "skills", "media-vault", "vault.py")
	cmd := exec.Command("python3", vaultPy, "list", "--topic", topic, "--limit", "1000", "--offset", "0")
	output, err := cmd.Output()
	if err != nil {
		return
	}
	var items []map[string]interface{}
	if json.Unmarshal(output, &items) != nil {
		return
	}
	for _, item := range items {
		if fn, ok := item["original_filename"].(string); ok && fn == originalFilename {
			if id, ok := item["id"].(string); ok {
				log.Printf("Replacing existing file %s in topic %s (id=%s)", originalFilename, topic, id)
				delCmd := exec.Command("python3", vaultPy, "delete", "--id", id)
				delCmd.Run()
			}
		}
	}
}

// VaultItem represents a media item from the vault
type VaultItem struct {
	ID              string   `json:"id"`
	Type            string   `json:"type"`
	Topic           string   `json:"topic"`
	OriginalFilename string  `json:"original_filename"`
	StoredFilename  string   `json:"stored_filename"`
	FilePath        string   `json:"file_path"`
	FileSize        int64    `json:"file_size"`
	MimeType        string   `json:"mime_type"`
	Description     string   `json:"description"`
	Tags            []string `json:"tags"`
	ContentText     *string  `json:"content_text"`
	CreatedAt       string   `json:"created_at"`
}

// vaultFileHandler serves files from the vault
func vaultFileHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Extract ID from path: /api/vault/file/{id}
	path := r.URL.Path
	id := strings.TrimPrefix(path, "/api/vault/file/")
	if id == "" || id == path {
		jsonError(w, "Missing file ID", http.StatusBadRequest)
		return
	}

	// Get file info from vault
	cmd := exec.Command("python3",
		filepath.Join(cfg.VaultDir, "..", "skills", "media-vault", "vault.py"),
		"get", "--id", id, "--include-file")

	output, err := cmd.Output()
	if err != nil {
		log.Printf("Vault get error: %v", err)
		jsonError(w, "File not found", http.StatusNotFound)
		return
	}

	var item VaultItem
	if err := json.Unmarshal(output, &item); err != nil {
		log.Printf("Vault parse error: %v", err)
		jsonError(w, "Invalid vault response", http.StatusInternalServerError)
		return
	}

	// Construct full file path
	fullPath := filepath.Join(cfg.VaultDir, "files", item.FilePath)

	// Check file exists
	if _, err := os.Stat(fullPath); os.IsNotExist(err) {
		jsonError(w, "File not found on disk", http.StatusNotFound)
		return
	}

	// Set content type
	w.Header().Set("Content-Type", item.MimeType)
	w.Header().Set("Content-Disposition", fmt.Sprintf("inline; filename=\"%s\"", item.OriginalFilename))

	// Serve the file
	http.ServeFile(w, r, fullPath)
}

// vaultListHandler returns vault items as JSON
func vaultListHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Get query params
	query := r.URL.Query().Get("q")
	mediaType := r.URL.Query().Get("type")
	limit := r.URL.Query().Get("limit")
	if limit == "" {
		limit = "20"
	}

	var cmd *exec.Cmd
	vaultPy := filepath.Join(cfg.VaultDir, "..", "skills", "media-vault", "vault.py")

	if query != "" {
		cmd = exec.Command("python3", vaultPy, "search", "--query", query, "--limit", limit)
	} else {
		args := []string{vaultPy, "list", "--limit", limit}
		if mediaType != "" {
			args = append(args, "--type", mediaType)
		}
		cmd = exec.Command("python3", args...)
	}

	output, err := cmd.Output()
	if err != nil {
		log.Printf("Vault list error: %v", err)
		jsonError(w, "Vault query failed", http.StatusInternalServerError)
		return
	}

	// Parse and add URLs to each item
	var items []map[string]interface{}
	if err := json.Unmarshal(output, &items); err != nil {
		log.Printf("Vault parse error: %v", err)
		jsonError(w, "Invalid vault response", http.StatusInternalServerError)
		return
	}

	// Add URL to each item
	for i := range items {
		if id, ok := items[i]["id"].(string); ok {
			items[i]["url"] = "/api/vault/file/" + id
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(items)
}

// isValidVaultID validates the vault ID format (mv_ + 12 alphanumeric chars)
func isValidVaultID(id string) bool {
	if len(id) != 15 { // "mv_" + 12 chars
		return false
	}
	if !strings.HasPrefix(id, "mv_") {
		return false
	}
	for _, c := range id[3:] {
		if !((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9')) {
			return false
		}
	}
	return true
}

// validateDimension validates dimension values for image/video processing
func validateDimension(dim string) (string, error) {
	if dim == "" || dim == "-1" {
		return dim, nil
	}
	// Remove any non-digit characters except for -1
	for _, c := range dim {
		if !((c >= '0' && c <= '9') || c == '-') {
			return "", fmt.Errorf("invalid dimension: contains non-numeric characters")
		}
	}
	// Parse as integer
	n, err := strconv.Atoi(dim)
	if err != nil {
		return "", fmt.Errorf("invalid dimension: %s", dim)
	}
	if n < -1 || n > 10000 {
		return "", fmt.Errorf("dimension out of range: %d", n)
	}
	return dim, nil
}

// validateTimestamp validates timestamp format (HH:MM:SS or MM:SS)
func validateTimestamp(ts string) (string, error) {
	if ts == "" {
		return "00:00:01", nil
	}
	// Simple validation: only digits and colons
	for _, c := range ts {
		if !((c >= '0' && c <= '9') || c == ':') {
			return "", fmt.Errorf("invalid timestamp: %s", ts)
		}
	}
	// Check format
	parts := strings.Split(ts, ":")
	if len(parts) < 2 || len(parts) > 3 {
		return "", fmt.Errorf("invalid timestamp format: %s", ts)
	}
	return ts, nil
}

// vaultThumbHandler serves thumbnails for vault items
func vaultThumbHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Extract ID from path: /api/vault/thumb/{id}
	path := r.URL.Path
	id := strings.TrimPrefix(path, "/api/vault/thumb/")
	if id == "" || id == path {
		jsonError(w, "Missing file ID", http.StatusBadRequest)
		return
	}

	// Check if thumbnail exists
	thumbPath := filepath.Join(cfg.VaultDir, "thumbs", id+".jpg")

	if _, err := os.Stat(thumbPath); os.IsNotExist(err) {
		// Try to generate thumbnail on-demand
		cmd := exec.Command("python3",
			filepath.Join(cfg.VaultDir, "..", "skills", "media-vault", "vault.py"),
			"thumbnail", "--id", id)

		if output, err := cmd.Output(); err == nil {
			var result map[string]interface{}
			if json.Unmarshal(output, &result) == nil {
				if thumbResult, ok := result["thumbnail"].(string); ok {
					thumbPath = thumbResult
				}
			}
		}
	}

	// Check again after potential generation
	if _, err := os.Stat(thumbPath); os.IsNotExist(err) {
		jsonError(w, "Thumbnail not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "image/jpeg")
	w.Header().Set("Cache-Control", "public, max-age=86400") // Cache for 24 hours
	http.ServeFile(w, r, thumbPath)
}

// MediaConvertRequest for document conversion
type MediaConvertRequest struct {
	SourceID     string            `json:"source_id"`              // Vault file ID (required)
	TargetFormat string            `json:"target_format"`          // pdf, docx, html, txt, etc.
	Options      map[string]string `json:"options,omitempty"`      // Additional conversion options
}

// MediaConvertResponse returned after conversion
type MediaConvertResponse struct {
	Success    bool   `json:"success"`
	OutputPath string `json:"output_path"`
	OutputURL  string `json:"output_url,omitempty"`
	OutputID   string `json:"output_id,omitempty"`
	Error      string `json:"error,omitempty"`
}

// mediaConvertHandler handles POST /api/media/convert
// Converts documents between formats using pandoc and other tools
func mediaConvertHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req MediaConvertRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		jsonError(w, "Invalid request: "+err.Error(), http.StatusBadRequest)
		return
	}

	if req.TargetFormat == "" {
		jsonError(w, "target_format is required", http.StatusBadRequest)
		return
	}

	// Validate source_id is required
	if req.SourceID == "" {
		jsonError(w, "source_id is required", http.StatusBadRequest)
		return
	}

	// Validate source_id format (mv_ + 12 alphanumeric chars)
	if !isValidVaultID(req.SourceID) {
		jsonError(w, "Invalid source_id format", http.StatusBadRequest)
		return
	}

	// Get source file from vault
	var sourcePath string
	var sourceItem VaultItem

	cmd := exec.Command("python3",
		filepath.Join(cfg.VaultDir, "..", "skills", "media-vault", "vault.py"),
		"get", "--id", req.SourceID)

	output, err := cmd.Output()
	if err != nil {
		jsonError(w, "Source file not found", http.StatusNotFound)
		return
	}

	if err := json.Unmarshal(output, &sourceItem); err != nil {
		jsonError(w, "Invalid vault response", http.StatusInternalServerError)
		return
	}
	sourcePath = filepath.Join(cfg.VaultDir, "files", sourceItem.FilePath)

	// Check source exists
	if _, err := os.Stat(sourcePath); os.IsNotExist(err) {
		jsonError(w, "Source file not found", http.StatusNotFound)
		return
	}

	// Determine output path
	sourceExt := filepath.Ext(sourcePath)
	baseName := strings.TrimSuffix(filepath.Base(sourcePath), sourceExt)
	outputFilename := baseName + "." + req.TargetFormat

	// Create temp output directory
	tmpDir, err := os.MkdirTemp("", "convert-*")
	if err != nil {
		jsonError(w, "Failed to create temp directory", http.StatusInternalServerError)
		return
	}
	defer os.RemoveAll(tmpDir)

	outputPath := filepath.Join(tmpDir, outputFilename)

	// Perform conversion based on format
	var convertErr error
	switch req.TargetFormat {
	case "pdf":
		convertErr = convertToPDF(sourcePath, outputPath, req.Options)
	case "html":
		convertErr = convertWithPandoc(sourcePath, outputPath, "html")
	case "docx":
		convertErr = convertWithPandoc(sourcePath, outputPath, "docx")
	case "txt", "text":
		convertErr = convertToText(sourcePath, outputPath)
	case "md", "markdown":
		convertErr = convertWithPandoc(sourcePath, outputPath, "markdown")
	default:
		// Try pandoc for unknown formats
		convertErr = convertWithPandoc(sourcePath, outputPath, req.TargetFormat)
	}

	if convertErr != nil {
		jsonError(w, "Conversion failed: "+convertErr.Error(), http.StatusInternalServerError)
		return
	}

	// Read output file
	outputData, err := os.ReadFile(outputPath)
	if err != nil {
		jsonError(w, "Failed to read output file", http.StatusInternalServerError)
		return
	}

	// Determine topic for output (same as source or "converted")
	topic := "converted"
	if sourceItem.Topic != "" {
		topic = sourceItem.Topic
	}

	// Save to vault
	datePrefix := time.Now().Format("20060102")
	storedFilename := datePrefix + "_" + sanitizeFilename(outputFilename)

	filePath, err := saveToVault(outputData, topic, storedFilename)
	if err != nil {
		jsonError(w, "Failed to save output: "+err.Error(), http.StatusInternalServerError)
		return
	}

	// Store metadata
	mimeType := getMimeType(req.TargetFormat)
	vaultResult, err := storeInVault(
		"document",
		topic,
		outputFilename,
		storedFilename,
		int64(len(outputData)),
		mimeType,
		fmt.Sprintf("Converted from %s", filepath.Base(sourcePath)),
		"converted",
		"",
		"",
		"",
	)
	if err != nil {
		log.Printf("Vault store error: %v", err)
	}

	response := MediaConvertResponse{
		Success:    true,
		OutputPath: filePath,
	}

	if vaultResult != nil {
		if id, ok := vaultResult["id"].(string); ok {
			response.OutputID = id
			response.OutputURL = "/api/vault/file/" + id
		}
	}

	jsonResponse(w, response)
}

// convertToPDF converts various formats to PDF
func convertToPDF(input, output string, options map[string]string) error {
	ext := strings.ToLower(filepath.Ext(input))

	switch ext {
	case ".md", ".markdown", ".txt", ".html", ".htm":
		// Use pandoc with wkhtmltopdf or pdflatex
		return convertWithPandoc(input, output, "pdf")
	case ".doc", ".docx", ".odt":
		// Use libreoffice if available, otherwise pandoc
		if _, err := exec.LookPath("libreoffice"); err == nil {
			cmd := exec.Command("libreoffice", "--headless", "--convert-to", "pdf", "--outdir", filepath.Dir(output), input)
			return cmd.Run()
		}
		return convertWithPandoc(input, output, "pdf")
	default:
		return convertWithPandoc(input, output, "pdf")
	}
}

// convertWithPandoc uses pandoc for format conversion
func convertWithPandoc(input, output, format string) error {
	args := []string{"-o", output}

	// Add format-specific options
	switch format {
	case "pdf":
		args = append(args, "--pdf-engine=wkhtmltopdf")
	case "html":
		args = append(args, "-s") // Standalone HTML
	}

	args = append(args, input)

	cmd := exec.Command("pandoc", args...)
	outputBytes, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("%v: %s", err, string(outputBytes))
	}
	return nil
}

// convertToText extracts plain text from various formats
func convertToText(input, output string) error {
	ext := strings.ToLower(filepath.Ext(input))

	var text []byte
	var err error

	switch ext {
	case ".pdf":
		cmd := exec.Command("pdftotext", input, "-")
		text, err = cmd.Output()
	case ".doc", ".docx":
		// Try pandoc
		cmd := exec.Command("pandoc", "-t", "plain", input)
		text, err = cmd.Output()
	default:
		// Just copy the file
		text, err = os.ReadFile(input)
	}

	if err != nil {
		return err
	}

	return os.WriteFile(output, text, 0644)
}

// getMimeType returns MIME type for format
func getMimeType(format string) string {
	mimeTypes := map[string]string{
		"pdf":      "application/pdf",
		"html":     "text/html",
		"htm":      "text/html",
		"docx":     "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
		"doc":      "application/msword",
		"txt":      "text/plain",
		"text":     "text/plain",
		"md":       "text/markdown",
		"markdown": "text/markdown",
		"json":     "application/json",
		"xml":      "application/xml",
	}

	if mime, ok := mimeTypes[format]; ok {
		return mime
	}
	return "application/octet-stream"
}

// MediaProcessRequest for image/video processing
type MediaProcessRequest struct {
	SourceID  string            `json:"source_id"`            // Vault file ID (required)
	Operation string            `json:"operation"`            // resize, crop, rotate, compress, thumbnail
	Options   map[string]string `json:"options,omitempty"`    // width, height, quality, etc.
}

// MediaProcessResponse returned after processing
type MediaProcessResponse struct {
	Success    bool   `json:"success"`
	OutputPath string `json:"output_path"`
	OutputURL  string `json:"output_url,omitempty"`
	OutputID   string `json:"output_id,omitempty"`
	Error      string `json:"error,omitempty"`
}

// mediaProcessHandler handles POST /api/media/process
// Processes images and videos (resize, crop, compress, etc.)
func mediaProcessHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req MediaProcessRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		jsonError(w, "Invalid request: "+err.Error(), http.StatusBadRequest)
		return
	}

	if req.Operation == "" {
		jsonError(w, "operation is required", http.StatusBadRequest)
		return
	}

	// Validate source_id is required
	if req.SourceID == "" {
		jsonError(w, "source_id is required", http.StatusBadRequest)
		return
	}

	if !isValidVaultID(req.SourceID) {
		jsonError(w, "Invalid source_id format", http.StatusBadRequest)
		return
	}

	// Validate options for command injection prevention
	if req.Options != nil {
		if width, ok := req.Options["width"]; ok {
			if _, err := validateDimension(width); err != nil {
				jsonError(w, "Invalid width: "+err.Error(), http.StatusBadRequest)
				return
			}
		}
		if height, ok := req.Options["height"]; ok {
			if _, err := validateDimension(height); err != nil {
				jsonError(w, "Invalid height: "+err.Error(), http.StatusBadRequest)
				return
			}
		}
	}

	// Get source file from vault
	var sourcePath string
	var sourceItem VaultItem

	cmd := exec.Command("python3",
		filepath.Join(cfg.VaultDir, "..", "skills", "media-vault", "vault.py"),
		"get", "--id", req.SourceID)

	output, err := cmd.Output()
	if err != nil {
		jsonError(w, "Source file not found", http.StatusNotFound)
		return
	}

	if err := json.Unmarshal(output, &sourceItem); err != nil {
		jsonError(w, "Invalid vault response", http.StatusInternalServerError)
		return
	}
	sourcePath = filepath.Join(cfg.VaultDir, "files", sourceItem.FilePath)

	// Check source exists
	if _, err := os.Stat(sourcePath); os.IsNotExist(err) {
		jsonError(w, "Source file not found", http.StatusNotFound)
		return
	}

	// Determine media type
	ext := strings.ToLower(filepath.Ext(sourcePath))
	isVideo := ext == ".mp4" || ext == ".mov" || ext == ".avi" || ext == ".webm" || ext == ".mkv"
	isImage := ext == ".jpg" || ext == ".jpeg" || ext == ".png" || ext == ".gif" || ext == ".webp"

	if !isVideo && !isImage {
		jsonError(w, "Unsupported media type", http.StatusBadRequest)
		return
	}

	// Create temp output
	tmpDir, err := os.MkdirTemp("", "process-*")
	if err != nil {
		jsonError(w, "Failed to create temp directory", http.StatusInternalServerError)
		return
	}
	defer os.RemoveAll(tmpDir)

	outputFilename := filepath.Base(sourcePath)
	outputPath := filepath.Join(tmpDir, outputFilename)

	// Perform processing
	var processErr error
	if isImage {
		processErr = processImage2(sourcePath, outputPath, req.Operation, req.Options)
	} else {
		processErr = processVideo(sourcePath, outputPath, req.Operation, req.Options)
	}

	if processErr != nil {
		jsonError(w, "Processing failed: "+processErr.Error(), http.StatusInternalServerError)
		return
	}

	// Read output file
	outputData, err := os.ReadFile(outputPath)
	if err != nil {
		jsonError(w, "Failed to read output file", http.StatusInternalServerError)
		return
	}

	// Save to vault
	topic := "processed"
	if sourceItem.Topic != "" {
		topic = sourceItem.Topic
	}

	datePrefix := time.Now().Format("20060102")
	storedFilename := datePrefix + "_" + req.Operation + "_" + sanitizeFilename(outputFilename)

	filePath, err := saveToVault(outputData, topic, storedFilename)
	if err != nil {
		jsonError(w, "Failed to save output: "+err.Error(), http.StatusInternalServerError)
		return
	}

	// Store metadata
	mediaType := "image"
	if isVideo {
		mediaType = "video"
	}

	vaultResult, err := storeInVault(
		mediaType,
		topic,
		outputFilename,
		storedFilename,
		int64(len(outputData)),
		sourceItem.MimeType,
		fmt.Sprintf("%s of %s", req.Operation, filepath.Base(sourcePath)),
		req.Operation,
		"",
		"",
		"",
	)
	if err != nil {
		log.Printf("Vault store error: %v", err)
	}

	response := MediaProcessResponse{
		Success:    true,
		OutputPath: filePath,
	}

	if vaultResult != nil {
		if id, ok := vaultResult["id"].(string); ok {
			response.OutputID = id
			response.OutputURL = "/api/vault/file/" + id
		}
	}

	jsonResponse(w, response)
}

// processImage2 processes an image using ImageMagick convert
func processImage2(input, output, operation string, options map[string]string) error {
	args := []string{input}

	switch operation {
	case "resize":
		width := options["width"]
		height := options["height"]
		if width != "" || height != "" {
			size := width
			if height != "" {
				if width != "" {
					size = width + "x" + height
				} else {
					size = "x" + height
				}
			}
			args = append(args, "-resize", size)
		}
	case "crop":
		geometry := options["geometry"] // e.g., "100x100+10+10"
		if geometry != "" {
			args = append(args, "-crop", geometry)
		}
	case "rotate":
		degrees := options["degrees"]
		if degrees != "" {
			args = append(args, "-rotate", degrees)
		}
	case "compress":
		quality := options["quality"]
		if quality == "" {
			quality = "85"
		}
		args = append(args, "-quality", quality)
	case "thumbnail":
		size := options["size"]
		if size == "" {
			size = "200x200"
		}
		args = append(args, "-thumbnail", size)
	case "grayscale":
		args = append(args, "-colorspace", "Gray")
	case "optimize":
		args = append(args, "-strip", "-quality", "85")
	default:
		return fmt.Errorf("unknown operation: %s", operation)
	}

	args = append(args, output)

	cmd := exec.Command("convert", args...)
	outputBytes, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("%v: %s", err, string(outputBytes))
	}
	return nil
}

// processVideo processes a video using ffmpeg
func processVideo(input, output, operation string, options map[string]string) error {
	args := []string{"-i", input, "-y"}

	switch operation {
	case "resize":
		width := options["width"]
		height := options["height"]
		if width != "" && height != "" {
			args = append(args, "-vf", fmt.Sprintf("scale=%s:%s", width, height))
		} else if width != "" {
			args = append(args, "-vf", fmt.Sprintf("scale=%s:-1", width))
		} else if height != "" {
			args = append(args, "-vf", fmt.Sprintf("scale=-1:%s", height))
		}
	case "compress":
		crf := options["crf"]
		if crf == "" {
			crf = "28" // Default compression level
		}
		args = append(args, "-crf", crf)
	case "thumbnail":
		timestamp := options["timestamp"]
		if timestamp == "" {
			timestamp = "00:00:01"
		}
		size := options["size"]
		if size == "" {
			size = "320:-1"
		}
		args = append(args, "-ss", timestamp, "-vframes", "1", "-vf", fmt.Sprintf("scale=%s", size))
		// Change output to jpg for thumbnail
		output = strings.TrimSuffix(output, filepath.Ext(output)) + ".jpg"
	case "rotate":
		degrees := options["degrees"]
		switch degrees {
		case "90":
			args = append(args, "-vf", "transpose=1")
		case "180":
			args = append(args, "-vf", "transpose=1,transpose=1")
		case "270":
			args = append(args, "-vf", "transpose=2")
		}
	case "trim":
		start := options["start"]
		end := options["end"]
		duration := options["duration"]
		if start != "" {
			args = append(args, "-ss", start)
		}
		if duration != "" {
			args = append(args, "-t", duration)
		} else if end != "" {
			args = append(args, "-to", end)
		}
		args = append(args, "-c", "copy")
	default:
		return fmt.Errorf("unknown operation: %s", operation)
	}

	args = append(args, output)

	cmd := exec.Command("ffmpeg", args...)
	outputBytes, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("%v: %s", err, string(outputBytes))
	}
	return nil
}

// MediaExtractRequest for extracting audio/thumbnail from media
type MediaExtractRequest struct {
	SourceID string            `json:"source_id"`         // Vault file ID (required)
	Extract  string            `json:"extract"`           // audio, thumbnail, frames
	Options  map[string]string `json:"options,omitempty"` // format, timestamp, interval, etc.
}

// MediaExtractResponse returned after extraction
type MediaExtractResponse struct {
	Success    bool     `json:"success"`
	OutputPath string   `json:"output_path"`
	OutputURL  string   `json:"output_url,omitempty"`
	OutputID   string   `json:"output_id,omitempty"`
	Outputs    []string `json:"outputs,omitempty"` // For multiple outputs (frames)
	Error      string   `json:"error,omitempty"`
}

// mediaExtractHandler handles POST /api/media/extract
// Extracts audio, thumbnails, or frames from video files
func mediaExtractHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req MediaExtractRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		jsonError(w, "Invalid request: "+err.Error(), http.StatusBadRequest)
		return
	}

	if req.Extract == "" {
		jsonError(w, "extract is required (audio, thumbnail, frames)", http.StatusBadRequest)
		return
	}

	// Validate source_id is required
	if req.SourceID == "" {
		jsonError(w, "source_id is required", http.StatusBadRequest)
		return
	}

	if !isValidVaultID(req.SourceID) {
		jsonError(w, "Invalid source_id format", http.StatusBadRequest)
		return
	}

	// Validate timestamp if provided
	if ts, ok := req.Options["timestamp"]; ok {
		if _, err := validateTimestamp(ts); err != nil {
			jsonError(w, "Invalid timestamp: "+err.Error(), http.StatusBadRequest)
			return
		}
	}

	// Get source file from vault
	var sourcePath string
	var sourceItem VaultItem

	cmd := exec.Command("python3",
		filepath.Join(cfg.VaultDir, "..", "skills", "media-vault", "vault.py"),
		"get", "--id", req.SourceID)

	output, err := cmd.Output()
	if err != nil {
		jsonError(w, "Source file not found", http.StatusNotFound)
		return
	}

	if err := json.Unmarshal(output, &sourceItem); err != nil {
		jsonError(w, "Invalid vault response", http.StatusInternalServerError)
		return
	}
	sourcePath = filepath.Join(cfg.VaultDir, "files", sourceItem.FilePath)

	// Check source exists
	if _, err := os.Stat(sourcePath); os.IsNotExist(err) {
		jsonError(w, "Source file not found", http.StatusNotFound)
		return
	}

	// Create temp output directory
	tmpDir, err := os.MkdirTemp("", "extract-*")
	if err != nil {
		jsonError(w, "Failed to create temp directory", http.StatusInternalServerError)
		return
	}
	defer os.RemoveAll(tmpDir)

	baseName := strings.TrimSuffix(filepath.Base(sourcePath), filepath.Ext(sourcePath))

	var outputPath string
	var extractErr error

	switch req.Extract {
	case "audio":
		format := req.Options["format"]
		if format == "" {
			format = "mp3"
		}
		outputPath = filepath.Join(tmpDir, baseName+"."+format)
		extractErr = extractAudio(sourcePath, outputPath, format)

	case "thumbnail":
		timestamp := req.Options["timestamp"]
		if timestamp == "" {
			timestamp = "00:00:01"
		}
		outputPath = filepath.Join(tmpDir, baseName+"_thumb.jpg")
		extractErr = extractThumbnail(sourcePath, outputPath, timestamp)

	case "frames":
		interval := req.Options["interval"]
		if interval == "" {
			interval = "1" // One frame per second
		}
		outputPath = filepath.Join(tmpDir, baseName+"_frame_%04d.jpg")
		extractErr = extractFrames(sourcePath, outputPath, interval)

	default:
		jsonError(w, "Unknown extract type: "+req.Extract, http.StatusBadRequest)
		return
	}

	if extractErr != nil {
		jsonError(w, "Extraction failed: "+extractErr.Error(), http.StatusInternalServerError)
		return
	}

	// For frames, we have multiple outputs
	if req.Extract == "frames" {
		// List all generated frames
		frames, _ := filepath.Glob(filepath.Join(tmpDir, baseName+"_frame_*.jpg"))
		jsonResponse(w, MediaExtractResponse{
			Success: true,
			Outputs: frames,
		})
		return
	}

	// Read output file
	outputData, err := os.ReadFile(outputPath)
	if err != nil {
		jsonError(w, "Failed to read output file", http.StatusInternalServerError)
		return
	}

	// Save to vault
	topic := "extracted"
	if sourceItem.Topic != "" {
		topic = sourceItem.Topic
	}

	datePrefix := time.Now().Format("20060102")
	storedFilename := datePrefix + "_" + sanitizeFilename(filepath.Base(outputPath))

	filePath, err := saveToVault(outputData, topic, storedFilename)
	if err != nil {
		jsonError(w, "Failed to save output: "+err.Error(), http.StatusInternalServerError)
		return
	}

	// Determine media type and mime
	mediaType := "audio"
	mimeType := "audio/mpeg"
	if req.Extract == "thumbnail" {
		mediaType = "image"
		mimeType = "image/jpeg"
	}

	vaultResult, err := storeInVault(
		mediaType,
		topic,
		filepath.Base(outputPath),
		storedFilename,
		int64(len(outputData)),
		mimeType,
		fmt.Sprintf("Extracted %s from %s", req.Extract, filepath.Base(sourcePath)),
		req.Extract,
		"",
		"",
		"",
	)
	if err != nil {
		log.Printf("Vault store error: %v", err)
	}

	response := MediaExtractResponse{
		Success:    true,
		OutputPath: filePath,
	}

	if vaultResult != nil {
		if id, ok := vaultResult["id"].(string); ok {
			response.OutputID = id
			response.OutputURL = "/api/vault/file/" + id
		}
	}

	jsonResponse(w, response)
}

// extractAudio extracts audio from video using ffmpeg
func extractAudio(input, output, format string) error {
	args := []string{"-i", input, "-vn", "-y"}

	switch format {
	case "mp3":
		args = append(args, "-acodec", "libmp3lame", "-q:a", "2")
	case "wav":
		args = append(args, "-acodec", "pcm_s16le")
	case "aac":
		args = append(args, "-acodec", "aac", "-b:a", "192k")
	case "ogg":
		args = append(args, "-acodec", "libvorbis", "-q:a", "5")
	default:
		args = append(args, "-acodec", "libmp3lame")
	}

	args = append(args, output)

	cmd := exec.Command("ffmpeg", args...)
	outputBytes, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("%v: %s", err, string(outputBytes))
	}
	return nil
}

// extractThumbnail extracts a single frame as thumbnail
func extractThumbnail(input, output, timestamp string) error {
	args := []string{
		"-i", input,
		"-ss", timestamp,
		"-vframes", "1",
		"-q:v", "2",
		"-y",
		output,
	}

	cmd := exec.Command("ffmpeg", args...)
	outputBytes, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("%v: %s", err, string(outputBytes))
	}
	return nil
}

// extractFrames extracts multiple frames at specified interval
func extractFrames(input, outputPattern, interval string) error {
	args := []string{
		"-i", input,
		"-vf", fmt.Sprintf("fps=1/%s", interval),
		"-q:v", "2",
		"-y",
		outputPattern,
	}

	cmd := exec.Command("ffmpeg", args...)
	outputBytes, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("%v: %s", err, string(outputBytes))
	}
	return nil
}
