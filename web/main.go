package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os/exec"
	"path/filepath"
	"strings"
)

var cfg *Config

func main() {
	port := flag.Int("port", 8085, "Server port")
	baseURL := flag.String("base-url", "", "Base URL for OAuth redirect (required)")
	flag.Parse()

	if *baseURL == "" {
		log.Fatal("ALFRED_WEB_BASE_URL / -base-url is required")
	}

	cfg = LoadConfig()
	cfg.Port = *port

	// Initialize database
	if err := InitDB(); err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	if err := InitJobsDB(); err != nil {
		log.Fatalf("Failed to initialize jobs table: %v", err)
	}

	logInfo(fmt.Sprintf("OpenClaw server starting on port %d", *port), "server", "")

	initAuth(cfg, *baseURL)

	// Public routes
	http.HandleFunc("/health", healthHandler)
	http.HandleFunc("/login", loginPageHandler)
	http.HandleFunc("/unauthorized", unauthorizedHandler)
	http.HandleFunc("/auth/google", loginHandler)
	http.HandleFunc("/auth/callback", callbackHandler)
	http.HandleFunc("/auth/logout", logoutHandler)

	// Static files
	http.Handle("/static/", http.StripPrefix("/static/", http.FileServer(http.Dir("static"))))

	// API routes (protected)
	http.HandleFunc("/api/voice", requireAuth(voiceHandler))
	http.HandleFunc("/api/voice/stream", requireAuth(voiceStreamHandler))
	http.HandleFunc("/api/chat", requireAuth(chatHandler))
	http.HandleFunc("/api/tts", requireAuth(ttsHandler))
	http.HandleFunc("/api/user/profile", requireAuth(userProfileHandler))
	http.HandleFunc("/api/media/upload", requireAuth(mediaUploadHandler))
	http.HandleFunc("/api/media/convert", requireAuth(mediaConvertHandler))
	http.HandleFunc("/api/media/process", requireAuth(mediaProcessHandler))
	http.HandleFunc("/api/media/extract", requireAuth(mediaExtractHandler))
	http.HandleFunc("/api/vault/file/", requireAuth(vaultFileDispatcher))
	http.HandleFunc("/api/vault/thumb/", requireAuth(vaultThumbHandler))
	http.HandleFunc("/api/vault/list", requireAuth(vaultListHandler))

	// Vault file management API
	http.HandleFunc("/api/vault/topics", requireAuth(vaultTopicsHandler))
	http.HandleFunc("/api/vault/topics/create", requireAuth(vaultCreateTopicHandler))
	http.HandleFunc("/api/vault/topic/", requireAuth(vaultTopicDispatcher))
	http.HandleFunc("/api/vault/stats", requireAuth(vaultStatsHandler))
	http.HandleFunc("/api/vault/files/bulk", requireAuth(vaultBulkHandler))
	http.HandleFunc("/api/vault/vault-md/", requireAuth(vaultMdDispatcher))

	// Debug/Logs API
	http.HandleFunc("/api/logs", requireAuth(logsHandler))
	http.HandleFunc("/api/thinking", requireAuth(thinkingHandler))

	// School API
	http.HandleFunc("/api/school/", requireAuth(schoolAPIHandler))

	// Threads API
	http.HandleFunc("/api/threads", requireAuth(threadsAPIHandler))
	http.HandleFunc("/api/threads/", requireAuth(threadsAPIHandler))

	// Jobs API (async chat)
	http.HandleFunc("/api/jobs", requireAuth(jobsAPIHandler))
	http.HandleFunc("/api/jobs/", requireAuth(jobsAPIHandler))

	// Protected routes
	http.HandleFunc("/school", requireAuth(schoolPageHandler))
	http.HandleFunc("/files", requireAuth(filesPageHandler))
	http.HandleFunc("/", requireAuth(indexHandler))

	// Scan for missing VAULT.md files on startup (background)
	go scanVaultMdOnStartup()

	addr := fmt.Sprintf(":%d", cfg.Port)
	log.Printf("OpenClaw starting on %s", addr)
	log.Printf("Base URL: %s", *baseURL)
	log.Fatal(http.ListenAndServe(addr, securityHeaders(http.DefaultServeMux)))
}

func securityHeaders(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("X-Frame-Options", "DENY")
		w.Header().Set("Referrer-Policy", "strict-origin-when-cross-origin")
		// Only send HSTS when behind TLS (r.TLS set, or X-Forwarded-Proto from reverse proxy)
		if r.TLS != nil || r.Header.Get("X-Forwarded-Proto") == "https" {
			w.Header().Set("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
		}
		w.Header().Set("Content-Security-Policy",
			"default-src 'self'; "+
				"script-src 'self' 'unsafe-eval' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "+
				"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "+
				"font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "+
				"img-src 'self' data: blob: https://*.googleusercontent.com; "+
				"connect-src 'self' https://cdn.jsdelivr.net; "+
				"media-src 'self' blob:")
		w.Header().Set("Permissions-Policy", "camera=(), microphone=(self), geolocation=()")
		next.ServeHTTP(w, r)
	})
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte("OK"))
}

func loginPageHandler(w http.ResponseWriter, r *http.Request) {
	// Check if already logged in
	session, _ := store.Get(r, sessionName)
	if email, ok := session.Values[userEmailKey].(string); ok && email != "" {
		http.Redirect(w, r, "/", http.StatusTemporaryRedirect)
		return
	}
	http.ServeFile(w, r, "static/login.html")
}

func unauthorizedHandler(w http.ResponseWriter, r *http.Request) {
	http.ServeFile(w, r, "static/unauthorized.html")
}

func indexHandler(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		http.NotFound(w, r)
		return
	}
	http.ServeFile(w, r, "static/index.html")
}

func userProfileHandler(w http.ResponseWriter, r *http.Request) {
	email, name, picture := getSessionUser(r)
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"email":   email,
		"name":    name,
		"picture": picture,
	})
}

func filesPageHandler(w http.ResponseWriter, r *http.Request) {
	http.ServeFile(w, r, "static/files.html")
}

func schoolPageHandler(w http.ResponseWriter, r *http.Request) {
	http.ServeFile(w, r, "static/school.html")
}

func scanVaultMdOnStartup() {
	vaultPy := filepath.Join(cfg.VaultDir, "..", "skills", "media-vault", "vault.py")
	cmd := exec.Command("python3", vaultPy, "scan-vault-md")

	output, err := cmd.Output()
	if err != nil {
		log.Printf("VAULT.md scan failed: %v", err)
		return
	}

	var result map[string]interface{}
	if err := json.Unmarshal(output, &result); err != nil {
		log.Printf("VAULT.md scan result parse failed: %v", err)
		return
	}

	generated, _ := result["generated"].([]interface{})
	if len(generated) > 0 {
		log.Printf("Generated %d missing VAULT.md files", len(generated))
	}
}

func vaultFileDispatcher(w http.ResponseWriter, r *http.Request) {
	// Check for /move suffix
	if strings.HasSuffix(r.URL.Path, "/move") {
		vaultMoveHandler(w, r)
		return
	}

	switch r.Method {
	case http.MethodGet:
		vaultFileHandler(w, r)
	case http.MethodPatch:
		vaultUpdateHandler(w, r)
	case http.MethodDelete:
		vaultDeleteHandler(w, r)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}
