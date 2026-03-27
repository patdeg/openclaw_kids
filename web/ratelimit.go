package main

import (
	"net"
	"net/http"
	"strings"
	"sync"
	"time"
)

type rateEntry struct {
	count     int
	windowEnd time.Time
}

var (
	rateMu  sync.Mutex
	rateMap = make(map[string]*rateEntry)
)

// realIP extracts the client IP, respecting X-Forwarded-For from trusted reverse proxies.
func realIP(r *http.Request) string {
	if xff := r.Header.Get("X-Forwarded-For"); xff != "" {
		// Take only the first (leftmost) IP — the actual client
		ip := strings.TrimSpace(strings.SplitN(xff, ",", 2)[0])
		if net.ParseIP(ip) != nil {
			return ip
		}
	}
	ip, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		return r.RemoteAddr
	}
	return ip
}

// checkRateLimit returns true if the request is within the allowed rate.
// Uses a fixed 1-minute window per IP.
func checkRateLimit(ip string, maxPerMinute int) bool {
	rateMu.Lock()
	defer rateMu.Unlock()

	now := time.Now()
	entry, exists := rateMap[ip]
	if !exists || now.After(entry.windowEnd) {
		rateMap[ip] = &rateEntry{count: 1, windowEnd: now.Add(time.Minute)}
		return true
	}
	entry.count++
	return entry.count <= maxPerMinute
}

// rateLimited wraps a handler with per-IP rate limiting.
func rateLimited(maxPerMinute int, next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		ip := realIP(r)
		if !checkRateLimit(ip, maxPerMinute) {
			http.Error(w, "Too many requests", http.StatusTooManyRequests)
			return
		}
		next(w, r)
	}
}

// cleanRateMap removes expired entries periodically to prevent unbounded growth.
func cleanRateMap() {
	for {
		time.Sleep(5 * time.Minute)
		rateMu.Lock()
		now := time.Now()
		for ip, e := range rateMap {
			if now.After(e.windowEnd) {
				delete(rateMap, ip)
			}
		}
		rateMu.Unlock()
	}
}
