# OpenClaw Kids

> **Experimental** — This project is a work in progress. I'm currently building it out with my kids and iterating as we go.

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
- All running on YOUR hardware, with your data staying on your machine
  (the AI brain itself runs via your family's ChatGPT Plus subscription)

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
2. Go to **Region & Language**
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

> **Security principles you'll learn in this guide:**
>
> Throughout this setup, you'll encounter real security concepts that
> professional engineers use every day. Here's a preview — each one will
> be taught in context when you need it:
>
> 1. **Strong passwords** — default credentials are the #1 way systems get hacked (Stage 1)
> 2. **Accountability** — every person gets their own account so actions are traceable (Stage 1)
> 3. **Principle of Least Privilege** — grant only the access needed, revoke when done (Stage 3)
> 4. **File permissions** — control who can read, write, or execute each file (Stage 4)
> 5. **SSH keys over passwords** — cryptographic keys are stronger than any password (Stage 8)
> 6. **Secrets management** — API keys and passwords never leave the machine, never get committed (Stage 12)
> 7. **Defense in depth** — multiple layers of protection so one failure doesn't compromise everything (Stage 14)
> 8. **Firewall rules** — block all network traffic except what you explicitly allow (Stage 14)
> 9. **Brute-force protection** — automatically ban IPs that try to guess passwords (Stage 14)
> 10. **Automatic updates** — patch security holes before attackers find them (Stage 14)
> 11. **Service accounts** — each service runs under its own user with minimal permissions (Stage 16)
> 12. **Localhost binding** — internal services only accept local connections (Stage 10)
> 13. **Container isolation** — Docker sandboxes processes so they can't affect your system (Stage 10)

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

First, decide your username and save it in a variable. **Type your actual
name here** — not the word "yourname":

```bash
# ┌─────────────────────────────────────────────────────────────┐
# │  STOP — replace lucas with YOUR name before pressing Enter  │
# └─────────────────────────────────────────────────────────────┘
MY_USER=lucas
```

Now use that variable for every command — this way you can't mistype it:

```bash
# Create your account
sudo adduser $MY_USER
```

It asks for a password (use a strong one!) and some optional info (full
name is useful; skip the rest with Enter).

Now give your account the permissions it needs:

```bash
# Add yourself to the necessary groups
sudo usermod -aG sudo,video,audio,render,plugdev $MY_USER

# Verify it worked — you should see your groups listed
groups $MY_USER
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
# ┌──────────────────────────────────────────────────────────────┐
# │  STOP — replace my-pi-name with YOUR choice before Enter     │
# └──────────────────────────────────────────────────────────────┘
sudo hostnamectl set-hostname my-pi-name
```

Pick something memorable — your name, your AI assistant's name, or
anything fun (`lucas-pi`, `atlas`, `phoenix`).

#### Switch to Your New Account

Log out and log back in as **your** user:

- **At the screen:** Click the top-right user menu → Log Out → log in
  with your new username
- **Over SSH:** `exit`, then reconnect using your new username:
  ```bash
  ssh lucas@192.168.1.42    # YOUR username and YOUR Pi's IP
  ```

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

### Codex Execution Modes

By default, Codex asks **"Do you accept?"** before every single command.
That's safe but slow — an SSD migration can trigger dozens of prompts.
Codex has four approval modes:

| Flag | What it does | Use when... |
|------|-------------|-------------|
| *(default)* | Asks before every non-trivial command | You want to approve each step manually |
| `--full-auto` | Runs automatically inside a sandbox (can only write to the current folder) | Editing files, exploring, coding |
| `-a on-failure` | Runs everything automatically, only asks if a command fails | **System setup** — installing packages, partitioning disks, configuring firewalls |
| `--dangerously-bypass-approvals-and-sandbox` | Never asks, no sandbox at all | You absolutely know what you're doing |

For the setup stages in this guide (SSD migration, package installs,
firewall rules), Codex needs to write to system directories like `/etc`
and `/dev` — outside the sandbox that `--full-auto` uses. That's why
we'll use **`-a on-failure`** for system setup stages.

Example — instead of just `codex`, run:

```bash
codex -a on-failure "Help me migrate my Orange Pi from SD card to SSD"
```

Codex will execute each command automatically. If something fails, it
stops and asks what to do instead of blindly retrying.

> **Security lesson — Trust but verify:** Using `-a on-failure` means
> you're trusting Codex to run commands without asking. That's why we
> combine it with `setup-codex-sudo.sh` (Stage 3) — you consciously
> enable elevated access before the session and revoke it after. This
> mirrors how professionals work: grant temporary access, do the job,
> revoke access. The flag saves you from clicking "accept" 50 times,
> but the sudo scripts keep the security boundary clear.

---

## Stage 3: Prepare Sudo for Codex

Codex needs to run commands as root (`sudo`) — to install packages,
partition disks, and configure the firewall. But Codex runs commands in a
**sandbox** that can't access your sudo credential cache. That means
`sudo -v` (which caches your password for 15 minutes) is useless —
Codex never sees the cached credentials.

The fix: **temporarily enable passwordless sudo** for your user before a
Codex session, then **remove it when you're done**. We do this with two
small scripts and a sudoers drop-in file — the proper way to customize
sudo without ever editing `/etc/sudoers` directly.

### Install the Helper Scripts

Copy-paste this entire block into your terminal. It creates two scripts
in `~/bin` and adds that folder to your PATH:

```bash
mkdir -p ~/bin

cat > ~/bin/setup-codex-sudo.sh << 'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail
USER_NAME="$(logname 2>/dev/null || echo "$USER")"
DROP_IN="/etc/sudoers.d/codex-nopasswd"
if [ -f "$DROP_IN" ]; then
    echo "Passwordless sudo is already enabled for $USER_NAME."
    echo "Run remove-codex-sudo.sh when you're done with Codex."
    exit 0
fi
echo "$USER_NAME ALL=(ALL) NOPASSWD: ALL" | sudo tee "$DROP_IN" > /dev/null
sudo chmod 440 "$DROP_IN"
if sudo visudo -c > /dev/null 2>&1; then
    echo "Passwordless sudo enabled for $USER_NAME."
    echo "Run remove-codex-sudo.sh when you're done with Codex."
else
    echo "ERROR: sudoers validation failed — rolling back!"
    sudo rm -f "$DROP_IN"
    exit 1
fi
SCRIPT

cat > ~/bin/remove-codex-sudo.sh << 'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail
DROP_IN="/etc/sudoers.d/codex-nopasswd"
if [ ! -f "$DROP_IN" ]; then
    echo "Passwordless sudo is not enabled — nothing to remove."
    exit 0
fi
sudo rm -f "$DROP_IN"
if sudo visudo -c > /dev/null 2>&1; then
    echo "Passwordless sudo removed. Sudo now requires your password again."
else
    echo "WARNING: sudoers validation returned an error. Run: sudo visudo -c"
fi
SCRIPT

chmod +x ~/bin/setup-codex-sudo.sh ~/bin/remove-codex-sudo.sh
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

> **Later, after you clone the repo (Stage 9),** you'll find these same
> scripts in `scripts/setup-codex-sudo.sh` and
> `scripts/remove-codex-sudo.sh`.

### How to Use Them

Before any Codex session that needs sudo:

```bash
setup-codex-sudo.sh
```

It will ask for your password once (the real `sudo` prompt), then Codex
can run `sudo` commands freely inside its sandbox.

When you're done with that Codex session:

```bash
remove-codex-sudo.sh
```

That's it. You'll see `setup-codex-sudo.sh` at the start of Stages 5,
6, and 13 — and `remove-codex-sudo.sh` in Stage 14 (Security Lockdown).

> **Security lesson — Principle of Least Privilege:** We're temporarily
> widening access because we need it for setup. In Stage 14 (Security
> Lockdown), we'll remove it for good. This is a core security principle:
> **grant the minimum access needed, then revoke it when done.** You
> never leave a door open longer than necessary.

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

> ### Why this matters
>
> Your SD card has **one** job after this stage: gathering dust in a
> drawer as a backup. The NVMe SSD is 20× faster and far more reliable
> for daily use. But the migration must copy **everything** the machine
> needs to boot on its own — not just your files, but the bootloader,
> kernel, and device-tree blobs too. Skip any of those and you get an
> expensive paperweight.

Enable passwordless sudo for this Codex session:

```bash
setup-codex-sudo.sh
```

Open Codex in auto mode (see Stage 2 — Codex Execution Modes) and
paste this prompt. It's long on purpose — every line prevents a
different way the migration can fail:

```bash
codex -a on-failure "Help me perform a fully bootable Orange Pi 6 Plus migration from the microSD card to the NVMe SSD. The NVMe MUST become self-bootable with the microSD removed. Do NOT stop after copying only the root filesystem.

Step 1 — Inspect the boot chain: Run lsblk, blkid, and ls /boot and ls /boot/efi (or wherever EFI files live). Identify which partition currently holds the EFI/bootloader files (FAT32/vfat) and which holds the root filesystem. Print a clear summary of what you found before proceeding.

Step 2 — Partition the NVMe: Use fdisk or parted to create a GPT partition table on the NVMe with exactly TWO partitions: (a) a small (~512 MB) FAT32 EFI System Partition (type EFI System), and (b) an ext4 partition using the remaining space for the root filesystem. Format them: mkfs.vfat -F 32 for the EFI partition, mkfs.ext4 for root.

Step 3 — Copy the EFI/boot partition: Mount both the source EFI partition (from the SD card) and the new NVMe EFI partition. Use rsync -aHAXx to copy ALL boot files: BOOTAA64.EFI, grub.cfg (or extlinux.conf or boot.scr — whatever this board uses), the kernel image (vmlinuz/Image), initramfs/initrd, device-tree blobs (.dtb files), and any board-specific boot assets. Verify the copy is complete by comparing file counts and sizes.

Step 4 — Copy the root filesystem: Mount the NVMe ext4 partition. Use rsync -aHAXx --exclude=/dev --exclude=/proc --exclude=/sys --exclude=/tmp --exclude=/run --exclude=/mnt --exclude=/media --exclude=/lost+found to copy the full root filesystem from the running SD card to the NVMe root partition. Create empty mountpoints for the excluded virtual filesystems (dev, proc, sys, tmp, run, mnt, media).

Step 5 — Update boot config: (a) Edit the bootloader config ON THE NVMe EFI partition (grub.cfg, extlinux.conf, or boot.scr — whichever exists) to set root= to the PARTUUID or UUID of the NVMe root partition. (b) Edit /etc/fstab ON THE NVMe root partition to mount the NVMe root partition as / and the NVMe EFI partition as /boot/efi (or /boot). Remove or comment out any lines referencing the old SD card partitions.

Step 6 — Verify before reboot: Print the updated fstab and bootloader config. Run blkid to show NVMe UUIDs. Confirm that: the NVMe EFI partition contains a valid bootloader, the NVMe root partition contains /etc /usr /bin /sbin /lib, and the UUIDs in the boot config and fstab match the actual NVMe partitions. Only proceed to reboot if ALL checks pass.

Step 7 — IMPORTANT: Before rebooting, print a big visible warning telling me to REMOVE THE SD CARD as soon as the screen goes black during reboot. Then reboot."
```

Codex will run each step automatically. If something fails, it stops
and asks you what to do. **Read its output** — it will print a summary
of the boot chain it found and what it's doing at each step.

At the end, Codex will reboot the system. **Watch the screen carefully.**

> ### ⛔ STOP — REMOVE THE SD CARD NOW ⛔
>
> **As soon as the screen goes black during reboot, IMMEDIATELY pull out
> the microSD card.** Do not wait for the system to come back up.
>
> If you leave the SD card in, the Orange Pi will boot from the SD card
> again instead of the SSD — undoing the whole migration.
>
> **If you see a BIOS/UEFI settings screen** instead of Ubuntu starting
> up, that means the boot configuration on the SD card was incorrect.
> Don't panic — just power off (unplug USB-C), remove the SD card,
> and power back on. The SSD should boot normally.

Once the system restarts (without the SD card), log back in and run
`lsblk` to confirm the migration worked:

```bash
lsblk
```

You should see the root filesystem (`/`) is now on `nvme` instead of
`mmcblk`. That's the migration at work — you're running from the fast
SSD now.

---

## Stage 6: Install Development Tools

You should now be booted from SSD with the SD card removed. (If you
skipped the warning above and left the SD card in — power off, remove
it, and power back on.)

Enable passwordless sudo for this Codex session (the reboot cleared
any previous state):

```bash
setup-codex-sudo.sh
```

Open Codex in auto mode:

```bash
codex -a on-failure "I just migrated to NVMe SSD. Help me verify that Node.js v22, npm, and Codex are still working (node --version, npm --version, codex --version). If not, reinstall them. Then install the following additional packages: Docker (with docker compose plugin), Git, Python3 with pip and venv, build-essential, and set up UFW firewall with rules to allow SSH (port 22) and web (port 8085). Also add my user to the docker group so I can run Docker commands without sudo."
```

---

## Stage 7: Create ~/AGENTS.md

This file helps Codex (and any other AI tool) understand your machine AND
your personal setup. It's the "about me" for your AI tools.

We create it now — after the SSD migration and package installs — so it
captures the complete picture in one shot.

Paste this prompt into Codex:

````text
Explore this machine and write ~/AGENTS.md with two sections:

Section 1: Machine Profile
Discover and document everything you can:
- Hardware specs (CPU model, core count, architecture, RAM, NPU/GPU)
- All storage devices and their layout (partitions, mount points,
  filesystem types, free space)
- OS version, kernel version, architecture
- Installed packages and versions (docker, docker compose, git, node,
  npm, python3, pip, curl, build-essential)
- Network configuration (interfaces, IP addresses, hostname, DNS)
- Docker version and configuration
- SSH configuration
- UFW firewall rules — include this note at the top of the firewall
  section:

  IMPORTANT: This machine uses UFW (Uncomplicated Firewall).
  If something network-related isn't working, it's probably because
  UFW is blocking it. Check with: sudo ufw status
  Add a rule with: sudo ufw allow <port>/tcp

Include the raw output of key commands in a collapsible section:
lscpu, free -h, lsblk -f, df -h, cat /etc/os-release,
uname -a, ip addr, docker --version, node --version,
python3 --version.

Section 2: Owner Profile (I'll fill this in)
Leave placeholders for me to fill in:
- Name and age
- School and grade
- School district and Canvas URL
- Sports: team, league, position
- Minecraft: server names and IP of the machine running them
- Hobbies and interests
- AI assistant name (will be set in Stage 11)
````

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

We use HTTPS to clone — no SSH key needed for a public repo:

```bash
# Create your dev folder
mkdir -p ~/dev && cd ~/dev

# Clone the project (HTTPS — works before SSH keys are set up)
git clone https://github.com/patdeg/openclaw_kids.git
cd openclaw_kids
```

> **After Stage 8** (SSH keys), you can switch to SSH for push access:
> ```bash
> cd ~/dev/openclaw_kids
> git remote set-url origin git@github.com:patdeg/openclaw_kids.git
> ```

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
npm install -g openclaw@latest    # always gets the newest version
```

We use `@latest` so you always get the newest OpenClaw version when you
rebuild your containers. If something stops working after a rebuild,
**open an issue** at
[github.com/patdeg/openclaw_kids/issues](https://github.com/patdeg/openclaw_kids/issues)
describing what broke — this helps us track compatibility. If you need
to pin a specific version temporarily, you can override it:

```bash
# Rebuild with a specific version if latest breaks something
docker compose build --build-arg OPENCLAW_VERSION=2026.2.26
```

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

Take a look at the main config template:

```bash
# This is the TEMPLATE — your personal copy is generated by configure.sh
cat ~/dev/openclaw_kids/config/openclaw.kids.json.example
```

Here's what each piece does:

### IDENTITY — Who Your Assistant Is

```json
"identity": {
  "name": "__ASSISTANT_NAME__",
  "description": "__ASSISTANT_DESCRIPTION__"
}
```

The name and one-line description that define your assistant's persona.
You'll choose your own name when you run `configure.sh` in Stage 11.

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

Read the template — it's the most important file in this project:

```bash
# This is the TEMPLATE — your personal copy is generated by configure.sh
cat ~/dev/openclaw_kids/config/FAMILY_COMPASS.md.example
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
- `config/FAMILY_COMPASS.md` — your age, school, sports, hobbies
  (generated by `configure.sh` from the template)

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

## Stage 11: Configure and Deploy Your AI Assistant

This is where you make it yours. The `configure.sh` script asks you a
few questions and generates your personal config files. Then `bootstrap.sh`
builds and deploys everything.

### Step 1: Run the Configuration Wizard

```bash
cd ~/dev/openclaw_kids
./configure.sh
```

It will ask you:
- **Your assistant's name** — JARVIS, FRIDAY, ORACLE, ECHO, NOVA,
  CORTANA, SAGE, ATLAS, PHOENIX, TITAN... or something completely
  original. It's your assistant, make it yours.
- **A short description** — what does it do?
- **Your timezone** and **active hours** — when should it be awake?
- **About you** — your age, location, sports, hobbies (so the AI can
  tailor its responses to your actual life)

This generates two files that are **yours** — git will never touch them:
- `config/openclaw.kids.json` — your assistant's identity and settings
- `config/FAMILY_COMPASS.md` — how the AI talks to you (personality,
  values, safety rules)

You can re-run `./configure.sh` anytime to change your settings.

> **Why does this matter?** These files live in git's ignore list (like
> `.env`). That means when you run `git pull` to get updates, your
> personal settings are safe — no merge conflicts, no overwritten config.
> The templates (`.example` files) update from GitHub; your local copies
> stay untouched.

### Step 2: Create Your AI's Avatar

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

````text
I have a new avatar at web/static/img/avatar.png. Generate resized
versions for the PWA icons at web/static/img/icons/ in sizes: 48x48,
72x72, 96x96, 144x144, 192x192, 384x384, 512x512. Use ImageMagick.
````

### Step 3: Rename the Assistant in the Web UI

The web UI HTML files still say "ATHENA". Ask Codex to rename them:

````text
I just configured my AI assistant in ~/dev/openclaw_kids. Its name is
"[YOUR_NAME]" (check config/openclaw.kids.json for the exact name).
Find every occurrence of "ATHENA" in these files and replace them all:
- web/static/index.html
- web/static/login.html
- web/static/school.html
- web/static/files.html
- web/static/tasks.html
- web/static/unauthorized.html
- web/static/manifest.json
- web/static/js/app.js
- web/static/js/files.js

Replace "ATHENA" with my assistant's name everywhere. Then show me
what changed.
````

### Step 4: Personalize (Optional)

**Minecraft servers** — If you run Minecraft servers, update
`skills/minecraft/servers.yaml` with your actual server names and paths.

**Sports skills** — If you play a different sport or are in a different
region, ask Codex:

````text
I play [your sport] for [your team] in [your league/region]. Help me
update the sports skills in this project to track my season.
````

### Step 5: Deploy

Now run the bootstrap — this is the ONE command that builds and starts
everything:

```bash
./bootstrap.sh
```

The bootstrap script will:
- Run `configure.sh` if you haven't already (or ask if you want to reconfigure)
- Create the `/opt/openclaw/` directory structure
- Build the Docker containers
- Deploy your config, skills, and web UI
- Set up systemd services so it starts on boot

At the end, it prints a summary of your config files and what to do next.

> **What `bootstrap.sh` does behind the scenes** (you don't need to run
> these — they're shown so you understand what happened):
> ```bash
> # DO NOT RUN — bootstrap.sh does all of this for you automatically:
> sudo mkdir -p /opt/openclaw/{workspace,vault,credentials,himalaya}
> cp config/openclaw.kids.json /opt/openclaw/openclaw.json
> cp config/FAMILY_COMPASS.md /opt/openclaw/workspace/FAMILY_COMPASS.md
> docker compose build
> docker compose up -d
> ```

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

Create your .env file (bootstrap.sh already told you this — here's a
reminder):

```bash
cd /opt/openclaw
cp /home/$USER/dev/openclaw_kids/.env.example .env
chmod 600 .env
nano .env    # See Stage 4 if you forgot how nano works
```

After editing, deploy your changes:

```bash
cd ~/dev/openclaw_kids && ./update.sh
```

> **Security lesson — File Permissions:** Remember `chmod 600` from
> Stage 4? Here it is in practice. `600` means only you (the file owner)
> can read and write the file — no other user on the machine can see it.
> Always set `600` on files containing secrets.

Fill in each value. Here's a guide organized by feature — **start with
the required keys**, then add optional ones as you need them.

### Which Keys Do You Actually Need?

| Key | Required? | Adult help? | What it powers |
|-----|-----------|-------------|----------------|
| `WEB_PASSWORD` | **Yes** | No | Password to access the web UI |
| `SESSION_SECRET` | **Yes** | No | Encrypts your login session |
| `CANVAS_API_KEY` + Base URL | **Yes** (for School) | No | Grade checking, assignment tracking |
| `DISCORD_BOT_TOKEN` + Guild/User ID | Optional | Yes | Chat via Discord |
| `WHATSAPP_ALLOWED_NUMBER` | Optional | Yes | Chat via WhatsApp |
| `MINECRAFT_SSH_*` | Optional | No | Minecraft server management (Stage 16) |
| `PRINTER_IP` | Optional | No | Network printing (Stage 17) |
| Email keys (`MIGADU_*`) | Optional | **Yes** | Email sending/receiving |

Everything else in `.env.example` is optional. Start with the required
keys and add more as you explore features.

---

### Web UI Password (you can do this yourself)

The web UI is protected by a password. The server **refuses to start**
if the password is too weak. Requirements:
- At least **16 characters**
- At least one uppercase letter, one lowercase letter, one digit, and
  one special character

Generate a strong password:

```bash
openssl rand -base64 24
```

Copy the output → `WEB_PASSWORD` in `alfred-web.env`.

Optionally set `WEB_USERNAME` to your name (defaults to "Player").

Also generate a session secret (this encrypts your login cookie):

```bash
openssl rand -hex 32
```

Copy the output → `SESSION_SECRET` in `alfred-web.env`.

### Chat via Discord (ask a parent)

Discord requires users to be **13 or older** to create an account. A
parent should help set up the bot and approve the Discord server.

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. Click "New Application" — name it (e.g., "MyAssistant")
3. Go to **Bot** in the sidebar
4. Click "Reset Token" — copy it → `DISCORD_BOT_TOKEN`
5. Under **Privileged Gateway Intents**, enable **Message Content Intent**
6. Go to **OAuth2** > **URL Generator**
7. Check "bot" scope, then "Send Messages" + "Read Message History"
8. Copy the URL and open it to invite the bot to your server
9. Your server ID → `DISCORD_GUILD_ID` (right-click server name > Copy ID — you need Developer Mode enabled in Discord settings)
10. Your user ID → `DISCORD_USER_ID` (right-click your name > Copy ID)

### School Dashboard (Canvas LMS)

Connects to your school's learning management system:

1. Go to your school's Canvas URL (e.g., `https://yourschool.instructure.com`)
2. Log in with your school account
3. Click your profile picture (top-left) → **Settings**
4. Scroll down to "Approved Integrations"
5. Click "+ New Access Token"
6. Purpose: "OpenClaw" — click "Generate Token"
7. **Copy the token immediately** (you can't see it again)
8. Paste it as `CANVAS_API_KEY` in your `.env`
9. Set `CANVAS_BASE_URL` to your school's Canvas URL + `/api/v1`
   (e.g., `https://yourschool.instructure.com/api/v1`)

### Agent Email (Optional)

Your assistant can have its own email address for notifications and
task creation. Ask a parent to set up a Migadu mailbox (or any IMAP
provider), then:
- `AGENT_EMAIL` → your assistant's email address
- `MIGADU_AGENT_PASSWORD` → its password
- `FAMILY_EMAILS` → comma-separated list of family email addresses
  allowed to send to/from the agent (safety filter)
- Copy the himalaya config template:
  ```bash
  cp config/himalaya.config.toml.example himalaya/config.toml
  nano himalaya/config.toml  # Fill in your email addresses
  ```

---

## Stage 13: Launch and Verify

If you just ran `bootstrap.sh`, your containers are already running.
Verify with:

```bash
docker ps
```

You should see two containers: `openclaw-gateway` and `openclaw-web`.

If they're not running, or if you changed `.env` or config files:

```bash
cd ~/dev/openclaw_kids && ./update.sh
```

> **Troubleshooting** — if you need to see what's happening inside the
> containers:
> ```bash
> # DO NOT RUN unless something is wrong — these are diagnostic commands:
> cd /opt/openclaw
> docker compose logs -f           # Watch live logs (Ctrl+C to stop)
> docker compose down && docker compose up -d --build   # Full rebuild
> ```

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

### Remove Passwordless Sudo

**Run this NOW — before doing anything else in this stage:**

```bash
remove-codex-sudo.sh
```

In Stage 3, we enabled passwordless sudo so Codex could run `sudo`
commands inside its sandbox. Setup is done — **remove it permanently.**

If you ever need passwordless sudo again for a future Codex session,
run `setup-codex-sudo.sh` before and `remove-codex-sudo.sh` after.
Never leave it enabled when you're not actively using Codex.

Verify it's gone:

```bash
# This should ask for your password (that means it's working correctly)
sudo echo "Sudo requires a password again — good."
```

**Every time you type your password for sudo, you're consciously
deciding "yes, I want to run this as root." That pause prevents
mistakes.**

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

# Copy your public key to the Orange Pi (YOUR username and YOUR Pi's IP)
ssh-copy-id lucas@192.168.1.42
```

Test it — you should be able to SSH in without typing a password:

```bash
ssh lucas@192.168.1.42
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
- [ ] Passwordless sudo removed with `remove-codex-sudo.sh` (this stage)
- [ ] UFW firewall active with only ports 22, 8085, and 25565 open
- [ ] fail2ban running
- [ ] Automatic security updates enabled
- [ ] `.env` file permissions are `600`
- [ ] SSH key login tested from your main computer
- [ ] SSH password authentication disabled (only after key login works!)

---

## Stage 15: Meet Your Assistant and Explore the Web UI

### How to Access the Web UI

Open a browser on **any device on your home network** (your phone,
laptop, or the Orange Pi itself) and go to:

```
http://YOUR_PI_IP:8085
```

Replace `YOUR_PI_IP` with your Orange Pi's IP address (run `hostname -I`
on the Pi to find it). For example: `http://192.168.1.42:8085`

You'll see a login page. Enter the password you set in `WEB_PASSWORD`
in your `alfred-web.env` file. Once logged in, you stay logged in for
90 days.

> **Tip:** Bookmark this URL on your phone and add it to your home
> screen. On the Pi itself, you can use `http://localhost:8085`.

### Personalizing the Web UI with Codex

Before diving into the features, use Codex to make the UI yours. In
Stage 11 you already renamed the assistant — now customize the look:

````text
I want to personalize my OpenClaw web UI in ~/dev/openclaw_kids/web/.
Please help me:
1. Update the color scheme in web/static/css/ to use my favorite colors
2. Update the page titles and descriptions in the HTML files
3. Make sure my assistant name appears correctly everywhere
Show me what files to edit and what to change.
````

After making changes, redeploy with `./update.sh` to see them live.

The key files for personalization:
- `web/static/css/` — colors, fonts, layout
- `web/static/img/avatar.png` — your assistant's avatar
- `web/static/index.html` — chat page layout
- `web/static/manifest.json` — PWA name and icons (for home screen)

### The Chat Page (`/`)

This is the main interface — a full-featured AI chat. When you first
open it, your assistant will run the **onboarding** questionnaire to
learn about you (favorite subjects, games, sports, study preferences).
Answer honestly — this personalizes everything.

**What you can do here:**
- Type messages to your assistant in the text box at the bottom
- Your assistant remembers conversation history across sessions
- It can call any of its 17+ skills based on what you ask
- Links, code blocks, and Markdown are rendered in responses
- Each conversation is a "thread" — you can start new ones or revisit
  old ones

**Try these prompts:**

| Category | Try saying... |
|----------|---------------|
| **School** | "What are my grades?" / "What assignments am I missing?" |
| **Study** | "Give me 10 practice problems for 8th grade math" / "Help me outline an essay about the Civil War" / "Start a pomodoro study session" |
| **Minecraft** | "Is the Minecraft server online?" / "Who's playing right now?" / "Start pokemonserver" |
| **Sports** | "When is my next tournament?" / "Give me a lower body workout" / "What should I eat on game day?" |
| **Tasks** | "Add a task: finish science project by Friday" / "What's on my to-do list?" |
| **General** | "Help me with this math problem: 3x + 7 = 22" / "I'm feeling stressed about school" |

### The School Dashboard (`/school`)

Click **School** in the navigation or go to `/school` directly.

This page connects to your school's **Canvas LMS** and shows:
- **Current grades** for each class (letter grade + percentage)
- **Missing assignments** — things you haven't turned in yet
- **Upcoming assignments** — what's due soon, sorted by date

The data comes from the Canvas API key you set up in Stage 12. If grades
aren't showing, double-check your `CANVAS_API_KEY` and `CANVAS_BASE_URL`
in the `.env` file.

### The Task Manager (`/tasks`)

Click **Tasks** in the navigation or go to `/tasks` directly.

A full task management system:
- **Create tasks** with a title, description, priority (low/medium/high),
  and due date
- **AI chat per task** — click on any task and chat with your assistant
  specifically about that task. Ask for help, brainstorm, or get
  unstuck
- **Link files** — attach vault files to tasks (e.g., attach your essay
  draft to your "Write English essay" task)
- **Track progress** — mark tasks as done, filter by status or priority
- **Sort and search** — find tasks quickly as your list grows

You can also create and manage tasks from chat — just say "add a task"
or "what's on my to-do list" and the assistant uses the tasks skill.

### The File Vault (`/files`)

Click **Files** in the navigation or go to `/files` directly.

A personal file storage and organization system:
- **Upload files** — drag and drop or click to upload images, documents,
  PDFs, audio, video
- **Organize with topics** — create folders/topics to group files
  (e.g., "Science Project", "Volleyball Photos", "Music")
- **File storage** — uploaded images and documents are stored securely
  with metadata
- **Search** — find files by name, description, or AI-generated tags
- **Preview** — view images, PDFs, and documents inline without
  downloading
- **Thumbnails** — visual grid of your files with auto-generated
  previews

### Getting a Shell Inside the Containers

Sometimes you need to poke around inside the Docker containers — to
debug, check logs, or test a skill manually. Here's how:

```bash
# Open a bash shell inside the gateway container (where OpenClaw runs)
docker exec -it openclaw-gateway bash

# Open a bash shell inside the web container (where the Go server runs)
docker exec -it openclaw-web bash

# Run a single command without opening a shell
docker exec openclaw-gateway openclaw doctor   # check gateway health
docker exec openclaw-web python3 skills/school/school.py grades   # test a skill
```

Inside the container, you're the `openclaw` user (UID 1001). The
filesystem is isolated from your Pi — you can look around without
breaking anything. Type `exit` to leave.

> **Tip:** If a skill isn't working, exec into the web container and
> run the skill's Python script directly to see the error output.

---

## Stage 16: Set Up a Minecraft Server

Now that your AI assistant is running, let's set up something fun — your
own Minecraft server, running locally on your Orange Pi. Your friends on
the same network can join directly, and with a parent's help you can
open it to friends outside your home too. Your AI assistant can manage
it from chat.

### Before You Start: What You Need

**A paid Minecraft account is required.** Minecraft is not free — you
need a Microsoft account with a purchased copy of Minecraft. There are
two editions:

| Edition | Platform | Server Type | Which to Pick |
|---------|----------|-------------|---------------|
| **Java Edition** | PC (Windows, Mac, Linux) | Paper MC (what we install here) | **Pick this one** if you and your friends play on computers |
| **Bedrock Edition** | Console, mobile, Windows 10+ | Bedrock Dedicated Server | Pick this if your friends play on Xbox, Switch, or phones |

**This guide sets up a Java Edition server** using Paper MC. If your
friends play Bedrock, you'll need a different server — ask Codex:

````text
Help me set up a Bedrock Dedicated Server on my Orange Pi instead of
Paper MC. My friends play Minecraft on Xbox/Switch/mobile.
````

Make sure everyone who wants to join has their own paid Minecraft
account with a valid Microsoft login. The server runs in `online-mode`
which verifies accounts — no pirated copies allowed.

### Read the Minecraft EULA

Before running a Minecraft server, you **must** read and accept
Mojang's End User License Agreement (EULA). This is a legal agreement
between you and Microsoft/Mojang.

Read it here: [minecraft.net/eula](https://www.minecraft.net/en-us/eula)

Key points:
- You can run a server for yourself and friends, but you **cannot
  charge money** for access
- You cannot sell in-game items for real money
- Mojang can change the terms at any time
- You're responsible for what happens on your server

**Do not skip this.** When Codex sets up the server below, it will ask
you to accept the EULA (`eula=true` in `eula.txt`). Only do this after
you've actually read it. Accepting terms you haven't read is a bad
habit — and this is a good opportunity to practice reading legal
documents critically.

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

````text
Help me set up a Paper Minecraft server on this Orange Pi. Here's what
I need:

1. Download the latest Paper MC 1.21.x jar to /opt/minecraft/
2. Show me the EULA file so I can read it before accepting
3. Configure server.properties with these settings:
   - server-port=25565
   - max-players=10
   - difficulty=normal
   - view-distance=10 (good for ARM CPUs)
   - simulation-distance=8
   - motd=A Minecraft Server (I'll customize this later)
   - online-mode=true
   - white-list=true (only invited players can join)
4. Create a start script at /opt/minecraft/start.sh that runs the
   server with 4GB RAM (-Xmx4G -Xms2G) and Paper's recommended
   JVM flags for ARM
5. Set file ownership to the minecraft user
6. Create a systemd service so the server starts on boot and can be
   managed with systemctl
7. Open port 25565 in UFW
````

### Install Fun Plugins

Paper supports plugins — mods that add features to your server. Here are
two great starter plugins. Ask Codex:

````text
Install these Paper MC plugins on my Minecraft server at /opt/minecraft/:

1. EssentialsX — adds /home, /tpa (teleport to a friend), /sethome,
   /warp, and dozens of useful commands. Download the latest jar from
   the EssentialsX GitHub releases page and put it in /opt/minecraft/plugins/

2. WorldEdit — lets you build massive structures instantly. Select
   a region and fill it, copy it, paste it, rotate it. Essential for
   creative builders. Download from the dev.bukkit.org or EngineHub site.

After adding the plugin jars, restart the server:
sudo systemctl restart minecraft

Then verify they loaded: check /opt/minecraft/logs/latest.log for
"[EssentialsX]" and "[WorldEdit]" loading messages.
````

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
- Use `localhost` or `127.0.0.1` (port 25565 is the default in the
  Minecraft client, so you don't need to type it)

**For friends outside your network (ask a parent first):**

This requires **port forwarding** on your home router — always do this
**with a parent's supervision**.

Here's how it works:
1. Your Orange Pi has a **local IP** (like `192.168.1.42`) — this only
   works inside your home network
2. Your **router** has a **public IP** — this is what the outside world
   sees. Find it by googling "what is my IP" from any device on your
   network
3. Port forwarding tells the router: "when someone connects to port
   25565, send them to my Orange Pi at 192.168.1.42"

To set it up:
1. Ask a parent to log into your router's admin page (usually
   `192.168.1.1` or `192.168.0.1` in a browser — check the sticker on
   your router for the address and password)
2. Find the **Port Forwarding** section (sometimes called "Virtual
   Servers" or "NAT")
3. Create a rule: external port `25565` → internal IP `YOUR_PI_IP` →
   internal port `25565` → protocol `TCP`
4. Save and apply

Then give your friends your **router's public IP** (not your Pi's local
IP). They enter it in Minecraft under Multiplayer → Add Server. Since
25565 is the default Minecraft port, they don't need to type the port
number — just the IP address.

> **Security note:** Port forwarding opens a door into your home
> network. Only forward the Minecraft port (25565), never forward SSH
> (22) or the web UI (8085). The whitelist (`white-list=true`) ensures
> only approved players can join, and `online-mode=true` verifies their
> Microsoft accounts. Always discuss with a parent before opening ports.

### Update Your .env for AI Management

Now that the Minecraft server is running, update your `.env` so the AI
assistant's Minecraft skill (see `skills/minecraft/`) can manage it:

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

## Stage 17: Set Up Network Printing (Optional)

If you have a network printer (most modern printers connect to WiFi),
your AI assistant can print documents for you using the printer skill.

### Find Your Printer's IP Address

Your printer needs to be on the same network as your Orange Pi. Find
its IP address:
- **On the printer:** Most printers have a "Network Info" or "Print
  Network Configuration" option in their settings menu
- **On your router:** Check the connected devices list in your router's
  admin page
- **From the Pi:** Try discovering printers on the network:
  ```bash
  sudo apt install -y cups-client avahi-utils
  avahi-browse -t _ipp._tcp    # Discover IPP printers on your network
  ```

### Test Printing

Once you have the IP, test it:

```bash
# Install CUPS (Common UNIX Printing System)
sudo apt install -y cups

# Add your printer (replace IP and give it a name)
sudo lpadmin -p myprinter -E -v ipp://192.168.1.200/ipp/print -m everywhere

# Print a test page
echo "Hello from my Orange Pi!" | lp -d myprinter
```

### Configure the Printer Skill

Update your `.env` with the printer's IP:

```bash
nano /opt/openclaw/.env
# Set: PRINTER_IP=192.168.1.200
```

After saving, restart the stack: `docker compose restart`

Now try asking your assistant: *"Print this document"* or use the
printer skill directly:

```bash
docker exec openclaw-web python3 skills/printer/print.py "test.pdf"
```

---

## Stage 18: Customize Your Desktop

Your Orange Pi is a full Linux desktop computer — not just a server.
Let's make it look and feel like a machine you actually want to use
every day.

### Your Desktop: GNOME

The Orange Pi ships with **GNOME** — the same desktop that Ubuntu uses.
It comes with GDM3 (GNOME Display Manager) pre-installed, so you get a
full graphical login screen and desktop environment out of the box.

### Make It Look Like Windows

Ask Codex:

````text
Install GNOME extensions to make my desktop look like Windows 11:
Dash to Panel (moves the dock to a bottom taskbar), ArcMenu (adds a
Windows-style Start menu), and set a modern theme. My desktop is
GNOME on Ubuntu ARM64.
````

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

````text
Install Visual Studio Code on this ARM64 Ubuntu machine.
````

VS Code has extensions for Python, Go, Markdown, and hundreds of other
languages. It also has a built-in terminal — so you can code and run
commands in the same window. Start here:
- Install the **Python** extension (for editing skills)
- Install the **Markdown Preview** extension (for reading .md files)

#### Vivaldi (Recommended Browser)

[Vivaldi](https://vivaldi.com/) is a browser built on **Chromium** (the
same engine as Chrome), but with way more features built in — and no
tracking or data mining. It runs natively on ARM64.

**Why Vivaldi over Chrome or Firefox?**

| Feature | Chrome | Firefox | Vivaldi |
|---------|--------|---------|---------|
| Built-in ad blocker | No | No | **Yes** |
| Built-in tracker blocker | No | Yes | **Yes** |
| Tab stacking (group tabs) | Basic | No | **Yes** |
| Tab tiling (split screen) | No | No | **Yes** |
| Tab hibernation (save RAM) | No | No | **Yes** (great for Orange Pi) |
| Web Panels (sidebar apps) | No | No | **Yes** |
| Built-in notes | No | No | **Yes** |
| Chrome extensions | Yes | No | **Yes** (full Chrome Web Store) |
| Privacy (no data mining) | No | Yes | **Yes** |
| Customizable UI | No | Some | **Yes** (everything) |

**Install it:**

```bash
# Add Vivaldi's repository (for automatic updates)
wget -qO- https://repo.vivaldi.com/archive/linux_signing_key.pub \
  | gpg --dearmor | sudo dd of=/usr/share/keyrings/vivaldi-browser.gpg

echo "deb [signed-by=/usr/share/keyrings/vivaldi-browser.gpg] https://repo.vivaldi.com/archive/deb/ stable main" \
  | sudo tee /etc/apt/sources.list.d/vivaldi-archive.list

sudo apt update && sudo apt install -y vivaldi-stable
```

Using the APT repo means Vivaldi updates automatically with
`sudo apt upgrade` — just like all your other software.

**First launch — set it up:**

1. Open Vivaldi from the app menu
2. Pick your theme (dark mode!) and tab bar position (bottom or side)
3. Enable the **ad blocker**: Settings → Privacy → Tracker and Ad
   Blocking → select **"Block Trackers and Ads"**
4. Import bookmarks from Chrome/Firefox if you had any

**Power features to explore:**

- **Web Panels** — click the `+` in the left sidebar to pin sites like
  Discord, Google Classroom, or your OpenClaw web UI
  (`http://localhost:8085`). They stay in a sidebar while you browse.
- **Tab Stacking** — drag one tab onto another to group them (great for
  research projects — stack all your sources together)
- **Tab Tiling** — select stacked tabs, right-click → **Tile Tabs** to
  view them side by side. Read a source and write your essay at the
  same time.
- **Tab Hibernation** — right-click a tab → **Hibernate Tab** to free
  RAM. On an Orange Pi with limited memory, this helps a lot.
- **Notes** — press the notes icon in the sidebar to jot down thoughts
  while browsing. Useful for homework research.
- **Chrome Web Store** — visit
  [chrome.google.com/webstore](https://chrome.google.com/webstore)
  and install any Chrome extension. They work in Vivaldi.

> **Why not just use Chrome?** Chrome is made by Google, and it tracks
> everything you do to sell ads. Vivaldi is built on the same engine
> (so websites look identical), but the company doesn't track you. It's
> free, and your data stays on your machine. Same speed, more features,
> more privacy.

#### Firefox (if not pre-installed)

```bash
sudo apt install -y firefox
```

Firefox is a solid backup browser. Having two browsers is useful — if
a website doesn't work in one, try the other.

### Set a Wallpaper

Open **Settings → Background** and pick a wallpaper that makes it feel
yours.

### (Optional) Extra Apps

Depending on your interests, ask Codex to install any of these:

````text
Install [APP] on my ARM64 Ubuntu machine.
````

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
Passwordless sudo isn't enabled. Press Ctrl+C, run
`setup-codex-sudo.sh` in the terminal, then restart Codex with the
remaining steps. Remember to run `remove-codex-sudo.sh` when you're done.

---

## Project Structure

```
openclaw_kids/
├── config/
│   ├── openclaw.kids.json.example  ← Template: AI model and skill config
│   ├── openclaw.kids.json          ← YOUR config (gitignored, made by configure.sh)
│   ├── FAMILY_COMPASS.md.example   ← Template: parenting guidance
│   └── FAMILY_COMPASS.md           ← YOUR copy (gitignored, made by configure.sh)
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
│   ├── printer/                ← Network printing
│   ├── tasks/                  ← Task management (to-dos, homework tracking)
│   └── ...
├── web/                        ← Go web server + frontend
├── docker-compose.yml
├── Dockerfile.openclaw
├── Dockerfile.web
├── scripts/
│   ├── setup-codex-sudo.sh     ← Enable passwordless sudo for Codex
│   └── remove-codex-sudo.sh    ← Disable passwordless sudo after Codex
├── configure.sh                ← Interactive config wizard (run anytime)
├── bootstrap.sh                ← First-time setup (runs configure.sh)
├── update.sh                   ← Incremental deploy (run after git pull)
├── .env.example                ← Template (safe to commit)
├── .env                        ← YOUR SECRETS (NEVER commit)
└── README.md                   ← This file
```

---

## What's Next

You've built a complete AI assistant from scratch — but right now, the
AI "brain" (GPT-5.4) runs on OpenAI's servers via your ChatGPT Plus
subscription. Your Orange Pi handles everything else: the skills,
the web UI, the Minecraft server, your files. But the actual thinking
happens in the cloud.

There are two directions to go from here.

### AI 101: Learn How AI APIs Work

**[AI 101](https://github.com/patdeg/ai101)** is a hands-on course
that teaches you how to call AI services directly — the same way
professional developers build AI-powered apps. It covers:

- **16 progressive examples** across 6 languages (Bash, Node.js,
  Python, Go, C, C++)
- **Chat and reasoning** — call Groq, OpenAI, and Anthropic APIs
  directly with `curl` and code
- **Vision** — send images to AI models and get descriptions back
- **Audio** — transcribe speech with Whisper, generate speech from text
- **Web search** — integrate Tavily for AI-powered research
- **AI agents** — build tools that call functions automatically
- **Safety** — content moderation (LlamaGuard) and prompt injection
  detection (Prompt Guard)
- **Economics** — understand API costs and rate limits
- **Featured project:** Alfred the Minecraft AI Counselor — an
  interactive chatbot that combines tool calling with content safety

Every example is ~80% comments — designed to teach, not just run. The
exercises follow Bloom's Taxonomy: understand → apply → create.

### Your Orange Pi Has a Secret Weapon: the NPU

Your Orange Pi 6 Plus has a dedicated **NPU** (Neural Processing Unit)
— a specialized chip designed to run AI models at high speed using very
little power.

**What is an NPU?** Regular CPUs are general-purpose — they do
everything (run your desktop, serve Minecraft, compile code). An NPU
is purpose-built for the math that AI models need: massive parallel
matrix multiplications. It's like the difference between a Swiss Army
knife (CPU) and a surgical scalpel (NPU) — the scalpel is far better
at the one thing it's designed for.

**What are TOPS?** NPU performance is measured in **TOPS** — **T**era
**O**perations **P**er **S**econd. "Tera" means trillion. So 1 TOPS =
1 trillion math operations per second. Your Orange Pi's CIX P1 NPU can
do tens of TOPS — that's enough to run real AI models locally:

- **Large Language Models** — chat with Qwen, Llama, DeepSeek running
  entirely on your hardware (no internet!)
- **Computer Vision** — object detection, face recognition, pose
  estimation
- **Speech Recognition** — Whisper converting your voice to text
- **Image Generation** — Stable Diffusion creating images from text

> **Interested in a full course on local AI with the Orange Pi 6?**
> A dedicated guide for running AI models on the NPU — from downloading
> models to building real-time computer vision apps — is being
> considered. If you'd like to see it, open an issue at
> [github.com/patdeg/openclaw_kids/issues](https://github.com/patdeg/openclaw_kids/issues)
> and let us know!

### Sneak Peek: Try Local AI Right Now

Even without a dedicated course, you can try two things right now.

**Step 1: Download a local AI model**

```bash
# Create the AI directory
sudo mkdir -p /opt/ai && sudo chown $USER:$USER /opt/ai
mkdir -p /opt/ai/models/gguf

# Download Qwen 2.5 7B — a 4.4GB language model
curl -L "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf" \
  -o /opt/ai/models/gguf/Qwen2.5-7B-Instruct-Q4_K_M.gguf
```

**Step 2: Chat with it — entirely offline**

Your Orange Pi comes with `llama-cli` pre-installed (the `cix-llama-cpp`
package). Point it at the model you just downloaded:

```bash
# Chat with Qwen 2.5 7B — running entirely on YOUR hardware
/usr/share/cix/bin/llama-cli \
  -m /opt/ai/models/gguf/Qwen2.5-7B-Instruct-Q4_K_M.gguf \
  -c 4096 -t 8 --conversation
```

That's it. You're now chatting with a 7-billion-parameter AI model
running on your Orange Pi — no internet, no subscription, no cloud.
It generates about 9 words per second on CPU. Not as fast as ChatGPT,
but it's **yours** and it's **private** — nothing you say ever leaves
your machine.

Type a question and press Enter. Type `/exit` to quit.

> **What just happened?** The model file (`.gguf`) contains billions of
> numbers called **weights** — the "knowledge" the AI learned during
> training. `llama-cli` loads those weights into your RAM and runs the
> math to generate each word. Your CPU does ~9 trillion operations per
> second to produce each token. That's what TOPS measures.

**Step 3: See AI detect objects in photos**

Download the CIX AI Model Hub (63GB — this one takes a while):

```bash
# Set up Python tools
python3 -m venv /opt/ai/venv
/opt/ai/venv/bin/pip install modelscope onnx onnxruntime numpy torch opencv-python-headless

# Download the full model hub (63GB — go grab a snack)
/opt/ai/venv/bin/modelscope download \
  --model cix/ai_model_hub_25_Q3 \
  --local_dir /opt/ai/ai_model_hub_25_Q3
```

Then run YOLOv8 object detection on the included test images:

```bash
cd /opt/ai/ai_model_hub_25_Q3/models/ComputeVision/Object_Detection/onnx_yolov8_n

# Detect objects in the test images
/opt/ai/venv/bin/python3 inference_onnx.py

# Open the results — images with colored boxes around detected objects
ls output/
```

Try it with your own photos:

```bash
cp ~/Pictures/my_photo.jpg test_data/
/opt/ai/venv/bin/python3 inference_onnx.py --image_path test_data/my_photo.jpg
```

> **What just happened?** YOLO ("You Only Look Once") scans the entire
> image in one pass and finds every object it recognizes — people, cars,
> dogs, chairs. The model is only 13MB but was trained on millions of
> labeled images. The NPU can run this in 15 milliseconds — fast enough
> for real-time video.

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
Your kid's local config files (`config/openclaw.kids.json`,
`config/FAMILY_COMPASS.md`, `.env`) are never overwritten — `git pull`
is always safe.

**First-time setup** uses `bootstrap.sh` instead (Stage 11). It runs
`configure.sh` automatically to ask the kid a few questions and generate
their personal config files.

To reconfigure (change assistant name, timezone, etc.):
```bash
cd ~/dev/openclaw_kids && ./configure.sh && ./update.sh
```

Each kid should have their own hardware with a separate deployment.
Email accounts are optional but recommended — set up via Migadu or any
IMAP provider and configure in the `.env` file.

### Automated Version Checks

A weekly scheduled agent runs every **Sunday at 3am Pacific** to
automatically review this project for compatibility with the latest
OpenClaw releases. It checks for:
- New OpenClaw npm versions and breaking changes
- Outdated deployment scripts or Docker base images
- Open GitHub issues reporting breakage

If fixes are needed, it opens a **pull request** for human review — it
never pushes directly to main. If everything is current, it does nothing.

Manage the schedule at:
[claude.ai/code/scheduled](https://claude.ai/code/scheduled)

### If Something Breaks

The `Dockerfile.openclaw` uses `openclaw@latest` by default. If a new
OpenClaw release causes issues:

1. **Report it:** Open an issue at
   [github.com/patdeg/openclaw_kids/issues](https://github.com/patdeg/openclaw_kids/issues)
2. **Quick fix:** Rebuild with the last known working version:
   ```bash
   cd /opt/openclaw
   docker compose build --build-arg OPENCLAW_VERSION=2026.2.26
   docker compose up -d
   ```
3. The weekly maintenance agent will investigate reported issues and
   propose fixes via PR.
