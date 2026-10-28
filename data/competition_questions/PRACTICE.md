# Output practice checks

`practice-answers.json` supplies instant output checking for the 2023, 2024, March 2025 and November 2025 archives. It contains 108 question records: 107 active checks and the one withdrawn March Intermediate question. Every active entry has input/format instructions, accepted output, comparison rules, a worked explanation and provenance. No learner code is executed, and no scores or submissions are written to the database. Attempts are transient. Existing database practice pages can also check typed output against their existing configured key.

The checks grade the **stated output**, not program correctness across unseen inputs. **36 entries are explicitly labelled practice checkpoints**: open-ended interfaces, random exercises, missing datasets, or ambiguous/incomplete questions. These labels and all assumptions are visible before the form. A correct checkpoint does not imply completion of the entire original project. Random-output checks accept any valid selection instead of comparing to a single random example. The withdrawn question has no submit form.

## Sources and decisions

- **2023:** official Behind the Screens Canva slides already preserved in `sources/2023/`. The public GIC Linktree still exposes the questions, but no separate solution-key link was available when checked on 28 October 2026. The school's 2023 article says solutions were originally shared through that Linktree. Worked outputs are derived from the archived statements, starter data and the three recovered files. Q11 uses the complete report actually shown on its source slide despite its missing history file. Newly supplied data for Q4, Q6 and open-ended exercises is clearly labelled illustrative, never live Instagram data or a recovered original. Q16 treats U as undoing one like. Q18 defines a percentage-point redistribution convention. Q29 prohibits repeat films; 24 hours is then impossible because the complete list totals 19 hours. Q36 explicitly supplies zero delivery fees and RM3000 balance because these were unspecified/random.
- **2024:** the supplied solutions PDF pages 5, 7, 9, 11 and 13 gives 400, unsafe landing, 302, indices `(1,2,4,6,8,9,11)`, and cannot land/can land with 187 fuel remaining. All were independently recalculated. Q4 explicitly asks for zero-based indices, matching the key rather than confusing them with temperatures.
- **March 2025:** all supplied answers were recalculated from their inputs. The original HTML answer sheets and verbatim archive answers remain intact. **Advanced Q7 is corrected:** Case 1 = `26505 / 50846 / 21729`; Case 2 = `12399 / 99932 / 95060` (one value per line). The supplied key contained erroneous promotion counts. The correction and explanation appear beside the form. Set order, deduplication-list order and order within even/odd groups are checked semantically.
- **November 2025:** no official key was found; answers were independently worked from the local original booklet. Wrapped commands are joined. Lists with incorrect advertised counts use every supplied entry, with visible notes. Intermediate Q1 uses the first 600 supplied attacks as declared (there are 636); Q2 treats each shipment as usable once and `2, 45` as a pair; Q6 uses the complete published sample because its final string has 23 rather than 24 characters. Q8 explicitly defines final Manhattan distance because the published sample is inconsistent. Q9/Q10 use the complete supplied strings despite incorrect length headers. Advanced Q1 checks the complete sample under the printed rules, giving **34**, not its inconsistent printed 31; the large dataset starts with an incomplete case. Advanced Q2 grades the **41 complete cases**, not the inaccurate 50-case header; the optimum is the kth largest value (singleton subarrays attain the bound). Advanced Q3 uses four-direction movement and zero energy for S/T, stated visibly. Advanced Q7 uses all **103** supplied points. Final input links for Advanced Q4, Q5, Q6, Q9 and Q10 could not be retrieved (HTTP 403 and unavailable through the web reader), so their forms explicitly check the complete published samples only.

Public sources checked:
- https://linktr.ee/girlsincodesea
- https://www.canva.com/design/DAFcblycHmM/Tz8z3c5wRGYUCG4fGsy6YA/view
- https://www.gardenschool.edu.my/gis-news/girls-in-code-sea-inspiring-future-female-tech-leaders/
- November input links: https://shorturl.at/HS7mo, https://shorturl.at/1NHcP, https://shorturl.at/HrFU0, https://shorturl.at/o9iFE, https://shorturl.at/rbrBh

## Rebuild and verify

```sh
python3 scripts/build_practice_answers.py
python3 -m unittest discover -s tests
```

The builder and `scripts/practice_solutions.py` run offline and never execute imported question text. They preserve the archived questions and original answer sheets. Generated keys are loaded by `practice.py` and cached per server process; restart the server after rebuilding keys.

Tests check every active answer and incorrect alternatives, all form links, multiple cases, CSRF, blank/oversized input, no-JavaScript submission, HTML escaping, non-execution, and order/multiplicity rules. Separate exhaustive small-instance oracles verify workload partitioning, shipment assignment, stall merges and the subarray-score proof. The API does not disclose answer keys in its response; worked solutions are intentionally available in collapsed educational reveals on the page. A text answer cannot prove randomness, algorithm choice, GUI behaviour, or general program correctness.
