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
	Port          int
	WebPassword   string
	WebUsername   string
	SessionSecret string
	ClawdbotCLI   string
	VaultDir      string
	SkillsDir     string
}

// LoadConfig loads configuration from environment variables
func LoadConfig() *Config {
	// Load .env file if present (ignore error if not found)
	godotenv.Load()

	// Validate WEB_PASSWORD
	webPassword := os.Getenv("WEB_PASSWORD")
	if webPassword == "" {
		log.Fatalf("WEB_PASSWORD is required.\n\n" +
			"Password requirements:\n" +
			"  - At least 16 characters\n" +
			"  - At least one uppercase letter\n" +
			"  - At least one lowercase letter\n" +
			"  - At least one digit\n" +
			"  - At least one special character (!@#$%%^&*...)\n\n" +
			"Generate one with: openssl rand -base64 24")
	}

	if errMsg := validatePassword(webPassword); errMsg != "" {
		log.Fatalf("WEB_PASSWORD is too weak: %s.\n\n"+
			"Password requirements:\n"+
			"  - At least 16 characters\n"+
			"  - At least one uppercase letter\n"+
			"  - At least one lowercase letter\n"+
			"  - At least one digit\n"+
			"  - At least one special character (!@#$%%^&*...)\n\n"+
			"Generate one with: openssl rand -base64 24", errMsg)
	}

	vaultDir := getEnvOrDefault("VAULT_DIR", "/opt/openclaw/vault")
	return &Config{
		Port:          8085,
		WebPassword:   webPassword,
		WebUsername:    getEnvOrDefault("WEB_USERNAME", "Player"),
		SessionSecret: requireSessionSecret(),
		ClawdbotCLI:   getEnvOrDefault("CLAWDBOT_CLI", "/usr/local/bin/openclaw-cli"),
		VaultDir:      vaultDir,
		SkillsDir:     getEnvOrDefault("SKILLS_DIR", "/opt/openclaw/skills"),
	}
}

func requireSessionSecret() string {
	secret := os.Getenv("SESSION_SECRET")
	if secret == "" || secret == "dev-secret-change-in-prod" {
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
