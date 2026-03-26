package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	_ "modernc.org/sqlite"
)

var db *sql.DB

// Thread represents a chat thread
type Thread struct {
	ID        string    `json:"id"`
	UserEmail string    `json:"user_email"`
	Title     string    `json:"title"`
	Messages  string    `json:"messages"` // JSON array of messages
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// InitDB initializes the SQLite database
func InitDB() error {
	dbPath := filepath.Join(cfg.VaultDir, "openclaw.db")

	// Ensure directory exists
	if err := os.MkdirAll(filepath.Dir(dbPath), 0755); err != nil {
		return err
	}

	var err error
	db, err = sql.Open("sqlite", dbPath)
	if err != nil {
		return err
	}

	// Create tables
	schema := `
	CREATE TABLE IF NOT EXISTS threads (
		id TEXT PRIMARY KEY,
		user_email TEXT NOT NULL,
		title TEXT NOT NULL DEFAULT 'New Chat',
		messages TEXT NOT NULL DEFAULT '[]',
		created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
		updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
	);
	CREATE INDEX IF NOT EXISTS idx_threads_user ON threads(user_email);
	CREATE INDEX IF NOT EXISTS idx_threads_updated ON threads(updated_at DESC);
	`

	_, err = db.Exec(schema)
	return err
}

// threadsAPIHandler dispatches thread API requests
func threadsAPIHandler(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/api/threads")

	switch {
	case path == "" || path == "/":
		if r.Method == http.MethodGet {
			listThreadsHandler(w, r)
		} else if r.Method == http.MethodPost {
			createThreadHandler(w, r)
		} else {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	default:
		// /api/threads/{id}
		threadID := strings.TrimPrefix(path, "/")
		threadID = strings.Split(threadID, "/")[0]

		switch r.Method {
		case http.MethodGet:
			getThreadHandler(w, r, threadID)
		case http.MethodPut, http.MethodPatch, http.MethodPost:
			// Accept POST for sendBeacon (beforeunload saves)
			updateThreadHandler(w, r, threadID)
		case http.MethodDelete:
			deleteThreadHandler(w, r, threadID)
		default:
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	}
}

func listThreadsHandler(w http.ResponseWriter, r *http.Request) {
	email, _, _ := getSessionUser(r)
	if email == "" {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	rows, err := db.Query(`
		SELECT id, title, messages, created_at, updated_at
		FROM threads
		WHERE user_email = ?
		ORDER BY updated_at DESC
		LIMIT 50
	`, email)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	threads := []map[string]interface{}{}
	for rows.Next() {
		var id, title, messages string
		var createdAt, updatedAt time.Time
		if err := rows.Scan(&id, &title, &messages, &createdAt, &updatedAt); err != nil {
			continue
		}

		// Count messages
		var msgArr []interface{}
		json.Unmarshal([]byte(messages), &msgArr)

		threads = append(threads, map[string]interface{}{
			"id":            id,
			"title":         title,
			"message_count": len(msgArr),
			"created_at":    createdAt.Format(time.RFC3339),
			"updated_at":    updatedAt.Format(time.RFC3339),
		})
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"threads": threads,
	})
}

func createThreadHandler(w http.ResponseWriter, r *http.Request) {
	email, _, _ := getSessionUser(r)
	if email == "" {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	var req struct {
		ID       string `json:"id"`
		Title    string `json:"title"`
		Messages string `json:"messages"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	if req.ID == "" {
		req.ID = fmt.Sprintf("thread_%d", time.Now().UnixMilli())
	}
	if req.Title == "" {
		req.Title = "New Chat"
	}
	if req.Messages == "" {
		req.Messages = "[]"
	}

	_, err := db.Exec(`
		INSERT INTO threads (id, user_email, title, messages, created_at, updated_at)
		VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
	`, req.ID, email, req.Title, req.Messages)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"id":      req.ID,
		"title":   req.Title,
		"success": true,
	})
}

func getThreadHandler(w http.ResponseWriter, r *http.Request, threadID string) {
	email, _, _ := getSessionUser(r)
	if email == "" {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	var id, title, messages string
	var createdAt, updatedAt time.Time
	err := db.QueryRow(`
		SELECT id, title, messages, created_at, updated_at
		FROM threads
		WHERE id = ? AND user_email = ?
	`, threadID, email).Scan(&id, &title, &messages, &createdAt, &updatedAt)

	if err == sql.ErrNoRows {
		http.Error(w, "Thread not found", http.StatusNotFound)
		return
	} else if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"id":         id,
		"title":      title,
		"messages":   json.RawMessage(messages),
		"created_at": createdAt.Format(time.RFC3339),
		"updated_at": updatedAt.Format(time.RFC3339),
	})
}

func updateThreadHandler(w http.ResponseWriter, r *http.Request, threadID string) {
	email, _, _ := getSessionUser(r)
	if email == "" {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	var req struct {
		Title    *string `json:"title"`
		Messages *string `json:"messages"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		log.Printf("Thread update decode error for %s: %v", threadID, err)
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	// Build update query
	updates := []string{"updated_at = CURRENT_TIMESTAMP"}
	args := []interface{}{}

	if req.Title != nil {
		updates = append(updates, "title = ?")
		args = append(args, *req.Title)
	}
	if req.Messages != nil {
		updates = append(updates, "messages = ?")
		args = append(args, *req.Messages)
	}

	args = append(args, threadID, email)

	query := fmt.Sprintf("UPDATE threads SET %s WHERE id = ? AND user_email = ?", strings.Join(updates, ", "))
	result, err := db.Exec(query, args...)
	if err != nil {
		log.Printf("Thread update DB error for %s: %v", threadID, err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	affected, _ := result.RowsAffected()
	if affected == 0 {
		log.Printf("Thread update: not found %s for %s", threadID, email)
		http.Error(w, "Thread not found", http.StatusNotFound)
		return
	}

	msgLen := 0
	if req.Messages != nil {
		msgLen = len(*req.Messages)
	}
	log.Printf("Thread updated: %s (messages: %d bytes)", threadID, msgLen)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
	})
}

func deleteThreadHandler(w http.ResponseWriter, r *http.Request, threadID string) {
	email, _, _ := getSessionUser(r)
	if email == "" {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	result, err := db.Exec("DELETE FROM threads WHERE id = ? AND user_email = ?", threadID, email)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	affected, _ := result.RowsAffected()
	if affected == 0 {
		http.Error(w, "Thread not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
	})
}
