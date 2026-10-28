-- Run once in the Supabase SQL editor against the existing application tables.
-- Resolve duplicate emails (case-insensitive) or team names before applying.
BEGIN;
CREATE UNIQUE INDEX IF NOT EXISTS users_email_normalized_unique ON public.users (lower(email));
CREATE UNIQUE INDEX IF NOT EXISTS users_team_name_unique ON public.users (name);
UPDATE public.users SET email = lower(trim(email));

CREATE OR REPLACE FUNCTION public.award_submission(
    p_team_name text, p_email text, p_question_id integer
) RETURNS boolean
LANGUAGE plpgsql
SET search_path = public
AS $$
DECLARE
    question_row public.questions%ROWTYPE;
BEGIN
    -- Serialize awards for the same team/question across all web workers.
    PERFORM pg_advisory_xact_lock(hashtext(p_team_name), p_question_id);
    IF NOT EXISTS (SELECT 1 FROM public.users WHERE name = p_team_name AND email = p_email) THEN
        RAISE EXCEPTION 'Unknown account';
    END IF;
    SELECT * INTO STRICT question_row FROM public.questions WHERE id = p_question_id;
    IF EXISTS (
        SELECT 1 FROM public.submissions_lock
        WHERE team_name = p_team_name AND question_id = p_question_id AND solved = true
    ) THEN
        RETURN false;
    END IF;
    INSERT INTO public.scores (team_name, email, score, competition)
        VALUES (p_team_name, p_email, COALESCE(question_row.points, 0), question_row.year);
    DELETE FROM public.submissions_lock WHERE team_name = p_team_name AND question_id = p_question_id;
    INSERT INTO public.submissions_lock (team_name, question_id, solved)
        VALUES (p_team_name, p_question_id, true);
    RETURN true;
END;
$$;
-- Only the server's service key may award points; browser clients must not call this RPC.
REVOKE ALL ON FUNCTION public.award_submission(text, text, integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.award_submission(text, text, integer) TO service_role;
COMMIT;
