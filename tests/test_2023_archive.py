import json
import re
import unittest
from unittest.mock import patch

import app as website


class Archive2023Tests(unittest.TestCase):
    def setUp(self):
        self.client = website.app.test_client()
        self.questions = website.questions_2023()

    def test_all_questions_are_linked_and_render_without_database(self):
        self.assertEqual(len(self.questions), 36)
        self.assertEqual([q['number'] for q in self.questions], list(range(1, 37)))
        with patch.object(website, 'supabase', None):
            archive = self.client.get('/2023')
            self.assertEqual(archive.status_code, 200)
            for question in self.questions:
                path = f'/competitions/2023/questions/{question["number"]}'
                with self.subTest(path=path):
                    self.assertIn(path.encode(), archive.data)
                    response = self.client.get(path)
                    self.assertEqual(response.status_code, 200)
                    self.assertIn(question['author'].encode(), response.data)
                    self.assertNotIn(b'name="code_file"', response.data)
                    self.assertNotIn(b'[[CODE]]', response.data)

    def test_original_text_and_image_transcripts_are_retained(self):
        source = website.BASE_DIR / 'data/competition_questions/sources/2023'
        slides = {s['page']: s['text'] for s in json.loads((source / 'slides.json').read_text())}
        images = json.loads((source / 'image-transcripts.json').read_text())
        normalise = lambda text: re.sub(r'\s+', '', text.replace('\u200b', ''))
        for question in self.questions:
            text = '\n'.join(block.get('text', block.get('url', '')) for block in question['blocks'])
            for page in question['source_pages']:
                original = re.sub(r'(Beginner|Intermediate|Advanced) [12] by [^\n]+', '', slides[page])
                if page == 48:
                    original = original.split('\n\nStarter\n\nCode\n\non\n\nNext\n\nSlide ->')[0]
                for paragraph in original.split('\n\n'):
                    with self.subTest(question=question['number'], paragraph=paragraph[:60]):
                        self.assertIn(normalise(paragraph), normalise(text))
                for transcript in images.get(str(page), {}).values():
                    self.assertIn(transcript, text)
        self.assertIn('track = [["Daydreaming by Harry Styles"]',
                      '\n'.join(b.get('text', '') for b in self.questions[7]['blocks']))
        self.assertEqual(self.questions[29]['source_pages'], [48, 49])

    def test_recovered_inputs_and_missing_inputs_are_distinguished(self):
        recovered, unavailable = [], []
        for question in self.questions:
            page = self.client.get(f'/competitions/2023/questions/{question["number"]}').data
            for block in question['blocks']:
                if block.get('local_file'):
                    recovered.append(question['number'])
                    path = '/static/' + block['local_file']
                    self.assertIn(path.encode(), page)
                    with self.client.get(path) as response:
                        self.assertEqual(response.status_code, 200)
                        self.assertGreater(len(response.data), 100)
                        self.assertNotIn(b'<html', response.data.lower())
                if block.get('unavailable'):
                    unavailable.append(question['number'])
                    self.assertIn(b'The original input file could not be recovered', page)
        self.assertEqual(recovered, [24, 27, 28])
        self.assertEqual(unavailable, [6, 11])

    def test_navigation_and_invalid_numbers(self):
        first = self.client.get('/competitions/2023/questions/1').data
        last = self.client.get('/competitions/2023/questions/36').data
        self.assertNotIn(b'Previous question', first)
        self.assertNotIn(b'Next question', last)
        self.assertIn(b'/competitions/2023/questions/2', first)
        self.assertIn(b'/competitions/2023/questions/35', last)
        for number in (0, 37, 999):
            self.assertEqual(self.client.get(f'/competitions/2023/questions/{number}').status_code, 404)


if __name__ == '__main__':
    unittest.main()
