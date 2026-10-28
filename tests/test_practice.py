import ast
from collections import Counter
from functools import lru_cache
from itertools import combinations, product
import json
from pathlib import Path
import random
import unittest
from unittest.mock import patch

import app as website
from practice import answer_keys, check_answers, matches
from scripts.build_practice_answers import build
from scripts.practice_solutions import (
    burgers, consistent_pairs, enclosure_saving, grid_energy, merge_stalls,
    minimum_energy_core, partition_work, equal_zone_merges, laser_cost_small,
)


class PracticeTests(unittest.TestCase):
    def setUp(self):
        self.client = website.app.test_client()
        with self.client.session_transaction() as session:
            session['_csrf_token'] = 'practice-token'

    def post(self, key, answers, json_response=True):
        return self.client.post('/practice/check/' + key, data={
            'csrf_token': 'practice-token',
            **{f'answer_{i}': value for i, value in enumerate(answers)},
        }, headers={'Accept': 'application/json'} if json_response else {})

    def test_every_active_question_accepts_reference_and_rejects_wrong_answer_without_database(self):
        keys = answer_keys()
        self.assertEqual(len(keys), 108)
        self.assertEqual(sum(bool(key['cases']) for key in keys.values()), 107)
        with patch.object(website, 'supabase', None), patch.object(website, 'run_code') as runner:
            for name, key in keys.items():
                if not key['cases']:
                    continue
                with self.subTest(question=name):
                    values = [part['expected'] for part in key['cases']]
                    response = self.post(name, values)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json['status'], 'correct')
                    self.assertNotIn('expected', response.json)
                    for i in range(len(values)):
                        wrong = values.copy()
                        wrong[i] = 'This is not the correct answer.'
                        result = self.post(name, wrong).json
                        self.assertEqual(result['status'], 'incorrect')
                        self.assertEqual(result['fields'][i], False)
            runner.assert_not_called()

    def test_all_answer_forms_link_to_the_correct_question(self):
        with patch.object(website, 'supabase', None), website.app.test_request_context():
            for name, key in answer_keys().items():
                path = website.practice_destination(name)
                response = self.client.get(path.split('#')[0])
                self.assertEqual(response.status_code, 200)
                if key['cases']:
                    self.assertIn(f'action="/practice/check/{name}"'.encode(), response.data)
                else:
                    self.assertNotIn(f'action="/practice/check/{name}"'.encode(), response.data)

    def test_blank_long_missing_and_withdrawn_answers_are_not_marked_wrong(self):
        for values in ([], [''], ['   '], ['1' * 20001]):
            response = self.post('2024-1', values)
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json['status'], 'invalid')
        self.assertEqual(self.post('2024-5', ['no']).json['status'], 'invalid')
        self.assertEqual(self.post('2025-march-intermediate-9', []).json['status'], 'unavailable')
        self.assertEqual(self.post('missing-1', ['1']).status_code, 404)

    def test_csrf_required_and_request_size_limited(self):
        self.assertEqual(self.client.post('/practice/check/2024-1', data={'answer_0': '400'}).status_code, 400)
        self.assertEqual(self.post('2024-1', ['x' * (1024 * 1024 + 1)]).status_code, 413)

    def test_no_javascript_result_and_html_escaping(self):
        response = self.post('2024-1', ['400'], json_response=False)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Correct!', response.data)
        self.assertIn(b'href="/2024#question-1"', response.data)
        response = self.post('2024-1', ['<script>alert(1)</script>'], json_response=False)
        self.assertNotIn(b'<script>alert', response.data)
        self.assertIn(b'&lt;script&gt;', response.data)

    def test_numeric_and_structural_equivalence_without_overaccepting(self):
        self.assertEqual(self.post('2024-1', [' 400.0\n']).json['status'], 'correct')
        for wrong in ('400.1', '400 cats', '400 400', 'NaN', 'Infinity'):
            self.assertEqual(self.post('2024-1', [wrong]).json['status'], 'incorrect')
        self.assertEqual(self.post('2024-4', ['(1,2,4,6,8,9,11)']).json['status'], 'correct')
        self.assertEqual(self.post('2024-4', ['1 2 4 6 8 11 9']).json['status'], 'incorrect')
        primes = ast.literal_eval(answer_keys()['2025-march-intermediate-1']['cases'][0]['expected'])
        self.assertEqual(self.post('2025-march-intermediate-1', [str(set(primes))]).json['status'], 'correct')
        self.assertEqual(self.post('2025-march-intermediate-1', [str(primes + [primes[0]])]).json['status'], 'incorrect')
        values = ast.literal_eval(answer_keys()['2025-march-intermediate-2']['cases'][0]['expected'])
        ordered = sorted([v for v in values if v % 2 == 0], reverse=True) + sorted([v for v in values if v % 2])
        self.assertEqual(self.post('2025-march-intermediate-2', [str(ordered)]).json['status'], 'correct')
        self.assertEqual(self.post('2025-march-intermediate-2', [str(list(reversed(ordered)))]).json['status'], 'incorrect')

    def test_random_and_priority_outputs_accept_other_valid_solutions(self):
        self.assertEqual(self.post('2023-3', ['nohtyp']).json['status'], 'correct')
        self.assertEqual(self.post('2023-3', ['python']).json['status'], 'incorrect')
        self.assertEqual(self.post('2023-8', ['0 Daydreaming by Harry Styles\n0 Daydreaming by Harry Styles\n9 Here With Me by d4vd']).json['status'], 'correct')
        self.assertEqual(self.post('2023-8', ['1 Daydreaming by Harry Styles\n0 Daydreaming by Harry Styles\n9 Here With Me by d4vd']).json['status'], 'incorrect')
        spec = answer_keys()['2023-15']['cases'][0]
        values = [title for group in spec['groups'] for title in reversed(group)]
        self.assertTrue(matches(json.dumps(values), spec))
        values[0], values[-1] = values[-1], values[0]
        self.assertFalse(matches(json.dumps(values), spec))
        self.assertEqual(self.post('2023-28', ['The Matrix']).json['status'], 'correct')
        self.assertEqual(self.post('2023-28', ['Invented movie']).json['status'], 'incorrect')

    def test_code_is_not_executed_and_nested_literals_fail_cleanly(self):
        spec = answer_keys()['2024-4']['cases'][0]
        for value in ("__import__('os').system('touch /tmp/never-run')", '[x for x in range(10)]',
                      '[' * 1000 + '1' + ']' * 1000, '[True, 2]', '{1:2}', "[float('nan')]"):
            with self.subTest(value=value[:50]):
                self.assertFalse(matches(value, spec))

    def test_worked_correction_and_known_outputs(self):
        keys = answer_keys()
        self.assertEqual([c['expected'] for c in keys['2025-march-advanced-7']['cases']],
                         ['26505\n50846\n21729', '12399\n99932\n95060'])
        self.assertEqual(self.post('2025-march-advanced-7', ['261005\n100846\n21729', '12399\n99932\n910060']).json['status'], 'incorrect')
        expected = {'2024-1': '400', '2024-3': '302', '2025-november-beginner-2': '56',
                    '2025-november-beginner-6': 'forward', '2025-november-beginner-9': 'QV18',
                    '2025-november-intermediate-5': '4', '2025-november-advanced-1': '34',
                    '2025-november-advanced-4': '6\n3\n7\n0\n-1\n-1\n7'}
        for name, value in expected.items():
            self.assertEqual(keys[name]['cases'][0]['expected'], value)
        self.assertEqual(keys['2023-23']['cases'][0]['expected'], '6.45')
        self.assertEqual(keys['2023-32']['cases'][0]['expected'], 'v*********8')

    def test_generated_keys_are_reproducible_and_complete(self):
        self.assertEqual(build(), answer_keys())
        for value in answer_keys().values():
            self.assertTrue(value['source'])
            if value['cases']:
                self.assertTrue(value['explanation'])
            if value['checkpoint']:
                self.assertTrue(value['note'])


class ReferenceAlgorithmTests(unittest.TestCase):
    def test_partition_solver_against_exhaustive_cuts(self):
        rng = random.Random(47)
        for _ in range(30):
            values = [rng.randrange(1, 15) for _ in range(7)]
            for workers in range(1, 5):
                expected = min(max(sum(values[a:b]) for a, b in zip((0,) + cuts, cuts + (7,)))
                               for cuts in combinations(range(1, 7), workers - 1))
                self.assertEqual(partition_work(values, workers), expected)

    def test_burger_matching_against_exhaustive_schedules(self):
        rng = random.Random(74)
        for _ in range(30):
            shipments = [(rng.randrange(1, 5), rng.randrange(10, 100)) for _ in range(5)]
            lifetime = rng.randrange(1, 5)
            @lru_cache(None)
            def exhaustive(hour, used):
                if hour == 5:
                    return 0
                possible = [exhaustive(hour+1, used)]
                for i, (arrival, calories) in enumerate(shipments):
                    if not used & (1 << i) and arrival <= hour < arrival+lifetime:
                        possible.append(calories + exhaustive(hour+1, used | (1 << i)))
                return max(possible)
            self.assertEqual(burgers(4, shipments, lifetime), exhaustive(1, 0))

    def test_merge_stalls_against_all_move_orders(self):
        @lru_cache(None)
        def exhaustive(values):
            options = [max(values)]
            for i in range(len(values)-1):
                if values[i] == values[i+1]:
                    options.append(exhaustive(values[:i] + (values[i]+1,) + values[i+2:]))
            return max(options)
        for values in product((1, 2), repeat=6):
            self.assertEqual(merge_stalls(list(values)), exhaustive(values))

    def test_subarray_score_proof_against_exhaustive_subarrays(self):
        # A mean >= X needs at least one member >= X. Disjoint subarrays
        # therefore cannot beat the k-th largest element; singleton choices attain it.
        for values in product((-1, 0, 2), repeat=4):
            intervals = [(a,b,sum(values[a:b])/(b-a)) for a in range(4) for b in range(a+1,5)]
            choices = [min(x[2],y[2]) for x,y in combinations(intervals,2) if x[1]<=y[0] or y[1]<=x[0]]
            self.assertEqual(max(choices), sorted(values, reverse=True)[1])

    def test_algorithms_on_independently_known_examples(self):
        self.assertEqual(grid_energy(['S23T']), 17)  # 5 + 2 + 10
        self.assertEqual(grid_energy(['S#T']), -1)
        self.assertEqual(minimum_energy_core([1,2,3], [2,4]), 4)
        self.assertEqual(minimum_energy_core([1,2,3], [2,3]), 0)
        self.assertEqual(minimum_energy_core([1,1,1], [4,4]), -1)
        self.assertEqual(enclosure_saving([(4,2),(8,10),(1,1),(9,12),(14,7),(2,3)]), 107)
        self.assertEqual(consistent_pairs([[4,1,2,3],[4,1,3,2],[4,2,1,3]]), 4)
        self.assertEqual(equal_zone_merges([1,2,3,1,1,1]), 3)
        self.assertEqual(equal_zone_merges([0,0,0]), 0)
        self.assertEqual(laser_cost_small([1,1,1], 2, 3, 2, 5), 5)


if __name__ == '__main__':
    unittest.main()
