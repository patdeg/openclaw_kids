package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"
)

// Task represents a task in the system
type Task struct {
	ID          string  `json:"id"`
	UserEmail   string  `json:"user_email"`
	Title       string  `json:"title"`
	Description string  `json:"description"`
	Status      string  `json:"status"`   // pending, started, done, archived
	Priority    string  `json:"priority"` // low, medium, high, urgent
	DueDate     *string `json:"due_date,omitempty"`
	ThreadID    *string `json:"thread_id,omitempty"`
	Source      string  `json:"source"` // web, email, alfred, skill
	CreatedAt   string  `json:"created_at"`
	UpdatedAt   string  `json:"updated_at"`
}

// TaskComment represents a comment on a task
type TaskComment struct {
	ID        string `json:"id"`
	TaskID    string `json:"task_id"`
	UserEmail string `json:"user_email"`
	Source    string `json:"source"` // user, alfred, system, email
	Body      string `json:"body"`
	CreatedAt string `json:"created_at"`
}

// TaskFile represents a link between a task and a vault file
type TaskFile struct {
	TaskID   string `json:"task_id"`
	FileID   string `json:"file_id"`
	LinkedAt string `json:"linked_at"`
}

// InitTasksDB creates tasks tables
func InitTasksDB() error {
	schema := `
	CREATE TABLE IF NOT EXISTS tasks (
		id TEXT PRIMARY KEY,
		user_email TEXT NOT NULL,
		title TEXT NOT NULL,
		description TEXT NOT NULL DEFAULT '',
		status TEXT NOT NULL DEFAULT 'pending',
		priority TEXT NOT NULL DEFAULT 'medium',
		due_date TEXT,
		thread_id TEXT,
		source TEXT NOT NULL DEFAULT 'web',
		created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
		updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
	);
	CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_email);
	CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
	CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_date);

	CREATE TABLE IF NOT EXISTS task_comments (
		id TEXT PRIMARY KEY,
		task_id TEXT NOT NULL,
		user_email TEXT NOT NULL,
		source TEXT NOT NULL DEFAULT 'user',
		body TEXT NOT NULL,
		created_at DATETIME DEFAULT CURRENT_TIMESTAMP
	);
	CREATE INDEX IF NOT EXISTS idx_task_comments_task ON task_comments(task_id);

	CREATE TABLE IF NOT EXISTS task_files (
		task_id TEXT NOT NULL,
		file_id TEXT NOT NULL,
		linked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
		PRIMARY KEY (task_id, file_id)
	);
	CREATE INDEX IF NOT EXISTS idx_task_files_task ON task_files(task_id);
	`
	_, err := db.Exec(schema)
	return err
}

// tasksPageHandler serves the tasks HTML page
func tasksPageHandler(w http.ResponseWriter, r *http.Request) {
	http.ServeFile(w, r, "static/tasks.html")
}

// tasksAPIHandler dispatches task API requests
func tasksAPIHandler(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/api/tasks")

	switch {
	case path == "" || path == "/":
		switch r.Method {
		case http.MethodGet:
			listTasksHandler(w, r)
		case http.MethodPost:
			createTaskHandler(w, r)
		default:
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}

	default:
		parts := strings.Split(strings.TrimPrefix(path, "/"), "/")
		taskID := parts[0]

		if len(parts) == 1 {
			switch r.Method {
			case http.MethodGet:
				getTaskHandler(w, r, taskID)
			case http.MethodPatch, http.MethodPut:
				updateTaskHandler(w, r, taskID)
			case http.MethodDelete:
				deleteTaskHandler(w, r, taskID)
			default:
				http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			}
			return
		}

		// Sub-resources: /api/tasks/{id}/comments, /api/tasks/{id}/files, /api/tasks/{id}/chat
		sub := parts[1]
		switch sub {
		case "comments":
			taskCommentsHandler(w, r, taskID)
		case "files":
			if len(parts) == 3 {
				// DELETE /api/tasks/{id}/files/{fileId}
				taskUnlinkFileHandler(w, r, taskID, parts[2])
			} else {
				taskFilesHandler(w, r, taskID)
			}
		case "chat":
			taskChatHandler(w, r, taskID)
		default:
			http.Error(w, "Not found", http.StatusNotFound)
		}
	}
}

func listTasksHandler(w http.ResponseWriter, r *http.Request) {
	email, _, _ := getSessionUser(r)

	// Optional filters
	status := r.URL.Query().Get("status")
	priority := r.URL.Query().Get("priority")
	search := r.URL.Query().Get("q")

	query := `SELECT id, title, description, status, priority, due_date, thread_id, source, created_at, updated_at
		FROM tasks WHERE user_email = ?`
	args := []interface{}{email}

	if status != "" {
		query += " AND status = ?"
		args = append(args, status)
	}
	if priority != "" {
		query += " AND priority = ?"
		args = append(args, priority)
	}
	if search != "" {
		query += " AND (title LIKE ? OR description LIKE ?)"
		term := "%" + search + "%"
		args = append(args, term, term)
	}

	query += " ORDER BY CASE status WHEN 'urgent' THEN 0 WHEN 'started' THEN 1 WHEN 'pending' THEN 2 WHEN 'done' THEN 3 WHEN 'archived' THEN 4 END, CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END, updated_at DESC LIMIT 200"

	rows, err := db.Query(query, args...)
	if err != nil {
		jsonError(w, "Database error", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	tasks := []map[string]interface{}{}
	for rows.Next() {
		var id, title, desc, st, pri, source, createdAt, updatedAt string
		var dueDate, threadID sql.NullString
		if err := rows.Scan(&id, &title, &desc, &st, &pri, &dueDate, &threadID, &source, &createdAt, &updatedAt); err != nil {
			continue
		}

		task := map[string]interface{}{
			"id":          id,
			"title":       title,
			"description": desc,
			"status":      st,
			"priority":    pri,
			"source":      source,
			"created_at":  createdAt,
			"updated_at":  updatedAt,
		}
		if dueDate.Valid {
			task["due_date"] = dueDate.String
		}
		if threadID.Valid {
			task["thread_id"] = threadID.String
		}

		// Count comments and files
		var commentCount int
		db.QueryRow("SELECT COUNT(*) FROM task_comments WHERE task_id = ?", id).Scan(&commentCount)
		task["comment_count"] = commentCount

		var fileCount int
		db.QueryRow("SELECT COUNT(*) FROM task_files WHERE task_id = ?", id).Scan(&fileCount)
		task["file_count"] = fileCount

		tasks = append(tasks, task)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"tasks": tasks,
	})
}

func createTaskHandler(w http.ResponseWriter, r *http.Request) {
	email, _, _ := getSessionUser(r)

	var req struct {
		Title       string  `json:"title"`
		Description string  `json:"description"`
		Priority    string  `json:"priority"`
		DueDate     *string `json:"due_date"`
		Source      string  `json:"source"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		jsonError(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	if req.Title == "" {
		jsonError(w, "Title is required", http.StatusBadRequest)
		return
	}
	if req.Priority == "" {
		req.Priority = "medium"
	}
	if req.Source == "" {
		req.Source = "web"
	}

	id := fmt.Sprintf("task_%d", time.Now().UnixMilli())

	_, err := db.Exec(`
		INSERT INTO tasks (id, user_email, title, description, priority, due_date, source, created_at, updated_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
	`, id, email, req.Title, req.Description, req.Priority, req.DueDate, req.Source)
	if err != nil {
		jsonError(w, "Failed to create task", http.StatusInternalServerError)
		return
	}

	logInfo("Task created: "+id+" — "+req.Title, "tasks", "")

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"id":      id,
		"success": true,
	})
}

func getTaskHandler(w http.ResponseWriter, r *http.Request, taskID string) {
	email, _, _ := getSessionUser(r)

	var id, title, desc, st, pri, source, createdAt, updatedAt string
	var dueDate, threadID sql.NullString
	err := db.QueryRow(`
		SELECT id, title, description, status, priority, due_date, thread_id, source, created_at, updated_at
		FROM tasks WHERE id = ? AND user_email = ?
	`, taskID, email).Scan(&id, &title, &desc, &st, &pri, &dueDate, &threadID, &source, &createdAt, &updatedAt)

	if err == sql.ErrNoRows {
		jsonError(w, "Task not found", http.StatusNotFound)
		return
	} else if err != nil {
		jsonError(w, "Database error", http.StatusInternalServerError)
		return
	}

	task := map[string]interface{}{
		"id":          id,
		"title":       title,
		"description": desc,
		"status":      st,
		"priority":    pri,
		"source":      source,
		"created_at":  createdAt,
		"updated_at":  updatedAt,
	}
	if dueDate.Valid {
		task["due_date"] = dueDate.String
	}
	if threadID.Valid {
		task["thread_id"] = threadID.String
	}

	// Fetch comments
	comments := []map[string]interface{}{}
	crows, err := db.Query("SELECT id, user_email, source, body, created_at FROM task_comments WHERE task_id = ? ORDER BY created_at ASC", taskID)
	if err == nil {
		defer crows.Close()
		for crows.Next() {
			var cid, cemail, csource, cbody, cat string
			if crows.Scan(&cid, &cemail, &csource, &cbody, &cat) == nil {
				comments = append(comments, map[string]interface{}{
					"id":         cid,
					"user_email": cemail,
					"source":     csource,
					"body":       cbody,
					"created_at": cat,
				})
			}
		}
	}
	task["comments"] = comments

	// Fetch linked files
	files := []map[string]interface{}{}
	frows, err := db.Query("SELECT file_id, linked_at FROM task_files WHERE task_id = ? ORDER BY linked_at DESC", taskID)
	if err == nil {
		defer frows.Close()
		for frows.Next() {
			var fid, lat string
			if frows.Scan(&fid, &lat) == nil {
				files = append(files, map[string]interface{}{
					"file_id":   fid,
					"linked_at": lat,
				})
			}
		}
	}
	task["files"] = files

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(task)
}

func updateTaskHandler(w http.ResponseWriter, r *http.Request, taskID string) {
	email, _, _ := getSessionUser(r)

	var req struct {
		Title       *string `json:"title"`
		Description *string `json:"description"`
		Status      *string `json:"status"`
		Priority    *string `json:"priority"`
		DueDate     *string `json:"due_date"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		jsonError(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	updates := []string{"updated_at = CURRENT_TIMESTAMP"}
	args := []interface{}{}

	if req.Title != nil {
		updates = append(updates, "title = ?")
		args = append(args, *req.Title)
	}
	if req.Description != nil {
		updates = append(updates, "description = ?")
		args = append(args, *req.Description)
	}
	if req.Status != nil {
		updates = append(updates, "status = ?")
		args = append(args, *req.Status)
	}
	if req.Priority != nil {
		updates = append(updates, "priority = ?")
		args = append(args, *req.Priority)
	}
	if req.DueDate != nil {
		if *req.DueDate == "" {
			updates = append(updates, "due_date = NULL")
		} else {
			updates = append(updates, "due_date = ?")
			args = append(args, *req.DueDate)
		}
	}

	args = append(args, taskID, email)

	query := fmt.Sprintf("UPDATE tasks SET %s WHERE id = ? AND user_email = ?", strings.Join(updates, ", "))
	result, err := db.Exec(query, args...)
	if err != nil {
		jsonError(w, "Failed to update task", http.StatusInternalServerError)
		return
	}

	affected, _ := result.RowsAffected()
	if affected == 0 {
		jsonError(w, "Task not found", http.StatusNotFound)
		return
	}

	// Add system comment for status changes
	if req.Status != nil {
		commentID := fmt.Sprintf("comment_%d", time.Now().UnixMilli())
		db.Exec(`INSERT INTO task_comments (id, task_id, user_email, source, body) VALUES (?, ?, ?, 'system', ?)`,
			commentID, taskID, email, fmt.Sprintf("Status changed to **%s**", *req.Status))
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{"success": true})
}

func deleteTaskHandler(w http.ResponseWriter, r *http.Request, taskID string) {
	email, _, _ := getSessionUser(r)

	result, err := db.Exec("DELETE FROM tasks WHERE id = ? AND user_email = ?", taskID, email)
	if err != nil {
		jsonError(w, "Failed to delete task", http.StatusInternalServerError)
		return
	}

	affected, _ := result.RowsAffected()
	if affected == 0 {
		jsonError(w, "Task not found", http.StatusNotFound)
		return
	}

	// Cleanup related data
	db.Exec("DELETE FROM task_comments WHERE task_id = ?", taskID)
	db.Exec("DELETE FROM task_files WHERE task_id = ?", taskID)

	logInfo("Task deleted: "+taskID, "tasks", "")

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{"success": true})
}

// Comments

func taskCommentsHandler(w http.ResponseWriter, r *http.Request, taskID string) {
	email, _, _ := getSessionUser(r)

	// Verify task ownership
	var exists int
	if db.QueryRow("SELECT 1 FROM tasks WHERE id = ? AND user_email = ?", taskID, email).Scan(&exists) != nil {
		jsonError(w, "Task not found", http.StatusNotFound)
		return
	}

	switch r.Method {
	case http.MethodGet:
		rows, err := db.Query("SELECT id, user_email, source, body, created_at FROM task_comments WHERE task_id = ? ORDER BY created_at ASC", taskID)
		if err != nil {
			jsonError(w, "Database error", http.StatusInternalServerError)
			return
		}
		defer rows.Close()

		comments := []map[string]interface{}{}
		for rows.Next() {
			var cid, cemail, csource, cbody, cat string
			if rows.Scan(&cid, &cemail, &csource, &cbody, &cat) == nil {
				comments = append(comments, map[string]interface{}{
					"id":         cid,
					"user_email": cemail,
					"source":     csource,
					"body":       cbody,
					"created_at": cat,
				})
			}
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{"comments": comments})

	case http.MethodPost:
		var req struct {
			Body   string `json:"body"`
			Source string `json:"source"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			jsonError(w, "Invalid request", http.StatusBadRequest)
			return
		}
		if req.Body == "" {
			jsonError(w, "Body is required", http.StatusBadRequest)
			return
		}
		if req.Source == "" {
			req.Source = "user"
		}

		commentID := fmt.Sprintf("comment_%d", time.Now().UnixMilli())
		_, err := db.Exec(`INSERT INTO task_comments (id, task_id, user_email, source, body) VALUES (?, ?, ?, ?, ?)`,
			commentID, taskID, email, req.Source, req.Body)
		if err != nil {
			jsonError(w, "Failed to add comment", http.StatusInternalServerError)
			return
		}

		// Touch the task's updated_at
		db.Exec("UPDATE tasks SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", taskID)

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"id":      commentID,
			"success": true,
		})

	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

// File linking

func taskFilesHandler(w http.ResponseWriter, r *http.Request, taskID string) {
	email, _, _ := getSessionUser(r)

	var exists int
	if db.QueryRow("SELECT 1 FROM tasks WHERE id = ? AND user_email = ?", taskID, email).Scan(&exists) != nil {
		jsonError(w, "Task not found", http.StatusNotFound)
		return
	}

	switch r.Method {
	case http.MethodGet:
		rows, err := db.Query("SELECT file_id, linked_at FROM task_files WHERE task_id = ? ORDER BY linked_at DESC", taskID)
		if err != nil {
			jsonError(w, "Database error", http.StatusInternalServerError)
			return
		}
		defer rows.Close()

		files := []map[string]interface{}{}
		for rows.Next() {
			var fid, lat string
			if rows.Scan(&fid, &lat) == nil {
				files = append(files, map[string]interface{}{
					"file_id":   fid,
					"linked_at": lat,
				})
			}
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{"files": files})

	case http.MethodPost:
		var req struct {
			FileID string `json:"file_id"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.FileID == "" {
			jsonError(w, "file_id is required", http.StatusBadRequest)
			return
		}

		_, err := db.Exec("INSERT OR IGNORE INTO task_files (task_id, file_id) VALUES (?, ?)", taskID, req.FileID)
		if err != nil {
			jsonError(w, "Failed to link file", http.StatusInternalServerError)
			return
		}

		db.Exec("UPDATE tasks SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", taskID)

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(map[string]interface{}{"success": true})

	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

func taskUnlinkFileHandler(w http.ResponseWriter, r *http.Request, taskID, fileID string) {
	if r.Method != http.MethodDelete {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	email, _, _ := getSessionUser(r)

	var exists int
	if db.QueryRow("SELECT 1 FROM tasks WHERE id = ? AND user_email = ?", taskID, email).Scan(&exists) != nil {
		jsonError(w, "Task not found", http.StatusNotFound)
		return
	}

	db.Exec("DELETE FROM task_files WHERE task_id = ? AND file_id = ?", taskID, fileID)
	db.Exec("UPDATE tasks SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", taskID)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{"success": true})
}

// Chat about task — creates/reuses a thread and starts a job with task context

func taskChatHandler(w http.ResponseWriter, r *http.Request, taskID string) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	email, _, _ := getSessionUser(r)

	// Fetch task
	var title, desc, status, priority string
	var dueDate, threadID sql.NullString
	err := db.QueryRow(`SELECT title, description, status, priority, due_date, thread_id
		FROM tasks WHERE id = ? AND user_email = ?`, taskID, email).
		Scan(&title, &desc, &status, &priority, &dueDate, &threadID)
	if err != nil {
		jsonError(w, "Task not found", http.StatusNotFound)
		return
	}

	var req struct {
		Message string `json:"message"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.Message == "" {
		jsonError(w, "Message is required", http.StatusBadRequest)
		return
	}

	// Create or reuse thread
	sessID := ""
	if threadID.Valid {
		sessID = threadID.String
	} else {
		sessID = fmt.Sprintf("task_%d_chat", time.Now().UnixMilli())
		db.Exec("UPDATE tasks SET thread_id = ? WHERE id = ?", sessID, taskID)

		// Create the thread record
		db.Exec(`INSERT INTO threads (id, user_email, title, messages) VALUES (?, ?, ?, '[]')`,
			sessID, email, "Task: "+title)
	}

	// Build context-enriched message
	var ctx strings.Builder
	ctx.WriteString(fmt.Sprintf("[Context: Task \"%s\" — Status: %s, Priority: %s", title, status, priority))
	if dueDate.Valid {
		ctx.WriteString(fmt.Sprintf(", Due: %s", dueDate.String))
	}
	ctx.WriteString("]\n")
	if desc != "" {
		ctx.WriteString(fmt.Sprintf("[Description: %s]\n", desc))
	}

	// Add linked file info
	frows, ferr := db.Query("SELECT file_id FROM task_files WHERE task_id = ?", taskID)
	if ferr == nil {
		var fileIDs []string
		for frows.Next() {
			var fid string
			if frows.Scan(&fid) == nil {
				fileIDs = append(fileIDs, fid)
			}
		}
		frows.Close()
		if len(fileIDs) > 0 {
			ctx.WriteString(fmt.Sprintf("[Linked vault files: %s]\n", strings.Join(fileIDs, ", ")))
		}
	}

	ctx.WriteString("\n")
	ctx.WriteString(req.Message)

	// Check for running job
	if active := getActiveJobForThread(sessID, email); active != nil {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"job_id":    active.ID,
			"thread_id": sessID,
			"status":    active.Status,
		})
		return
	}

	job := startJob(sessID, email, ctx.String())
	logInfo(fmt.Sprintf("Task chat job %s for task %s", job.ID, taskID), "tasks", sessID)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"job_id":    job.ID,
		"thread_id": sessID,
		"status":    job.Status,
	})
}

