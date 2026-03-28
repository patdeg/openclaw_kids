package main

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"log"
	"net/http"
	"strings"
	"sync"
	"time"
)

// Job represents an async chat job
type Job struct {
	ID          string `json:"id"`
	ThreadID    string `json:"thread_id"`
	UserEmail   string `json:"user_email"`
	Message     string `json:"message"`
	Status      string `json:"status"` // queued, running, done, error
	Response    string `json:"response,omitempty"`
	Error       string `json:"error,omitempty"`
	CreatedAt   int64  `json:"created_at"`
	CompletedAt int64  `json:"completed_at,omitempty"`
}

// In-memory job store with mutex for concurrent access.
// Jobs are also persisted to SQLite so results survive container restarts.
var (
	jobsMu sync.RWMutex
	jobs   = make(map[string]*Job)
)

// InitJobsDB creates the jobs table
func InitJobsDB() error {
	schema := `
	CREATE TABLE IF NOT EXISTS jobs (
		id TEXT PRIMARY KEY,
		thread_id TEXT NOT NULL,
		user_email TEXT NOT NULL,
		message TEXT NOT NULL,
		status TEXT NOT NULL DEFAULT 'queued',
		response TEXT DEFAULT '',
		error TEXT DEFAULT '',
		created_at INTEGER NOT NULL,
		completed_at INTEGER DEFAULT 0
	);
	CREATE INDEX IF NOT EXISTS idx_jobs_thread ON jobs(thread_id);
	CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
	`
	_, err := db.Exec(schema)
	if err != nil {
		return err
	}

	// Load incomplete jobs from DB into memory on startup
	rows, err := db.Query(`SELECT id, thread_id, user_email, message, status, response, error, created_at, completed_at FROM jobs WHERE status IN ('queued', 'running')`)
	if err != nil {
		return err
	}
	defer rows.Close()

	for rows.Next() {
		var j Job
		if err := rows.Scan(&j.ID, &j.ThreadID, &j.UserEmail, &j.Message, &j.Status, &j.Response, &j.Error, &j.CreatedAt, &j.CompletedAt); err != nil {
			continue
		}
		// Mark stale running jobs as error (server restarted mid-execution)
		if j.Status == "running" || j.Status == "queued" {
			j.Status = "error"
			j.Error = "Server restarted while job was running. Please retry."
			j.CompletedAt = time.Now().UnixMilli()
			db.Exec(`UPDATE jobs SET status = ?, error = ?, completed_at = ? WHERE id = ?`,
				j.Status, j.Error, j.CompletedAt, j.ID)
		}
		jobs[j.ID] = &j
	}

	// Cleanup old completed jobs on startup
	go cleanupOldJobs()

	return nil
}

func generateJobID() string {
	b := make([]byte, 12)
	rand.Read(b)
	return "job_" + hex.EncodeToString(b)
}

// startJob creates a job and runs OpenClaw in a background goroutine
func startJob(threadID, userEmail, message string) *Job {
	job := &Job{
		ID:        generateJobID(),
		ThreadID:  threadID,
		UserEmail: userEmail,
		Message:   message,
		Status:    "running",
		CreatedAt: time.Now().UnixMilli(),
	}

	// Store in memory
	jobsMu.Lock()
	jobs[job.ID] = job
	jobsMu.Unlock()

	// Persist to DB
	db.Exec(`INSERT INTO jobs (id, thread_id, user_email, message, status, created_at) VALUES (?, ?, ?, ?, ?, ?)`,
		job.ID, job.ThreadID, job.UserEmail, job.Message, job.Status, job.CreatedAt)

	logInfo("Job started: "+job.ID+" for thread "+threadID, "jobs", threadID)

	// Run OpenClaw in background goroutine
	go func() {
		llmResponse, err := callClawdbot(message, userEmail, threadID)

		jobsMu.Lock()
		defer jobsMu.Unlock()

		job.CompletedAt = time.Now().UnixMilli()

		if err != nil {
			log.Printf("Job %s clawdbot error: %v", job.ID, err)
			logError("Job clawdbot error: "+err.Error(), "jobs", threadID)

			// Try fallback LLM
			logWarning("Job falling back to secondary LLM", "jobs", threadID)
			llmResponse, err = callFallbackLLM(message)
			if err != nil {
				job.Status = "error"
				job.Error = "AI processing failed: all backends unavailable"
				logError("Job fallback also failed: "+err.Error(), "jobs", threadID)
			} else {
				job.Status = "done"
				job.Response = markdownToHTML(llmResponse)
				logInfo("Job completed via fallback LLM: "+job.ID, "jobs", threadID)
			}
		} else {
			job.Status = "done"
			job.Response = markdownToHTML(llmResponse)
			logInfo("Job completed: "+job.ID, "jobs", threadID)
		}

		// Persist result to DB
		db.Exec(`UPDATE jobs SET status = ?, response = ?, error = ?, completed_at = ? WHERE id = ?`,
			job.Status, job.Response, job.Error, job.CompletedAt, job.ID)
	}()

	return job
}

// getJob returns a job by ID (checks memory first, then DB)
func getJob(jobID string) *Job {
	jobsMu.RLock()
	j, ok := jobs[jobID]
	jobsMu.RUnlock()
	if ok {
		return j
	}

	// Fall back to DB for completed jobs that were evicted from memory
	var job Job
	err := db.QueryRow(`SELECT id, thread_id, user_email, message, status, response, error, created_at, completed_at FROM jobs WHERE id = ?`, jobID).
		Scan(&job.ID, &job.ThreadID, &job.UserEmail, &job.Message, &job.Status, &job.Response, &job.Error, &job.CreatedAt, &job.CompletedAt)
	if err != nil {
		return nil
	}

	// Cache back in memory
	jobsMu.Lock()
	jobs[job.ID] = &job
	jobsMu.Unlock()

	return &job
}

// getActiveJobForThread returns the most recent running job for a thread
func getActiveJobForThread(threadID, userEmail string) *Job {
	jobsMu.RLock()
	defer jobsMu.RUnlock()

	var latest *Job
	for _, j := range jobs {
		if j.ThreadID == threadID && j.UserEmail == userEmail && j.Status == "running" {
			if latest == nil || j.CreatedAt > latest.CreatedAt {
				latest = j
			}
		}
	}
	return latest
}

// getLatestJobForThread returns the most recent job (any status) for a thread
func getLatestJobForThread(threadID, userEmail string) *Job {
	// Check memory first
	jobsMu.RLock()
	var latest *Job
	for _, j := range jobs {
		if j.ThreadID == threadID && j.UserEmail == userEmail {
			if latest == nil || j.CreatedAt > latest.CreatedAt {
				latest = j
			}
		}
	}
	jobsMu.RUnlock()

	// Also check DB for recently completed jobs
	var dbJob Job
	err := db.QueryRow(`SELECT id, thread_id, user_email, message, status, response, error, created_at, completed_at
		FROM jobs WHERE thread_id = ? AND user_email = ? ORDER BY created_at DESC LIMIT 1`,
		threadID, userEmail).
		Scan(&dbJob.ID, &dbJob.ThreadID, &dbJob.UserEmail, &dbJob.Message, &dbJob.Status, &dbJob.Response, &dbJob.Error, &dbJob.CreatedAt, &dbJob.CompletedAt)
	if err == nil {
		if latest == nil || dbJob.CreatedAt > latest.CreatedAt {
			latest = &dbJob
			// Cache in memory
			jobsMu.Lock()
			jobs[dbJob.ID] = &dbJob
			jobsMu.Unlock()
		}
	}

	return latest
}

// cleanupOldJobs removes completed jobs older than 24 hours
func cleanupOldJobs() {
	cutoff := time.Now().Add(-24 * time.Hour).UnixMilli()

	// Clean DB
	db.Exec(`DELETE FROM jobs WHERE status IN ('done', 'error') AND completed_at > 0 AND completed_at < ?`, cutoff)

	// Clean memory
	jobsMu.Lock()
	for id, j := range jobs {
		if (j.Status == "done" || j.Status == "error") && j.CompletedAt > 0 && j.CompletedAt < cutoff {
			delete(jobs, id)
		}
	}
	jobsMu.Unlock()
}

// HTTP Handlers

func jobsAPIHandler(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/api/jobs")

	switch {
	case path == "" || path == "/":
		// GET /api/jobs?thread_id=X — get job status for a thread
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		jobsByThreadHandler(w, r)
	default:
		// GET /api/jobs/{id} — get specific job
		jobID := strings.TrimPrefix(path, "/")
		jobID = strings.Split(jobID, "/")[0]

		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		getJobHandler(w, r, jobID)
	}
}

func getJobHandler(w http.ResponseWriter, r *http.Request, jobID string) {
	email, _, _ := getSessionUser(r)
	if email == "" {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	job := getJob(jobID)
	if job == nil || job.UserEmail != email {
		http.Error(w, "Job not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(job)
}

func jobsByThreadHandler(w http.ResponseWriter, r *http.Request) {
	email, _, _ := getSessionUser(r)
	if email == "" {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	threadID := r.URL.Query().Get("thread_id")
	if threadID == "" {
		http.Error(w, "thread_id required", http.StatusBadRequest)
		return
	}

	// Return the latest job for this thread
	job := getLatestJobForThread(threadID, email)

	w.Header().Set("Content-Type", "application/json")
	if job == nil {
		json.NewEncoder(w).Encode(map[string]interface{}{
			"job": nil,
		})
	} else {
		json.NewEncoder(w).Encode(map[string]interface{}{
			"job": job,
		})
	}
}
