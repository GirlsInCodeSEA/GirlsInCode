"""Build the 2023 archive from captured slide text and verified image transcripts."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/competition_questions/sources/2023'
DECK = 'https://www.canva.com/design/DAFcblycHmM/Tz8z3c5wRGYUCG4fGsy6YA/view'
GROUPS = [
    ('Instagram', 'Finnick', 15, ['Restaurant reviews', 'Personalised feed', 'Password generator', 'Food account ratios', 'Post interactions', 'Engagement rankings']),
    ('Spotify', 'Vignesh', 22, ['Song queue', 'Shuffle play', 'Mood playlist', 'Unique playlists', 'Spotify Wrapped', 'Music player interface']),
    ('TikTok', 'Sofea', 29, ['Playback speed', 'Password validation', 'Wellness feed', 'Video engagement', 'Video predictions', 'Personalised recommendations']),
    ('Grab', 'Tristan', 36, ['Airport pickup', 'Driver confirmation', 'Restaurant categories', 'Driver earnings', 'Distance and fares', 'Cuisine finder']),
    ('Netflix', 'Charlotte', 43, ['Horse riding watchlist', 'Viewing queue', 'Movie search', 'Surprise me', 'Movie marathon', 'Viewing recommendations']),
    ('Shopee', 'Valerie', 51, ['Shopping cart', 'Anonymous reviews', 'Package tracking', 'Delivery order', 'Lowest price', 'Compare sellers']),
]
# Boundaries of code/data blocks within the original slide text.
CODE_RANGES = {
    19: ('posts =', 'Use these arrays'),
    23: ('import random', 'Example of output'),
    24: ('songs =', None), 25: ('playlist1 =', None),
    27: ('import tkinter', None), 31: ('Videos =', 'Output should'),
    32: ('"LUCL', 'Print the number'),
    33: ('Videos :', None), 34: ('posts =', None),
    38: ('grab =', None), 47: ('My_list =', None),
    53: ('Array1 =', None), 54: ('list =', 'Use the bubble sort'),
    56: ('xm13 =', None),
}
INPUT_FILES = {
    20: ('Instagram posts CSV', None),
    26: ('Spotify listening history', None),
    41: ('Grab restaurants and cuisines', 'documents/2023/grab-restaurants.txt'),
    45: ('Movie search input', 'documents/2023/netflix-search.txt'),
    46: ('Surprise me movie list', 'documents/2023/netflix-surprise.txt'),
}


def build_questions():
    slides = {s['page']: s['text'] for s in json.loads((SOURCE / 'slides.json').read_text())}
    images = json.loads((SOURCE / 'image-transcripts.json').read_text())
    questions = []
    for theme, character, first_page, titles in GROUPS:
        for offset, title in enumerate(titles):
            page = first_page + offset
            text = slides[page].replace('\u200b', '')
            heading = re.search(r'(Beginner|Intermediate|Advanced) ([12]) by ([^\n]+)', text)
            if heading is None:
                raise ValueError(f'Missing question heading on slide {page}')
            source_label, author = heading.group(1) + ' ' + heading.group(2), heading.group(3)
            text = (text[:heading.start()] + text[heading.end():]).strip()
            text = re.sub(r'\n{3,}', '\n\n', text)
            if page == 48:
                text = text.split('\n\nStarter\n\nCode\n\non\n\nNext\n\nSlide ->')[0]
            if page == 15:
                text = text.removesuffix('\n\n???')
            blocks = []
            code_parts = CODE_RANGES.get(page)
            code = None
            if code_parts:
                start, end = code_parts
                index = re.search(r'(?m)^' + re.escape(start), text).start()
                end_index = text.index(end, index) if end else len(text)
                code = text[index:end_index].strip().replace('\n\n', '\n')
                text = text[:index] + '[[CODE]]\n\n' + text[end_index:]
            supplement = images.get(str(page), {})
            for paragraph in text.split('\n\n'):
                paragraph = paragraph.strip()
                if not paragraph:
                    continue
                if paragraph == '[[CODE]]':
                    blocks.append({'type': 'code', 'text': code})
                    continue
                if page == 22 and paragraph.startswith('The output should'):
                    blocks.extend([{'type': 'paragraph', 'text': 'Use the following code as a starting point:'},
                                   {'type': 'code', 'text': supplement['starter']}])
                if paragraph.startswith('https://'):
                    block = {'type': 'link', 'url': paragraph}
                    if page in INPUT_FILES:
                        label, local_file = INPUT_FILES[page]
                        block.update(label=label, local_file=local_file, unavailable=local_file is None)
                    else:
                        block['label'] = 'Original reference link'
                    blocks.append(block)
                else:
                    blocks.append({'type': 'paragraph', 'text': paragraph})
                if 'output' in supplement and any(paragraph.startswith(prefix) for prefix in (
                    'The final output should', 'The output should', 'Example of output',
                    'The correct output is', 'Output should look',
                )):
                    blocks.append({'type': 'code', 'text': supplement['output']})
            source_pages = [page]
            if page == 48:
                source_pages.append(49)
                blocks.extend([{'type': 'paragraph', 'text': 'Starter code:'},
                               {'type': 'code', 'text': images['49']['starter']}])
            questions.append({
                'number': len(questions) + 1, 'title': title, 'theme': theme,
                'character': character, 'author': author, 'source_label': source_label,
                'source_pages': source_pages, 'source_url': DECK, 'blocks': blocks,
            })
    assert len(questions) == 36
    return questions


if __name__ == '__main__':
    output = ROOT / 'data/competition_questions/2023.json'
    output.write_text(json.dumps(build_questions(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Saved 36 questions to {output}')
