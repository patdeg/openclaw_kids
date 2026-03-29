#!/usr/bin/env bash
set -euo pipefail

#
# configure.sh — Interactive setup wizard for OpenClaw Kids
#
# Generates local config files from .example templates.
# Safe to run multiple times — re-reads existing values as defaults.
#
# Generated files (gitignored — never committed):
#   config/openclaw.kids.json    ← AI identity, schedule, skills
#   config/FAMILY_COMPASS.md     ← Parenting guidance with your kid's details
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$SCRIPT_DIR/config"
JSON_EXAMPLE="$CONFIG_DIR/openclaw.kids.json.example"
JSON_LOCAL="$CONFIG_DIR/openclaw.kids.json"
COMPASS_EXAMPLE="$CONFIG_DIR/FAMILY_COMPASS.md.example"
COMPASS_LOCAL="$CONFIG_DIR/FAMILY_COMPASS.md"

echo ""
echo "============================================"
echo "  OpenClaw Kids — Configuration"
echo "============================================"
echo ""

# ── Helper: read a value with a default ─────────────────────────────────────
ask() {
  local prompt="$1"
  local default="$2"
  local result
  if [[ -n "$default" ]]; then
    read -rp "  $prompt [$default]: " result
    echo "${result:-$default}"
  else
    read -rp "  $prompt: " result
    echo "$result"
  fi
}

# ── Load existing values if local config exists ─────────────────────────────
EXISTING_NAME=""
EXISTING_DESC=""
EXISTING_TZ=""
EXISTING_START=""
EXISTING_END=""

if [[ -f "$JSON_LOCAL" ]]; then
  echo "  Found existing config/openclaw.kids.json — loading current values."
  echo ""
  EXISTING_NAME=$(python3 -c "import json; d=json.load(open('$JSON_LOCAL')); print(d.get('identity',{}).get('name',''))" 2>/dev/null || true)
  EXISTING_DESC=$(python3 -c "import json; d=json.load(open('$JSON_LOCAL')); print(d.get('identity',{}).get('description',''))" 2>/dev/null || true)
  EXISTING_TZ=$(python3 -c "import json; d=json.load(open('$JSON_LOCAL')); print(d.get('heartbeat',{}).get('activeHours',{}).get('timezone',''))" 2>/dev/null || true)
  EXISTING_START=$(python3 -c "import json; d=json.load(open('$JSON_LOCAL')); print(d.get('heartbeat',{}).get('activeHours',{}).get('start',''))" 2>/dev/null || true)
  EXISTING_END=$(python3 -c "import json; d=json.load(open('$JSON_LOCAL')); print(d.get('heartbeat',{}).get('activeHours',{}).get('end',''))" 2>/dev/null || true)
fi

# ── Section 1: AI Assistant Identity ────────────────────────────────────────
echo "-- Your AI Assistant --"
echo ""
ASSISTANT_NAME=$(ask "What should your AI assistant be called?" "${EXISTING_NAME:-ATHENA}")
ASSISTANT_DESC=$(ask "Short description for your assistant?" "${EXISTING_DESC:-Personal AI assistant for school, gaming, and projects}")

echo ""
echo "-- Schedule --"
echo ""
TIMEZONE=$(ask "Your timezone?" "${EXISTING_TZ:-America/Los_Angeles}")
ACTIVE_START=$(ask "Wake-up hour (HH:MM)?" "${EXISTING_START:-07:00}")
ACTIVE_END=$(ask "Bedtime hour (HH:MM)?" "${EXISTING_END:-22:00}")

# ── Section 2: About You (for FAMILY_COMPASS.md) ───────────────────────────

# Load existing values from FAMILY_COMPASS if possible
EXISTING_AGE=""
EXISTING_GENDER=""
EXISTING_LOCATION=""
EXISTING_ACTIVITIES=""

echo ""
echo "-- About You (personalizes how the AI talks to you) --"
echo ""
KID_AGE=$(ask "How old are you?" "${EXISTING_AGE:-13}")
KID_GENDER=$(ask "boy or girl?" "${EXISTING_GENDER:-boy}")
KID_LOCATION=$(ask "City and state?" "${EXISTING_LOCATION:-}")
KID_ACTIVITIES=$(ask "Sports, hobbies, interests? (e.g., volleyball, Minecraft, coding)" "${EXISTING_ACTIVITIES:-}")

# ── Build pronoun strings ───────────────────────────────────────────────────
if [[ "$KID_GENDER" == "girl" ]]; then
  PRONOUN="she"; PRONOUN_CAP="She"; PRONOUN_OBJ="her"
else
  PRONOUN="he"; PRONOUN_CAP="He"; PRONOUN_OBJ="him"
fi

# Build the activities sentence
if [[ -n "$KID_ACTIVITIES" ]]; then
  ACTIVITIES_LINE="enjoys $KID_ACTIVITIES"
else
  ACTIVITIES_LINE="goes to school and is exploring interests"
fi

# ── Generate openclaw.kids.json ─────────────────────────────────────────────
echo ""
echo "==> Generating config/openclaw.kids.json..."

# If there's an existing local config, preserve skill entries and other
# customizations by doing a targeted update instead of overwriting.
if [[ -f "$JSON_LOCAL" ]]; then
  python3 -c "
import json, sys

with open('$JSON_LOCAL') as f:
    config = json.load(f)

# Update only the fields configure.sh manages
config['identity']['name'] = sys.argv[1]
config['identity']['description'] = sys.argv[2]
config['heartbeat']['activeHours']['timezone'] = sys.argv[3]
config['heartbeat']['activeHours']['start'] = sys.argv[4]
config['heartbeat']['activeHours']['end'] = sys.argv[5]

# Merge any new skills from the example template
with open('$JSON_EXAMPLE') as f:
    example = json.load(f)
example_skills = example.get('skills', {}).get('entries', {})
live_skills = config.setdefault('skills', {}).setdefault('entries', {})
for name, entry in example_skills.items():
    if name not in live_skills:
        live_skills[name] = entry
        print(f'    + Added new skill: {name}')

with open('$JSON_LOCAL', 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')
" "$ASSISTANT_NAME" "$ASSISTANT_DESC" "$TIMEZONE" "$ACTIVE_START" "$ACTIVE_END"
else
  # Fresh generation from template
  sed \
    -e "s|__ASSISTANT_NAME__|$ASSISTANT_NAME|g" \
    -e "s|__ASSISTANT_DESCRIPTION__|$ASSISTANT_DESC|g" \
    -e "s|__TIMEZONE__|$TIMEZONE|g" \
    "$JSON_EXAMPLE" > "$JSON_LOCAL"
fi

echo "    Done: config/openclaw.kids.json"

# ── Generate FAMILY_COMPASS.md ──────────────────────────────────────────────
echo "==> Generating config/FAMILY_COMPASS.md..."

sed \
  -e "s|__KID_AGE__|$KID_AGE|g" \
  -e "s|__KID_GENDER__|$KID_GENDER|g" \
  -e "s|__KID_LOCATION__|$KID_LOCATION|g" \
  -e "s|__KID_PRONOUN_CAP__|$PRONOUN_CAP|g" \
  -e "s|__KID_PRONOUN_OBJ__|$PRONOUN_OBJ|g" \
  -e "s|__KID_PRONOUN__|$PRONOUN|g" \
  -e "s|__KID_ACTIVITIES__|$ACTIVITIES_LINE|g" \
  "$COMPASS_EXAMPLE" > "$COMPASS_LOCAL"

echo "    Done: config/FAMILY_COMPASS.md"

echo ""
echo "============================================"
echo "  Configuration complete!"
echo "============================================"
echo ""
echo "  Your AI assistant: $ASSISTANT_NAME"
echo "  Timezone: $TIMEZONE  ($ACTIVE_START - $ACTIVE_END)"
echo ""
echo "  To change these settings later, run:"
echo "    ./configure.sh"
echo ""
echo "  To deploy, run:"
echo "    ./bootstrap.sh    (first time)"
echo "    ./update.sh       (after that)"
echo ""
