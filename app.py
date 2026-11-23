from pathlib import Path
import json
import os
import pickle
import secrets
import signal
import subprocess
import sys
import tempfile
from datetime import timedelta

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for
from dotenv import load_dotenv
from passlib.hash import argon2
from postgrest.exceptions import APIError
import pandas as pd
from httpx import HTTPError

import competition
from db import supabase
from extract_all_features import extract_all_features
from practice import answer_keys, check_answers

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY') or secrets.token_hex(32),
    MAX_CONTENT_LENGTH=1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    # Local Python subprocesses cannot safely execute arbitrary public uploads.
    ENABLE_UNSAFE_CODE_EXECUTION=os.getenv('ENABLE_UNSAFE_CODE_EXECUTION') == '1',
    CODE_TIMEOUT=5,
    ENABLE_OTHER_INITIATIVES=False,
    # Shared by the homepage and fundraising page.
    FUNDRAISING_RAISED=4000,
    FUNDRAISING_TARGET=10000,
    # Supabase tables for this competition all end in _<year>, e.g. competition_questions_2026.
    COMPETITION_YEAR='2026',
    # Competition day, Malaysia time (UTC+8). Override with env vars to rehearse locally.
    COMPETITION_START=competition.parse_time(os.getenv('COMPETITION_START', '2026-11-28T09:00:00+08:00')),
    COMPETITION_END=competition.parse_time(os.getenv('COMPETITION_END', '2026-11-28T17:00:00+08:00')),
    # Comma-separated emails that can open /admin/submissions.
    ADMIN_EMAILS={e.strip().lower() for e in os.getenv('ADMIN_EMAILS', '').split(',') if e.strip()},
    # Signed-in users only see the competition dashboard, not the public site.
    DASHBOARD_LOCKDOWN=True,
)

model = scaler = None


def load_classifier():
    global model, scaler
    try:
        with (BASE_DIR / 'model.pkl').open('rb') as stream:
            loaded_model = pickle.load(stream)
        with (BASE_DIR / 'scaler.pkl').open('rb') as stream:
            loaded_scaler = pickle.load(stream)
        model, scaler = loaded_model, loaded_scaler
    except (OSError, ValueError, ImportError, AttributeError, EOFError, pickle.UnpicklingError):
        app.logger.warning('Classifier unavailable; run feature extraction and model training.')


load_classifier()


def csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_urlsafe(32)
    return session['_csrf_token']


app.jinja_env.globals['csrf_token'] = csrf_token
app.jinja_env.globals['practice_key'] = lambda key: answer_keys().get(key)


@app.before_request
def validate_request():
    if request.method == 'POST':
        expected = session.get('_csrf_token', '')
        supplied = request.form.get('csrf_token', '')
        if not expected or not secrets.compare_digest(expected.encode(), supplied.encode()):
            abort(400, description='The form expired. Reload the page and try again.')


# Pages a signed-in competitor can still reach; everything else goes to the dashboard.
DASHBOARD_ENDPOINTS = {'dashboard', 'dashboard_question', 'admin_submissions', 'logout', 'static'}


@app.before_request
def competition_lockdown():
    if (app.config['DASHBOARD_LOCKDOWN'] and session.get('user_email')
            and request.endpoint not in DASHBOARD_ENDPOINTS):
        return redirect(url_for('dashboard'))


def database():
    if supabase is None:
        abort(503, description='The database is not configured.')
    return supabase


def get_question(question_id):
    rows = database().table('questions').select('*').eq('id', question_id).execute().data
    if not rows:
        abort(404, description='Question not found.')
    return rows[0]


def get_answer(question_id):
    rows = database().table('answers').select('answer_text').eq('question_id', question_id).execute().data
    return rows[0].get('answer_text') if rows else None


def run_code(filepath, input_text=''):
    """Run trusted local code only. Return output and an explicit execution error."""
    if not app.config['ENABLE_UNSAFE_CODE_EXECUTION']:
        return '', 'Code execution is unavailable on this server.'
    # A clean environment and working directory reduce accidental access, but are NOT a sandbox.
    with tempfile.TemporaryDirectory() as workdir:
        try:
            process = subprocess.Popen(
                [sys.executable, '-I', str(Path(filepath).resolve())],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding='utf-8', errors='replace', cwd=workdir,
                env={'PATH': os.defpath, 'PYTHONIOENCODING': 'utf-8'},
                start_new_session=os.name == 'posix',
            )
            try:
                stdout, stderr = process.communicate(
                    input='' if input_text is None else str(input_text),
                    timeout=app.config['CODE_TIMEOUT'],
                )
            except subprocess.TimeoutExpired:
                if os.name == 'posix':
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                process.communicate()
                return '', 'Error: Program took too long to run.'
            if process.returncode:
                return stdout, f'Error:\n{stderr}'
            return stdout, None
        except OSError:
            app.logger.exception('Failed to start code runner')
            return '', 'Error: Unable to start the Python interpreter.'


def classify(path):
    """Experimental AI/human estimate for a Python file; never used for scoring."""
    if model is None or scaler is None:
        return 'Unavailable'
    try:
        features = extract_all_features(path)
        if 'error' in features:
            raise ValueError(features['error'])
        frame = pd.DataFrame([features])
        if hasattr(scaler, 'feature_names_in_'):
            frame = frame[list(scaler.feature_names_in_)]
        return str(model.predict(scaler.transform(frame))[0])
    except Exception:
        app.logger.warning('Could not classify submission', exc_info=True)
        return 'Unavailable'


def judge_submission(question, answer):
    if answer is None:
        return None, 'This question does not have an answer configured yet.', None
    upload = request.files.get('code_file')
    if not upload or not upload.filename.lower().endswith('.py'):
        return None, 'Please upload a Python (.py) file.', None
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'submission.py'
        upload.save(path)
        if path.stat().st_size == 0:
            return None, 'The uploaded file is empty.', None
        classification = classify(path)
        output, error = run_code(path, question.get('your_input', ''))
        result = error or ('Correct' if output.strip() == str(answer).strip() else 'Incorrect')
        return output, result, classification


@app.route('/')
def home():
    return render_template('home.html', raised=app.config['FUNDRAISING_RAISED'],
                           target=app.config['FUNDRAISING_TARGET'])


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/fundraising')
def fundraising():
    return render_template('fundraising.html', raised=app.config['FUNDRAISING_RAISED'],
                           target=app.config['FUNDRAISING_TARGET'])


@app.route('/other-initiatives')
def other_initiatives():
    if not app.config['ENABLE_OTHER_INITIATIVES']:
        abort(404)
    return render_template('other_initiatives.html')


@app.route('/competitions')
def competitions():
    return render_template('competitions.html')


@app.route('/competitions/2026')
def competitions_2026():
    # Announcement only: unreleased questions and keys are never loaded here.
    return render_template('competitions_2026.html')


@app.route('/hackathon')
def hackathon():
    return render_template('hackathons.html')


@app.route('/hackathon/2025')
def hackathon_2025():
    return render_template('hackathon.html')


@app.route('/hackathon/2025/scoreboard')
def hackathon_scoreboard_2025():
    return render_template('hackathon_scoreboard.html')


@app.route('/competitions/2025')
def competitions_2025():
    return render_template('competitions_2025.html')


@app.route('/competitions/2025/scoreboard')
def competition_scoreboard_2025():
    return render_template('scoreboard.html')


def leaderboard():
    # Supabase returns at most one page unless ranges are requested explicitly.
    totals = {}
    offset = 0
    while True:
        rows = (database().table('scores').select('*').order('team_name').order('competition').order('email').order('score')
                .range(offset, offset + 999).execute().data or [])
        for row in rows:
            team = row.get('team_name')
            if team:
                totals[team] = totals.get(team, 0) + (row.get('score') or 0)
        if not rows:
            break
        offset += len(rows)
    return [{'team': team, 'score': score}
            for team, score in sorted(totals.items(), key=lambda item: (-item[1], item[0]))]


@app.route('/scoreboard')
def scoreboard():
    return redirect(url_for('competition_scoreboard_2025'))


@app.route('/api/leaderboard')
def api_leaderboard():
    return jsonify(leaderboard())


def november_booklet_questions():
    return json.loads((BASE_DIR / 'data/competition_questions/2025-november.json').read_text(encoding='utf-8'))


def march_booklet_questions():
    return json.loads((BASE_DIR / 'data/competition_questions/2025-march.json').read_text(encoding='utf-8'))


def competition_questions(year, template):
    levels = {level: [] for level in ('beginner', 'intermediate', 'advanced')}
    practice_available = supabase is not None
    if practice_available:
        try:
            for level in levels:
                levels[level] = (supabase.table('questions').select('title,id')
                                 .eq('year', year).eq('level', level.title())
                                 .order('id').execute().data or [])
        except (HTTPError, APIError):
            app.logger.warning('Competition practice questions are temporarily unavailable.')
            practice_available = False
            levels = {level: [] for level in levels}
    month = 'november' if year == '2025 November' else 'march'
    booklet = november_booklet_questions() if month == 'november' else march_booklet_questions()
    return render_template(template, **levels, booklet_questions=booklet,
                           booklet_endpoint=f'{month}_booklet_question',
                           practice_available=practice_available)


@app.route('/competitions/2025/november/questions/<level>/<int:number>')
def november_booklet_question(level, number):
    return render_booklet_question('november', level, number)


@app.route('/competitions/2025/march/questions/<level>/<int:number>')
def march_booklet_question(level, number):
    return render_booklet_question('march', level, number)


def render_booklet_question(month, level, number):
    questions = november_booklet_questions() if month == 'november' else march_booklet_questions()
    item = next((q for q in questions if q['level'].lower() == level and q['number'] == number), None)
    if item is None:
        abort(404)
    index = questions.index(item)
    return render_template('booklet_question.html', question=item,
                           edition=f'{month.title()} 2025', month=month,
                           archive_endpoint='y2025n' if month == 'november' else 'y2025m',
                           booklet_endpoint=f'{month}_booklet_question',
                           previous=questions[index - 1] if index else None,
                           next_question=questions[index + 1] if index + 1 < len(questions) else None)


@app.route('/2025m')
def y2025m():
    return competition_questions('2025 March', '2025m.html')


@app.route('/2025n')
def y2025n():
    return competition_questions('2025 November', '2025n.html')


@app.route('/2024')
def y2024():
    questions = json.loads((BASE_DIR / 'data/competition_questions/2024.json').read_text(encoding='utf-8'))
    return render_template('2024.html', questions=questions)


@app.route('/2023')
def y2023():
    questions = questions_2023()
    themes = list(dict.fromkeys(question['theme'] for question in questions))
    return render_template('2023.html', questions=questions, themes=themes)


def questions_2023():
    return json.loads((BASE_DIR / 'data/competition_questions/2023.json').read_text(encoding='utf-8'))


@app.route('/competitions/2023/questions/<int:number>')
def question_2023(number):
    questions = questions_2023()
    question = next((item for item in questions if item['number'] == number), None)
    if question is None:
        abort(404)
    index = questions.index(question)
    return render_template('question_2023.html', question=question,
                           previous=questions[index - 1] if index else None,
                           next_question=questions[index + 1] if index + 1 < len(questions) else None)


def practice_destination(key):
    """Resolve an answer key to a local question URL, never a supplied redirect."""
    parts = key.split('-')
    if parts[0] == '2023':
        return url_for('question_2023', number=int(parts[1]))
    if parts[0] == '2024':
        return url_for('y2024') + '#question-' + parts[1]
    if parts[0] == 'database':
        return url_for('question', question_id=int(parts[1]))
    return url_for(f'{parts[1]}_booklet_question', level=parts[2], number=int(parts[3]))


def database_practice_key(answer):
    return dict(cases=[] if answer is None else [dict(
        label='Your output', expected=str(answer), mode='text',
        instructions='Use Your input above. Paste your program output, without input prompts.')],
        checkpoint=False, explanation='Compare your output for the stated input with the configured answer.',
        source='Existing practice question answer key.',
        note='An answer has not been configured for this question.' if answer is None else '')


@app.route('/practice/check/<key>', methods=['POST'])
def check_practice(key):
    practice = answer_keys().get(key)
    if key.startswith('database-') and key[9:].isdigit():
        question_id = int(key[9:])
        get_question(question_id)
        practice = database_practice_key(get_answer(question_id))
    if practice is None:
        abort(404)
    values = [request.form.get(f'answer_{i}', '') for i in range(len(practice['cases']))]
    result = check_answers(practice, values)
    status = 422 if result['status'] == 'invalid' else 200
    if request.accept_mimetypes.best == 'application/json':
        return jsonify(result), status
    return render_template('practice_result.html', practice_id=key, practice=practice,
                           result=result, submitted=values,
                           back_url=practice_destination(key)), status


@app.route('/beginner/q1')
def q1():
    return redirect(url_for('question', question_id=1))


@app.route('/question/<int:question_id>', methods=['GET', 'POST'])
def question(question_id):
    item = get_question(question_id)
    answer = get_answer(question_id)
    output = result = classification = None
    if request.method == 'POST':
        output, result, classification = judge_submission(item, answer)
    return render_template('question.html', question=item, answer=answer, output=output,
                           result=result, classification=classification,
                           practice=database_practice_key(answer),
                           practice_id=f'database-{question_id}')


@app.route('/submissions/<int:question_id>', methods=['GET', 'POST'])
def submissions(question_id):
    if not session.get('user_email') or not session.get('user_name'):
        flash('Please sign in first.')
        return redirect(url_for('signIn'))
    item = get_question(question_id)
    team_name = session['user_name']
    locks = (database().table('submissions_lock').select('*').eq('team_name', team_name)
             .eq('question_id', question_id).eq('solved', True).execute().data)
    output = classification = result = None
    addscore = 0
    solved = bool(locks)
    if solved:
        result = 'Already solved'
    elif request.method == 'POST':
        output, result, classification = judge_submission(item, get_answer(question_id))
        if result == 'Correct':
            # The database transaction makes awarding points and locking a question atomic.
            try:
                awarded = database().rpc('award_submission', {
                    'p_team_name': team_name, 'p_email': session['user_email'],
                    'p_question_id': question_id,
                }).execute().data
            except APIError:
                app.logger.exception('Could not record submission')
                result = 'Correct, but your score could not be saved. Please try again.'
            else:
                solved = True
                if awarded:
                    addscore = item.get('points') or 0
                    result = 'Correct! Your submission is now locked.'
                else:
                    result = 'Already solved'
    return render_template('submissions.html', question=item, output=output, result=result,
                           classification=classification, addscore=addscore, solved=solved)


def ctable(name):
    """Year-specific competition table/function name, e.g. competition_questions_2026."""
    year = app.config['COMPETITION_YEAR']
    if name == 'record_submission':
        return f'record_competition_submission_{year}'
    return f'competition_{name}_{year}'


def fetch_all(table, columns, order, **filters):
    """Every matching row; Supabase caps a single response at 1,000 rows."""
    rows, offset = [], 0
    while True:
        query = database().table(table).select(columns)
        for column, value in filters.items():
            query = query.eq(column, value)
        for column in order:
            query = query.order(column)
        page = query.range(offset, offset + 999).execute().data or []
        rows.extend(page)
        if len(page) < 1000:
            return rows
        offset += len(page)


def competition_state():
    start, end = app.config['COMPETITION_START'], app.config['COMPETITION_END']
    local_start, local_end = (moment.astimezone(competition.MALAYSIA) for moment in (start, end))
    hours = []
    tick = local_start.replace(minute=0, second=0, microsecond=0)
    while tick <= local_end:
        hours.append({'label': f'{tick:%H}:00',
                      'at': max(0.0, min(1.0, (tick - local_start) / (local_end - local_start)))})
        tick += timedelta(hours=1)
    return {
        'phase': competition.phase(start, end),
        'start_iso': start.isoformat(), 'end_iso': end.isoformat(),
        'now_iso': competition.now().isoformat(),
        'start_day': f'{local_start:%A} {local_start.day} {local_start:%B %Y}',
        'start_time': f'{local_start:%H:%M}', 'end_time': f'{local_end:%H:%M}',
        'hours': hours,
    }


def scoreboard_rows():
    return competition.rank(fetch_all(ctable('solves'), 'team_name,question_id,points,solved_at',
                                      ('team_name', 'question_id')))


@app.context_processor
def admin_flag():
    return {'is_admin': session.get('user_email') in app.config['ADMIN_EMAILS']}


def require_competitor():
    if not session.get('user_email') or not session.get('user_name'):
        flash('Please sign in first.')
        return redirect(url_for('signIn'))
    return None


@app.route('/dashboard')
def dashboard():
    if (response := require_competitor()):
        return response
    state = competition_state()
    team = session['user_name']
    tiers, board, solved, unavailable = {}, [], set(), False
    try:
        # Titles stay on the server until the competition starts.
        columns = 'id,level,points,position' + ('' if state['phase'] == 'before' else ',title,theme')
        questions = (database().table(ctable('questions')).select(columns)
                     .eq('competition', app.config['COMPETITION_YEAR']).order('position').execute().data or [])
        for item in questions:
            tiers.setdefault(item['level'], []).append(item)
        if state['phase'] != 'before':
            board = scoreboard_rows()
            solved = {row['question_id'] for row in fetch_all(
                ctable('solves'), 'question_id', ('question_id',), team_name=team)}
    except (HTTPError, APIError):
        app.logger.warning('Competition data is temporarily unavailable.', exc_info=True)
        unavailable = True
    me = next((row for row in board if row['team'] == team), None)
    return render_template('dashboard.html', state=state, tiers=tiers, board=board, me=me,
                           solved=solved, unavailable=unavailable, colours=competition.LEVEL_COLOURS,
                           total_points=sum(q['points'] for items in tiers.values() for q in items))


def read_code_upload():
    """Return (filename, text) for the uploaded solution, or raise ValueError with a reason."""
    upload = request.files.get('code_file')
    if not upload or not upload.filename:
        raise ValueError('Attach the code file you used to get this output.')
    filename = Path(upload.filename).name[:200]
    if not filename.lower().endswith(('.py', '.ipynb')):
        raise ValueError('Upload a Python file (.py or .ipynb).')
    data = upload.read(competition.MAX_CODE_BYTES + 1)
    if not data.strip():
        raise ValueError('The uploaded file is empty.')
    if len(data) > competition.MAX_CODE_BYTES:
        raise ValueError('The code file is too large (200 KB maximum).')
    return filename, data.decode('utf-8', errors='replace').replace('\x00', '')


@app.route('/dashboard/<question_id>', methods=['GET', 'POST'])
def dashboard_question(question_id):
    if (response := require_competitor()):
        return response
    state = competition_state()
    if state['phase'] == 'before':
        flash('Questions unlock when the competition starts.')
        return redirect(url_for('dashboard'))
    rows = (database().table(ctable('questions'))
            .select('id,level,theme,title,points,statement,question_input,position')
            .eq('id', question_id).eq('competition', app.config['COMPETITION_YEAR']).execute().data)
    if not rows:
        abort(404)
    item = rows[0]
    team, email = session['user_name'], session['user_email']
    solved = bool(database().table(ctable('solves')).select('question_id')
                  .eq('team_name', team).eq('question_id', question_id).execute().data)
    if request.method == 'POST':
        output = request.form.get('output', '')
        if state['phase'] != 'live':
            flash('Submissions are closed.', 'error')
        elif solved:
            flash('You have already solved this question.', 'correct')
        elif not output.strip() or len(output) > competition.MAX_OUTPUT_CHARS:
            flash('Paste the output your program printed (up to 20,000 characters).', 'error')
        else:
            try:
                filename, code = read_code_upload()
            except ValueError as problem:
                flash(str(problem), 'error')
                return redirect(url_for('dashboard_question', question_id=question_id))
            classification = None
            if filename.lower().endswith('.py'):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / 'submission.py'
                    path.write_text(code, encoding='utf-8')
                    classification = classify(path)
            answers = (database().table(ctable('answers')).select('answer')
                       .eq('question_id', question_id).execute().data)
            if not answers:
                flash('This question has no answer configured yet. Please tell an organiser.', 'error')
                return redirect(url_for('dashboard_question', question_id=question_id))
            correct = competition.is_correct(output, answers[0]['answer'])
            try:
                awarded = database().rpc(ctable('record_submission'), {
                    'p_team_name': team, 'p_email': email, 'p_question_id': question_id,
                    'p_output': output.strip(), 'p_code': code, 'p_code_filename': filename,
                    'p_classification': classification, 'p_correct': correct,
                }).execute().data
            except (HTTPError, APIError):
                app.logger.exception('Could not record competition submission')
                flash('Your submission could not be saved. Please try again.', 'error')
            else:
                if correct and awarded:
                    flash(f'Correct! +{awarded} points.', 'correct')
                elif correct:
                    flash('Correct. This question was already solved, so no extra points.', 'correct')
                else:
                    flash('Not quite. Check your output against the question input and try again.', 'error')
        return redirect(url_for('dashboard_question', question_id=question_id))
    attempts = (database().table(ctable('submissions'))
                .select('created_at,correct,points_awarded,output,code_filename')
                .eq('team_name', team).eq('question_id', question_id)
                .order('created_at', desc=True).limit(20).execute().data or [])
    order = [row['id'] for row in (database().table(ctable('questions')).select('id')
                                   .eq('competition', app.config['COMPETITION_YEAR']).order('position').execute().data or [])]
    index = order.index(question_id) if question_id in order else -1
    return render_template('dashboard_question.html', state=state, question=item, solved=solved,
                           attempts=attempts, colour=competition.LEVEL_COLOURS.get(item['level'], 'c-pink'),
                           previous=order[index - 1] if index > 0 else None,
                           next_question=order[index + 1] if 0 <= index < len(order) - 1 else None)


@app.route('/admin/submissions')
def admin_submissions():
    if session.get('user_email') not in app.config['ADMIN_EMAILS']:
        abort(404)
    filters = {key: request.args[key] for key in ('team_name', 'question_id') if request.args.get(key)}
    rows = fetch_all(ctable('submissions'), '*', ('id',), **filters)
    rows.reverse()
    return render_template('admin_submissions.html', submissions=rows, board=scoreboard_rows(),
                           filters=filters, state=competition_state())


@app.route('/signIn', methods=['GET', 'POST'])
def signIn():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        action = request.form.get('action')
        if action not in ('login', 'register') or not email or '@' not in email or not password or len(password) > 4096:
            flash('Please enter a valid email and password.')
            return redirect(url_for('signIn'))
        existing = database().table('users').select('*').eq('email', email).execute().data
        if action == 'login':
            user = existing[0] if existing else None
            try:
                verified = bool(user and argon2.verify(password, user['password_hash']))
            except (ValueError, TypeError, KeyError):
                verified = False
            if not verified:
                flash('Incorrect email or password.')
                return redirect(url_for('signIn'))
            name, email = user['name'], user['email']
        else:
            if existing:
                flash('This email already has an account. Please sign in.')
                return redirect(url_for('signIn'))
            if not name:
                flash('Please enter a name / team name.')
                return redirect(url_for('signIn'))
            if database().table('users').select('name').eq('name', name).execute().data:
                flash('This name / team name is already in use.')
                return redirect(url_for('signIn'))
            try:
                database().table('users').insert({
                    'email': email, 'name': name, 'password_hash': argon2.hash(password), 'points': 0,
                }).execute()
            except APIError as exc:
                if exc.code != '23505':
                    raise
                flash('This email or team name is already in use.')
                return redirect(url_for('signIn'))
        session.clear()
        session['user_email'], session['user_name'] = email, name
        flash('Logged in!' if action == 'login' else 'Account created!')
        return redirect(url_for('dashboard'))
    return render_template('signIn.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out!')
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG') == '1')
#flask --app app run --debug
