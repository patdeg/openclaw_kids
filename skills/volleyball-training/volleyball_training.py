#!/usr/bin/env python3
"""Volleyball Training skill — evidence-based training & nutrition for teen volleyball."""

import argparse
import json
import sys
from datetime import datetime, date, timedelta

SAFETY_PREAMBLE = (
    "SAFETY: All recommendations follow NSCA, AAP, and IOC guidelines for "
    "adolescent athletes. No supplements beyond basic vitamins. No 1RM testing "
    "under 16. No caloric restriction under 18. Always train with qualified "
    "supervision. Sleep 8-10 hours is the #1 recovery tool."
)

WORKOUTS = {
    "upper": {
        "name": "Upper Body Strength",
        "exercises": [
            {"name": "Band pull-aparts", "sets": 3, "reps": 15, "note": "Warm-up / shoulder prehab"},
            {"name": "Push-ups", "sets": 3, "reps": "10-15", "note": "Chest, shoulders, core"},
            {"name": "Dumbbell rows", "sets": 3, "reps": "10-12 each arm", "note": "Upper back"},
            {"name": "Dumbbell overhead press", "sets": 3, "reps": "8-10", "note": "Light weight, full ROM"},
            {"name": "Face pulls (band)", "sets": 3, "reps": 15, "note": "Rear delts, rotator cuff"},
            {"name": "Prone Y-T-W raises", "sets": 2, "reps": "8 each", "note": "Scapular stability"},
        ],
    },
    "lower": {
        "name": "Lower Body Strength",
        "exercises": [
            {"name": "Bodyweight squats", "sets": 2, "reps": 10, "note": "Warm-up, check form"},
            {"name": "Goblet squats", "sets": 3, "reps": "10-12", "note": "Hold dumbbell at chest"},
            {"name": "Romanian deadlifts (DB)", "sets": 3, "reps": "10-12", "note": "Hamstrings, hips — flat back"},
            {"name": "Walking lunges", "sets": 3, "reps": "8 each leg", "note": "Balance + quad/glute strength"},
            {"name": "Calf raises", "sets": 3, "reps": "15-20", "note": "Both bilateral and single-leg"},
            {"name": "Glute bridges", "sets": 3, "reps": "12-15", "note": "Hip activation"},
            {"name": "Single-leg balance (eyes closed)", "sets": 2, "reps": "30 sec each", "note": "Ankle stability"},
        ],
    },
    "full": {
        "name": "Full Body Strength",
        "exercises": [
            {"name": "Goblet squats", "sets": 3, "reps": "10-12"},
            {"name": "Push-ups", "sets": 3, "reps": "10-15"},
            {"name": "DB Romanian deadlifts", "sets": 3, "reps": "10-12"},
            {"name": "Dumbbell rows", "sets": 3, "reps": "10-12 each"},
            {"name": "Overhead press (light DB)", "sets": 3, "reps": "8-10"},
            {"name": "Plank", "sets": 3, "reps": "30-45 sec"},
            {"name": "Band pull-aparts", "sets": 2, "reps": 15},
        ],
    },
    "core": {
        "name": "Core Stability Circuit",
        "exercises": [
            {"name": "Front plank", "sets": 3, "reps": "30-45 sec", "note": "Anti-extension"},
            {"name": "Side plank", "sets": 2, "reps": "20-30 sec each", "note": "Anti-lateral flexion"},
            {"name": "Dead bugs", "sets": 3, "reps": "8 each side", "note": "Anti-extension + coordination"},
            {"name": "Pallof press (band)", "sets": 3, "reps": "10 each side", "note": "Anti-rotation"},
            {"name": "Bird dogs", "sets": 2, "reps": "8 each side", "note": "Spinal stability"},
            {"name": "Medicine ball rotational throws", "sets": 3, "reps": "6 each side", "note": "Hitting power"},
        ],
    },
    "shoulder-prehab": {
        "name": "Shoulder Health Circuit",
        "note": "Do this BEFORE every hitting/serving session",
        "exercises": [
            {"name": "Band external rotation at side", "sets": 2, "reps": 15},
            {"name": "Band external rotation at 90°", "sets": 2, "reps": 12},
            {"name": "Band pull-aparts", "sets": 2, "reps": 15},
            {"name": "Prone Y raises", "sets": 2, "reps": 10},
            {"name": "Prone T raises", "sets": 2, "reps": 10},
            {"name": "Wall slides", "sets": 2, "reps": 10},
            {"name": "Thoracic spine foam roller extensions", "sets": 1, "reps": "10 reps"},
            {"name": "Open books (thoracic rotation)", "sets": 2, "reps": "8 each side"},
        ],
    },
    "ankle-prehab": {
        "name": "Ankle Stability Circuit",
        "note": "Reduces ankle sprain risk by 35-50% (Schiftan et al., 2015)",
        "exercises": [
            {"name": "Ankle circles", "sets": 2, "reps": "10 each direction"},
            {"name": "Banded dorsiflexion (knee-to-wall)", "sets": 2, "reps": "10 each"},
            {"name": "Single-leg balance (firm surface)", "sets": 2, "reps": "30 sec each"},
            {"name": "Single-leg balance (eyes closed)", "sets": 2, "reps": "20 sec each"},
            {"name": "Calf raises (bilateral)", "sets": 2, "reps": 15},
            {"name": "Calf raises (single-leg)", "sets": 2, "reps": "10 each"},
            {"name": "Band eversion/inversion", "sets": 2, "reps": "12 each direction"},
        ],
    },
    "jump-training": {
        "name": "Plyometrics — Vertical Jump Development",
        "note": "48-72 hours rest between plyo sessions. Never on fatigued legs.",
        "exercises": [
            {"name": "Squat jumps (stick landing)", "sets": 3, "reps": 6, "note": "Focus on soft, quiet landing"},
            {"name": "Tuck jumps", "sets": 3, "reps": 5, "note": "Drive knees up, land soft"},
            {"name": "Broad jumps (stick)", "sets": 3, "reps": 5, "note": "Max distance, stick 2 sec"},
            {"name": "Lateral bounds", "sets": 3, "reps": "5 each side", "note": "Side-to-side power"},
            {"name": "Box jumps (step down)", "sets": 3, "reps": 5, "note": "STEP down, don't jump down"},
            {"name": "Approach jumps", "sets": 3, "reps": 4, "note": "Volleyball approach technique"},
        ],
        "total_contacts": "~60-80 foot contacts (moderate volume)",
    },
    "mobility": {
        "name": "Full Body Mobility Routine",
        "note": "Daily, 10-15 minutes. Dynamic before activity, static after.",
        "exercises": [
            {"name": "Leg swings (sagittal)", "sets": 1, "reps": "10 each leg"},
            {"name": "Leg swings (frontal)", "sets": 1, "reps": "10 each leg"},
            {"name": "Walking lunges with rotation", "sets": 1, "reps": "8 each"},
            {"name": "90/90 hip switches", "sets": 2, "reps": 8},
            {"name": "Half-kneeling hip flexor stretch", "sets": 2, "reps": "30 sec each"},
            {"name": "Adductor rockbacks", "sets": 2, "reps": "8 each side"},
            {"name": "Thoracic spine foam roller", "sets": 1, "reps": "10 extensions"},
            {"name": "Quadruped rotations", "sets": 2, "reps": "8 each side"},
            {"name": "Sleeper stretch (shoulder)", "sets": 2, "reps": "30 sec each"},
            {"name": "Ankle dorsiflexion (knee to wall)", "sets": 2, "reps": "10 each"},
        ],
    },
}

MEAL_PLANS = {
    "training-day": {
        "context": "Practice/training day",
        "meals": [
            {"time": "Breakfast (7 AM)", "food": "Oatmeal with banana + peanut butter, 2 eggs, glass of milk", "notes": "Carbs + protein to fuel the day"},
            {"time": "Lunch (12 PM)", "food": "Turkey sandwich on whole wheat, apple, yogurt, water", "notes": "Balanced meal, avoid heavy fats"},
            {"time": "Pre-practice snack (3:30 PM)", "food": "Banana + granola bar, 16 oz water", "notes": "1-2 hours before practice, easily digestible carbs"},
            {"time": "During practice", "food": "Water every 15-20 min (5-10 oz). Sports drink if >60 min", "notes": "Stay hydrated"},
            {"time": "Post-practice (within 30 min)", "food": "Chocolate milk (16 oz) + banana", "notes": "3:1 carb-to-protein ratio for recovery"},
            {"time": "Dinner (7 PM)", "food": "Grilled chicken, rice, steamed broccoli, salad", "notes": "Complete recovery meal"},
        ],
    },
    "rest-day": {
        "context": "Rest/recovery day",
        "meals": [
            {"time": "Breakfast", "food": "Scrambled eggs, whole wheat toast, fruit, milk"},
            {"time": "Lunch", "food": "Pasta with lean meat sauce, side salad, water"},
            {"time": "Snack", "food": "Greek yogurt with berries, handful of nuts"},
            {"time": "Dinner", "food": "Fish or chicken, sweet potato, vegetables"},
        ],
        "notes": "Still eat well — your body is repairing. Don't skip meals.",
    },
    "tournament-day": {
        "context": "Tournament day (2-4 matches)",
        "meals": [
            {"time": "Breakfast (6:30 AM)", "food": "Oatmeal + banana + PB, scrambled eggs, OJ", "notes": "Eat 3-4 hours before first game"},
            {"time": "Between games (60-90 min gap)", "food": "Pretzels, fruit (bananas, oranges, grapes), applesauce pouch, string cheese", "notes": "Easily digestible carbs. AVOID heavy/fatty foods"},
            {"time": "Between games (2+ hour gap)", "food": "PB&J sandwich or bagel with turkey, fruit", "notes": "Can eat a more substantial snack"},
            {"time": "All day", "food": "Water constantly. Sports drink during/between play", "notes": "Bring 2-3 liters of water for the day"},
            {"time": "After last match", "food": "Chocolate milk + real meal within 1 hour", "notes": "Start recovery immediately"},
        ],
        "packing_list": [
            "Cooler with ice packs",
            "2-3 water bottles (fill before leaving)",
            "Sports drinks (Gatorade/Powerade)",
            "Bananas, oranges, grapes",
            "Pretzels, granola bars, fig bars, rice cakes",
            "PB&J sandwich (pre-made)",
            "String cheese, turkey slices, nut butter packets",
            "Chocolate milk boxes (recovery)",
            "NO: candy, soda, energy drinks, fast food",
        ],
    },
    "recovery": {
        "context": "Post-tournament recovery (1-2 days after)",
        "meals": [
            {"time": "Focus areas", "food": "High-quality protein (chicken, fish, eggs), complex carbs (rice, pasta, sweet potato), plenty of vegetables and fruit", "notes": "Your body is repairing — feed it well"},
        ],
        "priorities": [
            "Sleep 9-10 hours (growth hormone peaks during deep sleep)",
            "Hydrate fully (replace all fluid lost during tournament)",
            "Eat protein at every meal (1.2-1.6 g/kg/day)",
            "Light activity only (walk, stretch, foam roll)",
            "No heavy training for 1-2 days",
        ],
    },
}


def cmd_workout(args):
    """Generate a workout."""
    wtype = args.type.lower().replace("_", "-")
    if wtype not in WORKOUTS:
        print(json.dumps({
            "error": f"Unknown workout type '{wtype}'.",
            "available": list(WORKOUTS.keys()),
        }))
        sys.exit(1)

    workout = WORKOUTS[wtype]
    print(json.dumps({
        "safety": SAFETY_PREAMBLE,
        "workout": workout,
    }))


def cmd_meal_plan(args):
    """Generate a meal plan."""
    ctx = args.context.lower().replace("_", "-")
    if ctx not in MEAL_PLANS:
        print(json.dumps({
            "error": f"Unknown context '{ctx}'.",
            "available": list(MEAL_PLANS.keys()),
        }))
        sys.exit(1)

    plan = MEAL_PLANS[ctx]
    print(json.dumps({
        "safety": SAFETY_PREAMBLE,
        "meal_plan": plan,
    }))


def cmd_hydration(_args):
    """Hydration guidelines."""
    print(json.dumps({
        "safety": SAFETY_PREAMBLE,
        "hydration": {
            "before_practice": "400-600 mL (13-20 oz) 2-3 hours before. 200-300 mL (7-10 oz) 10-20 min before.",
            "during_practice": "150-300 mL (5-10 oz) every 15-20 minutes. Add electrolyte drink if >60 min or hot.",
            "after_practice": "Replace 150% of fluid lost. Weigh before and after to estimate.",
            "daily_minimum": "2-3 liters per day on training days.",
            "monitor": "Urine color: pale yellow = good, dark yellow = dehydrated.",
            "youth_note": "Teens are MORE susceptible to heat illness than adults (higher surface area-to-mass ratio, lower sweat rates). Drink more frequently in smaller amounts.",
        },
    }))


def cmd_recovery(_args):
    """Recovery protocol."""
    print(json.dumps({
        "safety": SAFETY_PREAMBLE,
        "recovery": {
            "sleep": "8-10 hours per night. This is NON-NEGOTIABLE. Growth hormone peaks during deep sleep. Athletes sleeping <8 hours have 1.7x increased injury risk.",
            "nutrition": "Post-exercise: 1.0-1.2 g/kg carbs + 0.3 g/kg protein within 30-60 minutes. Chocolate milk is excellent.",
            "hydration": "Replace 150% of fluid lost during activity.",
            "active_recovery": "Light walking, swimming, or cycling. Foam rolling. Stretching.",
            "rest_days": "Minimum 1-2 days off per week from organized training.",
            "annual_break": "2-3 months off from volleyball specifically per year.",
            "overtraining_signs": [
                "Persistent fatigue not relieved by sleep",
                "Declining performance despite training",
                "Recurring illness",
                "Persistent muscle soreness (>72 hours)",
                "Loss of motivation for the sport",
                "Mood disturbances (irritability, anxiety)",
                "Sleep disturbances",
                "Decreased academic performance",
            ],
            "if_overtraining": "REDUCE training volume immediately. Focus on sleep and nutrition. If symptoms persist >2 weeks, see a sports medicine doctor.",
        },
    }))


def cmd_taper(args):
    """Generate a taper plan for a tournament."""
    try:
        tourney_date = datetime.strptime(args.tournament_date, "%Y-%m-%d").date()
    except ValueError:
        print(json.dumps({"error": "Invalid date format. Use YYYY-MM-DD."}))
        sys.exit(1)

    today = date.today()
    days_until = (tourney_date - today).days

    print(json.dumps({
        "safety": SAFETY_PREAMBLE,
        "taper": {
            "tournament_date": args.tournament_date,
            "days_until": days_until,
            "plan": [
                {"day": "10-7 days out", "training": "Normal training volume. Last heavy strength session."},
                {"day": "6-5 days out", "training": "Reduce volume 40%. Maintain intensity. 1-2 quality practice sessions."},
                {"day": "4-3 days out", "training": "Light practice. Sharp skills, not volume. Reduce hitting volume."},
                {"day": "2 days out", "training": "Light movement prep. Mobility. Mental visualization."},
                {"day": "1 day out", "training": "Rest or very light activity. Pack gear. Early bed."},
                {"day": "Tournament day", "training": "Warm-up protocol. Execute. Nutrition plan. Hydrate."},
            ],
            "key_principles": [
                "Reduce VOLUME, maintain INTENSITY (fewer sets, same weight)",
                "Prioritize sleep (especially 3-5 days before)",
                "Ensure adequate carbohydrate intake",
                "Start hydrating well 48-72 hours before",
                "Do NOT stop playing entirely — keep skills sharp",
            ],
        },
    }))


def cmd_check_in(_args):
    """Weekly wellness check-in prompt."""
    print(json.dumps({
        "action": "wellness_check_in",
        "instructions": (
            "Ask the athlete to rate each of the following 1-10:\n"
            "1. Sleep quality this week\n"
            "2. Energy level\n"
            "3. Muscle soreness\n"
            "4. Mood / motivation\n"
            "5. Stress level (school + sports)\n\n"
            "Also ask: Any pain? Where? How long?\n\n"
            "Flag if: any score ≤3, persistent pain >1 week, or "
            "multiple scores declining over consecutive weeks."
        ),
        "overtraining_threshold": "If 3+ scores are ≤4, recommend reducing training volume and prioritizing sleep/recovery.",
    }))


def cmd_supplements(_args):
    """Supplement safety information."""
    print(json.dumps({
        "safety": SAFETY_PREAMBLE,
        "supplements": {
            "generally_safe": [
                {"name": "Multivitamin", "note": "As 'insurance' if diet is inconsistent. Age-appropriate formula."},
                {"name": "Vitamin D", "note": "600-1,000 IU/day if blood levels are low. Common deficiency in teens. AAP endorsed."},
                {"name": "Calcium", "note": "If dietary intake is below 1,300 mg/day. RDA for ages 9-18."},
                {"name": "Iron", "note": "ONLY if diagnosed with deficiency via blood test. Do NOT supplement without testing."},
            ],
            "NOT_RECOMMENDED_for_under_18": [
                {"name": "Creatine", "reason": "AAP and NSCA advise against use under 18. Insufficient long-term safety data in adolescents."},
                {"name": "Pre-workout / caffeine supplements", "reason": "AAP warns against caffeine supplements for all children/adolescents. Risk of cardiac arrhythmia, anxiety, sleep disruption."},
                {"name": "Protein powder", "reason": "Meet protein needs through food. Supplement industry poorly regulated. If family insists, use NSF Certified for Sport only."},
                {"name": "Testosterone boosters / DHEA / HGH", "reason": "ABSOLUTELY CONTRAINDICATED. Can disrupt hormonal development during puberty. Illegal without prescription."},
                {"name": "Weight loss supplements / fat burners", "reason": "DANGEROUS for adolescents. Can cause cardiac events, organ damage."},
                {"name": "Beta-alanine, citrulline, BCAAs", "reason": "Insufficient safety data in adolescents."},
            ],
            "bottom_line": "Food first. Always. The IOC states: 'The use of supplements by young athletes is discouraged. The focus should be on optimizing dietary intake.'",
        },
    }))


def cmd_injury_prevention(args):
    """Area-specific prehab exercises."""
    area = args.area.lower()

    areas = {
        "shoulder": WORKOUTS["shoulder-prehab"],
        "ankle": WORKOUTS["ankle-prehab"],
        "knee": {
            "name": "Knee Health (Osgood-Schlatter Prevention)",
            "exercises": [
                {"name": "Quad stretch (standing)", "sets": 2, "reps": "30 sec each"},
                {"name": "Foam roll quads/IT band", "sets": 1, "reps": "60 sec each"},
                {"name": "Terminal knee extensions (band)", "sets": 3, "reps": 15},
                {"name": "Single-leg glute bridges", "sets": 3, "reps": "10 each"},
                {"name": "Wall sits", "sets": 3, "reps": "20-30 sec"},
                {"name": "Step-downs (low box)", "sets": 2, "reps": "8 each leg"},
            ],
            "note": "Knee pain at the tibial tuberosity (bump below kneecap) during growth spurts is common (Osgood-Schlatter). Reduce squat depth and jumping volume if painful. Ice after activity. See a doctor if persistent.",
        },
    }

    if area not in areas:
        print(json.dumps({
            "error": f"Unknown area '{area}'.",
            "available": list(areas.keys()),
        }))
        sys.exit(1)

    print(json.dumps({
        "safety": SAFETY_PREAMBLE,
        "injury_prevention": areas[area],
    }))


def main():
    parser = argparse.ArgumentParser(description="Volleyball Training")
    subparsers = parser.add_subparsers(dest="command")

    w_p = subparsers.add_parser("workout", help="Generate a workout")
    w_p.add_argument("type", help="upper, lower, full, core, shoulder-prehab, ankle-prehab, jump-training, mobility")

    m_p = subparsers.add_parser("meal-plan", help="Nutrition plan")
    m_p.add_argument("context", help="training-day, rest-day, tournament-day, recovery")

    subparsers.add_parser("hydration", help="Hydration guidelines")
    subparsers.add_parser("recovery", help="Recovery protocol")

    t_p = subparsers.add_parser("taper", help="Tournament taper plan")
    t_p.add_argument("tournament_date", help="YYYY-MM-DD")

    subparsers.add_parser("check-in", help="Weekly wellness check")
    subparsers.add_parser("supplements", help="Supplement safety info")

    i_p = subparsers.add_parser("injury-prevention", help="Area-specific prehab")
    i_p.add_argument("area", help="shoulder, ankle, or knee")

    args = parser.parse_args()

    commands = {
        "workout": cmd_workout,
        "meal-plan": cmd_meal_plan,
        "hydration": cmd_hydration,
        "recovery": cmd_recovery,
        "taper": cmd_taper,
        "check-in": cmd_check_in,
        "supplements": cmd_supplements,
        "injury-prevention": cmd_injury_prevention,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
