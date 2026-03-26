# Onboarding — Get to Know You

First-run questionnaire that builds a personal profile so all other skills
can personalize their responses.

## When to Run

Run automatically on the FIRST conversation if `workspace/PROFILE.md` does
not exist. Can also be re-run with the `onboarding` command.

## Usage

```
exec: python3 ~/skills/onboarding/onboarding.py check
exec: python3 ~/skills/onboarding/onboarding.py save --json '<answers>'
exec: python3 ~/skills/onboarding/onboarding.py show
```

## Commands

- `check` — Returns whether PROFILE.md exists. If not, the agent should
  start the questionnaire conversationally.
- `save --json '{"nickname": "Alex", ...}'` — Save profile answers to
  PROFILE.md.
- `show` — Display the current profile.

## Questionnaire

Ask these questions conversationally (not as a boring form). Make it fun.

1. What should I call you? (nickname)
2. What grade are you in?
3. What are your favorite subjects in school? Least favorite?
4. What do you want to be when you grow up? (or what interests you most?)
5. What games do you play besides Minecraft?
6. What's your Minecraft username?
7. Do you play any sports? What teams?
8. What kind of music do you listen to?
9. Do you have any pets?
10. What's something you wish you were better at?
11. How do you prefer to study? (flashcards, practice problems, reading, videos?)
12. What time do you usually do homework?
13. Are there any subjects where you'd like extra help?

## Output Format

Saves `workspace/PROFILE.md`:

```markdown
# Profile: Alex

- **Nickname**: Alex
- **Grade**: 8th
- **Favorite Subjects**: Math, Computer Science
- **Least Favorite**: History
- **Interests**: Game dev, wants to learn Python
- **Games**: Minecraft, Roblox
- **Minecraft Username**: alex_gaming
- **Sports**: Soccer (local club)
- **Music**: Pop
- **Pets**: None
- **Wants to Improve**: Essay writing
- **Study Style**: Practice problems, short sessions
- **Homework Time**: 4-6 PM
- **Needs Help With**: Essay writing, history
```

All other skills should read this file to personalize their responses.
