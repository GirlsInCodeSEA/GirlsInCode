"""Load the private 2026 questions and answers into Supabase.

Run after applying migrations/002_competition_2026.sql (tables end in _2026):

    python3 scripts/seed_competition_2026.py

Reads data/competition_questions/private/2026/{questions,answers}.json (never committed)
and upserts them, so re-running after editing a question updates it in place.
Existing submissions and solves are left untouched.
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db import supabase  # noqa: E402

YEAR = '2026'
PRIVATE = ROOT / 'data/competition_questions/private' / YEAR


def main():
    if supabase is None:
        sys.exit('Supabase is not configured. Fill in .env first.')
    questions = json.loads((PRIVATE / 'questions.json').read_text(encoding='utf-8'))
    answers = json.loads((PRIVATE / 'answers.json').read_text(encoding='utf-8'))
    missing = [q['id'] for q in questions if not str(answers.get(q['id'], '')).strip()]
    if missing:
        sys.exit(f'No answer for: {", ".join(missing)}')
    rows = [{
        'id': q['id'], 'competition': YEAR, 'position': index, 'level': q['level'],
        'theme': q.get('theme'), 'title': q['title'], 'points': q['points'],
        'statement': q['statement'], 'question_input': q.get('question_input', ''),
    } for index, q in enumerate(questions, start=1)]
    supabase.table(f'competition_questions_{YEAR}').upsert(rows).execute()
    supabase.table(f'competition_answers_{YEAR}').upsert(
        [{'question_id': q['id'], 'answer': str(answers[q['id']])} for q in questions]).execute()
    print(f'Loaded {len(rows)} questions and answers '
          f'({sum(q["points"] for q in questions)} points in total).')


if __name__ == '__main__':
    main()
