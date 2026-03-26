# Security TODOs

Remaining security items from the 2025-01-31 audit. All critical and high severity issues have been fixed.

---

## Medium Priority

### 1. CSRF Protection

**Risk**: Cross-Site Request Forgery attacks could allow malicious sites to perform actions on behalf of authenticated users.

**Current state**: No CSRF tokens on state-changing endpoints.

**Fix**:
- Generate CSRF token on login, store in session
- Include token in a meta tag or cookie
- Validate token on all POST/PUT/DELETE requests
- Use `SameSite=Strict` cookie attribute

**Files to modify**:
- `web/main.go`: Add CSRF middleware
- `web/static/js/app.js`: Include CSRF token in fetch headers
- `web/static/js/files.js`: Include CSRF token in fetch headers

**Implementation sketch**:
```go
// Generate token
func generateCSRFToken() string {
    b := make([]byte, 32)
    rand.Read(b)
    return base64.StdEncoding.EncodeToString(b)
}

// Middleware
func csrfProtection(next http.HandlerFunc) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        if r.Method != "GET" && r.Method != "HEAD" && r.Method != "OPTIONS" {
            token := r.Header.Get("X-CSRF-Token")
            sessionToken := getSessionCSRFToken(r)
            if token == "" || token != sessionToken {
                http.Error(w, "CSRF token mismatch", http.StatusForbidden)
                return
            }
        }
        next(w, r)
    }
}
```

---

### 2. Content-Security-Policy Headers

**Risk**: XSS attacks could inject malicious scripts. CSP provides defense-in-depth.

**Current state**: No CSP headers set.

**Fix**:
- Add CSP header to all responses
- Start with report-only mode to identify violations
- Tighten policy once stable

**Files to modify**:
- `web/main.go`: Add CSP middleware

**Implementation**:
```go
func securityHeaders(next http.HandlerFunc) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Security-Policy",
            "default-src 'self'; "+
            "script-src 'self' https://cdnjs.cloudflare.com; "+
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "+
            "font-src 'self' https://fonts.gstatic.com; "+
            "img-src 'self' data: https:; "+
            "connect-src 'self'")
        w.Header().Set("X-Content-Type-Options", "nosniff")
        w.Header().Set("X-Frame-Options", "DENY")
        w.Header().Set("Referrer-Policy", "strict-origin-when-cross-origin")
        next(w, r)
    }
}
```

---

### 3. Rate Limiting for Processing Endpoints

**Risk**: Resource exhaustion through repeated expensive operations (video processing, OCR, conversions).

**Current state**: No rate limiting on any endpoints.

**Fix**:
- Implement per-user rate limiting for expensive operations
- Use token bucket or sliding window algorithm
- Return 429 Too Many Requests when limit exceeded

**Files to modify**:
- `web/main.go`: Add rate limiter middleware
- `web/media.go`: Apply to processing endpoints

**Implementation sketch**:
```go
type RateLimiter struct {
    mu       sync.Mutex
    visitors map[string]*rate.Limiter
}

func (rl *RateLimiter) GetLimiter(userID string) *rate.Limiter {
    rl.mu.Lock()
    defer rl.mu.Unlock()

    limiter, exists := rl.visitors[userID]
    if !exists {
        // 5 requests per minute for processing endpoints
        limiter = rate.NewLimiter(rate.Every(time.Minute/5), 2)
        rl.visitors[userID] = limiter
    }
    return limiter
}

func rateLimited(rl *RateLimiter, next http.HandlerFunc) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        userID := getUserID(r)
        if !rl.GetLimiter(userID).Allow() {
            http.Error(w, "Rate limit exceeded", http.StatusTooManyRequests)
            return
        }
        next(w, r)
    }
}
```

---

## Low Priority

### 4. Log Endpoint Access Restriction

**Risk**: Debug logs may expose sensitive information to non-admin users.

**Current state**: Any authenticated user can access `/api/logs` and `/api/thinking`.

**Fix**:
- Add admin role to user system
- Restrict log endpoints to admin users only
- Consider removing thinking blocks from production

**Files to modify**:
- `web/logs.go`: Add admin check
- `web/main.go`: Update route registration

**Implementation**:
```go
func requireAdmin(next http.HandlerFunc) http.HandlerFunc {
    return requireAuth(func(w http.ResponseWriter, r *http.Request) {
        userEmail := getSessionEmail(r)
        if !isAdmin(userEmail) {
            http.Error(w, "Admin access required", http.StatusForbidden)
            return
        }
        next(w, r)
    })
}

func isAdmin(email string) bool {
    // Hardcoded for now, move to config
    adminEmails := []string{"admin@example.com"}
    for _, admin := range adminEmails {
        if email == admin {
            return true
        }
    }
    return false
}
```

---

### 5. Error Message Sanitization

**Risk**: Verbose error messages may leak implementation details to attackers.

**Current state**: Some errors include internal paths, database errors, or Python traceback details.

**Fix**:
- Create wrapper functions for error responses
- Log full error internally, return generic message to user
- Use error codes for client-side handling

**Files to modify**:
- `web/media.go`: Sanitize subprocess errors
- `web/files.go`: Sanitize vault errors

**Implementation**:
```go
// Map internal errors to user-friendly messages
func sanitizeError(err error) string {
    errStr := err.Error()

    // Log the full error for debugging
    log.Printf("Internal error: %v", err)

    // Return generic messages
    switch {
    case strings.Contains(errStr, "no such file"):
        return "File not found"
    case strings.Contains(errStr, "permission denied"):
        return "Access denied"
    case strings.Contains(errStr, "conversion failed"):
        return "Conversion failed. Please try a different format."
    default:
        return "An error occurred. Please try again."
    }
}
```

---

## Completed (2025-01-31)

These issues were fixed during the initial security audit:

| Severity | Issue | Fix |
|----------|-------|-----|
| Critical | Path traversal via SourcePath in media endpoints | Removed SourcePath, require vault ID only |
| High | Command injection via dimension values | Added validateDimension() with numeric check |
| High | Command injection via timestamp | Added validateTimestamp() with format check |
| High | XSS via innerHTML in app.js | Changed to textContent/createElement |
| High | Missing filename validation in vault.py | Added validate_filename() |
| High | Missing topic name validation | Added validate_topic_name() |
| Medium | Weak vault ID validation | Added isValidVaultID() with strict format check |

---

## Testing Checklist

After implementing fixes, verify:

- [ ] CSRF: Requests without token are rejected
- [ ] CSRF: Requests with invalid token are rejected
- [ ] CSRF: Valid requests still work
- [ ] CSP: Check browser console for violations
- [ ] CSP: Highlight.js still works
- [ ] CSP: Google Fonts still load
- [ ] Rate limit: 6th request in 1 minute returns 429
- [ ] Rate limit: Limit resets after cooldown
- [ ] Admin: Non-admin gets 403 on /api/logs
- [ ] Admin: Admin can access /api/logs
- [ ] Errors: No internal paths in error responses
