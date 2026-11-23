-- Renames the tables created by the first version of 002 to *_2026, keeping all data.
-- Run once in the Supabase SQL editor. Only needed if you ran 002 before 23 November 2026.
BEGIN;
ALTER TABLE public.competition_questions   RENAME TO competition_questions_2026;
ALTER TABLE public.competition_answers     RENAME TO competition_answers_2026;
ALTER TABLE public.competition_submissions RENAME TO competition_submissions_2026;
ALTER TABLE public.competition_solves      RENAME TO competition_solves_2026;
ALTER VIEW  public.competition_scoreboard  RENAME TO competition_scoreboard_2026;
ALTER INDEX public.competition_submissions_team_question RENAME TO competition_submissions_2026_team_question;

-- The function body names tables directly, so it is replaced rather than renamed.
DROP FUNCTION public.record_competition_submission(text, text, text, text, text, text, text, boolean);

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
