package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os/exec"
	"path/filepath"
	"strings"
)

// schoolAPIHandler dispatches /api/school/* requests
func schoolAPIHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	path := strings.TrimPrefix(r.URL.Path, "/api/school/")
	path = strings.TrimSuffix(path, "/")

	switch path {
	case "grades":
		schoolSkillProxy(w, r, "grades")
	case "missing":
		schoolSkillProxy(w, r, "missing")
	case "upcoming":
		schoolSkillProxy(w, r, "upcoming")
	case "courses":
		schoolSkillProxy(w, r, "courses")
	case "curriculum":
		studySkillProxy(w, r, "curriculum")
	default:
		http.Error(w, `{"error": "unknown school endpoint"}`, http.StatusNotFound)
	}
}

// schoolSkillProxy calls the school.py skill and returns JSON
func schoolSkillProxy(w http.ResponseWriter, r *http.Request, command string) {
	skillPath := filepath.Join(cfg.SkillsDir, "school", "school.py")

	args := []string{skillPath, command}

	// Pass query params as flags
	if student := r.URL.Query().Get("student"); student != "" {
		args = append(args, "--student", student)
	}
	if course := r.URL.Query().Get("course"); course != "" {
		args = append(args, "--course", course)
	}
	if since := r.URL.Query().Get("since"); since != "" {
		args = append(args, "--since", since)
	}

	cmd := exec.Command("python3", args...)
	output, err := cmd.Output()
	if err != nil {
		log.Printf("school skill error (%s): %v", command, err)
		if exitErr, ok := err.(*exec.ExitError); ok {
			http.Error(w, string(exitErr.Stderr), http.StatusInternalServerError)
		} else {
			http.Error(w, `{"error": "skill execution failed"}`, http.StatusInternalServerError)
		}
		return
	}

	// Validate JSON before forwarding
	var raw json.RawMessage
	if err := json.Unmarshal(output, &raw); err != nil {
		log.Printf("school skill returned invalid JSON (%s): %s", command, string(output))
		http.Error(w, `{"error": "invalid skill output"}`, http.StatusInternalServerError)
		return
	}

	w.Write(output)
}

// studySkillProxy calls the california_study.py skill
func studySkillProxy(w http.ResponseWriter, r *http.Request, command string) {
	skillPath := filepath.Join(cfg.SkillsDir, "california-study", "california_study.py")

	args := []string{skillPath, command}

	if grade := r.URL.Query().Get("grade"); grade != "" {
		args = append(args, "--grade", grade)
	}

	cmd := exec.Command("python3", args...)
	output, err := cmd.Output()
	if err != nil {
		log.Printf("study skill error (%s): %v", command, err)
		http.Error(w, `{"error": "skill execution failed"}`, http.StatusInternalServerError)
		return
	}

	var raw json.RawMessage
	if err := json.Unmarshal(output, &raw); err != nil {
		http.Error(w, `{"error": "invalid skill output"}`, http.StatusInternalServerError)
		return
	}

	w.Write(output)
}
