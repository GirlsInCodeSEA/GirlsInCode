# Competition question archive

`2023.json` contains all 36 questions from the official [GIC 2023 Behind the Screens Canva presentation](https://www.canva.com/design/DAFcblycHmM/Tz8z3c5wRGYUCG4fGsy6YA/view), recovered on 28 October 2026. The archive groups the questions by their six app themes and numbers them 1–36. Original author credits, difficulty labels, and slide numbers remain in the data; difficulty categories are not used for navigation. The short descriptive titles are editorial additions.

`sources/2023/slides.json` preserves the original accessible slide text. `sources/2023/image-transcripts.json` contains the manually checked starter code and sample outputs from image elements on slides 15, 22, 23, 26, 29, 31, and 49. The Netflix recommendation question spans slides 48–49 and is one question. Its wrapped code lines have been joined while preserving indentation. Original wording, inputs, and samples are retained, including inconsistencies such as Kanpachi/Kampachi in the restaurant-review question. Only whitespace, zero-width characters, heading placement, and the obsolete “next slide” direction are normalised. The website does not embed the slide illustrations or run participant code. Output practice checks are documented in [PRACTICE.md](PRACTICE.md).

Three original datasets are preserved under `static/documents/2023/`: the restaurant/cuisine list from Drive file `1HqdAe1InVlW00i3IMCNKwa6eAKOgUpr1` (originally named `restaurant_list.py`, read only as text and saved as `.txt`), the movie search list from `1jCT7W5Z0YqSRaF-sj8T-HR_G_OP2Wk0k`, and the surprise-movie list from `1eebscVivfUrpdifCPJU7u5IP32tnbS6V`. The Instagram posts spreadsheet returned HTTP 410, and the Spotify listening-history download returned HTTP 404 when checked. Questions 6 and 11 retain the original links and explicitly state that their required input files could not be recovered. The archived records preserve these missing-file notices. Separate, explicitly labelled practice cases now provide small new datasets when needed; they are not represented as recovered original inputs. Other historic service/library instructions and source ambiguities are retained as archival material, not independently validated as current guidance or suitable grading fixtures.

Regenerate the 2023 data without network access or extra dependencies with `python3 scripts/import_2023_questions.py`. Run `python3 -m unittest tests.test_2023_archive` to check text coverage, image transcriptions, recovered input files, links, and navigation.

`2024.json` contains the five questions from the user-supplied `GIC Futuristc Festival 2024 Questions - Intermediate (Moon) Level Solutions - Aashutosh.pdf`, pages 4, 6, 8, 10, and 12. The 2024 page presents them together as Questions 1–5, without difficulty categories, illustrations, hints, or solution slides, as requested. Starting values, the temperature sample and starter code, and both fuel scenarios are preserved.

The duplicated paragraph in Question 4 is included once. Question 3's leading-zero binary value is displayed as a sample input rather than the source's invalid Python integer assignment; its digits are unchanged. Other question wording is retained with line wrapping normalised. The supplied PDF remains the source of record. Its solution slides now inform the separate output practice checks; no database question records were changed.

`2025-november.json` contains all 30 questions (10 per level) transcribed from the official November 2025 booklet. Each record keeps its original level, question number, title and PDF page. Advanced questions have no titles in the source, so retain “Question 1” through “Question 10”.

Source: https://drive.google.com/file/d/1tdHyqWyWvIr87oqLqZU1A3aQx3lpMVW9/view

The original 50-page PDF is preserved at `static/documents/gic-november-2025-booklet.pdf`. Its final page credits Emily Xu and permits sharing for non-commercial educational use with attribution. Question author credits also appear in the booklet and event archive.

These archive pages now support output practice checks, without creating scored database records. Existing database-backed practice links remain available separately. November has independently worked answers; March retains the supplied HTML keys alongside reviewed checks. No point awards or executable submissions were added for booklet pages.

PDF text extraction does not preserve all mathematical typography, and the printed source itself contains inconsistencies (including stated array/string lengths and some sample input/output labels). The practice key documents count discrepancies and explicit assumptions. Incomplete or ambiguous problems use clearly labelled checkpoints or complete samples; these are not certified contest judging fixtures. Original input-file links remain in the PDF.

`2025-march.json` contains the supplied March question sets: 18 Beginner, 11 Intermediate and 8 Advanced questions. The PDFs are preserved in `static/documents/gic-march-2025-{level}.pdf`. Original answer-sheet HTML is retained in `sources/2025-march/` for provenance, read as text only and never rendered as HTML.

March question numbering resets within each internal level. `source_level` and `source_number` preserve those labels, while `number` is a sequential URL identifier within each Beginner/Intermediate/Advanced category. Answers are matched using the sheet's column headers (`L1 Q1 Output`, etc.), not by column position. Advanced questions retain separate Case 1 and Case 2 outputs. Intermediate Level 1 Question 4 retains both supplied alternatives. Intermediate Level 2 Question 5 is marked withdrawn in the PDF and has a blank answer cell: it is preserved as a withdrawn archive entry with no invented answer. There are 36 questions with supplied answers and one withdrawn question.

Original answer outputs are reproduced verbatim in the archival answer reveals, including line breaks and ordering. The separate practice key independently recalculates the answers and corrects the erroneous Advanced Question 7 promotions. Its comparison rules accept unordered sets and other valid orderings where the question permits them. PDF extraction retains page wrapping, and mathematical glyphs may require consulting the original PDF. The existing database-backed practice questions remain separate.

To regenerate March data with the optional `pypdf` package installed:

```bash
python3 scripts/import_march_questions.py /path/to/pdfs '/path/to/GIC 2025 Answers'
```

The PDF directory must contain the three original `GIC 2025 {Beginner,Intermediate,Advanced} Questions.pdf` filenames. The answer directory must contain `Beginner.html`, `Intermediate.html` and `Advanced.html`. The importer verifies question counts and complete answer-column coverage. No PDF parsing dependency is required by the web app.

Other Initiatives is temporarily archived with `ENABLE_OTHER_INITIATIVES=False` in `app.py`. Its template, assets and homepage previews are preserved. Set the flag to `True` when the page is ready to launch.
