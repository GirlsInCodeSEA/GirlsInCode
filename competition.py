"""Timing, answer comparison and ranking for the live competition dashboard."""
from datetime import datetime, timedelta, timezone

MALAYSIA = timezone(timedelta(hours=8))
LEVEL_COLOURS = {'Beginner': 'c-pink', 'Intermediate': 'c-lavender',
                 'Advanced': 'c-blue', 'Bonus (ML)': 'c-orange'}
MAX_CODE_BYTES = 200 * 1024
MAX_OUTPUT_CHARS = 20000


def parse_time(value):
    moment = datetime.fromisoformat(value)
    return moment if moment.tzinfo else moment.replace(tzinfo=MALAYSIA)


def now():
    return datetime.now(timezone.utc)


def phase(start, end, moment=None):
    moment = moment or now()
    if moment < start:
        return 'before'
    return 'live' if moment < end else 'ended'


def normalise_output(value):
    """Ignore line endings and runs of whitespace; everything else must match exactly."""
    return ' '.join(str(value).split())


def is_correct(output, answer):
    return answer is not None and normalise_output(output) == normalise_output(answer) != ''


def rank(solves):
    """Total points per team; ties go to whoever reached the score first."""
    teams = {}
    for row in solves:
        team = teams.setdefault(row['team_name'], {'team': row['team_name'], 'score': 0,
                                                   'solved': 0, 'last_solve': ''})
        team['score'] += row.get('points') or 0
        team['solved'] += 1
        team['last_solve'] = max(team['last_solve'], str(row.get('solved_at') or ''))
    ordered = sorted(teams.values(), key=lambda t: (-t['score'], t['last_solve'] or '~', t['team']))
    for position, team in enumerate(ordered, start=1):
        team['rank'] = position
    return ordered
