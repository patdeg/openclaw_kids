package main

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"strings"

	"github.com/gorilla/sessions"
	"golang.org/x/oauth2"
	"golang.org/x/oauth2/google"
)

var (
	oauthConfig *oauth2.Config
	store       *sessions.CookieStore
)

const (
	sessionName    = "openclaw-session"
	userInfoURL    = "https://www.googleapis.com/oauth2/v2/userinfo"
	oauthStateKey  = "oauth_state"
	userEmailKey   = "user_email"
	userNameKey    = "user_name"
	userPictureKey = "user_picture"
)

// GoogleUserInfo represents the user info from Google OAuth
type GoogleUserInfo struct {
	ID      string `json:"id"`
	Email   string `json:"email"`
	Name    string `json:"name"`
	Picture string `json:"picture"`
}

func initAuth(cfg *Config, baseURL string) {
	store = sessions.NewCookieStore([]byte(cfg.SessionSecret))
	store.Options = &sessions.Options{
		Path:     "/",
		MaxAge:   86400 * 90, // 90 days
		HttpOnly: true,
		Secure:   strings.HasPrefix(baseURL, "https://"),
		SameSite: http.SameSiteLaxMode,
	}

	oauthConfig = &oauth2.Config{
		ClientID:     cfg.GoogleClientID,
		ClientSecret: cfg.GoogleSecret,
		RedirectURL:  baseURL + "/auth/callback",
		Scopes:       []string{"email", "profile"},
		Endpoint:     google.Endpoint,
	}
}

func loginHandler(w http.ResponseWriter, r *http.Request) {
	session, _ := store.Get(r, sessionName)

	// Generate cryptographically random state token
	stateBytes := make([]byte, 16)
	if _, err := rand.Read(stateBytes); err != nil {
		http.Error(w, "Internal error", http.StatusInternalServerError)
		return
	}
	state := hex.EncodeToString(stateBytes)
	session.Values[oauthStateKey] = state
	if err := session.Save(r, w); err != nil {
		log.Printf("Failed to save session: %v", err)
	}

	url := oauthConfig.AuthCodeURL(state, oauth2.AccessTypeOffline)
	http.Redirect(w, r, url, http.StatusTemporaryRedirect)
}

func callbackHandler(w http.ResponseWriter, r *http.Request) {
	session, _ := store.Get(r, sessionName)

	// Verify state
	expectedState, ok := session.Values[oauthStateKey].(string)
	if !ok || r.URL.Query().Get("state") != expectedState {
		http.Error(w, "Invalid state", http.StatusBadRequest)
		return
	}

	// Exchange code for token
	code := r.URL.Query().Get("code")
	token, err := oauthConfig.Exchange(context.Background(), code)
	if err != nil {
		log.Printf("OAuth exchange error: %v", err)
		http.Error(w, "OAuth error", http.StatusInternalServerError)
		return
	}

	// Get user info
	client := oauthConfig.Client(context.Background(), token)
	resp, err := client.Get(userInfoURL)
	if err != nil {
		log.Printf("Failed to get user info: %v", err)
		http.Error(w, "Failed to get user info", http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	var userInfo GoogleUserInfo
	if err := json.Unmarshal(body, &userInfo); err != nil {
		log.Printf("Failed to parse user info: %v", err)
		http.Error(w, "Failed to parse user info", http.StatusInternalServerError)
		return
	}

	// Check if email is allowed
	if userInfo.Email != cfg.AllowedEmail {
		log.Printf("Unauthorized login attempt: %s", userInfo.Email)
		http.Redirect(w, r, "/unauthorized", http.StatusTemporaryRedirect)
		return
	}

	// Store user info in session
	session.Values[userEmailKey] = userInfo.Email
	session.Values[userNameKey] = userInfo.Name
	session.Values[userPictureKey] = userInfo.Picture
	delete(session.Values, oauthStateKey)
	if err := session.Save(r, w); err != nil {
		log.Printf("Failed to save session: %v", err)
	}

	log.Printf("User logged in: %s", userInfo.Email)
	logInfo("User logged in: "+userInfo.Email, "auth", "")
	http.Redirect(w, r, "/", http.StatusTemporaryRedirect)
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
		email, ok := session.Values[userEmailKey].(string)
		if !ok || email == "" {
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

func getSessionUser(r *http.Request) (email, name, picture string) {
	session, _ := store.Get(r, sessionName)
	email, _ = session.Values[userEmailKey].(string)
	name, _ = session.Values[userNameKey].(string)
	picture, _ = session.Values[userPictureKey].(string)
	return
}
