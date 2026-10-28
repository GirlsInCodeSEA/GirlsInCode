"""Bounded output comparison for practice answers; never executes submissions."""
import ast
from collections import Counter
from decimal import Decimal, InvalidOperation
from functools import lru_cache
import json
from pathlib import Path
import re
import unicodedata

MAX_ANSWER_LENGTH = 20000
KEY_PATH = Path(__file__).resolve().parent / 'data/competition_questions/practice-answers.json'


@lru_cache(maxsize=1)
def answer_keys():
    return json.loads(KEY_PATH.read_text(encoding='utf-8'))


def text(value, ignore_case=False):
    value = unicodedata.normalize('NFC', value).translate(str.maketrans({
        '’': "'", '‘': "'", '“': '"', '”': '"', '–': '-', '−': '-',
    }))
    value = ' '.join(value.split())
    return value.casefold() if ignore_case else value


def sequence(value):
    """Flat literal lists/tuples/sets or one value per line; no executable code."""
    value = value.strip()
    if value.startswith(('[', '(', '{')):
        # Reject nested/large ASTs before literal_eval; bounded by input size too.
        tree = ast.parse(value, mode='eval')
        if not isinstance(tree.body, (ast.List, ast.Tuple, ast.Set)):
            raise ValueError('Enter a flat list.')
        if len(tree.body.elts) > 1500:
            raise ValueError('Too many values.')
        if any(not isinstance(node, (ast.Constant, ast.UnaryOp)) for node in tree.body.elts):
            raise ValueError('Enter a flat list.')
        parsed = ast.literal_eval(tree)
        if any(type(item) not in (str, int, float) for item in parsed):
            raise ValueError('Only numbers and text are allowed.')
        # Keep multiplicities: do not let Python silently deduplicate a submitted set.
        if isinstance(tree.body, ast.Set):
            parsed = [ast.literal_eval(node) for node in tree.body.elts]
        return [str(item) for item in parsed]
    return [line.strip() for line in value.splitlines() if line.strip()]


def numbers(value):
    value = value.strip()
    if value.startswith(('[', '(', '{')):
        items = sequence(value)
    else:
        items = re.split(r'[\s,]+', value)
    if not items or len(items) > 1500:
        raise ValueError('Enter numbers.')
    parsed = []
    for item in items:
        if not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d{1,4})?', item):
            raise ValueError('Enter numbers only.')
        number = Decimal(item)
        if not number.is_finite():
            raise ValueError('Enter finite numbers.')
        parsed.append(number)
    return parsed


def matches(value, spec):
    expected, mode = spec['expected'], spec['mode']
    norm = lambda v: text(v, spec.get('ignore_case', False))
    try:
        if mode in ('text', 'tokens'):
            return norm(value) == norm(expected)
        if mode == 'choice':
            return norm(value) in {norm(item) for item in spec['choices']}
        if mode in ('numeric', 'numbers'):
            got, want = numbers(value), numbers(expected)
            if len(got) != len(want) or (mode == 'numeric' and len(got) != 1):
                return False
            # Default is exact decimal equality. Any rounding tolerance is per-case.
            tolerance = Decimal(str(spec.get('tolerance', 0)))
            return all(abs(a - b) <= tolerance for a, b in zip(got, want))
        if mode == 'unordered_lines':
            return Counter(norm(line) for line in value.splitlines() if line.strip()) == Counter(
                norm(line) for line in expected.splitlines() if line.strip())
        if mode in ('sequence', 'unordered_sequence', 'subset', 'priority_sequence'):
            got = [norm(item) for item in sequence(value)]
            if mode == 'subset':
                return (len(got) == len(set(got)) == spec['count'] and
                        set(got) <= {norm(item) for item in spec['choices']})
            want = [norm(item) for item in sequence(expected)]
            if mode == 'sequence':
                return got == want
            if Counter(got) != Counter(want):
                return False
            if mode == 'priority_sequence':
                priority = {norm(item): i for i, group in enumerate(spec['groups']) for item in group}
                ranks = [priority[item] for item in got]
                return ranks == sorted(ranks)
            return True
        if mode == 'even_odd':
            got, want = numbers(value), numbers(expected)
            if any(item != item.to_integral_value() for item in got) or Counter(got) != Counter(want):
                return False
            parities = [int(item) % 2 for item in got]
            return parities == sorted(parities)
        if mode == 'track_pairs':
            lines = [line.strip() for line in value.splitlines() if line.strip()]
            if len(lines) != 3:
                return False
            for line in lines:
                match = re.fullmatch(r'(\d+)\s+(.+)', line)
                if not match or int(match[1]) >= len(spec['tracks']):
                    return False
                if norm(match[2]) != norm(spec['tracks'][int(match[1])]):
                    return False
            return True
    except (ValueError, SyntaxError, TypeError, InvalidOperation, RecursionError, OverflowError):
        return False
    raise ValueError(f'Unknown answer comparison mode: {mode}')


def check_answers(key, values):
    if not key['cases']:
        return dict(status='unavailable', message=key['note'], fields=[])
    if len(values) != len(key['cases']):
        return dict(status='invalid', message='Please answer every part of the question.', fields=[])
    if any(not value.strip() for value in values):
        return dict(status='invalid', message='Please enter an answer for every part.', fields=[])
    if any(len(value) > MAX_ANSWER_LENGTH for value in values):
        return dict(status='invalid', message='Each answer must be 20,000 characters or fewer.', fields=[])
    fields = [matches(value, spec) for value, spec in zip(values, key['cases'])]
    success = all(fields)
    return dict(status='correct' if success else 'incorrect', fields=fields,
                message=('Correct for this practice check!' if key['checkpoint'] else 'Correct!') if success
                else 'Not quite. Check the marked answers and try again.')
