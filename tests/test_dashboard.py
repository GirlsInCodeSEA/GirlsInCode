import io
from contextlib import closing
from datetime import datetime, timezone
import unittest
from unittest.mock import Mock, patch

from werkzeug.test import EnvironBuilder

import app as website
import competition
from test_app import Database

BEFORE = datetime(2026, 11, 27, 12, tzinfo=timezone.utc)
LIVE = datetime(2026, 11, 28, 3, tzinfo=timezone.utc)      # 11:00 in Malaysia
ENDED = datetime(2026, 11, 29, 12, tzinfo=timezone.utc)


class DashboardTests(unittest.TestCase):
    def setUp(self):
        website.app.config.update(TESTING=True, SECRET_KEY='test-secret', DASHBOARD_LOCKDOWN=True,
                                  ADMIN_EMAILS={'admin@example.com'})
        self.addCleanup(website.app.config.update, DASHBOARD_LOCKDOWN=False, ADMIN_EMAILS=set())
        self.client = website.app.test_client()
        self.db = Database()
        self.db.rows.update({
            'competition_questions_2026': [
                {'id': 'B1', 'competition': '2026', 'position': 1, 'level': 'Beginner', 'theme': 'Global warming',
                 'title': 'Climate Bulletin', 'points': 10, 'statement': 'Count vowels.', 'question_input': 'aeiou'},
                {'id': 'B2', 'competition': '2026', 'position': 2, 'level': 'Beginner', 'theme': 'Global warming',
                 'title': 'Second Secret', 'points': 10, 'statement': 'Two.', 'question_input': 'x'},
            ],
            'competition_answers_2026': [{'question_id': 'B1', 'answer': '5'}],
        })
        self.db.rpc = Mock(return_value=Mock(execute=Mock(return_value=Mock(data=10))))
        for target, value in ((website, 'supabase'), (website, 'model')):
            patcher = patch.object(target, value, self.db if value == 'supabase' else None)
            patcher.start()
            self.addCleanup(patcher.stop)

    def at(self, moment):
        patcher = patch.object(competition, 'now', return_value=moment)
        patcher.start()
        self.addCleanup(patcher.stop)

    def login(self, email='team@example.com', name='Team'):
        with self.client.session_transaction() as session:
            session['user_email'], session['user_name'] = email, name

    def submit(self, question='B1', output='5', code=b'print(5)', filename='solution.py'):
        with self.client.session_transaction() as session:
            session['_csrf_token'] = 'token'
        data = {'csrf_token': 'token', 'output': output}
        if code is not None:
            data['code_file'] = (io.BytesIO(code), filename)
        with closing(EnvironBuilder(path=f'/dashboard/{question}', method='POST', data=data)) as builder:
            environ = builder.get_environ()
            try:
                return self.client.open(environ)
            finally:
                environ['wsgi.input'].close()

    def test_signed_in_users_only_see_the_dashboard(self):
        self.at(BEFORE)
        self.login()
        for path in ('/', '/competitions', '/signIn', '/competitions/2026', '/question/1'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.headers['Location'].endswith('/dashboard'))
        self.assertEqual(self.client.get('/dashboard').status_code, 200)
        self.assertEqual(self.client.get('/logout').status_code, 302)
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_dashboard_requires_sign_in(self):
        response = self.client.get('/dashboard')
        self.assertTrue(response.headers['Location'].endswith('/signIn'))

    def test_login_lands_on_dashboard(self):
        self.db.rows['users'] = [{'name': 'Team', 'email': 'team@example.com',
                                  'password_hash': website.argon2.hash('pw')}]
        with self.client.session_transaction() as session:
            session['_csrf_token'] = 'token'
        response = self.client.post('/signIn', data={'csrf_token': 'token', 'action': 'login',
                                                     'email': 'team@example.com', 'password': 'pw'})
        self.assertTrue(response.headers['Location'].endswith('/dashboard'))

    def test_before_start_questions_stay_hidden(self):
        self.at(BEFORE)
        self.login()
        page = self.client.get('/dashboard').data
        self.assertIn(b'Starts in', page)
        self.assertIn(b'Saturday 28 November 2026', page)
        self.assertIn(b'09:00', page)
        self.assertNotIn(b'Climate Bulletin', page)
        self.assertNotIn(b'/dashboard/B1', page)
        response = self.client.get('/dashboard/B1')
        self.assertTrue(response.headers['Location'].endswith('/dashboard'))
        self.submit()
        self.db.rpc.assert_not_called()

    def test_live_dashboard_lists_questions_and_scoreboard(self):
        self.at(LIVE)
        self.login()
        self.db.rows['competition_solves_2026'] = [
            {'team_name': 'Team', 'question_id': 'B1', 'points': 10, 'solved_at': '2026-11-28T03:10:00+00:00'},
            {'team_name': 'Rivals', 'question_id': 'B1', 'points': 10, 'solved_at': '2026-11-28T03:05:00+00:00'},
        ]
        page = self.client.get('/dashboard').data
        self.assertIn(b'Climate Bulletin', page)
        self.assertIn(b'/dashboard/B1', page)
        self.assertLess(page.index(b'Rivals'), page.index(b'<span class="tag">you</span>'))
        question = self.client.get('/dashboard/B1').data
        self.assertIn(b'Count vowels.', question)
        self.assertIn(b'aeiou', question)
        self.assertNotIn(b'>5<', question)

    def test_correct_submission_is_recorded_with_code(self):
        self.at(LIVE)
        self.login()
        response = self.submit(output='  5\r\n')
        self.assertEqual(response.status_code, 302)
        args = self.db.rpc.call_args.args
        self.assertEqual(args[0], 'record_competition_submission_2026')
        self.assertEqual(args[1]['p_team_name'], 'Team')
        self.assertEqual(args[1]['p_question_id'], 'B1')
        self.assertEqual(args[1]['p_code'], 'print(5)')
        self.assertEqual(args[1]['p_code_filename'], 'solution.py')
        self.assertIs(args[1]['p_correct'], True)
        self.assertIn(b'+10 points', self.client.get('/dashboard/B1').data)

    def test_wrong_submission_is_still_recorded(self):
        self.at(LIVE)
        self.login()
        self.submit(output='6')
        self.assertIs(self.db.rpc.call_args.args[1]['p_correct'], False)

    def test_submission_needs_output_and_code(self):
        self.at(LIVE)
        self.login()
        self.submit(code=None)
        self.submit(output=' ')
        self.submit(filename='notes.txt')
        self.submit(code=b'')
        self.db.rpc.assert_not_called()

    def test_solved_question_cannot_be_resubmitted(self):
        self.at(LIVE)
        self.login()
        self.db.rows['competition_solves_2026'] = [{'team_name': 'Team', 'question_id': 'B1', 'points': 10}]
        self.submit()
        self.db.rpc.assert_not_called()

    def test_submissions_close_at_the_end(self):
        self.at(ENDED)
        self.login()
        self.assertIn(b'Final standings', self.client.get('/dashboard').data)
        self.submit()
        self.db.rpc.assert_not_called()

    def test_unknown_question_is_404(self):
        self.at(LIVE)
        self.login()
        self.assertEqual(self.client.get('/dashboard/Z9').status_code, 404)

    def test_admin_page_is_limited_to_admins(self):
        self.at(LIVE)
        self.db.rows['competition_submissions_2026'] = [
            {'id': 1, 'created_at': '2026-11-28T03:01:00+00:00', 'team_name': 'Team', 'email': 'team@example.com',
             'question_id': 'B1', 'output': '5', 'code': 'print("secret code")', 'code_filename': 'a.py',
             'classification': None, 'correct': True, 'points_awarded': 10}]
        self.login()
        self.assertEqual(self.client.get('/admin/submissions').status_code, 404)
        self.login('admin@example.com', 'Organisers')
        page = self.client.get('/admin/submissions').data
        self.assertIn(b'print(&#34;secret code&#34;)', page)


class CompetitionHelperTests(unittest.TestCase):
    def test_output_comparison_ignores_whitespace_only(self):
        self.assertTrue(competition.is_correct(' 29  16\n', '29 16'))
        self.assertTrue(competition.is_correct('a\r\nb', 'a\nb'))
        self.assertFalse(competition.is_correct('hana 8.72', 'Hana 8.72'))
        self.assertFalse(competition.is_correct('', ''))
        self.assertFalse(competition.is_correct('5', None))

    def test_rank_breaks_ties_by_earliest_finish(self):
        board = competition.rank([
            {'team_name': 'Late', 'points': 10, 'solved_at': '2026-11-28T05:00:00'},
            {'team_name': 'Early', 'points': 10, 'solved_at': '2026-11-28T04:00:00'},
            {'team_name': 'Top', 'points': 15, 'solved_at': '2026-11-28T06:00:00'},
            {'team_name': 'Top', 'points': 10, 'solved_at': '2026-11-28T03:00:00'},
        ])
        self.assertEqual([(t['team'], t['score'], t['rank']) for t in board],
                         [('Top', 25, 1), ('Early', 10, 2), ('Late', 10, 3)])

    def test_phase(self):
        start, end = competition.parse_time('2026-11-28T09:00'), competition.parse_time('2026-11-28T17:00')
        self.assertEqual(start.utcoffset().total_seconds(), 8 * 3600)
        self.assertEqual(competition.phase(start, end, BEFORE), 'before')
        self.assertEqual(competition.phase(start, end, LIVE), 'live')
        self.assertEqual(competition.phase(start, end, ENDED), 'ended')


if __name__ == '__main__':
    unittest.main()
