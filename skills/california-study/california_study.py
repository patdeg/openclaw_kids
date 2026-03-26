#!/usr/bin/env python3
"""California Study skill — curriculum-aligned practice tests and study tools."""

import argparse
import json
import os
import sys

WORKSPACE = os.path.expanduser("~/workspace")
PROFILE_PATH = os.path.join(WORKSPACE, "PROFILE.md")

# California curriculum mapping
CURRICULUM = {
    6: {
        "math": "CPM Core Connections, Course 1",
        "ela": "StudySync (McGraw-Hill)",
        "science": "Earth & Space Science (CA NGSS)",
        "history": "Ancient Civilizations — Mesopotamia, Egypt, Greece, Rome, China, India (TCI History Alive!)",
    },
    7: {
        "math": "CPM Core Connections, Course 2",
        "ela": "StudySync (McGraw-Hill)",
        "science": "Life Science (CA NGSS)",
        "history": "Medieval & Early Modern World — Islam, China, Africa, Europe, Renaissance (TCI History Alive!)",
    },
    8: {
        "math": "CPM Core Connections, Course 3 / Integrated Math 1",
        "ela": "StudySync (McGraw-Hill)",
        "science": "Physical Science (CA NGSS) — also takes CAST state test",
        "history": "US History — Constitution through Reconstruction (TCI History Alive!)",
    },
    9: {
        "math": "CPM Integrated Math 1",
        "ela": "Varies by school",
        "science": "Varies — Biology, Chemistry, or Physics",
        "history": "World History & Geography",
    },
}

# CA standards overview by subject and grade
STANDARDS = {
    "math": {
        6: [
            "6.RP — Ratios & Proportional Relationships",
            "6.NS — The Number System (division, negative numbers, coordinate plane)",
            "6.EE — Expressions & Equations",
            "6.G — Geometry (area, surface area, volume)",
            "6.SP — Statistics & Probability",
        ],
        7: [
            "7.RP — Proportional Relationships",
            "7.NS — Operations with Rational Numbers",
            "7.EE — Expressions & Equations",
            "7.G — Geometry (scale drawings, angles, area, volume)",
            "7.SP — Statistics & Probability (random sampling, probability models)",
        ],
        8: [
            "8.NS — The Number System (irrational numbers)",
            "8.EE — Expressions & Equations (linear equations, exponents)",
            "8.F — Functions (linear functions, rate of change)",
            "8.G — Geometry (Pythagorean theorem, transformations, volume)",
            "8.SP — Statistics & Probability (scatter plots, bivariate data)",
        ],
        9: [
            "IM1-N — Number & Quantity",
            "IM1-A — Algebra (linear & exponential expressions)",
            "IM1-F — Functions (linear, exponential, sequences)",
            "IM1-G — Geometry (transformations, congruence)",
            "IM1-S — Statistics (summarize, represent, interpret data)",
        ],
    },
    "ela": {
        6: ["RL/RI.6 — Reading Literature & Informational Text", "W.6 — Writing (argument, informative, narrative)", "SL.6 — Speaking & Listening", "L.6 — Language (grammar, vocabulary)"],
        7: ["RL/RI.7 — Reading Literature & Informational Text", "W.7 — Writing (argument, informative, narrative)", "SL.7 — Speaking & Listening", "L.7 — Language (grammar, vocabulary)"],
        8: ["RL/RI.8 — Reading Literature & Informational Text", "W.8 — Writing (argument, informative, narrative)", "SL.8 — Speaking & Listening", "L.8 — Language (grammar, vocabulary)"],
        9: ["RL/RI.9-10 — Reading (grade band 9-10)", "W.9-10 — Writing", "SL.9-10 — Speaking & Listening", "L.9-10 — Language"],
    },
    "science": {
        6: ["MS-ESS1 — Earth's Place in the Universe", "MS-ESS2 — Earth's Systems", "MS-ESS3 — Earth and Human Activity", "MS-PS1 — Matter and Its Interactions (intro)"],
        7: ["MS-LS1 — From Molecules to Organisms", "MS-LS2 — Ecosystems", "MS-LS3 — Heredity", "MS-LS4 — Biological Evolution"],
        8: ["MS-PS1 — Matter and Its Interactions", "MS-PS2 — Motion and Stability: Forces", "MS-PS3 — Energy", "MS-PS4 — Waves", "CAST test this year"],
        9: ["HS-LS/PS/ESS — depends on course sequence"],
    },
    "history": {
        6: ["6.1 — Early Humankind", "6.2 — Mesopotamia", "6.3 — Ancient Egypt", "6.4 — Ancient Hebrews", "6.5 — Ancient India", "6.6 — Ancient China", "6.7 — Ancient Greece", "6.8 — Ancient Rome"],
        7: ["7.1 — Roman Empire decline", "7.2 — Islam", "7.3 — Imperial China", "7.4 — Ghana, Mali, Songhai", "7.5 — Medieval Japan", "7.6 — Medieval Europe", "7.7 — Mesoamerica", "7.8 — Renaissance & Reformation"],
        8: ["8.1 — Connecting with Past Learnings", "8.2 — New Republic", "8.3 — Constitution", "8.4 — New Political Ideas", "8.5 — Foreign Affairs", "8.6 — Industrial Revolution", "8.7 — Manifest Destiny", "8.8 — Civil War"],
        9: ["Various — World History & Geography"],
    },
}

VALID_SUBJECTS = ["math", "ela", "science", "history"]


def get_grade_from_profile():
    """Try to read grade from PROFILE.md."""
    if not os.path.isfile(PROFILE_PATH):
        return None
    with open(PROFILE_PATH) as f:
        for line in f:
            if "**Grade**" in line:
                # Extract number from line like "- **Grade**: 8th"
                parts = line.split(":")
                if len(parts) >= 2:
                    grade_str = parts[1].strip().lower()
                    for g in [6, 7, 8, 9, 10, 11, 12]:
                        if str(g) in grade_str:
                            return g
    return None


def resolve_grade(args_grade):
    """Resolve grade from args or profile."""
    if args_grade:
        return args_grade
    grade = get_grade_from_profile()
    if grade:
        return grade
    return None


def cmd_standards(args):
    """Show CA standards for a subject and grade."""
    grade = resolve_grade(args.grade)
    if not grade:
        print(json.dumps({"error": "Grade not specified and not found in PROFILE.md. Use --grade N."}))
        sys.exit(1)

    subject = args.subject.lower()
    if subject not in VALID_SUBJECTS:
        print(json.dumps({"error": f"Unknown subject '{subject}'. Valid: {', '.join(VALID_SUBJECTS)}"}))
        sys.exit(1)

    stds = STANDARDS.get(subject, {}).get(grade, [])
    curriculum = CURRICULUM.get(grade, {}).get(subject, "Unknown")

    print(json.dumps({
        "subject": subject,
        "grade": grade,
        "textbook": curriculum,
        "standards": stds,
        "source": "California Common Core State Standards / CA NGSS / CA HSS Framework",
    }))


def cmd_practice(args):
    """Generate practice quiz instructions for the AI."""
    grade = resolve_grade(args.grade)
    if not grade:
        print(json.dumps({"error": "Grade not specified and not found in PROFILE.md. Use --grade N."}))
        sys.exit(1)

    subject = args.subject.lower()
    if subject not in VALID_SUBJECTS:
        print(json.dumps({"error": f"Unknown subject '{subject}'. Valid: {', '.join(VALID_SUBJECTS)}"}))
        sys.exit(1)

    n = args.questions or 10
    stds = STANDARDS.get(subject, {}).get(grade, [])
    curriculum = CURRICULUM.get(grade, {}).get(subject, "Unknown")

    print(json.dumps({
        "action": "generate_practice_quiz",
        "subject": subject,
        "grade": grade,
        "num_questions": n,
        "textbook": curriculum,
        "standards": stds,
        "format": "CAASPP/SBAC style — mix of multiple choice, short answer, and constructed response",
        "instructions": (
            f"Generate {n} practice questions for grade {grade} {subject} "
            f"aligned to these CA standards: {', '.join(stds[:3])}. "
            f"The student uses {curriculum}. "
            f"Mix question types: multiple choice, short answer, constructed response. "
            f"Include an answer key at the end."
        ),
    }))


def cmd_mock_exam(args):
    """Generate mock exam instructions for the AI."""
    grade = resolve_grade(args.grade)
    if not grade:
        print(json.dumps({"error": "Grade not specified and not found in PROFILE.md. Use --grade N."}))
        sys.exit(1)

    subject = args.subject.lower()
    if subject not in VALID_SUBJECTS:
        print(json.dumps({"error": f"Unknown subject '{subject}'. Valid: {', '.join(VALID_SUBJECTS)}"}))
        sys.exit(1)

    stds = STANDARDS.get(subject, {}).get(grade, [])
    curriculum = CURRICULUM.get(grade, {}).get(subject, "Unknown")

    test_type = "CAST" if subject == "science" and grade == 8 else "CAASPP/SBAC"

    print(json.dumps({
        "action": "generate_mock_exam",
        "subject": subject,
        "grade": grade,
        "test_type": test_type,
        "textbook": curriculum,
        "standards": stds,
        "instructions": (
            f"Generate a full mock {test_type} exam for grade {grade} {subject}. "
            f"Include 20-30 questions covering all standards: {', '.join(stds)}. "
            f"Use the {test_type} format: computer-adaptive style with varied difficulty. "
            f"Include performance tasks where appropriate. "
            f"Provide a scoring rubric and answer key."
        ),
    }))


def cmd_review(args):
    """Generate a targeted review for a topic."""
    grade = resolve_grade(args.grade)
    topic = " ".join(args.topic)

    result = {
        "action": "generate_review",
        "topic": topic,
        "grade": grade,
        "instructions": (
            f"Create a targeted review for the topic: '{topic}'"
            + (f" at grade {grade} level" if grade else "")
            + ". Include: (1) Key concepts explained simply, "
            "(2) 3-5 worked examples, (3) 5 practice problems with answers, "
            "(4) Common mistakes to avoid."
        ),
    }
    print(json.dumps(result))


def cmd_curriculum(args):
    """Show what the student studies at their grade."""
    grade = resolve_grade(args.grade)
    if not grade:
        print(json.dumps({"error": "Grade not specified and not found in PROFILE.md. Use --grade N."}))
        sys.exit(1)

    curr = CURRICULUM.get(grade, {})
    if not curr:
        print(json.dumps({"error": f"No curriculum data for grade {grade}."}))
        sys.exit(1)

    print(json.dumps({
        "grade": grade,
        "school_district": os.environ.get("SCHOOL_DISTRICT", "My School District"),
        "curriculum": curr,
        "state_tests": {
            "CAASPP_ELA": grade <= 8 or grade == 11,
            "CAASPP_Math": grade <= 8 or grade == 11,
            "CAST_Science": grade == 8 or grade >= 10,
        },
    }))


def main():
    parser = argparse.ArgumentParser(description="California Study skill")
    subparsers = parser.add_subparsers(dest="command")

    std_p = subparsers.add_parser("standards", help="Show CA standards")
    std_p.add_argument("subject", help="math, ela, science, or history")
    std_p.add_argument("--grade", type=int, help="Grade level")

    prac_p = subparsers.add_parser("practice", help="Generate practice quiz")
    prac_p.add_argument("subject", help="math, ela, science, or history")
    prac_p.add_argument("--questions", type=int, default=10, help="Number of questions")
    prac_p.add_argument("--grade", type=int, help="Grade level")

    mock_p = subparsers.add_parser("mock-exam", help="Generate mock exam")
    mock_p.add_argument("subject", help="math, ela, science, or history")
    mock_p.add_argument("--grade", type=int, help="Grade level")

    rev_p = subparsers.add_parser("review", help="Review a topic")
    rev_p.add_argument("topic", nargs="+", help="Topic to review")
    rev_p.add_argument("--grade", type=int, help="Grade level")

    curr_p = subparsers.add_parser("curriculum", help="Show curriculum for grade")
    curr_p.add_argument("--grade", type=int, help="Grade level")

    args = parser.parse_args()

    commands = {
        "standards": cmd_standards,
        "practice": cmd_practice,
        "mock-exam": cmd_mock_exam,
        "review": cmd_review,
        "curriculum": cmd_curriculum,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
