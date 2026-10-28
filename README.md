# Girls In Code Website

The official website and coding competition platform for **Girls In Code**, a student-led organisation working to encourage more girls to explore computer science and technology.

Alongside providing information about Girls In Code, the platform is used to host our coding competitions. Participants can create accounts, attempt challenges, submit Python solutions, earn points, and view a live scoreboard.

One of the more experimental parts of the project is our **Human vs AI Code Classifier**, which analyses features of submitted Python code and estimates whether the code was more likely written by a human or generated using AI.

---

## About Girls In Code

Girls In Code was created to make programming and technology more approachable and accessible to young girls.

Our work includes:

- Coding competitions and hackathons
- Coding workshops
- School chapters
- Outreach initiatives
- Technology-related events and resources
- Opportunities for students to learn and build together

This website was built to give these initiatives a central platform while also providing the infrastructure needed to run our coding competitions.

---

## What the Website Does

### Coding Competitions

Participants can browse coding competitions and attempt questions across different difficulty levels.

Competition questions and answers are stored in the database, allowing new competitions to be added without having to create an entirely new judging system each time.

### Automatic Code Checking

The 2023–2025 archives now offer instant **output practice checks**: participants run their code locally, paste its output, and receive feedback for each part. There are 107 active checks with worked answers, including clearly labelled checkpoints for open-ended or incomplete originals. The withdrawn March question remains ungraded. These attempts do not execute uploaded code, require a database, or award points. See [practice sources and limitations](data/competition_questions/PRACTICE.md) for corrected keys and input assumptions.

Participants upload their Python solution to a question.

The website runs the submitted program and compares its output against the expected answer. The submission is then marked as:

- **Correct**
- **Incorrect**
- **Error**

Programs are also given a time limit so that submissions which run for too long can be stopped.

### Accounts

Participants can create an account or sign back into an existing one.

Passwords are hashed rather than stored as plain text, and session data is used to keep users signed in while they use the platform.

### Scoring and Leaderboard

When a team successfully solves a question, the points assigned to that problem are added to their score.

Correct submissions are locked after completion so that the same team cannot repeatedly earn points from the same question.

Scores from all questions are combined to create the competition leaderboard.

### Human vs AI Code Classifier

Submitted Python files can also be passed through a machine-learning model that attempts to distinguish between human-written and AI-generated code.

The classifier was built using a **Random Forest model** with features extracted directly from Python source files.

The features currently include characteristics such as:

- Average token length
- Identifier length
- Number of lines and tokens
- Naming conventions such as snake_case
- Comment density
- Blank lines
- Average line length
- Functions
- `for` and `while` loops
- Loop nesting / AST depth
- Assignments
- List comprehensions
- Loops using `.append()`

These features combine information about the **lexical style, structure, and Abstract Syntax Tree (AST)** of a program.

The extracted data is standardised before being passed into the Random Forest classifier.

> **Note:** The classifier is an experimental feature. Its prediction should not be treated as definitive proof that a piece of code was written by AI or by a human.

---

## Tech Stack

### Backend

- Python
- Flask
- Supabase

### Frontend

- HTML
- CSS
- Jinja templates

### Machine Learning

- scikit-learn
- pandas
- NumPy
- Random Forest Classifier

### Authentication

- Flask sessions
- Passlib
- Argon2 password hashing

---

## Project Structure

```text
GirlsInCodeWebsite/
│
├── ai_samples/
│   └── Sample AI-generated Python programs used for classifier training
│
├── human_samples/
│   └── Sample human-written Python programs used for classifier training
│
├── static/
│   └── CSS, images and other static website assets
│
├── templates/
│   └── HTML / Jinja templates for the website
│
├── app.py
│   └── Main Flask application and website routes
│
├── db.py
│   └── Supabase connection
│
├── extract_all_features.py
│   └── Extracts code features used by the AI classifier
│
├── train_model.py
│   └── Trains and evaluates the Random Forest classifier
│
├── model.pkl
│   └── Saved trained classifier
│
├── scaler.pkl
│   └── Saved feature scaler
│
├── features.csv
│   └── Extracted training features
│
├── sorted_file.csv
│   └── Processed training dataset
│
├── feature_importance.png
│   └── Visualisation of Random Forest feature importance
│
├── requirements.txt
│   └── Python dependencies
│
└── README.md
```

---

## How the AI Classifier Works

The classifier pipeline is split into three main stages.

### 1. Collect Samples

Python files are placed into:

```text
human_samples/
ai_samples/
```

Each file is labelled depending on whether it belongs to the human or AI dataset.

### 2. Extract Features

Run:

```bash
python3 extract_all_features.py
```

The program analyses each Python file and extracts lexical, structural and AST-based features.

These are stored in:

```text
features.csv
sorted_file.csv
```

### 3. Train the Model

Run:

```bash
python3 train_model.py
```

The training script:

1. Loads the extracted dataset
2. Separates the features and labels
3. Standardises the features
4. Splits the dataset into training and testing sets
5. Trains a Random Forest classifier
6. Evaluates its accuracy
7. Performs cross-validation
8. Calculates feature importance
9. Saves the trained model and scaler

The resulting files are:

```text
model.pkl
scaler.pkl
```

These are loaded by the Flask application whenever a submitted program needs to be classified.

---

## Running the Website Locally

### 1. Clone the repository

```bash
git clone https://github.com/NatalieWongg/GirlsInCodeWebsite.git
cd GirlsInCodeWebsite
```

### 2. Create a virtual environment

Use Python 3.9–3.12 with the pinned dependencies. Virtual environments are machine-specific; recreate `venv` if its interpreter no longer exists.

macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Create a `.env` file in the root directory:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_supabase_service_key
SECRET_KEY=your_flask_secret_key
```

Do **not** commit your `.env` file or Supabase credentials to GitHub.

### 5. Set up Supabase

The current website expects database tables for:

```text
users
questions
answers
scores
submissions_lock
```

These store information including user accounts, competition questions, expected answers, scores, and completed submissions.

Apply [`migrations/001_atomic_scoring.sql`](migrations/001_atomic_scoring.sql) in the Supabase SQL editor before enabling scored submissions. It adds unique email/team-name indexes and the transactional `award_submission` function, restricted to the service role. Resolve existing duplicate accounts before applying it. The migration does not repair historical duplicate scores.

### 6. Build the optional classifier

If model files are missing or incompatible, regenerate them using the same environment as the web server:

```bash
python3 extract_all_features.py
python3 train_model.py
```

Rebuild both the dataset and model after changing feature extraction. Missing model files disable classification without preventing the website from starting.

### 7. Start the Flask server

```bash
flask --app app run --debug
```

Alternatively:

```bash
python3 app.py
```

Then open the local Flask address shown in the terminal, usually:

```text
http://127.0.0.1:5000
```

---

## Competition Flow

A simplified version of what happens during a competition is:

```text
Participant signs in
        ↓
Chooses a competition
        ↓
Selects a coding question
        ↓
Writes and uploads a Python solution
        ↓
Code features are extracted
        ↓
AI/Human classifier makes a prediction
        ↓
Program is executed
        ↓
Output is checked against the expected answer
        ↓
Correct submission → points awarded
        ↓
Question locked for that team
        ↓
Leaderboard updated
```

---

## Database

Supabase is currently used as the website's database.

The application works with the following main tables:

### `users`

Stores participant accounts.

Examples of fields used by the application:

```text
name
email
password_hash
points
```

### `questions`

Stores competition questions and metadata.

The application currently uses information such as:

```text
id
title
year
level
points
```

### `answers`

Stores the expected output for each question.

```text
id
answer_text
```

### `scores`

Stores points awarded during competitions.

```text
team_name
email
score
competition
```

### `submissions_lock`

Records questions that a team has already successfully completed.

```text
team_name
question_id
solved
```

---

## Security Note

Uploaded-code execution is **disabled by default** because the local subprocess runner is not a security sandbox. Browsing questions, accounts, and the scoreboard still work.

For trusted local testing only, set `ENABLE_UNSAFE_CODE_EXECUTION=1` in `.env` and restart the server. Never enable this setting on a public deployment: submitted programs still have the operating-system permissions of the web server. A clean environment, temporary working directory, upload size limit, and timeout do not prevent filesystem access or resource exhaustion. Public execution requires a separate sandboxed runner.

Set a stable, random `SECRET_KEY` shared by all workers. Without one, a temporary key is generated at startup and sessions will not survive restarts or work reliably across multiple workers. Debug mode is off for `python3 app.py`; use `flask --app app run --debug` only for local development.

This is suitable for development and controlled testing, but **should not be treated as a secure production sandbox for arbitrary public code**.

Before opening unrestricted code submission to the public, submitted programs should be isolated using a proper sandbox or containerised execution environment with restrictions on areas such as:

- File-system access
- Network access
- Memory usage
- CPU usage
- Process creation
- Execution time

This is an area we would like to improve as the platform develops.

---

## Current Development

The platform is actively being developed and redesigned.

Some areas we are working on include:

- Improving the overall website design and user experience
- Expanding competition functionality
- Improving the coding submission system
- Developing the Girls In Code organisation pages
- Improving the leaderboard and competition interface
- Making it easier to add future competitions
- Expanding and evaluating the Human vs AI Code Classifier
- Preparing the website for public deployment

---

## Contributing

Girls In Code is maintained by students, and different members of the technical team contribute to different parts of the website.

If you are working on the repository:

1. Pull the latest version of the project
2. Create a separate branch for your feature
3. Make and test your changes
4. Commit your work with a clear commit message
5. Push your branch
6. Open a pull request for review

For example:

```bash
git checkout -b feature-name
git add .
git commit -m "Add competition page redesign"
git push origin feature-name
```

Please avoid pushing major changes directly to `main` without checking with the team first.

---

## Our Goal

This project started as a way to run Girls In Code competitions more effectively, but we hope to develop it into something larger: a central platform for our events, chapters, resources and community.

Most importantly, we want Girls In Code to be a space where girls can **try coding, challenge themselves, build things, and meet other people who are interested in technology**.

The website is one part of helping us make that possible.

## Regression tests

```bash
python3 -m unittest discover -s tests -v
```

The tests use an in-memory database double and never query or write the connected Supabase database. They cover routes, authentication, uploads, judging, scoring RPC calls, pagination, subprocess input/timeouts, and feature extraction. Applying the SQL migration and verifying concurrent awards against a staging database are separate deployment checks.
