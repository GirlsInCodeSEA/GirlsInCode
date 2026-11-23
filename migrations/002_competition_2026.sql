-- 2026 competition (every name ends in _2026; copy this file with a new year for future competitions): questions, private answers, every submission (with code), and solves.
-- Run once in the Supabase SQL editor (Dashboard → SQL Editor → New query → paste → Run).
-- Safe to re-run. Then load the questions with: python3 scripts/seed_competition_2026.py
BEGIN;

CREATE TABLE IF NOT EXISTS public.competition_questions_2026 (
    id             text PRIMARY KEY,                 -- e.g. B1, I4, A10, ML2
    competition    text    NOT NULL DEFAULT '2026',
    position       integer NOT NULL,                 -- display order
    level          text    NOT NULL,
    theme          text,
    title          text    NOT NULL,
    points         integer NOT NULL CHECK (points >= 0),
    statement      text    NOT NULL,
    question_input text    NOT NULL DEFAULT ''
);

-- Kept in a separate table so answers are never selected alongside question text.
CREATE TABLE IF NOT EXISTS public.competition_answers_2026 (
    question_id text PRIMARY KEY REFERENCES public.competition_questions_2026 (id) ON DELETE CASCADE,
    answer      text NOT NULL
);

-- One row per attempt, right or wrong, including the uploaded code.
CREATE TABLE IF NOT EXISTS public.competition_submissions_2026 (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at     timestamptz NOT NULL DEFAULT now(),
    team_name      text    NOT NULL,
    email          text    NOT NULL,
    question_id    text    NOT NULL REFERENCES public.competition_questions_2026 (id),
    output         text    NOT NULL,
    code           text    NOT NULL,
    code_filename  text,
    classification text,
    correct        boolean NOT NULL,
    points_awarded integer NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS competition_submissions_2026_team_question
    ON public.competition_submissions_2026 (team_name, question_id, created_at);

-- First correct submission per team and question. The primary key stops double scoring.
CREATE TABLE IF NOT EXISTS public.competition_solves_2026 (
    team_name     text    NOT NULL,
    question_id   text    NOT NULL REFERENCES public.competition_questions_2026 (id),
    points        integer NOT NULL,
    solved_at     timestamptz NOT NULL DEFAULT now(),
    submission_id bigint REFERENCES public.competition_submissions_2026 (id),
    PRIMARY KEY (team_name, question_id)
);

-- Row level security on, with no policies: only the server's service key can read or write.
ALTER TABLE public.competition_questions_2026   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.competition_answers_2026     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.competition_submissions_2026 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.competition_solves_2026      ENABLE ROW LEVEL SECURITY;

-- Handy for browsing in the Table Editor; the website computes the same ranking itself.
CREATE OR REPLACE VIEW public.competition_scoreboard_2026 WITH (security_invoker = true) AS
    SELECT team_name,
           SUM(points)::integer AS score,
           COUNT(*)::integer    AS solved,
           MAX(solved_at)       AS last_solve
    FROM public.competition_solves_2026
    GROUP BY team_name
    ORDER BY score DESC, last_solve ASC;
REVOKE ALL ON public.competition_scoreboard_2026 FROM anon, authenticated;

-- Records an attempt and, if correct and not yet solved, awards the points atomically.
-- Returns the points awarded by this call (0 when wrong or already solved).
CREATE OR REPLACE FUNCTION public.record_competition_submission_2026(
    p_team_name text, p_email text, p_question_id text, p_output text,
    p_code text, p_code_filename text, p_classification text, p_correct boolean
) RETURNS integer
LANGUAGE plpgsql
SET search_path = public
AS $$
DECLARE
    v_points     integer;
    v_submission bigint;
    v_awarded    integer := 0;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM users WHERE name = p_team_name AND lower(email) = lower(p_email)) THEN
        RAISE EXCEPTION 'Unknown account';
    END IF;
    SELECT points INTO STRICT v_points FROM competition_questions_2026 WHERE id = p_question_id;

    INSERT INTO competition_submissions_2026
        (team_name, email, question_id, output, code, code_filename, classification, correct)
    VALUES
        (p_team_name, lower(p_email), p_question_id, p_output, p_code, p_code_filename, p_classification, p_correct)
    RETURNING id INTO v_submission;

    IF p_correct THEN
        INSERT INTO competition_solves_2026 (team_name, question_id, points, submission_id)
        VALUES (p_team_name, p_question_id, v_points, v_submission)
        ON CONFLICT (team_name, question_id) DO NOTHING;
        IF FOUND THEN
            v_awarded := v_points;
            UPDATE competition_submissions_2026 SET points_awarded = v_awarded WHERE id = v_submission;
        END IF;
    END IF;
    RETURN v_awarded;
END;
$$;
REVOKE ALL ON FUNCTION public.record_competition_submission_2026(text, text, text, text, text, text, text, boolean)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.record_competition_submission_2026(text, text, text, text, text, text, text, boolean)
    TO service_role;

COMMIT;
