#!/usr/bin/env python3
"""Volleyball Intel skill — tournament intelligence for SoCal 14U boys."""

import argparse
import json
import os
import sys
from datetime import datetime, date

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))

# Inline calendar data (also in competitors.yaml for reference)
SEASON_CALENDAR = [
    {"event": "SCVA Event #1", "date": "2026-01-10", "venue": "SoCal TBD"},
    {"event": "SCVA Event #2", "date": "2026-01-25", "venue": "SoCal TBD"},
    {"event": "Las Vegas Classic", "date": "2026-02-14", "end": "2026-02-16", "venue": "Las Vegas Convention Center"},
    {"event": "Coastal Combine #1", "date": "2026-02-21", "venue": "SoCal TBD"},
    {"event": "SCVA Event #3", "date": "2026-02-22", "venue": "SoCal TBD"},
    {"event": "Red Rock Rave #1 (JNQ)", "date": "2026-03-14", "end": "2026-03-16", "venue": "Las Vegas Convention Center"},
    {"event": "SCVA Event #4 (Div 5-20)", "date": "2026-03-22", "venue": "SoCal TBD"},
    {"event": "14U Bid Event", "date": "2026-03-28", "venue": "SoCal TBD"},
    {"event": "Red Rock Rave #2 (14s)", "date": "2026-04-04", "end": "2026-04-06", "venue": "Mandalay Bay Convention Center"},
    {"event": "SCVA Event #5 (Div 5-20)", "date": "2026-04-12", "venue": "SoCal TBD"},
    {"event": "USAV Boys JNC", "date": "2026-07-08", "end": "2026-07-11", "venue": "Phoenix, AZ"},
]

COMPETITORS = {
    "coast": {"name": "Coast VBC", "location": "San Diego", "website": "coastvbc.com", "note": "420 college scholarships"},
    "balboa": {"name": "Balboa Bay VBC", "location": "Newport Beach", "website": "balboabayvolleyball.club", "note": "Est. 1975"},
    "wave": {"name": "WAVE Volleyball", "location": "SoCal", "website": "wavevb.com"},
    "tstreet": {"name": "Tstreet VBC", "location": "Irvine", "website": "tstreetvolleyball.com", "note": "~#25 national"},
    "mizuno": {"name": "Mizuno Long Beach", "location": "Gardena", "website": "mizunovolleyballclub.com"},
    "california": {"name": "California VBC", "location": "Laguna Hills", "website": "cavolley.com", "note": "OC all-boys club"},
    "pulse": {"name": "Pulse VBC", "location": "Orange County", "website": "pulsevolleyball.com"},
    "ocvc": {"name": "Orange Coast VBC", "location": "Ladera Ranch", "website": "team-ocvc.com"},
    "socal": {"name": "SoCal VBC", "location": "N. County San Diego", "website": "socalvbc.com"},
    "sunshine": {"name": "Sunshine VBC", "location": "CA", "website": "sunshinevolleyballclub.com", "note": "#15 and #42 national"},
    "vision": {"name": "Vision VBC", "location": "CA", "note": "#3 national — top CA team"},
    "sgelite": {"name": "SG Elite VBC", "location": "CA", "note": "#15 national"},
    "sealbeach": {"name": "Seal Beach VBC", "location": "Seal Beach", "note": "#28 national"},
}


def cmd_next_tournament(_args):
    """Find the next upcoming tournament."""
    today = date.today()
    upcoming = []
    for event in SEASON_CALENDAR:
        event_date = datetime.strptime(event["date"], "%Y-%m-%d").date()
        if event_date >= today:
            days_until = (event_date - today).days
            upcoming.append({**event, "days_until": days_until})

    if not upcoming:
        print(json.dumps({"message": "No more tournaments this season."}))
        return

    nxt = upcoming[0]
    print(json.dumps({
        "next_tournament": nxt["event"],
        "date": nxt["date"],
        "end_date": nxt.get("end", nxt["date"]),
        "venue": nxt["venue"],
        "days_until": nxt["days_until"],
        "upcoming_count": len(upcoming),
    }))


def cmd_schedule(_args):
    """Show the full season calendar."""
    today = date.today()
    events = []
    for event in SEASON_CALENDAR:
        event_date = datetime.strptime(event["date"], "%Y-%m-%d").date()
        status = "upcoming" if event_date >= today else "past"
        events.append({**event, "status": status})

    print(json.dumps({
        "season": "2025-2026",
        "age_group": "Boys 14U",
        "events": events,
    }))


def cmd_rankings(_args):
    """Show ranking sources and instructions for the AI to look up current rankings."""
    print(json.dumps({
        "action": "lookup_rankings",
        "age_group": "Boys 14U",
        "sources": [
            {"name": "AES Power Rankings", "url": "https://www.advancedeventsystems.com/rankings/Male/U14/aes"},
            {"name": "USClubRankings 14s National", "url": "https://rankings.usclubrankings.com/vb/rankings/14-s-national-rankings"},
            {"name": "VolleyLens CA 14U Boys", "url": "https://volleylens.com/rankings/teams/2026/boys/ca-volley-14u-a551dc89"},
        ],
        "instructions": (
            "Use the tavily skill to search these ranking sources for current "
            "14U boys volleyball rankings. Look for our club and other SoCal clubs."
        ),
    }))


def cmd_scout(args):
    """Look up info about a competitor club."""
    query = args.team.lower().replace(" ", "").replace("vbc", "").replace("volleyball", "")

    # Try exact match first, then fuzzy
    match = COMPETITORS.get(query)
    if not match:
        for key, val in COMPETITORS.items():
            if query in key or query in val["name"].lower().replace(" ", ""):
                match = val
                break

    if match:
        print(json.dumps({
            "team": match,
            "suggestion": (
                f"For live stats and recent results, use tavily to search: "
                f"'{match['name']} 14U boys volleyball results 2026'"
            ),
        }))
    else:
        print(json.dumps({
            "error": f"Club '{args.team}' not found in tracker.",
            "available": [v["name"] for v in COMPETITORS.values()],
            "suggestion": f"Use tavily to search: '{args.team} volleyball club 14U'",
        }))


def cmd_competitors(_args):
    """List all tracked competitor clubs."""
    clubs = [{"key": k, **v} for k, v in COMPETITORS.items()]
    print(json.dumps({
        "age_group": "Boys 14U",
        "region": "Southern California",
        "our_club": os.environ.get("VOLLEYBALL_OUR_CLUB", "Set VOLLEYBALL_OUR_CLUB in .env"),
        "competitors": clubs,
    }))


def cmd_results(args):
    """Instruct the AI to look up recent results via web search."""
    tournament = args.tournament or "latest SCVA"
    print(json.dumps({
        "action": "search_results",
        "instructions": (
            f"Use the tavily skill to search for recent results: "
            f"'{os.environ.get('VOLLEYBALL_OUR_CLUB', 'our club')} {tournament} 14U boys volleyball results 2026'. "
            f"Also check results.advancedeventsystems.com for bracket data."
        ),
    }))


def main():
    parser = argparse.ArgumentParser(description="Volleyball Intel")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("next-tournament", help="Next upcoming tournament")
    subparsers.add_parser("schedule", help="Full season calendar")
    subparsers.add_parser("rankings", help="Current rankings sources")

    scout_p = subparsers.add_parser("scout", help="Scout a competitor")
    scout_p.add_argument("team", help="Team/club name")

    subparsers.add_parser("competitors", help="List tracked competitors")

    results_p = subparsers.add_parser("results", help="Recent results")
    results_p.add_argument("--tournament", help="Tournament name")

    args = parser.parse_args()

    commands = {
        "next-tournament": cmd_next_tournament,
        "schedule": cmd_schedule,
        "rankings": cmd_rankings,
        "scout": cmd_scout,
        "competitors": cmd_competitors,
        "results": cmd_results,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
