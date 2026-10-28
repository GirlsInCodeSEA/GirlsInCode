import ast
from collections import Counter
import unittest
from unittest.mock import patch

import app as website
from scripts.import_march_questions import answer_columns


class MarchArchiveTests(unittest.TestCase):
    def setUp(self):
        self.client = website.app.test_client()
        self.questions = website.march_booklet_questions()

    def test_every_question_is_linked_and_readable_without_database(self):
        self.assertEqual(Counter(q['level'] for q in self.questions),
                         {'Beginner': 18, 'Intermediate': 11, 'Advanced': 8})
        with patch.object(website, 'supabase', None):
            archive = self.client.get('/2025m')
            self.assertEqual(archive.status_code, 200)
            for question in self.questions:
                path = f'/competitions/2025/march/questions/{question["level"].lower()}/{question["number"]}'
                with self.subTest(path=path):
                    self.assertIn(path.encode(), archive.data)
                    response = self.client.get(path)
                    self.assertEqual(response.status_code, 200)
                    self.assertIn(b'March 2025 questions', response.data)
                    self.assertIn(f'{question["source_file"]}#page={question["source_page"]}'.encode(), response.data)
                    self.assertNotIn(b'name="code_file"', response.data)

    def test_answer_mapping_covers_original_sheet_columns_without_loss(self):
        for level in ('Beginner', 'Intermediate', 'Advanced'):
            sheet = answer_columns(website.BASE_DIR / f'data/competition_questions/sources/2025-march/{level}.html')
            imported = {}
            for question in self.questions:
                if question['level'] == level:
                    for answer in question['answers']:
                        imported.setdefault(answer['source_header'], []).append(answer['output'])
            self.assertEqual(imported, {key: values for key, values in sheet.items() if values})
        self.assertEqual(sum(bool(q['answers']) for q in self.questions), 36)

    def test_multiline_alternative_and_case_answers_are_preserved(self):
        by_id = {(q['level'], q['number']): q for q in self.questions}
        self.assertEqual(by_id['Beginner', 4]['answers'][0]['output'],
                         'Sheryl Sandberg\nRadia Perlman\nKatherine Johnson\nGrace Hopper\nAda Lovelace')
        alternatives = by_id['Intermediate', 4]['answers']
        self.assertEqual(len(alternatives), 2)
        self.assertEqual(set(ast.literal_eval(alternatives[0]['output'])),
                         set(ast.literal_eval(alternatives[1]['output'])))
        cases = by_id['Advanced', 3]['answers']
        self.assertEqual([(a['label'], a['output']) for a in cases], [
            ('Case 1', '0\n695789\n295509'),
            ('Case 2', '381199206\n687926653\n826393766'),
        ])
        page = self.client.get('/competitions/2025/march/questions/advanced/3').data
        self.assertIn(b'<details class="booklet-answers">', page)
        self.assertIn(b'0\n695789\n295509', page)
        self.assertNotIn(b'<details class="booklet-answers" open', page)

    def test_original_numbering_and_cross_page_content_are_preserved(self):
        by_id = {(q['level'], q['number']): q for q in self.questions}
        self.assertEqual(by_id['Beginner', 6]['label'], 'Level 2 · Question 1')
        self.assertEqual(by_id['Beginner', 12]['label'], 'Level 3 · Question 1')
        self.assertTrue(by_id['Beginner', 3]['statement'].endswith('User enters: 3'))
        self.assertTrue(by_id['Beginner', 17]['statement'].endswith('Input 1:\n5'))
        self.assertTrue(by_id['Intermediate', 8]['statement'].endswith('n = 215'))
        self.assertNotIn('Question 7', by_id['Advanced', 6]['statement'])

    def test_withdrawn_question_has_no_invented_answer(self):
        withdrawn = [q for q in self.questions if q['status'] == 'withdrawn']
        self.assertEqual(len(withdrawn), 1)
        self.assertEqual((withdrawn[0]['level'], withdrawn[0]['source_level'], withdrawn[0]['source_number']),
                         ('Intermediate', 2, 5))
        self.assertEqual(withdrawn[0]['answers'], [])
        page = self.client.get('/competitions/2025/march/questions/intermediate/9').data
        self.assertIn(b'Withdrawn question', page)
        self.assertNotIn(b'Reveal supplied answer', page)

    def test_navigation_stays_in_march_and_invalid_questions_return_404(self):
        first = self.client.get('/competitions/2025/march/questions/beginner/1').data
        self.assertNotIn(b'Previous question', first)
        boundary = self.client.get('/competitions/2025/march/questions/beginner/18').data
        self.assertIn(b'/competitions/2025/march/questions/intermediate/1', boundary)
        self.assertNotIn(b'/competitions/2025/november/questions/', boundary)
        last = self.client.get('/competitions/2025/march/questions/advanced/8').data
        self.assertNotIn(b'Next question', last)
        for suffix in ('beginner/0', 'beginner/19', 'intermediate/12', 'advanced/9', 'unknown/1'):
            self.assertEqual(self.client.get('/competitions/2025/march/questions/' + suffix).status_code, 404)

    def test_original_pdf_downloads_work(self):
        for level in ('beginner', 'intermediate', 'advanced'):
            response = self.client.get(f'/static/documents/gic-march-2025-{level}.pdf')
            try:
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.data.startswith(b'%PDF'))
            finally:
                response.close()


if __name__ == '__main__':
    unittest.main()
