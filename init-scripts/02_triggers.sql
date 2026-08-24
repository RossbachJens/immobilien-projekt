CREATE OR REPLACE FUNCTION fn_check_journal_balance()
RETURNS TRIGGER AS $$
DECLARE
    v_debit_sum NUMERIC(12, 2);
    v_credit_sum NUMERIC(12, 2);
    v_entry_id INT;
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_entry_id := OLD.entry_id;
    ELSE
        v_entry_id := NEW.entry_id;
    END IF;

    SELECT 
        COALESCE(SUM(CASE WHEN direction = 'DEBIT' THEN amount ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN direction = 'CREDIT' THEN amount ELSE 0 END), 0)
    INTO v_debit_sum, v_credit_sum
    FROM entry_lines
    WHERE entry_id = v_entry_id;

    IF v_debit_sum <> v_credit_sum THEN
        RAISE EXCEPTION 'Buchungsfehler: Beleg ID % ist unbalanciert! Soll (DEBIT): % €, Haben (CREDIT): % €.', 
            v_entry_id, v_debit_sum, v_credit_sum;
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER trg_check_journal_balance
AFTER INSERT OR UPDATE OR DELETE ON entry_lines
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION fn_check_journal_balance();
