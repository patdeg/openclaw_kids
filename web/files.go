package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// Note: All handlers in this file are used via http.HandleFunc in main.go

// sanitizeTopic validates and cleans a topic name to prevent path traversal.
// Returns the cleaned topic and true if valid, or empty string and false if invalid.
func sanitizeTopic(topic string) (string, bool) {
	topic = strings.TrimSpace(topic)
	if topic == "" {
		return "", true
	}
	// Reject path traversal attempts
	if strings.Contains(topic, "..") || strings.Contains(topic, "/") || strings.Contains(topic, "\\") || strings.ContainsAny(topic, "\x00") {
		return "", false
	}
	return topic, true
}

// vaultTopicsHandler returns topics with counts, plus root VAULT.md if exists
func vaultTopicsHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	vaultPy := filepath.Join(cfg.VaultDir, "..", "skills", "media-vault", "vault.py")
	cmd := exec.Command("python3", vaultPy, "topics", "--counts")

	output, err := cmd.Output()
	if err != nil {
		log.Printf("Vault topics error: %v", err)
		jsonError(w, "Failed to get topics", http.StatusInternalServerError)
		return
	}

	// Parse topics and add root VAULT.md if exists
	var topics []map[string]interface{}
	if err := json.Unmarshal(output, &topics); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.Write(output)
		return
	}

	// Check for root VAULT.md
	vaultMdPath := filepath.Join(cfg.VaultDir, "VAULT.md")
	if info, err := os.Stat(vaultMdPath); err == nil {
		vaultMdEntry := map[string]interface{}{
			"id":                "vault-md-root",
			"type":              "document",
			"topic":             "",
			"original_filename": "VAULT.md",
			"stored_filename":   "VAULT.md",
			"file_size":         info.Size(),
			"mime_type":         "text/markdown",
			"description":       "Vault overview and AI context",
			"is_vault_md":       true,
			"url":               "/api/vault/vault-md/",
		}
		// Prepend VAULT.md to response
		result := map[string]interface{}{
			"topics":   topics,
			"vault_md": vaultMdEntry,
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(result)
		return
	}

	// No VAULT.md, return just topics wrapped
	result := map[string]interface{}{
		"topics":   topics,
		"vault_md": nil,
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(result)
}

// vaultTopicDispatcher routes topic requests by method
func vaultTopicDispatcher(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		vaultTopicFilesHandler(w, r)
	case http.MethodDelete:
		vaultDeleteTopicHandler(w, r)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

// vaultTopicFilesHandler returns files in a specific topic
func vaultTopicFilesHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Extract topic from path: /api/vault/topic/{name}
	path := r.URL.Path
	topic := strings.TrimPrefix(path, "/api/vault/topic/")
	if topic == "" || topic == path {
		jsonError(w, "Missing topic name", http.StatusBadRequest)
		return
	}
	topic, ok := sanitizeTopic(topic)
	if !ok {
		jsonError(w, "Invalid topic name", http.StatusBadRequest)
		return
	}

	limit := r.URL.Query().Get("limit")
	if limit == "" {
		limit = "100"
	}
	offset := r.URL.Query().Get("offset")
	if offset == "" {
		offset = "0"
	}

	vaultPy := filepath.Join(cfg.VaultDir, "..", "skills", "media-vault", "vault.py")
	cmd := exec.Command("python3", vaultPy, "list", "--topic", topic, "--limit", limit, "--offset", offset)

	output, err := cmd.Output()
	if err != nil {
		log.Printf("Vault topic files error: %v", err)
		jsonError(w, "Failed to get files", http.StatusInternalServerError)
		return
	}

	// Parse and add URLs
	var items []map[string]interface{}
	if err := json.Unmarshal(output, &items); err != nil {
		jsonError(w, "Invalid response", http.StatusInternalServerError)
		return
	}

	for i := range items {
		if id, ok := items[i]["id"].(string); ok {
			items[i]["url"] = "/api/vault/file/" + id
		}
	}

	// Check for topic VAULT.md and include it
	vaultMdPath := filepath.Join(cfg.VaultDir, "files", topic, "VAULT.md")
	var vaultMdEntry map[string]interface{}
	if info, err := os.Stat(vaultMdPath); err == nil {
		vaultMdEntry = map[string]interface{}{
			"id":                "vault_md_" + topic,
			"original_filename": "VAULT.md",
			"stored_filename":   "VAULT.md",
			"type":              "document",
			"topic":             topic,
			"file_size":         info.Size(),
			"is_vault_md":       true,
		}
	}

	// Return as object with files and vault_md
	response := map[string]interface{}{
		"files":    items,
		"vault_md": vaultMdEntry,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// vaultStatsHandler returns vault statistics
func vaultStatsHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	vaultPy := filepath.Join(cfg.VaultDir, "..", "skills", "media-vault", "vault.py")
	cmd := exec.Command("python3", vaultPy, "stats")

	output, err := cmd.Output()
	if err != nil {
		log.Printf("Vault stats error: %v", err)
		jsonError(w, "Failed to get stats", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Write(output)
}

// vaultUpdateHandler updates file metadata
func vaultUpdateHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPatch {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Extract ID from path: /api/vault/file/{id}
	path := r.URL.Path
	id := strings.TrimPrefix(path, "/api/vault/file/")
	if id == "" || id == path || strings.Contains(id, "/") {
		jsonError(w, "Missing file ID", http.StatusBadRequest)
		return
	}

	var req struct {
		Description *string `json:"description"`
		Tags        *string `json:"tags"`
		Filename    *string `json:"filename"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		jsonError(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	vaultPy := filepath.Join(cfg.VaultDir, "..", "skills", "media-vault", "vault.py")

	// Handle rename separately
	if req.Filename != nil {
		cleanFilename := sanitizeFilename(*req.Filename)
		if cleanFilename == "" || strings.Contains(*req.Filename, "..") || strings.ContainsAny(*req.Filename, "/\\\x00\r\n") {
			jsonError(w, "Invalid filename", http.StatusBadRequest)
			return
		}
		cmd := exec.Command("python3", vaultPy, "rename", "--id", id, "--filename", cleanFilename)
		if output, err := cmd.Output(); err != nil {
			log.Printf("Vault rename error: %v", err)
			jsonError(w, "Rename failed", http.StatusInternalServerError)
			return
		} else {
			w.Header().Set("Content-Type", "application/json")
			w.Write(output)
			return
		}
	}

	// Handle metadata update
	args := []string{"update", "--id", id}
	if req.Description != nil {
		args = append(args, "--description", *req.Description)
	}
	if req.Tags != nil {
		args = append(args, "--tags", *req.Tags)
	}

	if len(args) == 3 {
		jsonError(w, "No updates provided", http.StatusBadRequest)
		return
	}

	cmd := exec.Command("python3", vaultPy)
	cmd.Args = append(cmd.Args, args...)

	output, err := cmd.Output()
	if err != nil {
		log.Printf("Vault update error: %v", err)
		jsonError(w, "Update failed", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Write(output)
}

// vaultMoveHandler moves a file to a different topic
func vaultMoveHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Extract ID from path: /api/vault/file/{id}/move
	path := r.URL.Path
	path = strings.TrimSuffix(path, "/move")
	id := strings.TrimPrefix(path, "/api/vault/file/")
	if id == "" || id == path {
		jsonError(w, "Missing file ID", http.StatusBadRequest)
		return
	}

	var req struct {
		Topic string `json:"topic"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.Topic == "" {
		jsonError(w, "Topic required", http.StatusBadRequest)
		return
	}

	topic, ok := sanitizeTopic(req.Topic)
	if !ok {
		jsonError(w, "Invalid topic name", http.StatusBadRequest)
		return
	}

	vaultPy := filepath.Join(cfg.VaultDir, "..", "skills", "media-vault", "vault.py")
	cmd := exec.Command("python3", vaultPy, "move", "--id", id, "--topic", topic)

	output, err := cmd.Output()
	if err != nil {
		log.Printf("Vault move error: %v", err)
		jsonError(w, "Move failed", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Write(output)
}

// vaultDeleteHandler deletes a single file
func vaultDeleteHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodDelete {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Extract ID from path: /api/vault/file/{id}
	path := r.URL.Path
	id := strings.TrimPrefix(path, "/api/vault/file/")
	if id == "" || id == path || strings.Contains(id, "/") {
		jsonError(w, "Missing file ID", http.StatusBadRequest)
		return
	}

	logInfo("Delete file: "+id, "vault", "")

	vaultPy := filepath.Join(cfg.VaultDir, "..", "skills", "media-vault", "vault.py")
	cmd := exec.Command("python3", vaultPy, "delete", "--id", id)

	output, err := cmd.Output()
	if err != nil {
		log.Printf("Vault delete error: %v", err)
		logError("Delete failed: "+id, "vault", "")
		jsonError(w, "Delete failed", http.StatusInternalServerError)
		return
	}

	// Trigger VAULT.md regeneration in background
	var result map[string]any
	if json.Unmarshal(output, &result) == nil {
		if topic, ok := result["topic"].(string); ok && topic != "" {
			go func() {
				regenCmd := exec.Command("python3", vaultPy, "generate-vault-md", "--topic", topic)
				if err := regenCmd.Run(); err != nil {
					log.Printf("VAULT.md regeneration failed for %s: %v", topic, err)
				}
			}()
		}
	}

	w.Header().Set("Content-Type", "application/json")
	w.Write(output)
}

// vaultCreateTopicHandler creates an empty topic
func vaultCreateTopicHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Name string `json:"name"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.Name == "" {
		jsonError(w, "Topic name required", http.StatusBadRequest)
		return
	}

	name, ok := sanitizeTopic(req.Name)
	if !ok || name == "" {
		jsonError(w, "Invalid topic name", http.StatusBadRequest)
		return
	}

	vaultPy := filepath.Join(cfg.VaultDir, "..", "skills", "media-vault", "vault.py")
	cmd := exec.Command("python3", vaultPy, "create-topic", "--name", name)

	output, err := cmd.Output()
	if err != nil {
		log.Printf("Vault create topic error: %v", err)
		jsonError(w, "Failed to create topic", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Write(output)
}

// vaultDeleteTopicHandler deletes a topic with cascade delete
func vaultDeleteTopicHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodDelete {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Extract topic name from path: /api/vault/topic/{name}
	path := r.URL.Path
	name := strings.TrimPrefix(path, "/api/vault/topic/")
	if name == "" || name == path {
		jsonError(w, "Missing topic name", http.StatusBadRequest)
		return
	}
	name, ok := sanitizeTopic(name)
	if !ok {
		jsonError(w, "Invalid topic name", http.StatusBadRequest)
		return
	}

	// Check for force parameter
	force := r.URL.Query().Get("force") == "1"

	vaultPy := filepath.Join(cfg.VaultDir, "..", "skills", "media-vault", "vault.py")
	args := []string{vaultPy, "delete-topic", "--name", name}
	if force {
		args = append(args, "--force")
	}
	cmd := exec.Command("python3", args...)

	output, err := cmd.Output()
	if err != nil {
		log.Printf("Vault delete topic error: %v", err)
		// Try to get stderr for more info
		if exitErr, ok := err.(*exec.ExitError); ok {
			log.Printf("Stderr: %s", string(exitErr.Stderr))
		}
		// Check if output has JSON error we can parse
		if len(output) > 0 {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusConflict)
			w.Write(output)
			return
		}
		jsonError(w, "Failed to delete topic", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Write(output)
}

// vaultGenerateVaultMdHandler generates VAULT.md for a topic or root
func vaultGenerateVaultMdHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Extract topic from path: /api/vault/vault-md/{topic}/generate or /api/vault/vault-md/generate
	path := r.URL.Path
	topic := ""
	if strings.HasSuffix(path, "/generate") {
		path = strings.TrimSuffix(path, "/generate")
		topic = strings.TrimPrefix(path, "/api/vault/vault-md/")
		if topic == path || topic == "" {
			topic = "" // Root
		}
	}

	vaultPy := filepath.Join(cfg.VaultDir, "..", "skills", "media-vault", "vault.py")
	args := []string{vaultPy, "generate-vault-md"}
	if topic != "" {
		args = append(args, "--topic", topic)
	}

	cmd := exec.Command("python3", args...)
	output, err := cmd.Output()
	if err != nil {
		log.Printf("Vault generate-vault-md error: %v", err)
		if exitErr, ok := err.(*exec.ExitError); ok {
			log.Printf("Stderr: %s", string(exitErr.Stderr))
		}
		jsonError(w, "Failed to generate VAULT.md", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Write(output)
}

// vaultGetVaultMdHandler gets VAULT.md content
func vaultGetVaultMdHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Extract topic from path: /api/vault/vault-md/{topic} or /api/vault/vault-md
	path := r.URL.Path
	topic := strings.TrimPrefix(path, "/api/vault/vault-md/")
	if topic == path || topic == "" {
		topic = "" // Root
	}
	// Remove trailing slash if present
	topic = strings.TrimSuffix(topic, "/")

	// Validate topic to prevent path traversal
	topic, ok := sanitizeTopic(topic)
	if !ok {
		jsonError(w, "Invalid topic name", http.StatusBadRequest)
		return
	}

	// Check if raw content is requested
	raw := r.URL.Query().Get("raw") == "1"

	// Determine file path
	var vaultMdPath string
	if topic != "" {
		vaultMdPath = filepath.Join(cfg.VaultDir, "files", topic, "VAULT.md")
	} else {
		vaultMdPath = filepath.Join(cfg.VaultDir, "VAULT.md")
	}

	// If raw requested, serve file directly
	if raw {
		content, err := os.ReadFile(vaultMdPath)
		if err != nil {
			http.Error(w, "VAULT.md not found", http.StatusNotFound)
			return
		}
		w.Header().Set("Content-Type", "text/markdown; charset=utf-8")
		w.Write(content)
		return
	}

	// Otherwise return JSON via Python
	vaultPy := filepath.Join(cfg.VaultDir, "..", "skills", "media-vault", "vault.py")
	args := []string{vaultPy, "get-vault-md"}
	if topic != "" {
		args = append(args, "--topic", topic)
	}

	cmd := exec.Command("python3", args...)
	output, err := cmd.Output()
	if err != nil {
		log.Printf("Vault get-vault-md error: %v", err)
		jsonError(w, "Failed to get VAULT.md", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Write(output)
}

// vaultSaveVaultMdHandler saves VAULT.md content
func vaultSaveVaultMdHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPut {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Extract topic from path
	path := r.URL.Path
	topic := strings.TrimPrefix(path, "/api/vault/vault-md/")
	if topic == path || topic == "" {
		topic = "" // Root
	}
	topic = strings.TrimSuffix(topic, "/")

	// Validate topic to prevent path traversal
	topic, ok := sanitizeTopic(topic)
	if !ok {
		jsonError(w, "Invalid topic name", http.StatusBadRequest)
		return
	}

	var req struct {
		Content string `json:"content"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		jsonError(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	vaultPy := filepath.Join(cfg.VaultDir, "..", "skills", "media-vault", "vault.py")
	args := []string{vaultPy, "save-vault-md", "--content-stdin"}
	if topic != "" {
		args = append(args, "--topic", topic)
	}

	cmd := exec.Command("python3", args...)
	cmd.Stdin = strings.NewReader(req.Content)
	output, err := cmd.Output()
	if err != nil {
		log.Printf("Vault save-vault-md error: %v", err)
		jsonError(w, "Failed to save VAULT.md", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Write(output)
}

// vaultMdDispatcher routes VAULT.md requests
func vaultMdDispatcher(w http.ResponseWriter, r *http.Request) {
	path := r.URL.Path

	// Check for /generate suffix
	if strings.HasSuffix(path, "/generate") {
		vaultGenerateVaultMdHandler(w, r)
		return
	}

	switch r.Method {
	case http.MethodGet:
		vaultGetVaultMdHandler(w, r)
	case http.MethodPut:
		vaultSaveVaultMdHandler(w, r)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

// vaultBulkHandler handles bulk operations
func vaultBulkHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Action string   `json:"action"` // "delete" or "move"
		IDs    []string `json:"ids"`
		Topic  string   `json:"topic"` // for move action
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		jsonError(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	if len(req.IDs) == 0 {
		jsonError(w, "No IDs provided", http.StatusBadRequest)
		return
	}

	vaultPy := filepath.Join(cfg.VaultDir, "..", "skills", "media-vault", "vault.py")

	switch req.Action {
	case "delete":
		ids := strings.Join(req.IDs, ",")
		cmd := exec.Command("python3", vaultPy, "delete-bulk", "--ids", ids)
		output, err := cmd.Output()
		if err != nil {
			log.Printf("Vault bulk delete error: %v", err)
			jsonError(w, "Bulk delete failed", http.StatusInternalServerError)
			return
		}

		// Trigger VAULT.md regeneration for affected topics in background
		var result map[string]any
		if json.Unmarshal(output, &result) == nil {
			if topics, ok := result["topics_affected"].([]any); ok {
				go func() {
					for _, t := range topics {
						if topic, ok := t.(string); ok && topic != "" {
							regenCmd := exec.Command("python3", vaultPy, "generate-vault-md", "--topic", topic)
							if err := regenCmd.Run(); err != nil {
								log.Printf("VAULT.md regeneration failed for %s: %v", topic, err)
							}
						}
					}
				}()
			}
		}

		w.Header().Set("Content-Type", "application/json")
		w.Write(output)

	case "move":
		if req.Topic == "" {
			jsonError(w, "Topic required for move", http.StatusBadRequest)
			return
		}
		moveTopic, ok := sanitizeTopic(req.Topic)
		if !ok || moveTopic == "" {
			jsonError(w, "Invalid topic name", http.StatusBadRequest)
			return
		}
		// Move each file and track source topics
		results := make([]map[string]any, 0)
		sourceTopics := make(map[string]bool)
		for _, id := range req.IDs {
			cmd := exec.Command("python3", vaultPy, "move", "--id", id, "--topic", moveTopic)
			output, _ := cmd.Output()
			var result map[string]any
			json.Unmarshal(output, &result)
			results = append(results, result)
			// Track source topic for VAULT.md regeneration
			if oldTopic, ok := result["from"].(string); ok && oldTopic != "" {
				sourceTopics[oldTopic] = true
			}
		}

		// Trigger VAULT.md regeneration for all affected topics in background
		go func() {
			// Regenerate for destination topic
			regenCmd := exec.Command("python3", vaultPy, "generate-vault-md", "--topic", moveTopic)
			if err := regenCmd.Run(); err != nil {
				log.Printf("VAULT.md regeneration failed for %s: %v", moveTopic, err)
			}
			// Regenerate for source topics
			for topic := range sourceTopics {
				if topic != moveTopic {
					regenCmd := exec.Command("python3", vaultPy, "generate-vault-md", "--topic", topic)
					if err := regenCmd.Run(); err != nil {
						log.Printf("VAULT.md regeneration failed for %s: %v", topic, err)
					}
				}
			}
		}()

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{
			"action":  "move",
			"topic":   moveTopic,
			"results": results,
		})

	default:
		jsonError(w, "Invalid action", http.StatusBadRequest)
	}
}
