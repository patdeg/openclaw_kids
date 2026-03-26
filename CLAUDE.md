# OpenClaw Kids — Developer Guide

Teenager-ready fork of [alfred_openclaw](https://github.com/patdeg/alfred_openclaw).
Each kid gets their own Orange Pi 6 Plus (or similar ARM SBC) with an
independent deployment.

## Architecture

- **Gateway**: OpenClaw (Node 22) on port 18789 — AI orchestration
- **Web UI**: Go server on port 8085 — chat, school dashboard, file vault
- **AI Model**: `openai-codex/gpt-5.4` via ChatGPT Plus subscription (Option B OAuth)
- **Channels**: WhatsApp + Discord
- **Minecraft**: SSH to a local server (configured in `.env`)

## Key Files

- `config/openclaw.kids.json` — OpenClaw agent config (model, skills, channels)
- `config/FAMILY_COMPASS.md` — Parental guidance injected into system prompt
- `.env.example` — Gateway secrets template
- `alfred-web.env.example` — Web UI secrets template
- `bootstrap.sh` — Deployment automation

## Skills (17 total)

**Kept from alfred_openclaw:** school, family-calendars, media-vault, tavily,
printer, demeterics, himalaya, groq-compound, local-ai

**New:** onboarding, minecraft, california-study, homework-helper,
canvas-notifications, volleyball-intel, volleyball-training

**Removed:** alpaca, bank-transactions, cashflow, finance-query,
investment-advisor, sleep, elevenlabs-voice, twilio

## Web UI

Pages: `/` (chat), `/school` (grades dashboard), `/files` (media vault)
Removed: `/trading`, `/finance`

## Security

- .env files NEVER committed (blocked by pre-commit hook in .githooks/)
- Rootless Docker, UFW firewall, fail2ban
- FAMILY_COMPASS.md enforces age-appropriate interaction safety

## Development

```bash
# Web UI (Go)
cd web && go build -o alfred && ./alfred -base-url http://localhost:8085

# Test a skill
python3 skills/minecraft/minecraft.py status
python3 skills/california-study/california_study.py curriculum --grade 8
python3 skills/volleyball-intel/volleyball_intel.py next-tournament
```
