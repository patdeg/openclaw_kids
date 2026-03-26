# California Study — Curriculum-Aligned Practice Tests

Generate practice quizzes, mock exams, and study materials aligned with
the **California state curriculum** and **your school district** textbooks.

## Usage

```
exec: python3 ~/skills/california-study/california_study.py standards <subject> [--grade <N>]
exec: python3 ~/skills/california-study/california_study.py practice <subject> [--questions 10] [--grade <N>]
exec: python3 ~/skills/california-study/california_study.py mock-exam <subject> [--grade <N>]
exec: python3 ~/skills/california-study/california_study.py review <topic> [--grade <N>]
exec: python3 ~/skills/california-study/california_study.py curriculum [--grade <N>]
```

## Commands

- `standards <subject>` — Show relevant CA standards for the subject and
  grade (reads grade from PROFILE.md if not specified).
- `practice <subject>` — Generate a practice quiz (default 10 questions)
  in CAASPP/SBAC format. Adapts difficulty to grade level.
- `mock-exam <subject>` — Full-length mock test matching the state test
  format (Smarter Balanced for ELA/Math, CAST for Science).
- `review <topic>` — Targeted review with explanations and examples for
  a specific topic.
- `curriculum` — Show what subjects, textbooks, and standards apply to
  the user's grade at your school district.

## Subjects

- `math` — CA CCSS Mathematics (CPM Core Connections at your school district)
- `ela` — CA CCSS English Language Arts (StudySync at your school district)
- `science` — CA NGSS (Next Generation Science Standards)
- `history` — CA History-Social Science Framework (TCI at your school district)

## Personalization

Reads `workspace/PROFILE.md` to determine:
- Grade level (adapts standards and difficulty)
- Favorite/least favorite subjects (adjusts encouragement)
- Study style preference (flashcards, problems, reading)
- Subjects needing extra help (focuses there)

## your school district Curriculum Reference

| Grade | Math | ELA | Science | History |
|-------|------|-----|---------|---------|
| 6th | CPM Core Connections 1 | StudySync | Earth & Space (CA NGSS) | Ancient Civilizations (TCI) |
| 7th | CPM Core Connections 2 | StudySync | Life Science (CA NGSS) | Medieval World (TCI) |
| 8th | CPM Core Connections 3 / IM1 | StudySync | Physical Science (CA NGSS) + CAST | US History (TCI) |
| 9th | CPM Integrated Math 1 | varies | varies | World History |

## Data Sources

- Common Standards Project API (commonstandardsproject.com) — machine-readable CA CCSS
- CAASPP Practice Tests (caaspp.cde.ca.gov/sb/PracticeTest) — official format reference
- Smarter Balanced Content Explorer (contentexplorer.smarterbalanced.org) — item specs
- Illustrative Mathematics (illustrativemathematics.org) — CCSS-aligned math problems
- CPM Homework Help (homework.cpm.org) — CPM math curriculum support
- CDE Standards (cde.ca.gov) — official CA standards documents

## Notes

- Questions are AI-generated to match the format and difficulty of the
  actual state assessments. They are NOT official test items.
- For CAASPP/SBAC: tests are computer-adaptive with multiple item types
  (selected response, constructed response, performance tasks).
- CAST (California Science Test) is given in grades 5, 8, and once in
  high school.
