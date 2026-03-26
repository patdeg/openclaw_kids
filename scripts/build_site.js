#!/usr/bin/env node
/**
 * Build the OpenClaw Kids site from MEDIUM_ARTICLE.md + template.html → docs/index.html
 *
 * Usage:
 *   cd scripts && npm install && npm run build
 *   — or —
 *   node scripts/build_site.js
 */

const fs = require("fs");
const path = require("path");
const { marked } = require(path.join(__dirname, "node_modules", "marked"));

const ROOT = path.resolve(__dirname, "..");
const MD_PATH = path.join(ROOT, "docs", "MEDIUM_ARTICLE.md");
const TEMPLATE_PATH = path.join(__dirname, "template.html");
const OUT_PATH = path.join(ROOT, "docs", "index.html");

// ── Read inputs ──────────────────────────────────────────────

const md = fs.readFileSync(MD_PATH, "utf-8");
const template = fs.readFileSync(TEMPLATE_PATH, "utf-8");

// ── Parse the markdown into sections ─────────────────────────

const lines = md.split("\n");

// Extract title (first H1)
let title = "";
let subtitleLine = "";
let bodyStart = 0;

for (let i = 0; i < lines.length; i++) {
  const line = lines[i];
  if (!title && line.startsWith("# ")) {
    title = line.replace(/^# /, "");
    continue;
  }
  if (!subtitleLine && line.startsWith("*") && line.endsWith("*") && !line.startsWith("**")) {
    subtitleLine = line.replace(/^\*/, "").replace(/\*$/, "");
    bodyStart = i + 1;
    break;
  }
}

// Skip leading --- after subtitle
while (bodyStart < lines.length && (lines[bodyStart].trim() === "" || lines[bodyStart].trim() === "---")) {
  bodyStart++;
}

// Find trailing tags line and CTA
let bodyEnd = lines.length;
let tagsLine = "";
let ctaLines = [];

for (let i = lines.length - 1; i >= 0; i--) {
  const line = lines[i].trim();
  if (line === "" || line === "---") continue;
  if (line.startsWith("**Tags:**")) {
    tagsLine = line;
    bodyEnd = i;
    continue;
  }
  if (line.startsWith("*") && line.endsWith("*") && (line.includes("GitHub") || line.includes("Unscarcity"))) {
    ctaLines.unshift(line);
    bodyEnd = Math.min(bodyEnd, i);
    continue;
  }
  break;
}

// Trim trailing --- from body
while (bodyEnd > 0 && (lines[bodyEnd - 1].trim() === "" || lines[bodyEnd - 1].trim() === "---")) {
  bodyEnd--;
}

const bodyMd = lines.slice(bodyStart, bodyEnd).join("\n");

// ── Configure marked ─────────────────────────────────────────

marked.setOptions({
  gfm: true,
  breaks: false,
});

// ── Convert to HTML ──────────────────────────────────────────

const bodyHtml = marked.parse(bodyMd);

// Parse tags
const tags = tagsLine
  .replace(/\*\*Tags:\*\*\s*/, "")
  .split(/\s+/)
  .filter((t) => t.startsWith("#"))
  .map((t) => t.replace("#", ""));

const tagsHtml = tags.map((t) => `<span class="tag">${t}</span>`).join("\n            ");

// Parse CTA
const ctaHtml = ctaLines.map((l) => marked.parse(l)).join("\n");

// ── Inject into template ─────────────────────────────────────

let html = template;
html = html.replaceAll("{{TITLE}}", title);
html = html.replaceAll("{{SUBTITLE}}", subtitleLine);
html = html.replaceAll("{{BODY}}", bodyHtml);
html = html.replaceAll("{{TAGS}}", tagsHtml);
html = html.replaceAll("{{CTA}}", ctaHtml);

fs.writeFileSync(OUT_PATH, html, "utf-8");

const sizeKb = (Buffer.byteLength(html) / 1024).toFixed(1);
console.log(`✓ Built docs/index.html (${sizeKb} KB)`);
console.log(`  Title:    ${title}`);
console.log(`  Sections: ${(bodyHtml.match(/<h2/g) || []).length} H2, ${(bodyHtml.match(/<h3/g) || []).length} H3`);
console.log(`  Tags:     ${tags.join(", ")}`);
