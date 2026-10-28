import io
from contextlib import closing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from werkzeug.test import EnvironBuilder

import app as website
from extract_all_features import extract_all_features


class Query:
    def __init__(self, db, table):
        self.db, self.table_name = db, table
        self.filters = []
        self.payload = None
        self.bounds = None

    def select(self, *_):
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def order(self, *_):
        return self

    def range(self, start, end):
        self.bounds = (start, end)
        return self

    def insert(self, payload):
        self.payload = payload
        return self

    def execute(self):
        if self.payload is not None:
            self.db.rows.setdefault(self.table_name, []).append(self.payload)
            return Mock(data=[self.payload])
        rows = [row for row in self.db.rows.get(self.table_name, [])
                if all(row.get(k) == v for k, v in self.filters)]
        if self.bounds is not None:
            start, end = self.bounds
            rows = rows[start:end + 1]
        return Mock(data=rows)


class Database:
    def __init__(self):
        self.rows = {
            'questions': [{'id': 1, 'title': 'Question 1', 'year': '2025 March',
                           'level': 'Beginner', 'points': 10, 'your_input': '42\n'}],
            'answers': [{'id': 1, 'answer_text': '42'}],
        }
        self.rpc = Mock(return_value=Mock(execute=Mock(return_value=Mock(data=True))))

    def table(self, name):
        return Query(self, name)


class AppTests(unittest.TestCase):
    def setUp(self):
        website.app.config.update(TESTING=True, SECRET_KEY='test-secret',
                                  ENABLE_UNSAFE_CODE_EXECUTION=False, CODE_TIMEOUT=5)
        self.client = website.app.test_client()
        self.db = Database()
        self.db_patch = patch.object(website, 'supabase', self.db)
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.model_patch = patch.object(website, 'model', None)
        self.model_patch.start()
        self.addCleanup(self.model_patch.stop)

    def post(self, path, data):
        with self.client.session_transaction() as session:
            session['_csrf_token'] = 'test-token'
        with closing(EnvironBuilder(path=path, method='POST', data={**data, 'csrf_token': 'test-token'})) as builder:
            environ = builder.get_environ()
            try:
                return self.client.open(environ)
            finally:
                environ['wsgi.input'].close()

    def login(self):
        with self.client.session_transaction() as session:
            session['user_email'] = 'test@example.com'
            session['user_name'] = 'Team'

    def upload(self, path='/question/1', source=b'print(42)', filename='code.py'):
        return self.post(path, {'code_file': (io.BytesIO(source), filename)})

    def test_all_pages_render(self):
        for path in ('/', '/contact', '/competitions', '/hackathon', '/fundraising', '/2023', '/2024',
                     '/2025m', '/2025n', '/signIn', '/question/1',
                     '/competitions/2025', '/competitions/2025/scoreboard',
                     '/hackathon/2025', '/hackathon/2025/scoreboard'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
        self.login()
        self.assertEqual(self.client.get('/submissions/1').status_code, 200)

    def test_november_route_is_unique(self):
        self.assertEqual(sum(rule.rule == '/2025n' for rule in website.app.url_map.iter_rules()), 1)

    def test_other_initiatives_archived_until_enabled(self):
        self.assertEqual(self.client.get('/other-initiatives').status_code, 404)
        home = self.client.get('/').data
        self.assertNotIn(b'href="/other-initiatives"', home)
        self.assertNotIn(b'class="home-initiatives"', home)
        with patch.dict(website.app.config, ENABLE_OTHER_INITIATIVES=True):
            self.assertEqual(self.client.get('/other-initiatives').status_code, 200)
            self.assertIn(b'href="/other-initiatives"', self.client.get('/').data)

    def test_all_november_booklet_questions_work_without_database(self):
        with patch.object(website, 'supabase', None):
            archive = self.client.get('/2025n').data
            for level in ('beginner', 'intermediate', 'advanced'):
                for number in range(1, 11):
                    path = f'/competitions/2025/november/questions/{level}/{number}'
                    with self.subTest(path=path):
                        self.assertIn(path.encode(), archive)
                        response = self.client.get(path)
                        self.assertEqual(response.status_code, 200)
                        self.assertIn(b'gic-november-2025-booklet.pdf#page=', response.data)
                        self.assertNotIn(b'name="code_file"', response.data)
            response = self.client.get('/static/documents/gic-november-2025-booklet.pdf')
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.data.startswith(b'%PDF'))
            response.close()

    def test_invalid_booklet_questions_are_404(self):
        for suffix in ('beginner/0', 'advanced/11', 'unknown/1'):
            self.assertEqual(self.client.get('/competitions/2025/november/questions/' + suffix).status_code, 404)

    def test_booklet_navigation_crosses_levels(self):
        first = self.client.get('/competitions/2025/november/questions/beginner/1').data
        self.assertNotIn(b'Previous question', first)
        boundary = self.client.get('/competitions/2025/november/questions/beginner/10').data
        self.assertIn(b'/competitions/2025/november/questions/intermediate/1', boundary)
        last = self.client.get('/competitions/2025/november/questions/advanced/10').data
        self.assertNotIn(b'Next question', last)

    def test_booklet_remains_available_when_database_connection_fails(self):
        self.db.rpc.reset_mock()
        with patch.object(self.db, 'table', side_effect=website.HTTPError('Connection failed')):
            with self.assertLogs(website.app.logger, level='WARNING'):
                response = self.client.get('/2025n')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'String Reversal', response.data)
        self.assertIn(b'practice questions are temporarily unavailable', response.data)

    def test_legacy_question_redirects(self):
        response = self.client.get('/beginner/q1')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith('/question/1'))

    def test_missing_question_is_404(self):
        self.assertEqual(self.client.get('/question/999').status_code, 404)
        self.login()
        self.assertEqual(self.client.get('/submissions/999').status_code, 404)

    def test_missing_database_does_not_break_static_pages(self):
        with patch.object(website, 'supabase', None):
            self.assertEqual(self.client.get('/').status_code, 200)
            self.assertEqual(self.client.get('/2025m').status_code, 200)

    def test_missing_answer_does_not_execute(self):
        self.db.rows['answers'] = []
        with patch.object(website, 'run_code') as runner:
            response = self.upload()
        self.assertIn(b'does not have an answer configured', response.data)
        runner.assert_not_called()

    def test_empty_or_wrong_file_rejected(self):
        for source, filename in ((b'', 'empty.py'), (b'print(42)', 'test.txt')):
            with patch.object(website, 'run_code') as runner:
                self.assertEqual(self.upload(source=source, filename=filename).status_code, 200)
            runner.assert_not_called()

    def test_missing_upload_has_feedback(self):
        self.assertIn(b'Please upload', self.post('/question/1', {}).data)

    def test_csrf_required(self):
        self.assertEqual(self.client.post('/signIn', data={}).status_code, 400)
        self.assertEqual(self.client.post('/question/1', data={}).status_code, 400)

    def test_unicode_csrf_token_rejected_without_crashing(self):
        with self.client.session_transaction() as session:
            session['_csrf_token'] = 'token'
        response = self.client.post('/signIn', data={'csrf_token': '你好'})
        self.assertEqual(response.status_code, 400)

    def test_award_failure_allows_retry(self):
        self.login()
        self.db.rpc.return_value.execute.side_effect = website.APIError({
            'code': 'PGRST202', 'message': 'Missing RPC', 'details': '', 'hint': '',
        })
        with patch.object(website, 'run_code', return_value=('42', None)):
            with self.assertLogs(website.app.logger, level='ERROR'):
                response = self.upload('/submissions/1')
        self.assertIn(b'score could not be saved', response.data)
        self.assertIn(b'name="code_file"', response.data)
        self.assertNotIn(b'Points awarded:', response.data)

    def test_actual_model_accepts_extracted_features(self):
        # Use the rebuilt artifact, not a mocked prediction.
        import pickle
        with (website.BASE_DIR / 'model.pkl').open('rb') as stream:
            classifier = pickle.load(stream)
        with patch.object(website, 'model', classifier):
            with patch.object(website, 'run_code', return_value=('42', None)):
                response = self.upload()
        self.assertNotIn(b'Unavailable', response.data)
        self.assertIn(b'Correct', response.data)

    def test_large_upload_rejected(self):
        response = self.upload(source=b'x' * (1024 * 1024 + 1))
        self.assertEqual(response.status_code, 413)

    def test_unknown_login_does_not_register(self):
        self.post('/signIn', {'action': 'login', 'email': 'new@example.com', 'password': 'password'})
        self.assertFalse(self.db.rows.get('users'))
        with self.client.session_transaction() as session:
            self.assertNotIn('user_email', session)

    def test_registration_requires_team_name(self):
        self.post('/signIn', {'action': 'register', 'name': ' ', 'email': 'a@b.com', 'password': 'pw'})
        self.assertFalse(self.db.rows.get('users'))

    def test_register_normalizes_email_and_hashes_password(self):
        self.post('/signIn', {'action': 'register', 'name': ' Team ',
                             'email': ' Test@Example.com ', 'password': 'password'})
        user = self.db.rows['users'][0]
        self.assertEqual(user['name'], 'Team')
        self.assertEqual(user['email'], 'test@example.com')
        self.assertTrue(website.argon2.verify('password', user['password_hash']))
        with self.client.session_transaction() as session:
            self.assertEqual(session['user_name'], 'Team')

    def test_login_and_wrong_password(self):
        self.db.rows['users'] = [{'name': 'Team', 'email': 'test@example.com',
                                  'password_hash': website.argon2.hash('right')}]
        for password, expected in [('wrong', False), ('right', True)]:
            self.post('/signIn', {'action': 'login', 'email': 'test@example.com', 'password': password})
            with self.client.session_transaction() as session:
                self.assertEqual(bool(session.get('user_email')), expected)

    def test_register_existing_email_does_not_log_in(self):
        self.db.rows['users'] = [{'email': 'test@example.com', 'name': 'Team'}]
        self.post('/signIn', {'action': 'register', 'name': 'Other',
                             'email': 'test@example.com', 'password': 'pw'})
        self.assertEqual(len(self.db.rows['users']), 1)
        with self.client.session_transaction() as session:
            self.assertNotIn('user_email', session)

    def test_register_existing_team_rejected(self):
        self.db.rows['users'] = [{'email': 'a@example.com', 'name': 'Team'}]
        self.post('/signIn', {'action': 'register', 'name': 'Team',
                             'email': 'b@example.com', 'password': 'pw'})
        self.assertEqual(len(self.db.rows['users']), 1)

    def test_missing_classifier_is_nonfatal(self):
        with patch.object(website, 'run_code', return_value=('42\n', None)) as runner:
            response = self.upload()
        self.assertIn(b'Correct', response.data)
        self.assertEqual(runner.call_args.args[1], '42\n')

    def test_error_prefixed_output_can_be_correct(self):
        self.db.rows['answers'][0]['answer_text'] = 'Error is a valid answer'
        with patch.object(website, 'run_code', return_value=('Error is a valid answer', None)):
            self.assertIn(b'<h2>Correct</h2>', self.upload().data)

    def test_unsuccessful_program_never_scores(self):
        self.login()
        with patch.object(website, 'run_code', return_value=('42', 'Error running code')):
            self.upload('/submissions/1')
        self.db.rpc.assert_not_called()

    def test_submission_requires_login(self):
        response = self.client.get('/submissions/1')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith('/signIn'))

    def test_success_uses_atomic_award(self):
        self.login()
        with patch.object(website, 'run_code', return_value=('42', None)):
            response = self.upload('/submissions/1')
        self.db.rpc.assert_called_once_with('award_submission', {
            'p_team_name': 'Team', 'p_email': 'test@example.com', 'p_question_id': 1})
        self.assertIn(b'Points awarded: 10', response.data)
        self.assertNotIn(b'name="code_file"', response.data)

    def test_concurrent_winner_does_not_award_again(self):
        self.login()
        self.db.rpc.return_value.execute.return_value.data = False
        with patch.object(website, 'run_code', return_value=('42', None)):
            response = self.upload('/submissions/1')
        self.assertIn(b'Already solved', response.data)
        self.assertNotIn(b'Points awarded:', response.data)

    def test_existing_lock_does_not_execute(self):
        self.login()
        self.db.rows['submissions_lock'] = [{'team_name': 'Team', 'question_id': 1, 'solved': True}]
        with patch.object(website, 'run_code') as runner:
            response = self.upload('/submissions/1')
        runner.assert_not_called()
        self.assertIn(b'Already solved', response.data)

    def test_leaderboard_paginates_and_handles_null_score(self):
        self.db.rows['scores'] = [{'team_name': 'Team', 'score': 1} for _ in range(1001)]
        self.db.rows['scores'].append({'team_name': 'Other', 'score': None})
        self.assertEqual(self.client.get('/api/leaderboard').json,
                         [{'team': 'Team', 'score': 1001}, {'team': 'Other', 'score': 0}])

    def test_competition_results_are_archived_not_live(self):
        with patch.object(website, 'supabase', None):
            response = self.client.get('/competitions/2025/scoreboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'November 2025', response.data)
        self.assertIn(b'Yashvi/Melissa', response.data)
        self.assertNotIn(b'/api/leaderboard', response.data)
        self.assertNotIn(b'AUTO-REFRESH', response.data)

    def test_old_scoreboard_link_redirects_to_competition_archive(self):
        response = self.client.get('/scoreboard')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith('/competitions/2025/scoreboard'))

    def test_scoreboards_are_linked_from_their_years(self):
        competition = self.client.get('/competitions/2025').data
        hackathon = self.client.get('/hackathon/2025').data
        self.assertIn(b'href="/competitions/2025/scoreboard"', competition)
        self.assertNotIn(b'href="/hackathon/2025/scoreboard"', competition)
        self.assertIn(b'href="/hackathon/2025/scoreboard"', hackathon)
        self.assertNotIn(b'href="/competitions/2025/scoreboard"', hackathon)
        for path in ('/', '/competitions', '/hackathon', '/2023', '/2024'):
            with self.subTest(path=path):
                self.assertNotIn(b'/scoreboard', self.client.get(path).data)

    def test_scoreboards_only_exist_for_2025(self):
        for event in ('competitions', 'hackathon'):
            for year in (2023, 2024, 2026):
                with self.subTest(event=event, year=year):
                    self.assertEqual(self.client.get(f'/{event}/{year}/scoreboard').status_code, 404)

    def test_hackathon_is_completed_2025_archive_with_pending_results(self):
        archive = self.client.get('/hackathon/2025').data
        self.assertIn(b'Held in 2025', archive)
        self.assertIn(b'COMPLETED', archive)
        self.assertNotIn(b'2026', archive)
        scoreboard = self.client.get('/hackathon/2025/scoreboard').data
        self.assertIn(b'Results to be added.', scoreboard)
        self.assertNotIn(b'<table', scoreboard)
        self.assertNotIn(b'Yashvi/Melissa', scoreboard)


class RunnerTests(unittest.TestCase):
    def run_source(self, source, input_text=''):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.py'
            path.write_text(source)
            return website.run_code(path, input_text)

    def test_execution_disabled_by_default(self):
        with patch.dict(website.app.config, ENABLE_UNSAFE_CODE_EXECUTION=False):
            output, error = self.run_source('raise RuntimeError()')
        self.assertEqual(output, '')
        self.assertIn('unavailable', error)

    def test_stdin_and_success(self):
        with patch.dict(website.app.config, ENABLE_UNSAFE_CODE_EXECUTION=True):
            self.assertEqual(self.run_source('print(input())', '42\n'), ('42\n', None))

    def test_runtime_error(self):
        with patch.dict(website.app.config, ENABLE_UNSAFE_CODE_EXECUTION=True):
            _, error = self.run_source('raise ValueError("bad input")')
        self.assertIn('ValueError', error)

    def test_timeout(self):
        with patch.dict(website.app.config, ENABLE_UNSAFE_CODE_EXECUTION=True, CODE_TIMEOUT=0.1):
            _, error = self.run_source('while True: pass')
        self.assertIn('too long', error)

    def test_secrets_not_inherited(self):
        with patch.dict(website.app.config, ENABLE_UNSAFE_CODE_EXECUTION=True):
            with patch.dict('os.environ', SUPABASE_SERVICE_KEY='must-not-leak'):
                output, error = self.run_source('import os; print(os.getenv("SUPABASE_SERVICE_KEY"))')
        self.assertEqual(output, 'None\n')
        self.assertIsNone(error)


class FeatureTests(unittest.TestCase):
    def extract(self, source):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sample.py'
            path.write_text(source)
            return extract_all_features(path)

    def test_empty_file(self):
        self.assertEqual(self.extract('')['comment_density'], 0)

    def test_nested_function_body_visited(self):
        features = self.extract('def f():\n    x = []\n    for i in range(2):\n        x.append(i)\n')
        self.assertEqual(features['for_loop_count'], 1)
        self.assertEqual(features['assignment_count'], 1)
        self.assertEqual(features['for_loops_with_append'], 1)

    def test_async_function_body_visited(self):
        features = self.extract('async def f():\n    while False:\n        pass\n    else:\n        pass\n')
        self.assertTrue(features['function'])
        self.assertEqual(features['while_loop_count'], 1)
        self.assertEqual(features['else_in_loop'], 1)

    def test_append_counts_loops_not_calls(self):
        features = self.extract('for x in []:\n    a.append(x)\n    a.append(x)\n')
        self.assertEqual(features['for_loops_with_append'], 1)

    def test_import_does_not_rebuild_dataset(self):
        import importlib
        import extract_all_features as extractor
        with patch.object(extractor.os, 'listdir', side_effect=AssertionError('Import read samples')):
            importlib.reload(extractor)


if __name__ == '__main__':
    unittest.main()
