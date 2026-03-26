# Family Calendars

## Overview
Access family calendar events via iCal (.ics) feeds.

## Calendars

Configure your calendar feeds below. Each feed is an iCal URL that the
skill fetches and parses for upcoming events.

<!-- PERSONALIZE: Replace these examples with your actual calendar URLs.
     To find your iCal URL:
     - Google Calendar: Settings > Calendar > "Secret address in iCal format"
     - TeamSnap: Team Page > Schedule > "Subscribe" > copy iCal URL
     - Sports club: Check your club's website for an iCal/calendar feed -->

### Family Calendar
- **URL**: `YOUR_FAMILY_CALENDAR_ICAL_URL`
- Contains family events, appointments, and activities

### Sports Team Calendar
- **URL**: `YOUR_SPORTS_TEAM_ICAL_URL`
- Contains practices and tournaments
- Filter by your team name in SUMMARY field

### Rec League Calendar (optional)
- **URL**: `YOUR_REC_LEAGUE_ICAL_URL`
- Contains practices and games with locations

## How to Check Calendars

```bash
# Test a calendar feed
curl -s "YOUR_CALENDAR_ICAL_URL"
```

## Parsing iCal Format

Events in .ics files are structured as:
- `BEGIN:VEVENT` starts an event
- `SUMMARY:` contains the event title (e.g., team name, event type)
- `DTSTART:` or `DTSTART;TZID=America/Los_Angeles:` contains the start date/time
- `DTEND:` contains the end date/time
- `LOCATION:` contains the venue address (if available)
- `END:VEVENT` ends an event

### Date Format Examples
- `DTSTART;TZID=America/Los_Angeles;VALUE=DATE-TIME:20260130T173000` = Jan 30, 2026 at 5:30pm PT
- `DTSTART;VALUE=DATE:20260131` = Jan 31, 2026 (all day)

## Common Queries

### Player Schedule
- Fetch sports calendar, filter for your team name in SUMMARY
- "What practices do I have this week?"

### Family
- "What's on the family calendar this week?" → Fetch family calendar, filter by date range

## Team Info

<!-- PERSONALIZE: Add your team details here -->
- Team name:
- Practice location:
- Game/tournament locations:
