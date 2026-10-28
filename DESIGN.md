# Girls In Code — design direction

The current design uses shades of pink: rose buttons and headings, blush panels, pale pink backgrounds, and deep rose sections. The homepage introduces Girls In Code, its purpose, team, events, CCA teaching, chapters, fundraising, and NGO partners. Its content has no navigation links or calls to action: the header is the main page navigation, and the footer contains only contact links. Competitions and Hackathon are grouped under the Events menu. Sign-in stays secondary and explains that accounts are for competition participation.

## Where to make changes

- `static/styles.css`: palette and font variables at the top, shared components, then responsive rules at 1100, 850, and 600 pixels.
- `templates/base.html`: shared page metadata, fonts, navigation, flash messages, and footer.
- `templates/includes/header.html` and `footer.html`: site navigation and contact links.
- `templates/home.html`: homepage copy and sections.
- `templates/other_initiatives.html`: GIC CCA / Octobuddy teaching and chapter distribution.
- `static/data/chapters.json`: chapter names, coordinates, and descriptions (currently empty, awaiting locations). See `static/data/README.md` for fields.
- `static/chapters.js`: interactive chapter map, pins, and directory.
- `templates/fundraising.html`: fundraising page and the UNICEF/MACO about placeholders. Update `FUNDRAISING_RAISED` and `FUNDRAISING_TARGET` in the `app.py` configuration to change the total and goal for both the homepage and fundraising page; both calculate the progress percentage automatically.
- `templates/archive.html`: shared competition archive layout. Edition-specific winners and resource links live in `2025m.html` and `2025n.html`.
- `templates/competitions_2025.html` and `hackathons.html`: archive navigation by year.
- `templates/scoreboard.html`: archived November 2025 competition standings.
- `templates/hackathon_scoreboard.html`: dedicated place for the 2025 hackathon results when supplied.
- `templates/challenge.html`: shared practice and scored-submission layout.
- `static/site.js`: mobile navigation, the illustrative code example, account-form switching, and upload feedback.

The code example on the homepage illustrates two Python print statements introducing GIC; it does not execute uploaded Python. Existing backend judging and scoring behavior is unchanged by the redesign.

Google Fonts supplies Space Grotesk and DM Sans; the layout falls back to local sans-serif fonts if the font service is unavailable. Existing team photography, competition results, and event resources are retained. The completed hackathon is archived under 2025. Competition and hackathon scoreboards each live within their own 2025 archive; there is no global scoreboard link. The competition results retain the supplied November 2025 standings. Hackathon results are marked as not yet added.

## Local review

Run `python3 app.py` in the configured Python environment. Run the regression suite with `python3 -m unittest discover -s tests -v`.

The redesign was checked in Chrome at desktop and phone widths, with additional homepage checks at 320 and 768 pixels. Database-dependent browser previews used local test data rather than querying Supabase.
