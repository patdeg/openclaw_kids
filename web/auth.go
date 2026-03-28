package main

import (
	"crypto/subtle"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"
	"unicode"

	"github.com/gorilla/sessions"
)

var store *sessions.CookieStore

var sessionName = "openclaw-session" // upgraded to __Host-openclaw on HTTPS in initAuth

const (
	loggedInKey = "logged_in"
	userNameKey = "user_name"
)

func initAuth(cfg *Config) {
	store = sessions.NewCookieStore([]byte(cfg.SessionSecret))
	store.Options = &sessions.Options{
		Path:     "/",
		MaxAge:   86400 * 90, // 90 days
		HttpOnly: true,
		SameSite: http.SameSiteLaxMode,
	}
}

// validatePassword checks that a password meets complexity requirements.
// Returns an error description string if invalid, or empty string if OK.
func validatePassword(password string) string {
	if len(password) < 16 {
		return "password must be at least 16 characters long"
	}

	var hasUpper, hasLower, hasDigit, hasSpecial bool
	for _, ch := range password {
		switch {
		case unicode.IsUpper(ch):
			hasUpper = true
		case unicode.IsLower(ch):
			hasLower = true
		case unicode.IsDigit(ch):
			hasDigit = true
		case unicode.IsPunct(ch) || unicode.IsSymbol(ch):
			hasSpecial = true
		}
	}

	var missing []string
	if !hasUpper {
		missing = append(missing, "an uppercase letter")
	}
	if !hasLower {
		missing = append(missing, "a lowercase letter")
	}
	if !hasDigit {
		missing = append(missing, "a digit")
	}
	if !hasSpecial {
		missing = append(missing, "a special character (!@#$%^&*...)")
	}

	if len(missing) > 0 {
		return fmt.Sprintf("password must contain %s", strings.Join(missing, ", "))
	}
	return ""
}

func loginHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	password := r.FormValue("password")

	// Constant-time comparison to prevent timing attacks
	passwordMatch := subtle.ConstantTimeCompare([]byte(password), []byte(cfg.WebPassword)) == 1

	if !passwordMatch {
		log.Printf("Failed login attempt from %s", r.RemoteAddr)
		http.Redirect(w, r, "/login?error=1", http.StatusSeeOther)
		return
	}

	session, _ := store.Get(r, sessionName)
	session.Values[loggedInKey] = true
	session.Values[userNameKey] = cfg.WebUsername
	if err := session.Save(r, w); err != nil {
		log.Printf("Failed to save session: %v", err)
		http.Error(w, "Internal error", http.StatusInternalServerError)
		return
	}

	log.Printf("User logged in: %s", cfg.WebUsername)
	logInfo("User logged in: "+cfg.WebUsername, "auth", "")
	http.Redirect(w, r, "/", http.StatusSeeOther)
}

func logoutHandler(w http.ResponseWriter, r *http.Request) {
	session, _ := store.Get(r, sessionName)
	session.Options.MaxAge = -1
	if err := session.Save(r, w); err != nil {
		log.Printf("Failed to save session: %v", err)
	}
	http.Redirect(w, r, "/login", http.StatusTemporaryRedirect)
}

func requireAuth(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		session, _ := store.Get(r, sessionName)
		loggedIn, ok := session.Values[loggedInKey].(bool)
		if !ok || !loggedIn {
			// For API requests, return JSON 401 instead of redirect.
			// fetch() follows redirects and would get HTML, breaking JSON parsing.
			if strings.HasPrefix(r.URL.Path, "/api/") {
				w.Header().Set("Content-Type", "application/json")
				w.WriteHeader(http.StatusUnauthorized)
				json.NewEncoder(w).Encode(map[string]string{
					"error": "Session expired. Please refresh the page to log in again.",
				})
				return
			}
			http.Redirect(w, r, "/login", http.StatusTemporaryRedirect)
			return
		}
		next(w, r)
	}
}

// getSessionUser returns user identity from the session.
// For compatibility with existing callers, it returns (email, name, picture).
// In password auth mode, email is set to the username, and picture is empty.
func getSessionUser(r *http.Request) (email, name, picture string) {
	session, _ := store.Get(r, sessionName)
	name, _ = session.Values[userNameKey].(string)
	email = name // use the username as the identity key
	picture = ""
	return
}
