"""Import the supplied March PDFs and HTML answer sheets (requires pypdf)."""

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil


class AnswerTable(HTMLParser):
    """Read spreadsheet cells as text, including multiline and alternative answers."""

    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = []
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.row = []
        elif tag == 'td':
            self.cell = ''
        elif tag == 'br' and self.cell is not None:
            self.cell += '\n'

    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data

    def handle_endtag(self, tag):
        if tag == 'td':
            self.row.append(self.cell)
            self.cell = None
        elif tag == 'tr' and self.row:
            self.rows.append(self.row)


def answer_columns(path):
    table = AnswerTable()
    table.feed(path.read_text(encoding='utf-8'))
    headers, *rows = table.rows
    if any(len(row) != len(headers) for row in rows):
        raise ValueError(f'Inconsistent answer table width: {path}')
    return {header.strip(): [row[i] for row in rows if row[i].strip() not in ('', 'or')]
            for i, header in enumerate(headers)}


def extract_questions(reader, category):
    questions = []
    current = None
    lines = []
    stage = None

    def finish():
        if current:
            current['statement'] = '\n'.join(lines).strip()
            questions.append(current)

    for page_number, page in enumerate(reader.pages, 1):
        text = page.extract_text(extraction_mode='layout', layout_mode_space_vertically=False)
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line in ('Submit your answers on this form', f'{category} Questions'):
                continue
            stage_match = re.match(r'^Level (\d+)', line)
            if stage_match:
                finish()
                current, lines = None, []
                stage = int(stage_match[1])
                continue
            if category == 'Beginner':
                match = re.match(r'^ {0,3}(\d+)(?:\s{2,}(.*))?$', raw_line)
            else:
                match = re.match(r'^Question (\d+)(.*)$', line)
            if match:
                finish()
                source_number = int(match[1])
                label = f'Level {stage} · Question {source_number}' if stage else f'Question {source_number}'
                current = {
                    'number': len(questions) + 1,
                    'level': category,
                    'source_level': stage,
                    'source_number': source_number,
                    'title': label,
                    'label': label,
                    'source_page': page_number,
                    'source_file': f'documents/gic-march-2025-{category.lower()}.pdf',
                    'status': 'withdrawn' if category == 'Intermediate' and stage == 2 and source_number == 5 else 'archived',
                }
                lines = []
                if category == 'Beginner':
                    lines.append('Give your answer in the same format as the sample output.' if stage == 1
                                 else 'Give only the answer and no other words.')
                    if match[2]:
                        lines.append(match[2].strip())
                elif current['status'] == 'withdrawn':
                    lines.append('Withdrawn in the original booklet: “Please skip this question as there is a mistake.”')
            elif current:
                # Unmapped PDF glyphs are visibly marked; original notation remains in the PDF.
                lines.append(line.replace('\x00', '�'))
    finish()
    return questions


def import_archive(pdf_directory, answer_directory, root):
    from pypdf import PdfReader

    records = []
    data_directory = root / 'data/competition_questions'
    source_directory = data_directory / 'sources/2025-march'
    document_directory = root / 'static/documents'
    for directory in (source_directory, document_directory):
        directory.mkdir(parents=True, exist_ok=True)
    for category, count in (('Beginner', 18), ('Intermediate', 11), ('Advanced', 8)):
        pdf = pdf_directory / f'GIC 2025 {category} Questions.pdf'
        html = answer_directory / f'{category}.html'
        questions = extract_questions(PdfReader(pdf), category)
        columns = answer_columns(html)
        used = set()
        if len(questions) != count:
            raise ValueError(f'{category}: expected {count} questions, found {len(questions)}')
        for question in questions:
            n, stage = question['source_number'], question['source_level']
            headers = [f'Q{n} Output (Case {case})' for case in (1, 2)] if category == 'Advanced' else [f'L{stage} Q{n} Output']
            question['answers'] = []
            for header in headers:
                used.add(header)
                outputs = columns[header]
                if not outputs and question['status'] != 'withdrawn':
                    raise ValueError(f'Missing answer: {category} {header}')
                for i, output in enumerate(outputs):
                    label = header.split('(')[1].rstrip(')') if category == 'Advanced' else ('Alternative output' if i else 'Expected output')
                    question['answers'].append({'label': label, 'output': output, 'source_header': header})
            if not question['statement']:
                raise ValueError(f'Empty question: {category} {n}')
        if used != set(columns):
            raise ValueError(f'Unmatched answer columns: {set(columns) - used}')
        records.extend(questions)
        shutil.copyfile(pdf, document_directory / f'gic-march-2025-{category.lower()}.pdf')
        shutil.copyfile(html, source_directory / html.name)
    (data_directory / '2025-march.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Imported {len(records)} questions; {sum(bool(q["answers"]) for q in records)} have supplied answers.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf_directory', type=Path)
    parser.add_argument('answer_directory', type=Path)
    args = parser.parse_args()
    import_archive(args.pdf_directory, args.answer_directory, Path(__file__).resolve().parents[1])
