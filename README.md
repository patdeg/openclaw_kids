# OpenClaw Kids

Your personal AI assistant — for school, sports, Minecraft, and life.

This is a teenager-ready fork of an adult AI assistant framework. It comes
with custom skills for schoolwork, sports tracking, Minecraft server management,
and more — all running on your own hardware, with a parenting philosophy baked
into every interaction (see `config/FAMILY_COMPASS.md`).

**Read the full article:** [patdeg.github.io/openclaw_kids](https://patdeg.github.io/openclaw_kids/)

This guide walks you through setting up everything from scratch on your
Orange Pi 6 Plus (or any ARM single-board computer with enough RAM). Follow
each stage in order. If you get stuck, ask Codex (once it's installed) or
a parent.

---

## What You're Building

By the end of this guide, you'll have:
- An AI assistant you can talk to via Discord, WhatsApp, and a web app
- A school dashboard that shows your grades and assignments from Canvas
- Minecraft server management from chat
- A sports tournament tracker and training coach
- Study tools: practice tests, flashcards, essay outlines, math help
- All running on YOUR hardware, secured and private

---

## Stage 0: Flash Ubuntu to SD Card

**You need:** Your Orange Pi 6 Plus, a microSD card (16GB+), and a computer.

1. Download the Ubuntu image for Orange Pi 6 Plus from
   [orangepi.org](http://www.orangepi.org/html/hardWare/computerAndMicrocontrollers/service-and-support/Orange-Pi-6-Plus.html)
2. Flash it to the microSD card using [balenaEtcher](https://etcher.balena.io/)
   or `dd`
3. Insert the microSD card into your Orange Pi
4. Connect: power, ethernet (or WiFi), keyboard, monitor
5. Boot up and follow the first-boot setup (create your user account)

---

## Stage 1: Install Codex and Log In

Codex is your AI co-pilot. It will help you with everything from here on.

Open a terminal and run:

```bash
# Update the system
sudo apt update && sudo apt install -y curl git

# Install Codex (OpenAI's CLI)
curl -fsSL https://get.openai.com/codex | bash

# Log in with your ChatGPT Plus subscription
codex login
```

When Codex asks how to authenticate, choose **"Log in with ChatGPT
subscription"** (NOT API key). It will open a browser — sign in with your
ChatGPT account.

Test it works:

```bash
codex "What is 2 + 2?"
```

If you get an answer, you're good. **Codex is now your guide for the rest
of this setup.**

---

## Stage 2: Bootstrap and Migrate to SSD

The SD card is slow. Let's move everything to the fast NVMe SSD.

Open Codex and paste this prompt:

> Help me migrate my Orange Pi 6 Plus from the SD card to the NVMe SSD.
> First, run `sudo apt update && sudo apt upgrade -y`. Then partition the
> NVMe SSD, format it as ext4, copy the entire root filesystem using rsync,
> update the boot configuration to boot from SSD, and then reboot.

Follow Codex's instructions step by step. Approve each command before it
runs.

**After the reboot, remove the SD card.** You're now running from SSD.

---

## Stage 3: SSD Boot — Continue Setup

You should now be booted from SSD with the SD card removed.

Open Codex again and paste:

> I just migrated to NVMe SSD. Help me install the following packages:
> Docker (with docker compose plugin), Git, Node.js v22, Python3 with
> pip and venv, build-essential, and set up UFW firewall with rules to
> allow SSH (port 22) and web (port 8085).

---

## Stage 4: Create ~/AGENTS.md

This file helps Codex (and any other AI tool) understand your machine AND
your personal setup. It's the "about me" for your AI tools.

Paste this prompt into Codex:

> Explore this machine and write ~/AGENTS.md with two sections:
>
> **Section 1: Machine Profile**
> - Hardware specs (CPU, RAM, storage, NPU)
> - OS version, kernel, architecture
> - Installed packages and versions (docker, git, node, python3)
> - Network configuration (IP addresses, interfaces)
> - UFW firewall rules — include this note at the top of the firewall
>   section:
>
>   IMPORTANT: This machine uses UFW (Uncomplicated Firewall).
>   If something network-related isn't working, it's probably because
>   UFW is blocking it. Check with: sudo ufw status
>   Add a rule with: sudo ufw allow <port>/tcp
>
> - Docker version and configuration
> - SSH configuration
> - Mounted drives and storage layout
>
> **Section 2: Owner Profile (I'll fill this in)**
> Leave placeholders for me to fill in:
> - Name and age
> - School and grade
> - School district and Canvas URL
> - Sports: team, league, position
> - Minecraft: server names and IP of the machine running them
> - Hobbies and interests
> - AI assistant name (will be set in Stage 6.5)

---

## Stage 5: Set Up GitHub SSH Key

You need an SSH key to clone code from GitHub.

```bash
# Generate your SSH key (use your email address)
ssh-keygen -t ed25519 -C "your-email@example.com"

# Press Enter for default location, then set a passphrase (or leave empty)

# Copy your public key
cat ~/.ssh/id_ed25519.pub
```

Now add it to GitHub:
1. Go to [github.com/settings/keys](https://github.com/settings/keys)
2. Click "New SSH key"
3. Title: "Orange Pi 6 Plus"
4. Paste the key from the terminal
5. Click "Add SSH key"

Test it:

```bash
ssh -T git@github.com
# Should say: "Hi <username>! You've successfully authenticated..."
```

---

## Stage 6: Clone the Project

```bash
# Create your dev folder
mkdir -p ~/dev && cd ~/dev

# Clone the project
git clone git@github.com:patdeg/openclaw_kids.git
cd openclaw_kids
```

---

## Stage 6.5: Name Your AI Assistant

Right now, your assistant is called **ATHENA** — that's just a placeholder.
Pick YOUR name. It's your assistant, make it yours.

Some ideas: JARVIS, FRIDAY, ORACLE, ECHO, NOVA, CORTANA, SAGE, ATLAS,
PHOENIX, TITAN... or something completely original.

Once you've chosen, ask Codex to rename it:

> I just cloned openclaw_kids into ~/dev/openclaw_kids. I want to rename
> my AI assistant from "ATHENA" to "[YOUR_NAME]". Find every occurrence of
> "ATHENA" in these files and replace them all:
> - web/static/index.html
> - web/static/login.html
> - web/static/school.html
> - web/static/files.html
> - web/static/unauthorized.html
> - web/static/manifest.json
> - web/static/js/app.js
> - web/static/js/files.js
> - web/voice.go
> - config/openclaw.kids.json
>
> Replace "ATHENA" with "[YOUR_NAME]" everywhere. Then show me what changed.

### Create Your AI's Avatar

Your assistant needs a face! Use any image generator you like:
- ChatGPT (Image generation) — "Create a logo/avatar for an AI assistant
  named [YOUR_NAME]"
- Or draw one yourself

Save the image and replace the placeholder:

```bash
# Copy your avatar image (PNG, roughly 200x200 pixels)
cp /path/to/your-avatar.png web/static/img/avatar.png
```

For the PWA icons (optional but nice), ask Codex:

> I have a new avatar at web/static/img/avatar.png. Generate resized
> versions for the PWA icons at web/static/img/icons/ in sizes: 48x48,
> 72x72, 96x96, 144x144, 192x192, 384x384, 512x512. Use ImageMagick.

### Personalize Your Setup

This project ships with generic placeholders. You need to plug in YOUR
details so the AI knows about your school, your sports, and your setup.

**1. Personalize the Family Compass**

Open `config/FAMILY_COMPASS.md` and find the `<!-- PERSONALIZE -->` comment
near the top. Update the user description with your details — age, location,
school district, sports, hobbies. For example:

```
Your user is a 14-year-old boy in San Diego, California. He plays club
volleyball for Seaside VBC, attends Poway Unified School District, and
runs Minecraft servers with his brother.
```

The more specific you are, the better the AI tailors its responses.

**2. Personalize the .env file**

When you fill in `.env` (Stage 7), you'll set your school's Canvas URL,
your Minecraft server's IP address, and other details specific to your
network. See `.env.example` for guidance on each value.

**3. Personalize Minecraft servers**

If you run Minecraft servers, update `skills/minecraft/servers.yaml` (or
the equivalent config) with your actual server names and paths.

**4. Personalize sports skills**

If you play a different sport or are in a different region, update the
skill configs under `skills/volleyball-intel/` and
`skills/volleyball-training/` to match your league, region, and team.

Or, ask Codex:

> I play [your sport] for [your team] in [your league/region]. Help me
> update the sports skills in this project to track my season.

### Deploy

Now run the bootstrap:

```bash
./bootstrap.sh
```

The bootstrap script will:
- Create the `/opt/openclaw/` directory structure
- Build the Docker containers
- Deploy the OpenClaw config
- Set up systemd services

---

## Stage 7: Set Up Your Secrets (.env)

```
============================================================
         YOUR .env FILE CONTAINS SECRETS
============================================================

The .env file holds API keys and passwords.
Think of it like your house key + bank PIN combined.

RULES:
  1. NEVER share this file with ANYONE
  2. NEVER upload it to GitHub (it's in .gitignore for a reason)
  3. NEVER paste its contents in Discord, WhatsApp, or email
  4. NEVER take a screenshot of it
  5. If you think it leaked, tell Dad IMMEDIATELY

What happens if someone gets your .env:
  - They can use your AI subscription (costs real money)
  - They can read your school grades
  - They can send messages pretending to be you
  - They can access all your files

This file should NEVER leave this computer.
============================================================
```

Create your .env file:

```bash
cd /opt/openclaw
cp /home/YOUR_USER/dev/openclaw_kids/.env.example .env
chmod 600 .env
nano .env
```

Fill in each value. Here's where to get them:

### Canvas API Key (School Grades)
1. Go to your school's Canvas URL (e.g., `https://yourschool.instructure.com`)
2. Log in with your school account
3. Click your profile picture (top-left) > Settings
4. Scroll down to "Approved Integrations"
5. Click "+ New Access Token"
6. Purpose: "OpenClaw" — click "Generate Token"
7. **Copy the token immediately** (you can't see it again)
8. Paste it as `CANVAS_API_KEY` in your .env

### Discord Bot Token
1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. Click "New Application" — name it (e.g., "MyAssistant")
3. Go to "Bot" in the sidebar
4. Click "Reset Token" — copy it → `DISCORD_BOT_TOKEN`
5. Under "Privileged Gateway Intents", enable Message Content Intent
6. Go to "OAuth2" > "URL Generator"
7. Check "bot" scope, then "Send Messages" + "Read Message History"
8. Copy the URL and open it to invite the bot to your server
9. Your server ID → `DISCORD_GUILD_ID` (right-click server name > Copy ID)
10. Your user ID → `DISCORD_USER_ID` (right-click your name > Copy ID)

### Tavily API Key (Web Search)
1. Go to [tavily.com](https://tavily.com) and sign up (free tier available)
2. Copy your API key → `TAVILY_API_KEY`

### Other Keys
Ask a parent for help with: `MIGADU_PASSWORD`, `GOOGLE_CLIENT_ID`,
`GOOGLE_CLIENT_SECRET`, `SESSION_SECRET`, `DEMETERICS_API_KEY`, `GROQ_API_KEY`

---

## Stage 8: Launch and Verify

```bash
cd /opt/openclaw

# Build and start everything
docker compose up -d --build

# Check containers are running
docker ps

# View logs if something went wrong
docker compose logs -f
```

Open your browser to `http://YOUR_PI_IP:8085` and log in.

**Test these in chat:**
- "What are my grades?"
- "Is the Minecraft server online?"
- "Generate 5 math practice problems"
- "When is my next volleyball tournament?"

### Connect Discord
```bash
docker exec -it openclaw-gateway openclaw pair discord
```

### Connect WhatsApp
```bash
docker exec -it openclaw-gateway openclaw pair whatsapp
```

---

## Stage 9: Security Lockdown

This is important. Your Orange Pi is a real computer on the network.

### UFW Firewall (should already be set up from Stage 3)
```bash
sudo ufw status
# Should show: 22/tcp ALLOW, 8085/tcp ALLOW, default deny

# If not:
sudo ufw default deny incoming
sudo ufw allow ssh
sudo ufw allow 8085/tcp
sudo ufw enable
```

### fail2ban (protects against SSH brute force)
```bash
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### Automatic Security Updates
```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

### SSH Key-Only Auth (disable passwords)
```bash
# Make sure you can log in with your SSH key first!
# Then edit sshd_config:
sudo nano /etc/ssh/sshd_config

# Change these lines:
#   PasswordAuthentication no
#   ChallengeResponseAuthentication no

sudo systemctl restart sshd
```

### Verify .env Permissions
```bash
ls -la /opt/openclaw/.env
# Should show: -rw------- (only you can read it)
```

---

## Stage 10: Meet Your Assistant

On first chat, your assistant will ask you some questions to get to know
you — favorite subjects, games, sports, study preferences. Answer honestly!
This helps it personalize everything for you.

After onboarding, try these:

**School:**
- "What are my grades?"
- "What assignments am I missing?"
- "Give me 10 practice problems for 8th grade math"
- "Help me outline an essay about the Civil War"
- "Start a pomodoro study session"

**Minecraft:**
- "Is the Minecraft server online?"
- "Who's playing right now?"
- "Start [your server name]"

**Sports:**
- "When is my next tournament?"
- "Scout [opponent team name]"
- "Give me a lower body workout"
- "What should I eat on game day?"
- "Create a taper plan for this weekend"

**General:**
- "Help me with this math problem: 3x + 7 = 22"
- "What should I read next?"
- "I'm feeling stressed about school"

---

## Troubleshooting

### "Connection refused" on port 8085
Check UFW: `sudo ufw status` — make sure port 8085 is allowed.

### Docker containers won't start
```bash
docker compose logs -f  # Check for errors
docker compose down && docker compose up -d --build  # Rebuild
```

### "CANVAS_API_KEY must be set"
You forgot to fill in your .env file. Go back to Stage 7.

### Can't SSH to GitHub
Make sure your SSH key is added: `ssh -T git@github.com`

### Minecraft commands are slow
SSH to the Minecraft server can take a moment. Be patient.

### Something network-related isn't working
**Check UFW first:** `sudo ufw status`. If the port isn't listed, add it:
`sudo ufw allow <PORT>/tcp`

---

## Project Structure

```
openclaw_kids/
├── config/
│   ├── openclaw.kids.json     ← AI model and skill config
│   └── FAMILY_COMPASS.md      ← How the AI should interact with you
├── skills/
│   ├── school/                 ← Canvas LMS grades & assignments
│   ├── california-study/       ← CA curriculum practice tests
│   ├── homework-helper/        ← Pomodoro, flashcards, math, citations
│   ├── canvas-notifications/   ← Grade alerts via Discord
│   ├── minecraft/              ← Server management via SSH
│   ├── volleyball-intel/       ← Tournament scouting & live scores
│   ├── volleyball-training/    ← Workouts, nutrition, recovery
│   ├── onboarding/             ← First-run questionnaire
│   ├── media-vault/            ← File storage & search
│   ├── family-calendars/       ← iCal feeds for your activities
│   ├── tavily/                 ← Web search
│   ├── printer/                ← Network printing
│   └── ...
├── web/                        ← Go web server + frontend
├── docker-compose.yml
├── Dockerfile.openclaw
├── Dockerfile.web
├── bootstrap.sh
├── .env.example                ← Template (safe to commit)
├── .env                        ← YOUR SECRETS (NEVER commit)
└── README.md                   ← This file
```

---

## For Parents

To update after changes are pushed to GitHub:
```bash
cd ~/dev/openclaw_kids && git pull
cd /opt/openclaw && docker compose up -d --build
```

Each kid should have their own hardware with a separate deployment.
Email accounts are optional but recommended — set up via Migadu or any
IMAP provider and configure in the `.env` file.
