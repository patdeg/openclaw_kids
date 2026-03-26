package main

import (
	"crypto/rand"
	"encoding/hex"
	"log"
	"os"

	"github.com/joho/godotenv"
)

// Config holds application configuration
type Config struct {
	Port               int
	GoogleClientID     string
	GoogleSecret       string
	AllowedEmail       string
	SessionSecret      string
	DemetericsAPIKey   string
	DemetericsBaseURL  string
	ClawdbotCLI        string
	GroqAPIKey         string
	VaultDir           string
	SkillsDir          string
}

// LoadConfig loads configuration from environment variables
func LoadConfig() *Config {
	// Load .env file if present (ignore error if not found)
	godotenv.Load()

	vaultDir := getEnvOrDefault("VAULT_DIR", "/opt/openclaw/vault")
	return &Config{
		Port:               8085,
		GoogleClientID:     os.Getenv("GOOGLE_CLIENT_ID"),
		GoogleSecret:       os.Getenv("GOOGLE_CLIENT_SECRET"),
		AllowedEmail:       getEnvOrDefault("ALLOWED_EMAIL", "you@example.com"),
		SessionSecret:      requireSessionSecret(),
		DemetericsAPIKey:   os.Getenv("DEMETERICS_API_KEY"),
		DemetericsBaseURL:  getEnvOrDefault("DEMETERICS_BASE_URL", "https://api.demeterics.com"),
		ClawdbotCLI:        getEnvOrDefault("CLAWDBOT_CLI", "/usr/local/bin/openclaw-cli"),
		GroqAPIKey:         os.Getenv("GROQ_API_KEY"),
		VaultDir:           vaultDir,
		SkillsDir:          getEnvOrDefault("SKILLS_DIR", "/opt/openclaw/skills"),
	}
}

func requireSessionSecret() string {
	secret := os.Getenv("SESSION_SECRET")
	if secret == "" || secret == "alfred-dev-secret-change-in-prod" {
		// Generate a random secret for development; log a warning
		b := make([]byte, 32)
		if _, err := rand.Read(b); err != nil {
			log.Fatalf("SESSION_SECRET not set and failed to generate random secret: %v", err)
		}
		secret = hex.EncodeToString(b)
		log.Printf("WARNING: SESSION_SECRET not set — using random ephemeral secret (sessions won't survive restarts)")
	}
	return secret
}

func getEnvOrDefault(key, defaultVal string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return defaultVal
}
