# Volleyball Intel — Tournament Intelligence

Scouting and tournament tracking for SoCal 14U boys club volleyball.
Player 1 and Player 2 play at Your Club (set via VOLLEYBALL_OUR_CLUB env var).

## Usage

```
exec: python3 ~/skills/volleyball-intel/volleyball_intel.py next-tournament
exec: python3 ~/skills/volleyball-intel/volleyball_intel.py schedule
exec: python3 ~/skills/volleyball-intel/volleyball_intel.py rankings
exec: python3 ~/skills/volleyball-intel/volleyball_intel.py scout <team>
exec: python3 ~/skills/volleyball-intel/volleyball_intel.py competitors
exec: python3 ~/skills/volleyball-intel/volleyball_intel.py results [--tournament <name>]
```

## Commands

- `next-tournament` — Next tournament date, venue, and division info.
- `schedule` — Full SCVA 2025-2026 season calendar for Boys 14U.
- `rankings` — Current 14U SoCal rankings from multiple sources.
- `scout <team>` — Look up a competing team/club (ranking, location, website).
- `competitors` — List all tracked SoCal 14U competitor clubs.
- `results` — Recent tournament results (requires web search via tavily).

## Data Sources

- AES / SportsEngine (results.advancedeventsystems.com) — tournament brackets, scores
- SportsEngine GraphQL API (api.sportsengine.com/graphql) — structured data
- USClubRankings (rankings.usclubrankings.com) — national rankings
- VolleyLens (volleylens.com) — Elo-based rankings
- AES Power Rankings (advancedeventsystems.com/rankings/Male/U14/aes)
- SCVA (scvavolleyball.org) — tournament schedule
- Sprocket Sports app — SCVA schedule updates
- Exposure Events API (volleyball.exposureevents.com/api/v1/)

## Key SoCal 14U Competitors

See competitors.yaml for the full list. Top clubs include:
Coast VBC, Balboa Bay, WAVE, Tstreet, Mizuno Long Beach, California VBC,
Pulse VBC, OCVC, SoCal VBC, Sunshine VBC, Vision VBC, SG Elite VBC.

## Tournament Day Mode

For live tournament tracking, the agent should:
1. Poll AES results every 5-10 minutes
2. Post score updates to Discord
3. Track bracket progression
4. Answer "Who do we play next?"

This requires the tavily skill for web searches during tournaments.
