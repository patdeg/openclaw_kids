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
- A task manager to track homework, projects, and to-dos (with AI chat per task)
- Minecraft server management from chat
- A sports tournament tracker and training coach
- Study tools: practice tests, flashcards, essay outlines, math help
- Your own Minecraft server with plugins, playable from any device on your network
- A polished desktop with apps for school, creativity, and daily use
- All running on YOUR hardware, secured and private

---

## Before You Start

Make sure you have all the hardware. **Do not skip the power supply** —
using an underpowered charger will cause random crashes and corrupted data.

See the **[Bill of Materials](#bill-of-materials)** at the bottom of this
document for the full shopping list with links.

Short version — you need:
- Orange Pi 6 Plus (16GB RAM recommended)
- NVMe M.2 SSD (256GB+)
- **100W USB-C power supply** (phone chargers are NOT enough)
- microSD card (16GB+) for initial boot
- HDMI cable + display (any TV or monitor works)
- USB keyboard + mouse
- Ethernet cable or a compatible WiFi module

---

## Stage 0: Flash Ubuntu to SD Card

**You need:** Your Orange Pi 6 Plus, a microSD card (16GB+), and a computer.

1. Download the Ubuntu image for Orange Pi 6 Plus from
   [orangepi.org](http://www.orangepi.org/html/hardWare/computerAndMicrocontrollers/service-and-support/Orange-Pi-6-Plus.html)
2. Flash it to the microSD card using [balenaEtcher](https://etcher.balena.io/)
   (a simple drag-and-drop tool — recommended for first-timers)
3. Insert the microSD card into your Orange Pi
4. Connect: power (100W USB-C!), ethernet (or WiFi), keyboard, monitor
5. Boot up — you should see the Ubuntu desktop after a moment

---

## Stage 1: First Boot

You've just booted Ubuntu on your Orange Pi. Let's get oriented.

### Log In

The default credentials are:
- **Username:** `orangepi`
- **Password:** `orangepi`

Yes, the password is the same as the username. That's terrible security —
and it's printed on the internet for anyone to read. We'll fix it in a minute.

### Open a Terminal

Click the **white bar at the top-left** of the screen to open the
application menu. Click **Terminal**.

This is where you'll type every command in this guide. Get comfortable
with it — the terminal is the most powerful tool on any Linux machine.

> **Tip:** You'll also see a **Chrome** icon in the menu — open this
> README on GitHub so you can copy commands directly. Use **Ctrl+C** to
> copy in Chrome, and **Shift+Ctrl+V** to paste in the Terminal. (Regular
> Ctrl+V doesn't work in Linux terminals — it means something else.)

### Set Your Keyboard Layout and Language

If you're not using a US English keyboard, fix this **now** — before you
start typing passwords and commands. Wrong keyboard layout means wrong
characters, which means wrong passwords and broken commands.

**Why this matters first:** When you change your password in the next
step, every character needs to be exactly what you intend. If your `@` key
produces `"` because the layout is wrong, your password won't be what you
think it is.

**Option A: GUI (if you have a display connected)**

1. Click the **top-right corner** of the screen → **Settings** (gear icon)
2. Go to **Region & Language** (GNOME) or **Keyboard** (XFCE)
3. Under **Input Sources**, click **+** and add your keyboard layout
   (e.g., French, German, Spanish, UK English, Brazilian Portuguese)
4. Remove "English (US)" if you don't need it, or keep both and use
   **Super+Space** to switch between them
5. While you're here, set your **Language** and **Formats** (date, time,
   currency) to your country

**Option B: Terminal (works over SSH too)**

```bash
# See what keyboard layouts are available (long list!)
localectl list-keymaps | grep -i french    # replace "french" with your language

# Set your keyboard layout (examples)
sudo localectl set-keymap fr               # French (AZERTY)
sudo localectl set-keymap de               # German (QWERTZ)
sudo localectl set-keymap gb               # British English
sudo localectl set-keymap es               # Spanish
sudo localectl set-keymap br-abnt2         # Brazilian Portuguese
sudo localectl set-keymap us               # US English (default)
sudo localectl set-keymap latam            # Latin American Spanish

# Set your locale (language for menus, dates, currency)
sudo localectl set-locale LANG=fr_FR.UTF-8        # French (France)
sudo localectl set-locale LANG=de_DE.UTF-8        # German (Germany)
sudo localectl set-locale LANG=es_ES.UTF-8        # Spanish (Spain)
sudo localectl set-locale LANG=pt_BR.UTF-8        # Portuguese (Brazil)
sudo localectl set-locale LANG=en_US.UTF-8        # English US (default)

# Set your timezone
sudo timedatectl set-timezone America/Los_Angeles  # US Pacific
sudo timedatectl set-timezone Europe/Paris          # France
sudo timedatectl set-timezone Europe/Berlin         # Germany
sudo timedatectl set-timezone America/Sao_Paulo    # Brazil

# Verify everything
localectl
timedatectl
```

> **Tip:** Not sure what your keymap is called? Try
> `localectl list-keymaps | less` and scroll through, or search with
> `grep`. Press **q** to exit the list.

After changing the locale, you may need to generate it:

```bash
sudo locale-gen
```

> **How to test your keyboard:** Open a terminal and type special
> characters from your language — accented letters (é, ñ, ü, ç),
> symbols (@, #, {, }), and the pipe character (|). If they all come
> out right, you're set. If not, double-check the keymap name.

### Connect to the Network

You need internet access. Pick one:

**Option A: Ethernet (easiest)** — plug an ethernet cable between the
Orange Pi and your WiFi router. Done. No configuration needed.

**Option B: WiFi** — click the **top-right corner** of the screen to
open the system menu, click **WiFi**, and connect to your home network.

Verify you're connected:

```bash
ping -c 3 google.com
```

If you see replies, you're online.

### (Optional) Work Remotely via SSH

From now on, you don't need to sit in front of the Orange Pi. You can
run all commands from your main computer (laptop, desktop, even a phone
with a terminal app) using **SSH** — a secure remote connection.

First, find your Orange Pi's IP address:

```bash
hostname -I
```

This prints something like `192.168.1.42`. That's your Pi's address on
your home network.

Now, from a terminal on your **other computer**, connect:

```bash
ssh orangepi@192.168.1.42    # replace with your actual IP
# (After you create your own account below, use YOUR username instead)
```

Type `yes` when asked about the fingerprint, then enter the password
(`orangepi` if you haven't changed it yet, or your new password if you
already changed it below).

You're now controlling your Orange Pi remotely. Everything in this guide
works the same over SSH — you're just typing from a more comfortable
keyboard.

> **Tip:** On macOS and Linux, SSH is built in — just open Terminal. On
> Windows, use Windows Terminal or PowerShell (SSH is built into Windows
> 10+). On a Chromebook, use the built-in Linux terminal.

### Change Your Password — NOW

This is your **first security lesson**: default passwords are dangerous.
Anyone who knows the default (and it's publicly documented) can log into
your machine over the network.

```bash
passwd
```

It will ask for the current password (`orangepi`), then your new one twice.

Pick a **strong** password:
- At least 12 characters
- Mix of uppercase, lowercase, numbers, and symbols
- NOT your name, birthday, pet's name, or "password123"
- Something you can remember without writing it down on a sticky note

> **Why this matters:** Your Orange Pi is a real computer on your home
> network. If someone gets access — a friend, a visitor, or someone on
> your WiFi — they could read your files, use your AI subscription
> (which costs real money), or even access other devices on your network.
> A strong password is your first line of defense. You'll see this
> pattern throughout this guide: **security isn't optional, it's built in.**

### Create Your Own User Account

You're logged in as `orangepi` — a generic default that every Orange Pi
ships with. Let's create YOUR account with your own username.

Pick a username — lowercase letters, no spaces. Your first name works:
`lucas`, `max`, `sofia`, `alex`.

```bash
# Create your account (replace "yourname" with your chosen username)
sudo adduser yourname
```

It asks for a password (use a strong one!) and some optional info (full
name is useful; skip the rest with Enter).

Now give your account the permissions it needs:

```bash
# Add yourself to the necessary groups
sudo usermod -aG sudo,video,audio,render,plugdev yourname
```

What these groups do:
- **sudo** — run commands as administrator
- **video** / **render** — access the GPU for video and graphics
- **audio** — play sound
- **plugdev** — use USB devices

> We'll add the `docker` group later in Stage 6 when Docker is installed.

#### Name Your Machine

Your Pi's hostname is how it shows up on the network. Give it a name
you'll recognize:

```bash
sudo hostnamectl set-hostname my-pi-name
```

Pick something memorable — your name, your AI assistant's name, or
anything fun.

#### Switch to Your New Account

Log out and log back in as **your** user:

- **At the screen:** Click the top-right user menu → Log Out → log in
  with your new username
- **Over SSH:** `exit`, then `ssh yourname@YOUR_PI_IP`

**From this point forward, every command in this guide runs as YOUR user,
not `orangepi`.** When you see example commands with `orangepi`, replace
it with your username.

The `orangepi` account still exists as a safety net — if you ever lock
yourself out, you can recover through it.

> **Security lesson — Identity:** Using your own account instead of a
> shared default means every action is logged under YOUR name. If
> multiple people share the `orangepi` account, there's no way to tell
> who did what. In companies and on servers, every person gets their own
> account for exactly this reason — it's called **accountability**.

---

## Stage 2: Install Node.js, npm, and Codex

Codex is your AI co-pilot. It will help you with everything from here on.
It requires **Node.js 22** and **npm**, so we install those first.

```bash
# Update the system and install essentials
sudo apt update && sudo apt upgrade -y && sudo apt install -y curl git

# NOTE: A popup may ask you to create a "keyring password".
# This is GNOME's password manager. Use the same password as your
# orangepi user account — it unlocks automatically on login that way.

# Install Node.js 22 (includes npm)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

# Verify Node.js and npm are installed
node --version   # should show v22.x.x
npm --version    # should show 10.x.x or later

# Install Codex CLI globally via npm
sudo npm install -g @openai/codex
```

> **Why `sudo` for `npm install -g`?** The `-g` flag installs packages
> globally (for all users), and the global directory (`/usr/lib/node_modules`)
> is owned by root. So you need `sudo` to write there. This is fine for
> tools you trust (like Codex). For project dependencies, you'll use
> `npm install` without `-g` or `sudo` — those go in your project folder.

> **Troubleshooting:** If you'd rather avoid `sudo` for npm globals, you
> can redirect them to your home directory:
> ```bash
> mkdir -p ~/.npm-global
> npm config set prefix ~/.npm-global
> echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.bashrc
> source ~/.bashrc
> npm install -g @openai/codex
> ```
>
> If you see `codex: command not found` after installing, your PATH doesn't
> include npm's global bin directory. Run `npm bin -g` to find it, then add
> it to your `~/.bashrc`.

Now log in:

```bash
codex login
```

Select **"Sign in with ChatGPT"**. It will open a browser; sign in with
your ChatGPT Plus account (do NOT use an API key).

Test it works:

```bash
codex "What is 2 + 2?"
```

If you get an answer, you're good. **Codex is now your guide for the rest
of this setup.**

To update Codex later: `sudo npm install -g @openai/codex@latest`

---

## Stage 3: Prepare Sudo for Codex

Codex needs to run commands as root (`sudo`) — to install packages,
partition disks, and configure the firewall. But Codex runs commands in a
sandbox and **can't type your password**.

Here's how sudo works: after you type your password, Linux remembers it
for **15 minutes** (the "sudo timeout"). After that, it asks again. Fifteen
minutes is too short for our setup steps — an SSD migration can take longer
than that.

We'll temporarily extend the timeout to **2 hours** using a sudoers
drop-in file. This is the proper way to customize sudo — you should never
edit `/etc/sudoers` directly.

```bash
# Extend the sudo timeout to 2 hours (120 minutes) for setup
echo 'Defaults timestamp_timeout=120' | sudo tee /etc/sudoers.d/setup-timeout > /dev/null
sudo chmod 440 /etc/sudoers.d/setup-timeout

# IMPORTANT: verify the sudo config is still valid
# A broken sudoers file can lock you out of sudo entirely
sudo visudo -c
# Should say: "parsed OK" for each file
```

> **Security lesson — Principle of Least Privilege:** We're temporarily
> widening access because we need it for setup. In Stage 14 (Security
> Lockdown), we'll remove this file and go back to 15 minutes. This is a
> core security principle: **grant the minimum access needed, then revoke
> it when done.** You never leave a door open longer than necessary.

Now, before each Codex session that needs sudo, refresh the sudo timer:

```bash
sudo -v
```

`sudo -v` is the proper way to prime sudo credentials — unlike
`sudo ls` or `sudo echo`, it doesn't run any unnecessary command. It
just validates your password and resets the 2-hour timer.

You'll see `sudo -v` at the start of Stages 5, 6, and 13.

---

## Stage 4: Explore Your Computer

Before we start changing things, let's understand what we're working with.
A good engineer knows their tools — and right now, your tool is a real
Linux computer.

### Linux Commands Crash Course

Here are the 10 commands you'll use most. Try each one right now.

```bash
pwd                     # Print Working Directory — where am I?
ls                      # List files in the current folder
ls -la                  # List ALL files (including hidden), with details
cd /etc                 # Change Directory — go to /etc
cd ~                    # Go back to your home folder (~ = home)
cd ..                   # Go up one folder
cat /etc/hostname       # Print a file's contents to the screen
mkdir test              # Make a new folder called "test"
rm -r test              # Remove that folder (-r = recursive)
sudo                    # Run a command as root (admin). Asks for password.
```

That's it. `pwd` to see where you are, `ls` to see what's here, `cd` to
move, `cat` to read, `mkdir`/`rm` to create/delete. Everything else
builds on these.

A few tricks:
- Press **Tab** to autocomplete file and folder names
- Press **Up arrow** to repeat the last command
- **Ctrl+C** cancels whatever is running
- **Ctrl+L** clears the screen

### Editing Files with nano

When you need to *edit* a file (not just read it), use `nano`:

```bash
nano ~/test.txt           # Opens (or creates) a file for editing
```

Type whatever you want. Then:
- **Ctrl+O** → save (it asks for the filename, just press Enter)
- **Ctrl+X** → exit
- **Ctrl+K** → cut (delete) a whole line
- **Ctrl+W** → search for text

That's it. `nano` is simple on purpose. You'll use it later to edit
config files and secrets.

> There are fancier editors (vim, VS Code) but nano works everywhere
> and you can learn it in 30 seconds. Use it for now.

Now let's explore what's inside this machine.

### Who Are You?

```bash
whoami          # Your username
hostname        # Your computer's name on the network
```

### What Operating System?

```bash
cat /etc/os-release   # Linux distribution and version
uname -a              # Kernel version and CPU architecture
```

You're running **Ubuntu** on **ARM architecture** (aarch64). Most laptops
and desktops use x86 processors (Intel/AMD), but your Orange Pi uses ARM —
the same architecture as your phone. ARM chips are more power-efficient:
your Orange Pi runs on about 15 watts, while a gaming PC might use 300+.

### How Much Brain Power? (CPU)

```bash
lscpu
```

Look for:
- **CPU(s)** — how many cores you have
- **Model name** — the processor model
- **Architecture** — should say `aarch64` (64-bit ARM)

Your Orange Pi 6 Plus has a **tri-cluster** CPU design — three groups of
cores:
- **Big** cores (Cortex-A720 @ 2.8 GHz) — for heavy tasks like compiling
  code or running AI
- **Medium** cores (Cortex-A720 @ 2.4 GHz) — a balance of power and
  efficiency
- **LITTLE** cores (Cortex-A520 @ 1.8 GHz) — for light background work,
  saving power

This is the same strategy phones use to balance performance and battery
life — except here it's about performance and heat. Linux decides which
cores to use automatically based on the workload. You'll see all 12
cores in `htop`.

### How Much Memory? (RAM)

```bash
free -h       # -h means "human-readable" (MB/GB instead of bytes)
```

- **total** — how much RAM your board has
- **used** — how much is in use right now
- **available** — how much is free for new programs
- **Swap** — overflow space on disk (much slower than RAM)

Think of RAM like your desk: the bigger it is, the more things you can
work on at once without shuffling papers around. Swap is like a filing
cabinet next to your desk — it works, but you have to reach over to use
it, so it's slower.

### How Much Storage? (Disk)

```bash
df -h           # Disk space on mounted filesystems
lsblk           # All storage devices (even unmounted ones)
```

You should see:
- **mmcblk** — your microSD card (where you're booted from right now)
- **nvme** — your NVMe SSD (empty for now — we'll migrate to it next)

Notice the speed difference when we move to SSD. The SD card reads at
about 100 MB/s; the NVMe SSD can do 2,000+ MB/s.

### See It All Live: htop

`htop` is like Task Manager on Windows, but way more informative.

```bash
sudo apt install -y htop
htop
```

What you're looking at:
- **Top bars** — one bar per CPU core. Watch them jump around! Each bar
  shows how busy that core is right now.
- **Mem** — RAM usage. Green = used by programs, yellow/orange = disk
  caches (Linux uses free RAM as cache — that's smart, not wasteful).
- **Swp** — Swap usage. Should be near zero if you have enough RAM.
- **Process list** — every program running on your machine, sorted by
  CPU or memory usage. You can see what's hogging resources.

Press **F6** to change sort order. Press **q** to quit.

### Your Network

```bash
ip addr
```

Find your IP address — it's the number after `inet` on your active
interface (look for `eth0` for ethernet or `wlan0` for WiFi). It looks
something like `192.168.1.42`. You'll need this later to access the
web UI from your phone or another computer.

### File Permissions (Your First Security Deep-Dive)

Every file on Linux has permissions that control who can read, write, or
execute it. This is fundamental to security.

```bash
ls -la /etc/shadow
```

You'll see something like: `-rw-r----- 1 root shadow`

That means:
- **Owner (root):** can read and write (`rw-`)
- **Group (shadow):** can read (`r--`)
- **Everyone else:** nothing (`---`)

This file stores password hashes. If everyone could read it, they could
try to crack passwords offline. Linux prevents that with permissions.

You'll use this concept later when we `chmod 600` your secrets file —
that means "only the owner can read and write; nobody else can touch it."

> **Want to learn more Linux commands?** Bookmark this:
> [linuxcommand.org](https://linuxcommand.org/) — it's a free online
> book that starts from zero and goes deep. You don't need to read it
> now, but it's there when you're curious.

---

## Stage 5: Migrate to SSD

Now you know your machine — and you've seen how the SD card and SSD
show up in `lsblk`. Time to move everything to the fast SSD.

Refresh sudo, then open Codex:

```bash
sudo -v
```

Open Codex and paste this prompt:

> Help me migrate my Orange Pi 6 Plus from the SD card to the NVMe SSD.
> Partition the NVMe SSD, format it as ext4, copy the entire root
> filesystem using rsync, update the boot configuration to boot from SSD,
> and reboot.

Follow Codex's instructions step by step. Approve each command before it
runs.

**After the reboot, remove the SD card.** You're now running from SSD.

> After you reboot, run `lsblk` again and compare with what you saw in
> Stage 4. Notice how the root filesystem (`/`) is now on `nvme` instead
> of `mmcblk`. That's the migration at work.

---

## Stage 6: Install Development Tools

You should now be booted from SSD with the SD card removed.

Refresh sudo (the reboot cleared the timer):

```bash
sudo -v
```

Open Codex and paste:

> I just migrated to NVMe SSD. Help me verify that Node.js v22, npm, and
> Codex are still working (`node --version`, `npm --version`, `codex --version`).
> If not, reinstall them. Then install the following additional packages:
> Docker (with docker compose plugin), Git, Python3 with pip and venv,
> build-essential, and set up UFW firewall with rules to allow SSH (port 22)
> and web (port 8085). Also add my user to the `docker` group so I can
> run Docker commands without sudo.

---

## Stage 7: Create ~/AGENTS.md

This file helps Codex (and any other AI tool) understand your machine AND
your personal setup. It's the "about me" for your AI tools.

We create it now — after the SSD migration and package installs — so it
captures the complete picture in one shot.

Paste this prompt into Codex:

> Explore this machine and write ~/AGENTS.md with two sections:
>
> **Section 1: Machine Profile**
> Discover and document everything you can:
> - Hardware specs (CPU model, core count, architecture, RAM, NPU/GPU)
> - All storage devices and their layout (partitions, mount points,
>   filesystem types, free space)
> - OS version, kernel version, architecture
> - Installed packages and versions (docker, docker compose, git, node,
>   npm, python3, pip, curl, build-essential)
> - Network configuration (interfaces, IP addresses, hostname, DNS)
> - Docker version and configuration
> - SSH configuration
> - UFW firewall rules — include this note at the top of the firewall
>   section:
>
>   IMPORTANT: This machine uses UFW (Uncomplicated Firewall).
>   If something network-related isn't working, it's probably because
>   UFW is blocking it. Check with: sudo ufw status
>   Add a rule with: sudo ufw allow <port>/tcp
>
> Include the raw output of key commands in a collapsible section:
> `lscpu`, `free -h`, `lsblk -f`, `df -h`, `cat /etc/os-release`,
> `uname -a`, `ip addr`, `docker --version`, `node --version`,
> `python3 --version`.
>
> **Section 2: Owner Profile (I'll fill this in)**
> Leave placeholders for me to fill in:
> - Name and age
> - School and grade
> - School district and Canvas URL
> - Sports: team, league, position
> - Minecraft: server names and IP of the machine running them
> - Hobbies and interests
> - AI assistant name (will be set in Stage 11)

---

## Stage 8: Set Up GitHub SSH Key

You need an SSH key to clone code from GitHub.

```bash
# Generate your SSH key (use your email address)
ssh-keygen -t ed25519 -C "your-email@example.com"

# Press Enter for default location
# Set a passphrase — this protects your key if someone copies the file

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

> **Security lesson — Why SSH keys instead of passwords?** A password can
> be guessed, phished, or leaked in a data breach. An SSH key is a pair of
> mathematically linked files: a **private key** (stays on your machine,
> never shared) and a **public key** (given to GitHub). It's like a lock
> that only YOUR specific key can open. Even if someone knows your GitHub
> username, they can't get in without the private key file sitting on your
> computer. That's why GitHub is moving away from password authentication
> entirely.

---

## Stage 9: Clone the Project

```bash
# Create your dev folder
mkdir -p ~/dev && cd ~/dev

# Clone the project
git clone git@github.com:patdeg/openclaw_kids.git
cd openclaw_kids
```

---

## Stage 10: How OpenClaw Works

You've cloned the project. Before we start customizing, let's understand
what you've just downloaded — and where the software behind it comes from.

### What is OpenClaw?

[OpenClaw](https://github.com/openclaw/openclaw) is a popular open-source
AI assistant framework — think of it as "Android for personal AI
assistants." It's a community-driven project with 247,000+ stars on GitHub
that lets you run your own AI assistant on your own hardware.

The official resources:
- **GitHub:** [github.com/openclaw/openclaw](https://github.com/openclaw/openclaw)
- **Docs:** [docs.openclaw.ai](https://docs.openclaw.ai/)
- **Website:** [openclaw.ai](https://openclaw.ai/)

There are several ways to install OpenClaw:

| Method | What it does | Best for |
|--------|-------------|----------|
| `npm install -g openclaw` | Installs directly on your system | Quick testing |
| [Docker image](https://github.com/openclaw/openclaw/pkgs/container/openclaw) (`ghcr.io/openclaw/openclaw`) | Pre-built container, supports ARM64 | Simple deployments |
| [MyClaw.ai](https://myclaw.ai) | Managed cloud hosting (paid) | People who don't want to manage hardware |
| **Custom Docker build** (what we use) | Our own Dockerfile that installs OpenClaw + extra tools | **This project** |

**We use a custom Docker build** because our skills need extra software
that the stock OpenClaw image doesn't include — Python for the skill
scripts, Chromium for browser automation, ffmpeg for media processing,
himalaya for email, and more.

Under the hood, our `Dockerfile.openclaw` does this:

```dockerfile
# Inside the Docker container:
npm install -g openclaw@2026.2.26    # pinned version for stability
```

We pin a specific version (`2026.2.26`) so your setup doesn't break when
OpenClaw publishes updates. When you're ready to upgrade later, change
the version in `Dockerfile.openclaw` and rebuild.

> **Why not just `npm install -g openclaw` directly on the Pi?** You
> could — and for a quick test, that works. But running inside Docker
> gives us **isolation** (the assistant can't accidentally mess up your
> system), **reproducibility** (the same setup works on any machine),
> and **easy updates** (rebuild the container instead of debugging
> dependency conflicts). These are the same reasons professional
> developers use containers.

The `bootstrap.sh` script (Stage 11) handles all of this automatically —
you don't need to run any of these install commands yourself. But now
you know what's happening behind the scenes.

> **Explore the source:** If you're curious, browse the OpenClaw repo
> on GitHub. Reading other people's open-source code is one of the best
> ways to learn engineering. You're already running it on your own
> hardware — understanding how it works is the next level.

---

Now let's understand the pieces of this project. But first — many config
files use **Markdown**, so here's a 2-minute crash course.

### Markdown Crash Course

Markdown (`.md` files) is a simple way to write formatted text using
plain characters. This README you're reading right now is Markdown.
Here's the syntax you'll see in the config files:

```markdown
# Heading 1 (biggest)
## Heading 2
### Heading 3 (smallest commonly used)

**bold text**           ← surround with double asterisks
*italic text*           ← surround with single asterisks

- bullet point          ← dash + space
- another bullet
  - indented bullet     ← two spaces + dash

1. numbered list
2. second item

> blockquote            ← greater-than sign + space
> (used for callouts and notes)

`inline code`           ← backticks around short code

```                     ← triple backticks for code blocks
code goes here
```                     ← close with triple backticks again

[link text](https://example.com)    ← text in brackets, URL in parens

<!-- this is a comment — invisible in rendered output -->
```

That's it. You now know enough Markdown to read and edit every `.md`
file in this project. If you want the full reference:
[markdownguide.org/cheat-sheet](https://www.markdownguide.org/cheat-sheet/)

---

OpenClaw is built around a set of core concepts — each one maps to a
section in the config file or a file on disk.

Take a look at the main config:

```bash
cat ~/dev/openclaw_kids/config/openclaw.kids.json
```

Here's what each piece does:

### IDENTITY — Who Your Assistant Is

```json
"identity": {
  "name": "ATHENA",
  "description": "Personal AI assistant for school, gaming, volleyball, and projects"
}
```

The name and one-line description that define your assistant's persona.
You'll change "ATHENA" to your own name in the next stage.

### SOUL — How Your Assistant Behaves

In OpenClaw, the **soul** is a Markdown file that gets injected into
every conversation as the system prompt. It defines the AI's personality,
communication style, values, and boundaries. Out of the box, OpenClaw
ships with a generic soul — polite, helpful, neutral.

This project replaces the generic soul with `config/FAMILY_COMPASS.md` —
a detailed parenting philosophy document written specifically for teenage
users. It tells the AI to be a **coach and mentor**: use Socratic
questioning, hold high standards, be warm but challenging, never provide
explicit content, escalate crisis situations to parents.

Read it — it's the most important file in this project:

```bash
cat ~/dev/openclaw_kids/config/FAMILY_COMPASS.md
```

The Family Compass covers:
- How the AI should communicate (direct, honest, uses humor)
- Psychological frameworks (growth mindset, Stoicism, grit)
- How to handle sensitive topics (mental health, peer pressure, substances)
- What the AI must NEVER do (explicit content, supplement advice, take
  sides in parental conflicts)
- Crisis protocols (self-harm, abuse, danger → escalate to parents)

If you want your assistant to behave differently — more humor, different
coaching approach, different study strategies — this is where you change
it. **But talk to your parents first.** The Family Compass includes
safety guardrails and crisis protocols that your parents chose for a
reason. Tweaking the personality is fine; removing safety boundaries is
not something you do on your own.

### SKILLS — What Your Assistant Can Do

```json
"skills": {
  "entries": {
    "school": { "enabled": true },
    "minecraft": { "enabled": true },
    "volleyball-intel": { "enabled": true },
    ...
  }
}
```

Each skill is a module in the `skills/` folder — typically a Python
script that gives the AI a specific ability: check your grades, manage
Minecraft servers, look up tournament brackets, generate practice tests.

Skills are like apps on a phone. The AI picks the right skill based on
what you ask it. You can enable or disable them in the config, and each
skill has its own configuration files in its folder.

Explore them:

```bash
ls skills/
```

### HEARTBEAT — The Wake-Up Loop

```json
"heartbeat": {
  "enabled": true,
  "interval": "1h",
  "activeHours": { "start": "07:00", "end": "22:00" }
}
```

Every hour (between 7 AM and 10 PM), OpenClaw wakes up and checks if
there's anything to do: new assignments posted in Canvas, upcoming
tournaments, overdue tasks. If something needs your attention, it sends
you a message on Discord or WhatsApp. Outside active hours, it sleeps —
nobody wants a 3 AM notification about homework.

### CHANNELS — How You Talk to It

```json
"channels": [
  { "type": "discord", "requireMention": true, ... },
  { "type": "whatsapp", ... }
]
```

Channels are the messaging interfaces — Discord, WhatsApp, and the
web UI (port 8085). Each channel has its own security policy (allowlist)
so only YOU can talk to your assistant. On Discord, it requires an
`@mention` to avoid reacting to every message in your server.

### MODEL — The AI Brain

```json
"model": {
  "primary": "openai-codex/gpt-5.4"
}
```

Which large language model powers the thinking. We use GPT-5.4 through
your family's ChatGPT Plus subscription. The model handles understanding
your questions, reasoning about them, and generating responses. The
skills give it specific tools to act on the world (check grades, start
a Minecraft server) — the model decides which tools to use and when.

### MEMORY — How It Remembers You

OpenClaw maintains conversation memory so your assistant remembers
context across messages and sessions. It knows your name, your
preferences, what you talked about last time, and what tasks you're
tracking. Memory is stored locally on your Orange Pi — it never leaves
your machine.

### USER — Who You Are

Your profile lives in two places:
- `~/AGENTS.md` (created in Stage 7) — your machine and personal details
- The `<!-- PERSONALIZE -->` section of `FAMILY_COMPASS.md` — your age,
  school, sports, hobbies

These tell the AI about YOU — not a generic teenager — so it can tailor
every response to your actual life.

### GATEWAY — The Server That Ties It Together

```json
"gateway": {
  "port": 18789,
  "bind": "127.0.0.1",
  "auth": "token"
}
```

The gateway is the central process that connects everything. It receives
messages from channels, routes them through the AI model, invokes skills
when needed, and sends responses back. It listens on port 18789 but only
on `127.0.0.1` (localhost) — meaning only your own machine can talk to
it, not anyone on the network. The web UI on port 8085 is the
public-facing interface.

> **Security lesson — Binding to localhost:** Notice `"bind": "127.0.0.1"`.
> This means the gateway ONLY accepts connections from the local machine.
> Even if someone on your network knows the port, they can't reach it.
> The web UI (port 8085) is the only thing exposed to the network, and
> it has its own authentication. This is **defense in depth** again —
> multiple layers of protection.

### How It All Fits Together

```
You (Discord / WhatsApp / Web UI)
  │
  ▼
CHANNELS receive your message
  │
  ▼
GATEWAY routes it to the MODEL
  │
  ▼
MODEL reads the SOUL + MEMORY + USER context
MODEL decides which SKILL(s) to call
  │
  ▼
SKILLS execute (check grades, query Minecraft, etc.)
  │
  ▼
MODEL composes a response using the results
  │
  ▼
CHANNELS send the response back to you

Meanwhile: HEARTBEAT wakes up every hour to check for proactive alerts
```

Now that you understand the architecture, let's make it yours.

---

## Stage 11: Name Your AI Assistant

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
> - web/static/tasks.html
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
Your user is a [age]-year-old [boy/girl] in [City, State]. [He/She]
plays [sport] for [Club Name], attends [School District], and [hobbies
— e.g., runs Minecraft servers with friends].
```

The more specific you are, the better the AI tailors its responses.

**2. Personalize the .env file**

When you fill in `.env` (Stage 12), you'll set your school's Canvas URL,
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

## Stage 12: Set Up Your Secrets (.env)

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
cp /home/$USER/dev/openclaw_kids/.env.example .env
chmod 600 .env
nano .env    # See Stage 4 if you forgot how nano works
```

> **Security lesson — File Permissions:** Remember `chmod 600` from
> Stage 4? Here it is in practice. `600` means only you (the file owner)
> can read and write the file — no other user on the machine can see it.
> Always set `600` on files containing secrets.

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

### Agent Email (Optional)
Your assistant can have its own email address for sending you notifications
and receiving task requests. Ask a parent to set up a Migadu mailbox, then:
- `AGENT_EMAIL` → your assistant's email address
- `MIGADU_AGENT_PASSWORD` → its password
- `FAMILY_EMAILS` → comma-separated list of family email addresses allowed
  to send to/from the agent (safety filter)
- Copy the himalaya config template:
  ```bash
  cp config/himalaya.config.toml.example himalaya/config.toml
  nano himalaya/config.toml  # Fill in your email addresses
  ```

### Other Keys
Ask a parent for help with: `MIGADU_PASSWORD`, `GOOGLE_CLIENT_ID`,
`GOOGLE_CLIENT_SECRET`, `SESSION_SECRET`, `DEMETERICS_API_KEY`, `GROQ_API_KEY`

---

## Stage 13: Launch and Verify

Refresh sudo (needed for Docker):

```bash
sudo -v
```

```bash
cd /opt/openclaw

# Build and start everything
docker compose up -d --build

# Check containers are running
docker ps

# View logs if something went wrong
docker compose logs -f
```

Find your Pi's IP if you forgot it (`hostname -I`), then open your
browser to `http://YOUR_PI_IP:8085` and log in.

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

## Stage 14: Security Lockdown

Everything is running. Now we lock it down. Your Orange Pi is a real
computer on your home network — treat it like one.

### Remove the Extended Sudo Timeout

In Stage 3, we extended the sudo timeout to 2 hours for setup. Setup is
done — time to tighten it back.

```bash
# Remove the setup-only sudo timeout extension
sudo rm /etc/sudoers.d/setup-timeout

# Verify sudo config is still valid
sudo visudo -c
# Should say: "/etc/sudoers: parsed OK"
```

Your sudo timeout is now back to the default 15 minutes. You'll need to
type your password more often — **that's a feature, not a bug.** Every time
you type your password, you're consciously deciding "yes, I want to run
this as root." That pause prevents mistakes.

### UFW Firewall (should already be set up from Stage 6)
```bash
sudo ufw status
# Should show: 22/tcp ALLOW, 8085/tcp ALLOW, default deny

# If not:
sudo ufw default deny incoming
sudo ufw allow ssh
sudo ufw allow 8085/tcp
sudo ufw enable
```

> **Security lesson — Defense in Depth:** A firewall blocks network
> traffic that shouldn't reach your machine. Even if a service has a bug,
> the firewall prevents the outside world from reaching it. This is called
> "defense in depth" — multiple layers of protection, so a single failure
> doesn't compromise everything.

### fail2ban (protects against SSH brute force)
```bash
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

fail2ban watches your login logs. If someone tries to guess your password
by attempting hundreds of logins, fail2ban automatically blocks their IP
address. It's like a bouncer that remembers troublemakers.

### Automatic Security Updates
```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

Software has bugs, and some bugs are security holes. Automatic updates
patch those holes without you having to remember. This is one of the
most important things you can enable on any server.

### SSH Key-Only Auth (disable passwords)

In Stage 8, you created an SSH key for GitHub. Now create one for
logging into your Orange Pi from your other computer. Run this **on
your main computer** (laptop/desktop), not on the Pi:

```bash
# On your MAIN COMPUTER — generate a key if you don't already have one
ssh-keygen -t ed25519 -C "your-email@example.com"

# Copy your public key to the Orange Pi (use YOUR username and IP)
ssh-copy-id yourname@192.168.1.42
```

Test it — you should be able to SSH in without typing a password:

```bash
ssh yourname@192.168.1.42
# Should log in immediately (or ask for your key passphrase, not the Pi password)
```

**Only after you've confirmed key login works**, disable password auth:

```bash
# On the Orange Pi:
sudo nano /etc/ssh/sshd_config

# Find and change these lines:
#   PasswordAuthentication no
#   ChallengeResponseAuthentication no

sudo systemctl restart sshd
```

> **Why disable password login over SSH?** Keys are stronger than any
> password. By disabling password authentication, you eliminate brute-force
> password guessing entirely. Anyone without your private key can't even
> attempt to log in. But do NOT disable passwords before confirming key
> login works — or you'll lock yourself out.

### Verify .env Permissions
```bash
ls -la /opt/openclaw/.env
# Should show: -rw------- (only you can read it)
```

### Security Checklist

Before you're done, verify everything:

- [ ] Default `orangepi` password changed (Stage 1)
- [ ] Personal user account created with own username (Stage 1)
- [ ] Sudo timeout reverted to 15 minutes (this stage)
- [ ] UFW firewall active with only ports 22, 8085, and 25565 open
- [ ] fail2ban running
- [ ] Automatic security updates enabled
- [ ] `.env` file permissions are `600`
- [ ] SSH key login tested from your main computer
- [ ] SSH password authentication disabled (only after key login works!)

---

## Stage 15: Meet Your Assistant

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

**Tasks:**
- "Add a task: finish science project by Friday"
- "What's on my to-do list?"
- "Mark the math homework as done"
- Open `/tasks` in the web UI to manage visually

**General:**
- "Help me with this math problem: 3x + 7 = 22"
- "What should I read next?"
- "I'm feeling stressed about school"

---

## Stage 16: Set Up a Minecraft Server

Now that your AI assistant is running, let's set up something fun — your
own Minecraft server, running locally on your Orange Pi. Your friends on
the same network (or via port forwarding) can join. And your AI assistant
can manage it from chat.

### Create a Minecraft Service Account

Minecraft servers should run under their own dedicated user — not your
personal account. This is a security best practice: if the server gets
compromised, the attacker only has access to the Minecraft files, not
your personal data.

```bash
# Create a system user for Minecraft (no login shell, no home directory clutter)
sudo adduser --system --home /opt/minecraft --group minecraft

# Give your user access to the minecraft group (so you can manage files)
sudo usermod -aG minecraft $USER
```

### Install Java

Minecraft servers need Java. Paper MC works best with Java 21:

```bash
sudo apt install -y openjdk-21-jre-headless
java -version    # Should show openjdk 21.x.x
```

### Install Paper MC

[Paper](https://papermc.io/) is the most popular Minecraft server — it's
a high-performance fork of the official server with plugin support and
better performance on ARM hardware like your Orange Pi.

Ask Codex to help with this part:

> Help me set up a Paper Minecraft server on this Orange Pi. Here's what
> I need:
>
> 1. Download the latest Paper MC 1.21.x jar to /opt/minecraft/
> 2. Accept the EULA (eula.txt → eula=true)
> 3. Configure server.properties with these settings:
>    - server-port=25565
>    - max-players=10
>    - difficulty=normal
>    - view-distance=10 (good for ARM CPUs)
>    - simulation-distance=8
>    - motd=A Minecraft Server (I'll customize this later)
>    - online-mode=true
>    - white-list=true (only invited players can join)
> 4. Create a start script at /opt/minecraft/start.sh that runs the
>    server with 4GB RAM (-Xmx4G -Xms2G) and Paper's recommended
>    JVM flags for ARM
> 5. Set file ownership to the minecraft user
> 6. Create a systemd service so the server starts on boot and can be
>    managed with systemctl
> 7. Open port 25565 in UFW

### Install Fun Plugins

Paper supports plugins — mods that add features to your server. Here are
two great starter plugins. Ask Codex:

> Install these Paper MC plugins on my Minecraft server at /opt/minecraft/:
>
> 1. **EssentialsX** — adds /home, /tpa (teleport to a friend), /sethome,
>    /warp, and dozens of useful commands. Download the latest jar from
>    the EssentialsX GitHub releases page and put it in /opt/minecraft/plugins/
>
> 2. **WorldEdit** — lets you build massive structures instantly. Select
>    a region and fill it, copy it, paste it, rotate it. Essential for
>    creative builders. Download from the dev.bukkit.org or EngineHub site.
>
> After adding the plugin jars, restart the server:
> sudo systemctl restart minecraft
>
> Then verify they loaded: check /opt/minecraft/logs/latest.log for
> "[EssentialsX]" and "[WorldEdit]" loading messages.

### Add Players to the Whitelist

Since we enabled `white-list=true`, only approved players can join.
Add yourself and your friends:

```bash
# Connect to the Minecraft server console
sudo -u minecraft screen -r minecraft
# (If using screen — or use the rcon method Codex set up)

# In the server console:
whitelist add YourMinecraftUsername
whitelist add FriendUsername
```

Or ask your AI assistant: *"Add PlayerName to the Minecraft whitelist"*

### Connect From Your Computer

**From any computer on the same WiFi/network:**

1. Open Minecraft Java Edition
2. Click **Multiplayer** → **Add Server**
3. Server Address: `YOUR_PI_IP:25565` (e.g., `192.168.1.42:25565`)
   - Find your Pi's IP: run `hostname -I` on the Pi
4. Click **Done** → select the server → **Join Server**

**From the Orange Pi itself** (if you have Minecraft installed):
- Use `localhost:25565` or `127.0.0.1:25565`

**For friends outside your network (optional, ask a parent):**
- This requires port forwarding on your router (forward port 25565 to
  your Pi's IP), or a tool like
  [playit.gg](https://playit.gg/) which creates a tunnel without
  touching the router. Ask Codex:

> Help me set up playit.gg so my friends outside my home network can
> join my Minecraft server without port forwarding.

### Update Your .env for AI Management

Now update your `.env` so the AI assistant can manage the server:

```bash
nano /opt/openclaw/.env
```

Set these values:

```
MINECRAFT_SSH_HOST=127.0.0.1
MINECRAFT_SSH_USER=minecraft
MINECRAFT_SERVER_DIR=/opt/minecraft
```

After saving, restart the stack: `docker compose restart`

Now try asking your assistant: *"Is the Minecraft server online?"* or
*"Start the Minecraft server"*

> **Security lesson — Service Accounts:** Notice we created a separate
> `minecraft` user that owns only the server files. This is the principle
> of **least privilege** again — the Minecraft server process can only
> touch its own files, not your personal data or the AI assistant's
> secrets. Professional servers ALWAYS run each service under its own
> account.

---

## Stage 17: Customize Your Desktop

Your Orange Pi is a full Linux desktop computer — not just a server.
Let's make it look and feel like a machine you actually want to use
every day.

### Which Desktop Do You Have?

Orange Pi Ubuntu images ship with different desktops depending on the
version. Find out which one you're running:

```bash
echo $XDG_CURRENT_DESKTOP
```

- **XFCE** — lightweight, already somewhat Windows-like (panel at top)
- **GNOME** — Ubuntu's default, more modern but heavier
- **Something else** — less common, but the app installs below still work

### Make It Look Like Windows

#### If You Have XFCE

XFCE is lightweight and perfect for the Orange Pi. Get a Windows layout:

1. **Move the panel to the bottom:**
   - Right-click the top panel → **Panel** → **Panel Preferences**
   - Uncheck "Lock panel"
   - Drag the panel to the **bottom** of the screen
   - Set size to 40-48 pixels (Windows taskbar height)

2. **Get a Windows-style app menu:**
   - In Panel Preferences → **Items** tab
   - Replace "Applications Menu" with "Whisker Menu" (install it first:
     `sudo apt install -y xfce4-whiskermenu-plugin`)
   - Whisker Menu looks and works like the Windows Start menu

3. **Pick a modern theme:**
   - **Settings → Appearance** → choose a theme (try **Greybird-dark**)
   - **Settings → Window Manager** → match the window decorations

#### If You Have GNOME

Ask Codex:

> Install GNOME extensions to make my desktop look like Windows 11:
> Dash to Panel (moves the dock to a bottom taskbar), ArcMenu (adds a
> Windows-style Start menu), and set a modern theme. My desktop is
> GNOME on Ubuntu ARM64.

Or do it manually:

```bash
# Install the tools
sudo apt install -y gnome-tweaks gnome-shell-extension-manager

# Then open Extension Manager from the app menu:
# - Search "Dash to Panel" → Install → Enable
# - Search "ArcMenu" → Install → Enable
```

After installing:
1. Open **Extensions** → enable **Dash to Panel** and **ArcMenu**
2. Dash to Panel settings: position = **bottom**, panel size = **48px**
3. ArcMenu settings: choose **"Windows"** layout
4. Open **GNOME Tweaks** → Appearance → pick a theme you like

### Install Apps for School and Life

These are the essentials. Copy-paste the whole block:

```bash
# Office suite — opens and saves .docx, .xlsx, .pptx (like Microsoft Office)
sudo apt install -y libreoffice

# Media player — plays any video or audio format
sudo apt install -y vlc

# Image editor — like a free Photoshop
sudo apt install -y gimp

# Audio editor — for podcasts, music projects, sound effects
sudo apt install -y audacity

# Screenshot tool — select a region, annotate, share
sudo apt install -y flameshot

# PDF viewer
sudo apt install -y evince

# Archive manager — zip, tar, 7z
sudo apt install -y file-roller p7zip-full

# Webcam/video recording (if you have a USB camera)
sudo apt install -y cheese
```

#### Visual Studio Code (Code Editor)

You've been using `nano` — it's time for an upgrade. VS Code is the most
popular code editor in the world, and it runs natively on ARM64:

```bash
# Download and install VS Code for ARM64
curl -L "https://code.visualstudio.com/sha/download?build=stable&os=linux-deb-arm64" \
  -o /tmp/vscode.deb
sudo apt install -y /tmp/vscode.deb
rm /tmp/vscode.deb
```

Or ask Codex:

> Install Visual Studio Code on this ARM64 Ubuntu machine.

VS Code has extensions for Python, Go, Markdown, and hundreds of other
languages. It also has a built-in terminal — so you can code and run
commands in the same window. Start here:
- Install the **Python** extension (for editing skills)
- Install the **Markdown Preview** extension (for reading .md files)

#### Firefox (if not pre-installed)

```bash
sudo apt install -y firefox
```

### Set a Wallpaper

Right-click the desktop → **Desktop Settings** (XFCE) or **Settings →
Background** (GNOME). Pick something that makes it feel yours.

### (Optional) Extra Apps

Depending on your interests, ask Codex to install any of these:

> Install [APP] on my ARM64 Ubuntu machine.

Some ideas:
- **Inkscape** — vector graphics (logos, illustrations)
- **Blender** — 3D modeling and animation (heavy, needs GPU)
- **OBS Studio** — screen recording and streaming
- **Kdenlive** — video editing
- **Telegram Desktop** — messaging
- **Thunderbird** — email client

> **Tip:** You've now set up a fully-functional Linux desktop from
> scratch — something most adults have never done. Every piece of
> software on this machine is there because YOU chose to install it.
> That's the difference between using a computer and understanding one.

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
You forgot to fill in your .env file. Go back to Stage 12.

### Can't SSH to GitHub
Make sure your SSH key is added: `ssh -T git@github.com`

### Minecraft commands are slow
SSH to the Minecraft server can take a moment. Be patient.

### Something network-related isn't working
**Check UFW first:** `sudo ufw status`. If the port isn't listed, add it:
`sudo ufw allow <PORT>/tcp`

### Codex says "permission denied" or hangs on a sudo command
Your sudo timer expired. Press Ctrl+C, run `sudo -v` in the terminal to
re-enter your password, then restart Codex with the remaining steps.

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
│   ├── tasks/                  ← Task management (to-dos, homework tracking)
│   └── ...
├── web/                        ← Go web server + frontend
├── docker-compose.yml
├── Dockerfile.openclaw
├── Dockerfile.web
├── bootstrap.sh                ← First-time setup
├── update.sh                   ← Incremental deploy (run after git pull)
├── .env.example                ← Template (safe to commit)
├── .env                        ← YOUR SECRETS (NEVER commit)
└── README.md                   ← This file
```

---

## Bill of Materials

Everything you need to buy before starting. **Pay special attention to the
power supply** — the Orange Pi 6 Plus draws significant power, especially
under load with an NVMe SSD attached. An underpowered supply causes random
freezes, filesystem corruption, and hours of frustrating debugging.

### Required

| Item | Why | Example |
|------|-----|---------|
| Orange Pi 6 Plus (16GB+ RAM) | Your computer — 12-core ARM, up to 64GB RAM | [Amazon](https://www.amazon.com/dp/B0G3P8VFHK) |
| NVMe M.2 SSD (256GB+) | Fast, reliable storage (replaces the slow SD card) | [Amazon (Samsung 9100 PRO 1TB)](https://www.amazon.com/dp/B0DX2G349M) |
| **100W USB-C PD power supply** | **CRITICAL — see warning below** | [Amazon (Orange Pi official)](https://www.amazon.com/dp/B0FX2SGPJL) |
| microSD card (16GB+) | Initial boot only (used once, then removed) | Any brand, Class 10 or better |
| HDMI cable + display | To see what you're doing during first boot | Any TV or monitor with HDMI |
| USB keyboard + mouse | To type commands | Any USB keyboard and mouse |

> **About the power supply:** The Orange Pi 6 Plus requires **20V via
> USB-C Power Delivery** — this is NOT optional. A phone charger (5V/2A)
> or even a basic USB-C cable won't work because the board needs PD
> negotiation to reach 20V. A laptop charger at 65W+ that supports 20V
> output will likely work, but the official 100W adapter gives headroom
> for the NVMe SSD and USB peripherals. Symptoms of insufficient power:
> random reboots mid-setup, SD card or SSD filesystem corruption, USB
> devices disconnecting, or the board refusing to turn on.

### Recommended

| Item | Why | Example |
|------|-----|---------|
| Metal case with heatsink | Keeps the 12-core CPU cool under load | [Amazon (Orange Pi official)](https://www.amazon.com/dp/B0FX2Q14Y9) |
| Ethernet cable | More reliable than WiFi, no module needed | Any Cat5e or Cat6 cable |
| WiFi module (M.2 E-key) | Wireless networking if ethernet isn't practical | [Amazon (Orange Pi R6)](https://www.amazon.com/dp/B0CFY7SJRN) — see note below |

> **WiFi vs Ethernet:** If your Orange Pi is within cable-reach of your
> router, **use ethernet**. It's faster, more reliable, and needs zero
> setup. The Orange Pi 6 Plus has dual 5 Gbps ethernet ports — just plug
> in and go. WiFi is only needed if running a cable isn't practical.
>
> **WiFi module compatibility:** The Orange Pi R6 module (RTL8852BE,
> WiFi 6 + Bluetooth 5.2, M.2 E-key) is physically compatible with the
> Orange Pi 6 Plus, but it was originally designed and tested for the
> Orange Pi 5 Plus. **Driver support on the 6 Plus (CIX P1 SoC) may
> vary depending on the OS image.** Check the
> [Orange Pi forums](http://www.orangepi.org/orangepibbsen/) for the
> latest compatibility reports before buying. If you need guaranteed
> WiFi, start with ethernet and add WiFi later once it's confirmed
> working with your OS version.

### You Probably Already Have

- A computer with an SD card reader (to flash Ubuntu in Stage 0)
- A WiFi router (for internet access)

---

## For Parents

To update after changes are pushed to GitHub:
```bash
cd ~/dev/openclaw_kids && ./update.sh
```

This pulls the latest code, copies files to `/opt/openclaw/`, fixes ownership,
rebuilds Docker only if needed, and restarts services. Safe to run repeatedly.

**First-time setup** uses `bootstrap.sh` instead (Stage 11).

Each kid should have their own hardware with a separate deployment.
Email accounts are optional but recommended — set up via Migadu or any
IMAP provider and configure in the `.env` file.
