package main

import (
	"encoding/json"
	"net/http"
	"strconv"
	"sync"
	"time"
)

// LogEntry represents a single log entry
type LogEntry struct {
	Timestamp time.Time `json:"timestamp"`
	Level     string    `json:"level"`   // debug, info, warning, error
	Message   string    `json:"message"`
	Source    string    `json:"source,omitempty"`
	SessionID string    `json:"session_id,omitempty"`
	Details   any       `json:"details,omitempty"`
}

// LogStore is a thread-safe in-memory log store with size limits
type LogStore struct {
	mu       sync.RWMutex
	entries  []LogEntry
	maxSize  int
	thinking map[string][]string // sessionID -> thinking blocks
}

var logStore = &LogStore{
	entries:  make([]LogEntry, 0, 1000),
	maxSize:  1000,
	thinking: make(map[string][]string),
}

// AddLog adds a new log entry
func (ls *LogStore) AddLog(level, message, source, sessionID string, details any) {
	ls.mu.Lock()
	defer ls.mu.Unlock()

	entry := LogEntry{
		Timestamp: time.Now(),
		Level:     level,
		Message:   message,
		Source:    source,
		SessionID: sessionID,
		Details:   details,
	}

	ls.entries = append(ls.entries, entry)

	// Trim if over limit (remove oldest entries)
	if len(ls.entries) > ls.maxSize {
		ls.entries = ls.entries[len(ls.entries)-ls.maxSize:]
	}
}

// GetLogs returns logs filtered by level and limited
func (ls *LogStore) GetLogs(level string, limit int, sessionID string) []LogEntry {
	ls.mu.RLock()
	defer ls.mu.RUnlock()

	// Level priority for filtering
	levelPriority := map[string]int{
		"debug":   0,
		"info":    1,
		"warning": 2,
		"error":   3,
	}

	minLevel := levelPriority[level]
	if minLevel == 0 && level != "debug" {
		minLevel = 1 // Default to info if invalid level
	}

	// Filter entries
	var filtered []LogEntry
	for i := len(ls.entries) - 1; i >= 0; i-- {
		entry := ls.entries[i]

		// Filter by level
		if levelPriority[entry.Level] < minLevel {
			continue
		}

		// Filter by session if specified
		if sessionID != "" && entry.SessionID != sessionID {
			continue
		}

		filtered = append(filtered, entry)

		if len(filtered) >= limit {
			break
		}
	}

	// Reverse to get chronological order
	for i, j := 0, len(filtered)-1; i < j; i, j = i+1, j-1 {
		filtered[i], filtered[j] = filtered[j], filtered[i]
	}

	return filtered
}

// AddThinking adds a thinking block for a session
func (ls *LogStore) AddThinking(sessionID, content string) {
	ls.mu.Lock()
	defer ls.mu.Unlock()

	if ls.thinking[sessionID] == nil {
		ls.thinking[sessionID] = make([]string, 0)
	}
	ls.thinking[sessionID] = append(ls.thinking[sessionID], content)

	// Limit to last 10 thinking blocks per session
	if len(ls.thinking[sessionID]) > 10 {
		ls.thinking[sessionID] = ls.thinking[sessionID][len(ls.thinking[sessionID])-10:]
	}
}

// GetThinking gets thinking blocks for a session
func (ls *LogStore) GetThinking(sessionID string) []string {
	ls.mu.RLock()
	defer ls.mu.RUnlock()

	return ls.thinking[sessionID]
}

// ClearThinking clears thinking blocks for a session
func (ls *LogStore) ClearThinking(sessionID string) {
	ls.mu.Lock()
	defer ls.mu.Unlock()

	delete(ls.thinking, sessionID)
}

// Convenience functions for logging
func logDebug(message string, source string, sessionID string) {
	logStore.AddLog("debug", message, source, sessionID, nil)
}

func logInfo(message string, source string, sessionID string) {
	logStore.AddLog("info", message, source, sessionID, nil)
}

func logWarning(message string, source string, sessionID string) {
	logStore.AddLog("warning", message, source, sessionID, nil)
}

func logError(message string, source string, sessionID string) {
	logStore.AddLog("error", message, source, sessionID, nil)
}

// logsHandler handles GET /api/logs
func logsHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Parse query parameters
	level := r.URL.Query().Get("level")
	if level == "" {
		level = "info"
	}

	limitStr := r.URL.Query().Get("limit")
	limit := 100
	if limitStr != "" {
		if n, err := strconv.Atoi(limitStr); err == nil && n > 0 && n <= 500 {
			limit = n
		}
	}

	sessionID := r.URL.Query().Get("session_id")

	logs := logStore.GetLogs(level, limit, sessionID)

	// Log when logs are fetched (debug level so it doesn't flood)
	logDebug("Logs fetched: "+strconv.Itoa(len(logs))+" entries", "logs", "")

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{
		"logs":  logs,
		"count": len(logs),
		"level": level,
	})
}

// thinkingHandler handles GET /api/thinking/:session_id
func thinkingHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	sessionID := r.URL.Query().Get("session_id")
	if sessionID == "" {
		jsonError(w, "session_id is required", http.StatusBadRequest)
		return
	}

	thinking := logStore.GetThinking(sessionID)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{
		"thinking":   thinking,
		"session_id": sessionID,
	})
}
