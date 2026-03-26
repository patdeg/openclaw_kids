# Skills Governance

How ATHENA should use its skills to help with school, volleyball, gaming, and life.

## Available Skills

| Skill | Purpose | Key Capability |
|-------|---------|----------------|
| **school** | School monitoring | Grades, assignments, submissions (Canvas LMS) |
| **california-study** | Curriculum study | CA standards, practice tests, mock exams (CAASPP/SBAC) |
| **homework-helper** | Study tools | Pomodoro timer, flashcards, essay outlines, math solver, citations |
| **canvas-notifications** | Grade alerts | Missing work and grade changes pushed to Discord |
| **onboarding** | Profile setup | First-run questionnaire that builds PROFILE.md |
| **minecraft** | Server management | Start/stop/restart servers on remote server via SSH |
| **volleyball-intel** | Tournament intel | Schedule, rankings, opponent scouting, live scores |
| **volleyball-training** | Training coach | Workouts, nutrition, recovery, taper plans (age-safe) |
| **media-vault** | File storage | Images, audio, documents with AI analysis |
| **family-calendars** | Schedule access | Google Calendar, volleyball (SDVBC), TeamSnap |
| **himalaya** | Email | Read/send email |
| **tavily** | Web search | Research and current information |
| **printer** | Network printing | Print to network printer via IPP |
| **demeterics** | LLM proxy | Route paid LLM calls through Demeterics for cost tracking |
| **groq-compound** | Agentic AI | Web search + code execution (learning tool) |
| **local-ai** | On-device AI | Local LLM chat, Whisper STT |

## Built-in Tools (always available)

| Tool | What It Does |
|------|-------------|
| **browser** | Headless Chromium — JS-heavy sites, interactive pages |
| **web_fetch** | Fetch raw HTML from a URL |
| **exec** | Run shell commands and skill scripts |

## Decision Tree

### School questions
```
"What are my grades?" → school grades
"What's missing?" → school missing
"What's due?" → school upcoming
"Give me practice problems" → california-study practice
"Help me study" → homework-helper flashcards or california-study
"Start a study session" → homework-helper pomodoro start
```

### Minecraft questions
```
"Is the server online?" → minecraft status
"Who's playing?" → minecraft players
"Start pokemonserver" → minecraft start pokemonserver
```

### Volleyball questions
```
"Next tournament?" → volleyball-intel next-tournament
"Scout Coast VBC" → volleyball-intel scout coast
"Give me a workout" → volleyball-training workout <type>
"What should I eat?" → volleyball-training meal-plan <context>
"Tournament Saturday" → volleyball-training meal-plan tournament-day
```

### Vault / files
```
User uploads something → media-vault auto-stores
"What files do I have?" → media-vault search/list
```

### Web research
```
Unknown topic → tavily search
Known URL → web_fetch or browser
```

## Skill Documentation

Each skill has its own `SKILL.md` with full command reference.

## IMPORTANT: Vault Operations

Always use `vault.py` commands for file operations. Never manipulate vault
files directly with `mkdir`, `mv`, `rm`, etc. The vault database is the
source of truth, not the filesystem.
