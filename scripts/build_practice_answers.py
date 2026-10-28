"""Rebuild reviewed output checks from archived inputs and offline solutions.

Run: python3 scripts/build_practice_answers.py
No participant code, network calls, or database writes are involved.
"""
import ast
from collections import Counter
from datetime import date
from decimal import Decimal, localcontext
from itertools import groupby, permutations
import json
from pathlib import Path
import re
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from practice import matches

from scripts.practice_solutions import (
    balanced_sectors, battle_winner, burgers, consistent_pairs, enclosure_saving,
    equal_zone_merges, grid_energy, laser_cost_small, merge_stalls,
    minimum_energy_core, partition_work, traffic_bounds,
)

DATA = ROOT / 'data/competition_questions'
ANSWERS = {}


def read(edition):
    return json.loads((DATA / f'{edition}.json').read_text())


def display(value):
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def case(label, expected, mode='text', instructions='', **options):
    return dict(label=label, expected=display(expected), mode=mode,
                instructions=instructions, **options)


def add(key, cases, explanation, note='', source='Worked solution from the archived question.', checkpoint=False):
    ANSWERS[key] = dict(cases=cases, explanation=explanation, note=note,
                        source=source, checkpoint=checkpoint)


def ints(text):
    return [int(n) for n in re.findall(r'-?\d+', text)]


def array(text):
    # Only parse repository source literals, never execute source code.
    value = text[text.index('['):text.rindex(']') + 1]
    value = value.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    return ast.literal_eval(value.replace('\n', ' '))


def original_2023():
    questions = {q['number']: q for q in read('2023')}
    def add23(n, cases, explanation, note='', checkpoint=False):
        add(f'2023-{n}', cases, explanation, note,
            '2023 Behind the Screens slides ' + ', '.join(map(str, questions[n]['source_pages'])) +
            '; independently worked output/checkpoint.', checkpoint)
    add23(1, [case('Would I return?', 'yes', 'text', 'Enter only yes or no.', ignore_case=True)],
          '7.5 + 8.3 = 15.8, which is at least 12.', 'This checks the return decision; the full exercise also asks you to format the restaurant review.', True)
    keep = ['cooking reels', 'clothing posts', 'rugby posts', 'anything meme related']
    hide = ['political posts', 'diving compilations', 'celebrity drama', 'pet posts']
    add23(2, [case('Feed decisions', '\n'.join([f'{p}: keep in feed' for p in keep] + [f'{p}: hide from feed' for p in hide]), 'unordered_lines',
                  'Enter one “content: keep in feed” or “content: hide from feed” line for each of the eight content types, using the names in the question. Any line order is accepted.'),
              case('Counts', [4, 4], 'numbers', 'Enter the number kept, then the number hidden.')],
          'Each of the four liked categories stays; each of the four disliked categories is hidden.')
    words = ['coding', 'planet', 'rocket', 'galaxy', 'python', 'school', 'garden', 'friend', 'future', 'puzzle']
    add23(3, [case('Generated password', words[0][::-1], 'choice', 'Use this practice word list: ' + ', '.join(words) + '. Submit one randomly selected word reversed.', choices=[w[::-1] for w in words])],
          'Select any index from 0 through 9, then reverse that word with word[::-1]. Any of the ten valid reversals is accepted.',
          'New practice word list. A submitted output cannot demonstrate that selection was random or that subroutines were used.', True)
    add23(4, [case('Follower/post ratios', [200, 150, 300], 'numbers', 'Practice snapshot (followers, posts): buzzfeedtasty (12000, 60), milktpapi (9000, 60), doobydobap (15000, 50). Enter all three ratios in that order.'),
              case('Most successful account', 'doobydobap')],
          'Divide followers by posts: 200, 150 and 300. The largest ratio is 300 for doobydobap.',
          'New illustrative snapshot, not live or historical Instagram statistics. The original question requires changing external data.', True)
    add23(5, [case('Post 3 state', [2, 1, 1], 'numbers', 'Starting with the original empty arrays: view post 3 twice, like it once, and comment “Great!”. Enter its final views, likes and number of comments.'),
              case('Comments for post 3', ['Great!'], 'sequence', 'Enter the comments as a list.')],
          'Each view adds one, one like adds one, and appending the comment leaves a one-item comment list.', 'New interaction sequence for checking the original app behaviour.', True)
    add23(6, [case('Post order', ['B', 'A', 'C'], 'sequence', 'New practice CSV rows (post, likes, comments): A,80,20; B,150,50; C,30,20. num_followers = 1000. Enter post IDs in descending engagement order.'),
              case('Engagement rates', [0.2, 0.1, 0.05], 'numbers', 'Enter the three engagement rates in the same descending order.')],
          'B: (150+50)/1000 = 0.2; A: 0.1; C: 0.05.', 'The original spreadsheet is unavailable. These labelled practice rows replace it only for this check.', True)
    songs = ['Murder And Crime – Sufjan Stevens', 'To Let A Good Thing Die – Bruno Major', 'Reach Out – Sufjan Stevens', 'Home – Bruno Major', 'Mystery of Love – Sufjan Stevens']
    queue = [song for song in songs for _ in range(3)]
    add23(7, [case('Numbered queue', '\n'.join(f'{i}. {song}' for i, song in enumerate(queue, 1)), 'text', 'Paste all 15 numbered lines, including song and artist.')],
          'Repeat each song three times before moving to the next song, numbering continuously from 1 to 15.')
    tracks = ['Daydreaming by Harry Styles', 'Workin Out by JID', 'Old Love by yuji', 'Eventually by Tame Impala', 'After Hours by The Weekend', 'Ghostin by Ariana Grande', 'Hey, Mickey! by Baby Tate', 'Low by SZA', 'Pink + White by Frank Ocean', 'Here With Me by d4vd']
    add23(8, [case('Three shuffled tracks', '\n'.join(f'{i} {tracks[i]}' for i in [9, 5, 7]), 'track_pairs', 'Enter three lines, each containing the zero-based track number followed by its name. Repeats are allowed.', tracks=tracks)],
          'Choose an index in range(10) three times and output the matching track. Every valid combination is accepted.', 'This checks track/index consistency, not randomness.', True)
    add23(9, [case('Songs with both preferred properties', ['above the chinese restaurant', 'let you break my heart again', 'someone new'], 'unordered_sequence', 'Enter only the songs tagged both slow and sad, as a list or one per line.')],
          'Filter songs where both “slow” and “sad” appear in the properties.', 'This checkpoint checks the highest-priority group, rather than prescribing an order for the remaining playlist.', True)
    add23(10, [case('Bad habit by Steve Lacy', '2 False', 'tokens', 'Enter the occurrence count followed by True or False.'), case('Solo by Future', '1 True', 'tokens', 'Enter the occurrence count followed by True or False.')],
          'Bad habit appears in playlists 2 and 3. Solo appears only in playlist 1.')
    wrapped = next(b['text'] for b in questions[11]['blocks'] if b.get('type') == 'code')
    add23(11, [case('Spotify Wrapped', wrapped, 'text', 'Paste the complete Wrapped report with its headings, ranked songs and artists, genre and minutes.')],
          'Count song, artist and genre occurrences; rank by count. Sum track durations and convert seconds to minutes.',
          'The original history file is unavailable, but the original slide supplies the complete expected output. This checks that published report.', True)
    add23(12, [case('Player state', 'Song B\n45\n70', 'tokens', 'Practice state: songs [Song A, Song B, Song C], current index 0. Press Next once, set progress to 45 seconds and volume to 70. Enter the current title, progress and volume in that order.')],
          'Next advances the index to 1 (Song B). The slider values are 45 seconds and 70.', 'New state-tracing checkpoint. The graphical interface itself requires manual review.', True)
    add23(13, [case('Speed confirmation', 'Speed change successful, now playing at 1.25x speed.', 'text', 'Use the example input 1.25. Submit the success message only.')], 'Validate the speed against the allowed list, then insert 1.25 into the confirmation message.')
    add23(14, [case('Validation messages', 'Please input a password containing 8 to 20 letters:\npassword has been validated\nlogged in', 'text', 'Practice inputs: abc, codegirls2023, wrong, codegirls2023. Enter only the three status messages in order; omit input prompts.')],
          'abc is too short. codegirls2023 is valid. The first confirmation is wrong, so keep asking until the second confirmation matches.', 'New interaction sequence. Length validation and the double-entry check are separate loops.', True)
    wellness = ['curry', 'fried rice', 'noodles', 'schedule', 'zumba', 'workout', 'tips', 'cardio', 'habits', 'marathon', 'painting', 'dancing', 'acrylics', 'singing']
    add23(15, [case('Feed order', wellness, 'priority_sequence', 'Enter video titles as a list or one per line. Cooking videos first, then other wellness videos, then arts. Any order within each group is accepted.', groups=[wellness[:3], wellness[3:10], wellness[10:]])],
          'Sort by priority: wellness/cooking = 0, other wellness = 1, arts = 2. All 14 videos must appear exactly once.')
    interactions = next(b['text'] for b in questions[16]['blocks'] if b.get('type') == 'code').strip('"')
    add23(16, [case('Likes, comments, shares', [interactions.count('L') - interactions.count('U'), interactions.count('C'), interactions.count('S')], 'numbers', 'Enter final likes, comments, shares in that order. Treat each U as undoing one like.')],
          f"There are {interactions.count('L')} L events, {interactions.count('U')} U events, {interactions.count('C')} C events and {interactions.count('S')} S events. Final likes = L − U.")
    likes = [13600, 21600, 6300, 17100, 7700, 23400, 8400, 15200]
    views = [17000, 24000, 9000, 19000, 11000, 26000, 12000, 19000]
    rates = [a / b * 100 for a, b in zip(likes, views)]
    add23(17, [case('Like percentages', rates, 'numbers', 'Enter the eight like percentages in the order of the listed videos (numbers only, without %).'),
               case('Summary', [sum(views), sum(likes) / 8, sum(rates) / 8], 'numbers', 'Enter total views, average likes, and the arithmetic mean of the eight like percentages.')],
          'For each video, percentage = 100 × likes/views. Sum views and divide total likes by 8. Average the eight percentages.',
          'This checks the numeric summary. The original question does not define a prediction model, so predicted rankings are not graded.', True)
    add23(18, [case('Updated topic probabilities', [18.75, 25, 18.75, 18.75, 18.75], 'numbers', 'Practice convention: start at 20% per topic; a like adds 5 percentage points to that topic and removes 1.25 from each other topic. Then a skip reverses those adjustments. Like gym, then skip gym, then like cooking. Enter gym, cooking, travel, gardening, art percentages.')],
          'The gym like and skip cancel. The final cooking like gives cooking 25% and each other topic 18.75%.',
          'New deterministic checkpoint with an explicit probability-redistribution rule, since “5% increased chance” is ambiguous in the source.', True)
    add23(19, [case('Arrival time', '08:35', 'text', 'Practice drivers: A takes 20 minutes; B takes 35 minutes. Choose B and depart at 08:00. Enter arrival as HH:MM.')],
          '08:00 + 35 minutes = 08:35.', 'New driver data. This checks arrival-time calculation; the full exercise also asks for driver selection and a confirmation.', True)
    add23(20, [case('Driver confirmation', 'Booking successful\nAisha\n* * * *\nABC1234\nToyota Prius', 'text', 'Practice driver: Aisha, 4 stars, ABC1234, Toyota Prius. Enter five lines: Booking successful, name, stars separated by spaces, plate and model. Centring spaces are ignored.')],
          'Format the supplied fields and repeat “*” four times. Use str.center(width) for the complete console exercise.', 'New driver details; checking the message content does not verify screen alignment.', True)
    add23(21, [case('Fast Food', ['McDonalds', 'KFC'], 'unordered_sequence', 'Use input Fast Food. Enter the matching restaurant names as a list or one per line.')],
          'Filter the dictionaries where Category equals Fast Food.')
    add23(22, [case('Running distance and cost', '5 10\n12 24\n15 30', 'numbers', 'New rides (distance km, cost): (5,10), (7,14), (3,6). Enter running distance and cost after each ride, one pair per line.')],
          'Maintain two running totals, adding each new ride: (5,10), (12,24), (15,30).', 'New rides for the accumulation checkpoint. Name, ID and locations still belong in the full interactive program.', True)
    add23(23, [case('Fare', '6.45', 'numeric', 'Practice distance is 12 km. Use base $0.75, $0.50/km for the first 10 km and $0.35/km after that. Enter the fare to 2 decimal places.')],
          '0.75 + 10×0.50 + 2×0.35 = 6.45.', 'This checkpoint supplies distance directly to check the fare bands; the complete exercise also needs coordinate-to-distance conversion.', True)
    rows = [row.strip() for row in (ROOT / 'static/documents/2023/grab-restaurants.txt').read_text().splitlines() if row.strip() and not row.startswith('#')]
    chinese = [rows[i] for i in range(0, len(rows), 2) if rows[i + 1] == 'Chinese']
    add23(24, [case('Chinese cuisine', chinese, 'unordered_sequence', 'Use input Chinese. Enter the matching restaurants from the supplied file.')],
          'Read alternating restaurant/cuisine lines, group by cuisine, then select Chinese.')
    add23(25, [case('Watch later', ['Spirit', 'Black Beauty'], 'sequence', 'New practice actions: add Spirit, add Black Beauty. Enter the watch-later list in insertion order.')],
          'Start with an empty list and append the two selected titles.', 'This checks a small watchlist operation. The original menu, ten chosen films, ratings and age restrictions require manual review.', True)
    add23(26, [case('Updated queue', ['C', 'D', 'E'], 'sequence', 'New practice queue [A, B, C, D, E]. Mark B watched, then A watched. Enter the remaining queue.')],
          'Remove watched titles without reordering the remaining entries.', 'New deterministic queue checkpoint; it does not test the full interactive five-input interface.', True)
    movies = [row.strip() for row in (ROOT / 'static/documents/2023/netflix-search.txt').read_text().splitlines() if re.search(r'\bspace\b', row, re.I)]
    add23(27, [case('Space films', movies, 'unordered_sequence', 'Search for the whole word space, case-insensitively, in the supplied file. Include years. Enter one matching film per line or a list; any order is accepted.')],
          'Read the file line by line and select titles matching the whole word “space”, ignoring case.')
    movies = [m.strip() for m in (ROOT / 'static/documents/2023/netflix-surprise.txt').read_text().split(',')]
    add23(28, [case('Surprise selection', movies[0], 'choice', 'Submit one randomly chosen movie title from the supplied surprise-movie file.', choices=movies)],
          'Split this file on commas, then call random.choice on the titles. Any listed title is accepted.', 'Checks membership of the output, not randomness.', True)
    marathon = ['The Incantation', 'The Invitation', 'The School for good and evil', 'Spirited Away', 'Your Name', 'Enola Holmes', 'A Silent Voice', 'The Tale of Princess Kaguya', 'Pitch Perfect 2']
    add23(29, [case('6-hour marathon', marathon[:3], 'subset', 'Without repeating movies, enter any three 2-hour titles from My_list as a list or one per line.', choices=marathon, count=3),
               case('24-hour marathon', 'impossible', 'text', 'Using each film at most once, enter possible or impossible.', ignore_case=True)],
          'Any three of the nine 2-hour films total 6 hours. All ten films together last 19 hours, so 24 hours is impossible without repeats.', 'Practice convention: films cannot repeat; the original question did not specify this.', True)
    add23(30, [case('Recommended title', 'Orbit', 'choice', 'New viewing_history.txt: Orbit,Sci-Fi; Meadow,Drama; Comet,Sci-Fi. favorite_genres.txt contains Sci-Fi. Enter a possible recommended title.', choices=['Orbit', 'Comet'])],
          'Filter history to matching genres, then choose randomly from Orbit and Comet.', 'New tiny datasets; the original task asks participants to create their own files.', True)
    add23(31, [case('Discounted amount', 80, 'numeric', 'New practice prices: Shoes RM50, Phone case RM20, Earphones RM30. Buy one of each and select the 20% discount. Enter the final amount.')],
          '(50 + 20 + 30) × 0.8 = RM80.', 'New prices and selections; the original exercise lets participants choose prices.', True)
    add23(32, [case('Anonymous username', 'v*********8', 'text', 'Enter the displayed username after hiding the middle characters of valerie8588.')],
          'valerie8588 has 11 characters. Keep v and the final 8, replacing the nine middle characters with asterisks.', 'Checks the anonymisation step; the full exercise also prints the review fields.', True)
    add23(33, [case('Location and postcode', 'Hanoi 11109', 'tokens', 'Enter the city and postcode for Valerie’s headphones.')],
          'Match both owner Valerie and item Headphones, then look up Hanoi in the postcode table.')
    add23(34, [case('Sorted purchases', sorted([4, 9, 2, 1, 2, 6, 3]), 'numbers', 'Enter the sorted values as a list or separated by spaces.')],
          'Swap adjacent out-of-order values until sorted. Retain both occurrences of 2.')
    add23(35, [case('Cheapest item', 'P2 Notebook 8', 'tokens', 'New catalogue rows (ID, name, price): P1 Lamp 20; P2 Notebook 8; P3 Mug 12. Enter ID, name and price of the cheapest item.')],
          'Parse numeric prices and select the record with minimum price: 8.', 'New catalogue; the original question asks participants to create their own file.', True)
    sellers = {'Official Xiaomi Store': (2999, 30), 'Official Siaome Store': (.99, 90), 'mmgbpmall': (3499, 40), 'spraygadget': (4599, 25), 'calastore': (1905, 33), 'mayatech': (2555, 22), 'mcdecotech': (2359, 20), 'caviar': (59999, 0), 'rocketgadgets': (3349, 12), 'realstore': (20, 50)}
    prices = {name: Decimal(str(price)) * (100 - discount) / 100 for name, (price, discount) in sellers.items()}
    ordered = sorted(prices, key=prices.get)
    add23(36, [case('Seller order', ordered, 'sequence', 'Practice convention: delivery is RM0 for every seller. Apply the given percentage discounts. Enter seller names from cheapest to most expensive.'),
               case('Affordable sellers', [name for name in ordered if prices[name] <= 3000], 'unordered_sequence', 'Use a practice balance of RM3000. Enter every affordable seller.')],
          'Price after discount = price × (1 − discount/100). Sort these totals and compare each against RM3000.', 'New fixed balance and delivery fees (fees were absent from the source). This checks costs and affordability; PIN and purchase flows require manual review.', True)


def festival_2024():
    source = 'User-supplied 2024 solutions PDF, answer slides 5, 7, 9, 11 and 13; calculations independently checked.'
    def add24(n, cases, explanation):
        add(f'2024-{n}', cases, explanation, source=source)
    add24(1, [case('Total fuel', 4 * 100, 'numeric', 'Enter total fuel units.')], '4 tanks × 100 units = 400 units.')
    add24(2, [case('Safe to land?', 'no', 'choice', 'At the given velocity of 4 m/s, enter yes or no.', choices=['no', 'false', 'unsafe', 'not safe', 'Landing not safe! Velocity too high.'], ignore_case=True)], '4 is not less than 2, so landing is not safe.')
    add24(3, [case('Decimal value', int('0100101110', 2), 'numeric')], 'The set bits contribute 256 + 32 + 8 + 4 + 2 = 302.')
    values = [25, 0, 4, 37, 12, 85, 14, 63, 7, 10, -3, 20, 56]
    add24(4, [case('Suitable landing-zone indices', [i for i, value in enumerate(values) if 0 <= value <= 20], 'numbers', 'Following the supplied key, enter the zero-based indices of readings from 0 through 20 inclusive, in ascending order. Submit indices, not temperatures.')], 'The suitable readings are 0, 4, 12, 14, 7, 10 and 20, at indices 1, 2, 4, 6, 8, 9 and 11.')
    add24(5, [case('Scenario 1: can land?', 'no', 'choice', 'Enter yes or no.', choices=['no', 'cannot land', 'false'], ignore_case=True),
              case('Scenario 2: remaining fuel at the surface', 4503 - 332 * 13, 'numeric', 'Enter remaining fuel units.')], 'Scenario 1 needs 92×5 = 460 units but has only 230. Scenario 2 needs 332×13 = 4316 and has 4503, leaving 187.')


def march_2025():
    questions = read('2025-march')
    for q in questions:
        n, level, statement = q['number'], q['level'], q['statement']
        key = f'2025-march-{level.lower()}-{n}'
        source = f'Supplied March {level} answer sheet and booklet page {q["source_page"]}; independently recalculated.'
        if q['status'] == 'withdrawn':
            add(key, [], '', 'The organisers withdrew this question because the original problem contains a mistake. It is not graded.', source)
            continue
        explanation, note, mode = '', '', 'numeric'
        answers = []
        if level == 'Beginner':
            if n == 1:
                answers, mode = ['Your favourite astronaut is Sally Ride.'], 'text'
                explanation = 'Insert Sally Ride into the sentence template.'
            elif n == 2:
                answers, mode = [sorted(['Python', 'JavaScript', 'Ruby'])], 'sequence'
                explanation = 'Sort the three strings alphabetically.'
            elif n == 3:
                answers, mode = ['Mae Jemison'], 'text'
                explanation = 'Index 3 is the fourth item because indexing starts at zero.'
            elif n == 4:
                names = ['Sheryl Sandberg', 'Radia Perlman', 'Grace Hopper', 'Ada Lovelace', 'Katherine Johnson']
                answers, mode = ['\n'.join(sorted(names, reverse=True))], 'text'
                explanation = 'Sort names in reverse alphabetical order and print each on its own line.'
            elif n == 5:
                answers, mode = ['\n'.join(name for name in array(statement[statement.index('names ='):]) if name.startswith('A'))], 'text'
                explanation = 'Keep names starting with A, preserving their input order.'
            elif n in (6, 8, 9, 10, 11, 12, 14, 15, 16, 18):
                values = array(statement)
                if n == 6:
                    answer = sum(v % 4 == 0 for v in values)
                    explanation = 'Count entries whose remainder on division by 4 is zero.'
                elif n == 8:
                    answer, mode = max(values, key=len), 'text'
                    explanation = 'Compare word lengths; passionfruit is the longest.'
                elif n == 9:
                    answer = sum(len(v) > 5 for v in values)
                    explanation = 'Count every entry longer than five letters, including duplicate entries.'
                elif n == 10:
                    answer = Counter(values).most_common(1)[0][0]
                    explanation = 'Count frequencies; choose the value with the largest count.'
                elif n == 11:
                    answer = sum(map(len, values)) / len(values)
                    explanation = 'Divide the sum of all word lengths by the number of entries.'
                elif n == 12:
                    answer = sum(v * v for v in values)
                    explanation = 'Square each number, then sum the squares.'
                elif n == 14:
                    answer = values.count(11)
                    explanation = 'Count exact occurrences of the integer 11, not numbers merely containing its digits.'
                elif n == 15:
                    answer = values[56] % 3
                    explanation = f'The 57th element is at index 56: {values[56]}. Its remainder modulo 3 is {answer}.'
                elif n == 16:
                    answer = sum(v > 100 for v in values)
                    explanation = 'Count values strictly greater than 100.'
                else:
                    answer = max(values) - min(values)
                    explanation = f'Range = {max(values)} − {min(values)} = {answer}.'
                answers = [answer]
            elif n == 7:
                word = re.search(r'String\s*=\s*"([^"]+)"', statement)[1].replace('\n', '')
                answers = [sum(c in 'aeiou' for c in word)]
                explanation = 'Count a, e, i, o and u in the complete string, joining printed line wraps.'
            elif n == 13:
                prefix = statement.split('numbers =', 1)[1].split('#', 1)[0]
                values = ints(prefix)
                answers = [values.index(315)]
                explanation = 'The first 315 is the 100th value, so its zero-based index is 99.'
            elif n == 17:
                seq = [5, 5]
                while len(seq) < 15:
                    seq.append(sum(seq[-2:]))
                answers, mode = [seq], 'numbers'
                explanation = 'Start with 5,5; repeatedly append the sum of the previous two values until there are 15 terms.'
        elif level == 'Intermediate':
            if n == 1:
                values = array(statement)
                prime = lambda v: v >= 2 and all(v % d for d in range(2, int(v ** .5) + 1))
                answers, mode = [sorted({v for v in values if prime(v)})], 'unordered_sequence'
                explanation = 'Test divisors through the square root of each value, discard composites and remove duplicates. Any set order is accepted.'
            elif n == 2:
                values = array(statement)
                answers, mode = [[v for v in values if v % 2 == 0] + [v for v in values if v % 2]], 'even_odd'
                explanation = 'Keep the original multiset of numbers, placing all evens before all odds. Any order within each parity group is accepted.'
            elif n == 3:
                value = statement.split('string1 = "', 1)[1].rsplit('"', 1)[0].replace('\n', ' ')
                answers = [len([part for part in re.split(r'[ ,.!?\-]+', value) if part])]
                explanation = 'Split on the specified punctuation and count non-empty words.'
            elif n == 4:
                answers, mode = [list(dict.fromkeys(array(statement)))], 'unordered_sequence'
                explanation = 'Keep each distinct value once. The question does not require an ordering, so all orders are accepted.'
            elif n == 5:
                answers, mode = ['\n'.join(sorted({''.join(p) for p in permutations('ada')}))], 'text'
                explanation = 'Generate permutations, remove duplicates, then sort alphabetically: aad, ada, daa.'
            elif n == 6:
                values = [55000, 60000, 62000, 75000, 80000, 50000]
                median = statistics.median(values)
                answers = [int(sum(abs(v - median) for v in values))]
                explanation = 'Any target between 60000 and 62000 minimises the sum of absolute differences; the total is 52000.'
            elif n == 7:
                with localcontext() as context:
                    context.prec = 100
                    population = Decimal('1000.076893438')
                    capacity = Decimal('7897654345678965345678907654323456789876534567432345698767890987.987678')
                    factor = 1 + Decimal('0.3758938726')
                    days = 0
                    while population < capacity:
                        population *= factor
                        days += 1
                answers = [days]
                explanation = 'Multiply the population by 1+r each day until it reaches the carrying capacity. High-precision decimal arithmetic gives the first qualifying day.'
            elif n == 8:
                values = array(statement.split('Find the output for the following input:', 1)[1])
                answers = [sum(values) * 215]
                explanation = f'The data sum for one cycle is {sum(values)}; multiply by 215.'
            elif n == 10:
                value = statement.rsplit('“', 1)[1].split('”')[0].replace('\n', '')
                longest = set()
                size = 0
                for center in range(len(value)):
                    for l, r in [(center, center), (center, center + 1)]:
                        while l >= 0 and r < len(value) and value[l] == value[r]:
                            length = r - l + 1
                            if length > size:
                                size, longest = length, set()
                            if length == size:
                                longest.add(value[l:r + 1])
                            l, r = l - 1, r + 1
                answers, mode = [sorted(longest)[0]], 'choice'
                explanation = 'Expand around every odd and even centre; keep the longest matching substring. Any equally long palindrome is accepted.'
            elif n == 11:
                # After minute 2 the reproducing population alternates 4,16.
                minutes = 10000000
                reproducing = 4 if minutes % 2 else 16
                merged = 3 * ((minutes - 1) // 2)
                answers, mode = [f'{reproducing}\n{merged}'], 'numbers'
                explanation = 'After minute 2, live counts alternate 4 and 16. Every odd minute from minute 3 creates three non-reproducing alomomoja.'
        else:
            mode = 'numbers'
            raw_cases = re.split(r'Case [12]:', statement.split('\nInput\n', 1)[1])[1:]
            for raw in raw_cases:
                if n == 1:
                    rows = re.findall(r'^[GH]+$', raw, re.M)
                    # The PDF wraps both strings over the same number of rows.
                    a, b = ''.join(rows[:len(rows)//2]), ''.join(rows[len(rows)//2:])
                    assert len(a) == len(b), (key, len(a), len(b))
                    different = [x != y for x, y in zip(a, b)]
                    answers.append(sum(value and (i == 0 or not different[i - 1]) for i, value in enumerate(different)))
                    assert len(a) == ints(raw)[0], (key, len(a))
                    explanation = 'Each maximal consecutive run of mismatches requires one flip. Count starts of mismatch runs.'
                elif n == 2:
                    a, b, c, d = ints(raw)
                    answers.append(b - a + d - c - max(0, min(b, d) - max(a, c)))
                    explanation = 'Add the interval lengths, subtracting their overlap once.'
                elif n == 3:
                    values = ints(raw)
                    capacity, milk = values[::2], values[1::2]
                    for pour in range(100):
                        a, b = pour % 3, (pour + 1) % 3
                        amount = min(milk[a], capacity[b] - milk[b])
                        milk[a] -= amount
                        milk[b] += amount
                    answers.append('\n'.join(map(str, milk)))
                    explanation = 'Simulate all 100 pours cyclically, transferring min(source amount, destination free capacity) each time.'
                elif n == 4:
                    values = ints(raw)
                    a, b = values[:2]
                    pairs = list(zip(values[2::2], values[3::2]))
                    limit = [speed for length, speed in pairs[:a] for _ in range(length)]
                    driven = [speed for length, speed in pairs[a:] for _ in range(length)]
                    assert len(pairs) == a + b and len(limit) == len(driven) == 100
                    answers.append(max(0, max(v - limit[i] for i, v in enumerate(driven))))
                    explanation = 'Expand each road and journey segment mile by mile. Take max(0, actual speed − limit) across all 100 miles.'
                elif n == 5:
                    segments = [(kind, int(a), int(b)) for kind, a, b in re.findall(r'(on|off|none) (\d+) (\d+)', raw)]
                    assert len(segments) == ints(raw)[0]
                    before, after = traffic_bounds(segments)
                    answers.append(f'{before[0]} {before[1]}\n{after[0]} {after[1]}')
                    explanation = 'Propagate interval bounds forwards for final traffic, and backwards with on/off reversed for initial traffic. Intersect at every none sensor.'
                elif n == 6:
                    a, b, x, y = ints(raw)
                    answers.append(min(abs(a-b), abs(a-x)+abs(y-b), abs(a-y)+abs(x-b)))
                    explanation = 'Compare the direct distance with both possible directions through the teleporter.'
                elif n == 7:
                    counts = ints(raw)
                    changes = [counts[i+1] - counts[i] for i in range(0, 8, 2)]
                    promotions = [sum(changes[1:]), sum(changes[2:]), changes[3]]
                    answers.append('\n'.join(map(str, promotions)))
                    explanation = 'Gold→platinum is the platinum increase. Add the gold increase for silver→gold, then the silver increase for bronze→silver.'
                elif n == 8:
                    values = sorted(ints(raw))
                    result = [values[0], values[1], values[-1] - values[0] - values[1]]
                    a, b, c = result
                    assert sorted([a,b,c,a+b,b+c,c+a,a+b+c]) == values
                    answers.append(' '.join(map(str, result)))
                    explanation = 'The two smallest values are A and B; subtract them from the largest (A+B+C) to find C.'
        assert answers, key
        specs = [case(f'Case {i+1}' if level == 'Advanced' else 'Your output', output, mode,
                      'Use the corresponding input from the question. For lists, brackets and commas are optional for numeric answers; text lists may also be entered one item per line.') for i, output in enumerate(answers)]
        if mode == 'choice':
            specs[0]['choices'] = sorted(longest)
        supplied = [a['output'] for a in q['answers'] if a['label'] != 'Alternative output']
        # Compare semantically using the same well-defined output contract.
        if len(supplied) == len(specs) and not all(matches(value, spec) for value, spec in zip(supplied, specs)):
            note += (' ' if note else '') + 'The supplied answer sheet disagrees with the worked result. This checker uses the recalculated answer; the original sheet is retained below for reference.'
        add(key, specs, explanation, note, source)


def november_2025():
    questions = read('2025-november')
    for q in questions:
        level, n, statement = q['level'], q['number'], q['statement']
        key = f'2025-november-{level.lower()}-{n}'
        note, explanation, checkpoint, mode = '', '', False, 'numeric'
        instruction = 'Use the question input above. Enter only the output.'
        answer = None
        specs = None
        if level == 'Beginner':
            if n == 1:
                value = ''.join(statement.split('reverse:\n', 1)[1].split())
                answer, mode = value[::-1], 'text'
                instruction = 'Reverse the entire command, joining the printed line wraps first. Submit one continuous string.'
                explanation = 'Join the wrapped command without adding spaces, then take command[::-1].'
            elif n in (2, 4):
                names = [value.replace('\n', '') for value in re.findall(r'"([^"]+)"', statement)]
                if n == 2:
                    answer = names.index('delta-spark')
                    explanation = 'Count from index zero; delta-spark is at index 56.'
                else:
                    answer = sum(len(value) > 6 for value in names)
                    explanation = 'Count characters in each complete name, including hyphens and spaces; retain only lengths greater than 6.'
            elif n in (3, 5, 7):
                values = array(statement)
                if n == 3:
                    answer = statistics.median(values)
                    explanation = f'Sort all {len(values)} supplied readings, then average the two middle entries.'
                elif n == 5:
                    evens = [value for value in values if value % 2 == 0]
                    answer = f'{sum(evens)/len(evens):.2f}'
                    explanation = f'Sum the {len(evens)} even entries, divide by {len(evens)}, and round to two decimal places.'
                else:
                    answer, mode = sorted(values), 'numbers'
                    explanation = 'Sort every supplied serial number in ascending order, retaining repeated values.'
                note = f'The printed count is inaccurate: there are {len(values)} supplied entries. This check uses all of them.'
            elif n == 6:
                answer, mode = ['forward', 'left', 'right'][(2911 - 1) % 3], 'text'
                explanation = 'Use one-based step numbering: (2911−1) modulo 3 is 0, which is forward.'
            elif n == 8:
                value = statement.split('types:\n', 1)[1].split('\nSort the list', 1)[0].replace('-\n', '-')
                names = [word.strip() for word in value.replace('\n', ' ').split(',')]
                answer, mode = sorted(names), 'sequence'
                explanation = 'Sort the supplied names alphabetically, keeping hyphenated suffixes.'
                instruction = 'Enter the sorted robot names as a list or one name per line.'
                note = f'There are {len(names)} listed robot types, despite the printed count of 100. Use all listed names.'
            elif n == 9:
                names = re.findall(r'\b[A-Z]{2}\d{2}\b', statement)
                answer, mode = names[48], 'text'
                explanation = 'The 49th item uses zero-based index 48: QV18.'
            elif n == 10:
                values = ints(statement.split('battery.\n', 1)[1].split('\nPrint')[0])
                answer = sum(v >= 50 for v in values)
                explanation = 'Count all battery readings at least 50, including readings equal to 50.'
                note = 'The first sentence is truncated in the booklet. This check uses the stated threshold of at least 50.'
        elif level == 'Intermediate':
            if n == 1:
                rows = statement.split('Question Input:', 1)[1].strip().splitlines()
                value = ''.join(rows[1:])
                # Respect the declared 600 attacks; explicitly expose this decision.
                answer, mode = battle_winner(value[:600], 30), 'text'
                explanation = 'Split the 600 attacks into 20 groups of 30. In each group choose the highest frequency, breaking ties alphabetically. Apply the same rule to group winners.'
                note = 'The booklet supplies 636 characters but declares 600 attacks. For this practice check, use only the first 600 characters; ignore the extra 36.'
                checkpoint = True
            elif n == 2:
                data = ints(statement.split('Question Input:', 1)[1])
                hours, count, lifetime = data[:3]
                shipments = list(zip(data[3::2], data[4::2]))
                assert len(shipments) == count
                answer = burgers(hours, shipments, lifetime)
                explanation = 'Assign shipments to eligible hours to maximise total calories. A shipment arriving at t is usable at t through t+K−1; each shipment can supply at most one burger.'
                note = 'Practice convention: each shipment is consumed once. Read the printed “2, 45” as the pair (2,45).'
                checkpoint = True
            elif n == 3:
                data = ints(statement.split('Final Input:', 1)[1])
                workers, count, *values = data
                assert len(values) == count
                answer = partition_work(values, workers)
                explanation = 'Binary-search a maximum workload. Greedily form contiguous groups under that limit; accept a limit if it needs no more than 25 groups.'
            elif n == 4:
                value = statement.split('Question Input:', 1)[1].splitlines()[-1]
                frequency = Counter(value)
                answer, mode = ''.join(c * frequency[c] for c in sorted(frequency, key=lambda c: (-frequency[c], c))), 'text'
                explanation = 'Count letters; order them by decreasing frequency and alphabetically for tied counts.'
            elif n == 5:
                log = array(statement.split('Question Input:')[-1])
                log = sorted((date.fromisoformat(day), reps) for day, reps in log)
                streak = best = 1
                for (day, reps), (prev_day, prev_reps) in zip(log[1:], log):
                    streak = streak + 1 if (day-prev_day).days == 1 and reps > prev_reps else 1
                    best = max(best, streak)
                answer = best
                explanation = 'Sort by date, then extend a streak only when the date is the next day and repetitions strictly increase.'
            elif n == 6:
                # Use a complete new case; do not invent the missing 24th character.
                value = 'AABBCCBAA'
                answer, mode = battle_winner(value, 3), 'text'
                instruction = 'Check the complete published sample instead: p=9, n=3, s=AABBCCBAA. Break any tie alphabetically.'
                explanation = 'The three groups are AAB, BCC and BAA; their winners are A, C and A.'
                note = 'The final input declares 24 characters but supplies 23. The checker uses the complete sample, not a guessed missing character.'
                checkpoint = True
            elif n == 7:
                data = ints(statement.split('Question Input:', 1)[1])
                count, size, *values = data
                assert count == len(values)
                medians = [statistics.median(values[i:i+size]) for i in range(0, count, size)]
                answer = Counter(medians).most_common(1)[0][0]
                explanation = 'Block medians are 4, 9, 4, 5 and 8. The most frequent is 4.'
            elif n == 8:
                rows = statement.split('Question Input:', 1)[1].strip().splitlines()
                assert len(rows[1:]) == int(rows[0])
                distances = [abs(row.count('R')-row.count('L')) + abs(row.count('U')-row.count('D')) for row in rows[1:]]
                distance = max(distances)
                answer, mode = [distances.index(distance)+1, distance], 'numbers'
                instruction = 'For this check, distance means final Manhattan distance from (0,0): |x|+|y|. IDs start at 1. Enter ID and distance.'
                explanation = 'Compute final horizontal and vertical displacements for each robot, then maximise their absolute-value sum; choose the first ID on ties.'
                note = 'The printed sample conflicts with standard distance definitions. This check explicitly uses final Manhattan distance for all 32 final-input robots.'
                checkpoint = True
            elif n == 9:
                rows = statement.split('Question Input:', 1)[1].strip().splitlines()
                value = ''.join(rows[1:])
                answer, mode = ''.join(f'{char}{len(list(group))}' for char, group in groupby(value)), 'text'
                explanation = 'Scan maximal runs and emit their character followed by run length, including runs of length 1. Join wrapped lines before counting.'
                note = f'The printed length 1233 disagrees with the {len(value)} supplied characters. This check compresses the full supplied string without padding.'
            elif n == 10:
                rows = statement.split('Question Input:', 1)[1].strip().splitlines()
                value = ''.join(rows[1:])
                stack = []
                for char in value:
                    if stack and stack[-1] == char:
                        stack.pop()
                    else:
                        stack.append(char)
                answer, mode = ''.join(stack), 'text'
                explanation = 'Use a stack. Pop when the next character equals the top; otherwise push it. The final stack is the reduced string.'
                note = f'The header says 1014, but only {len(value)} characters are supplied. Use the full supplied string. The sample output also conflicts with the stated pair-removal rule; the checker follows the rule.'
        else:
            mode = 'numbers'
            if n == 1:
                answer = 2 * sum([2, 3, 1, 4, 2, 3, 2])
                instruction = 'Check the published sample: n=7, k=3, costs x=8, y=2, z=5; health [2,3,1,4,2,3,2]. Enter minimum bullets under the printed rules.'
                explanation = 'NovaStrike costs 2 per health removed. Photon costs 8 for only 3 health (worse than 6); Lumina costs 5 and can reduce the middle health by at most 1. Therefore all 17 health units cost 34 bullets.'
                note = 'The large input is malformed (its first case declares 83 robots but supplies only 35 before the next case), so it cannot be graded reliably. This check uses the complete sample; its printed answer 31 conflicts with the printed rules, which give 34.'
                checkpoint = True
            elif n == 2:
                raw = ints(statement.split('Question input:', 1)[1])
                claimed, values = raw[0], raw[1:]
                outputs = []
                while values:
                    count, k = values[:2]
                    assert 1 <= k <= count and len(values) >= count + 2
                    group, values = values[2:count+2], values[count+2:]
                    outputs.append(sorted(group, reverse=True)[k-1])
                answer = '\n'.join(map(str, outputs))
                explanation = 'The optimum is the k-th largest element: choose those k elements as singleton subarrays. Any k disjoint subarrays with average at least X would each need a distinct element at least X, proving the upper bound.'
                note = f'The header claims {claimed} cases, but only {len(outputs)} complete cases are supplied. Submit one output for each of those {len(outputs)} cases in order.'
            elif n == 3:
                rows = statement.split('\nInput\n', 1)[1].strip().splitlines()
                height, width = ints(rows[0])
                grid = rows[1:]
                assert len(grid) == height and all(len(row) == width for row in grid)
                answer = grid_energy(grid)
                explanation = 'Use Dijkstra’s algorithm on orthogonal non-wall neighbours with cost 1+(A−B)². Start and target cells have energy 0 for this check; return −1 if unreachable.'
                note = 'Practice convention: S and T have energy 0 and moves are up/down/left/right. The published sample output conflicts with that convention; this check uses the stated cost formula on the full final grid.'
                checkpoint = True
            elif n == 4:
                values = ints(statement.split('Sample Input:', 1)[1].split('Sample Output:', 1)[0])
                count, values = values[0], values[1:]
                outputs = []
                for _ in range(count):
                    size, needed = values[:2]
                    energy = values[2:size+2]
                    requirements = values[size+2:size+2+needed]
                    values = values[size+2+needed:]
                    outputs.append(minimum_energy_core(energy, requirements))
                assert not values
                answer = '\n'.join(map(str, outputs))
                instruction = 'Use all seven published sample cases. Enter one minimum energy per line.'
                explanation = 'First greedily match requirements without insertion. Otherwise try supplying each requirement with the new core; match the remaining ordered requirements against existing cores and minimise the supplied requirement value.'
                checkpoint = True
            elif n == 5:
                edges = [(1,2,5), (2,3,2), (2,4,8), (4,5,6)]
                outputs = []
                for threshold in [1,3,5,7]:
                    visited, todo = {1}, [1]
                    while todo:
                        node = todo.pop()
                        for a,b,thrill in edges:
                            other = b if node == a else a if node == b else None
                            if other and thrill >= threshold and other not in visited:
                                visited.add(other)
                                todo.append(other)
                    outputs.append(len(visited))
                answer = '\n'.join(map(str, outputs))
                instruction = 'Use the published five-attraction example, with thresholds 1, 3, 5 and 7. Enter four counts in that order.'
                explanation = 'For each threshold traverse only qualifying edges from node 1. Include node 1 itself in the count.'
                checkpoint = True
            elif n == 6:
                answer = merge_stalls([1,1,1,2])
                instruction = 'Use the published sample: N=4 and powers [1,1,1,2]. Enter the maximum obtainable power.'
                explanation = 'Merge the second and third 1 into 2, then merge that 2 with the last 2 to create power 3. Interval dynamic programming handles general inputs.'
                checkpoint = True
            elif n == 7:
                data = ints(statement.split('Question Input:', 1)[1])
                points = list(zip(data[1::2], data[2::2]))
                answer = enclosure_saving(points)
                explanation = 'Try every strictly separating horizontal and vertical cut. For each, sum the two minimum bounding-box areas. Subtract the minimum sum from the one-box area.'
                note = f'The final input declares 100 points but supplies {len(points)}. This check uses all {len(points)} supplied points.'
            elif n == 8:
                rows = statement.split('Question Input\n', 1)[1].splitlines()
                k, size = ints(rows[0])
                rankings = [ints(row) for row in rows[1:] if row.strip()]
                assert len(rankings) == k and all(sorted(row)==list(range(1,size+1)) for row in rankings)
                answer = consistent_pairs(rankings)
                explanation = 'Consider each unordered pair once, using its order in the first round. Count it only if that same order holds in all ten rounds.'
            elif n == 9:
                answer = balanced_sectors([(7,3),(5,5),(9,7),(3,1),(7,7),(5,3),(9,1)])
                instruction = 'Use the published seven-robot sample. Enter the smallest possible maximum quadrant count.'
                explanation = 'Try even barriers just past each distinct x and y coordinate. Count all four quadrants and minimise their largest count.'
                checkpoint = True
            elif n == 10:
                answer = '\n'.join(str(equal_zone_merges(values)) for values in [[1,2,3,1,1,1],[2,2,3],[0,0,0,0,0]])
                instruction = 'Use the three published sample cases. Enter the minimum merge counts in order.'
                explanation = 'Try candidate counts of equal-sum contiguous groups from largest to smallest. If a partition exists, merges = original length − group count. All-zero arrays need no merges.'
                checkpoint = True
            if n in (4,5,6,9,10):
                note = 'The linked final-input download could not be retrieved (checked 28 October 2026). This checks the complete published sample, not the unavailable final input.'
        assert answer is not None, key
        if specs is None:
            specs = [case('Your output', answer, mode, instruction)]
        add(key, specs, explanation, note,
            f'Worked independently from the November 2025 booklet, page {q["source_page"]}. No official answer key was found.', checkpoint)


def build():
    ANSWERS.clear()
    original_2023()
    festival_2024()
    march_2025()
    november_2025()
    return ANSWERS


if __name__ == '__main__':
    results = build()
    target = DATA / 'practice-answers.json'
    target.write_text(json.dumps(results, indent=2, ensure_ascii=False) + '\n')
    print(f'Wrote {len(results)} question records; {sum(bool(q["cases"]) for q in results.values())} with answer checks.')
