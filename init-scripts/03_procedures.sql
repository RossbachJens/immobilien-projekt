CREATE OR REPLACE PROCEDURE generate_monthly_lease_demands(p_target_date DATE)
LANGUAGE plpgsql AS $$
DECLARE
    r_lease RECORD;
    v_entry_id INT;
    v_doc_num VARCHAR(50);
    v_desc TEXT;
    
    v_acc_forderungs_miete INT := 1200; -- SKR 04: Forderungen aus L&L (Mieter)
    v_acc_erloese_kalt INT := 4400;     -- SKR 04: Erlöse aus Vermietung (Kaltmiete)
    v_acc_umlagen_nk INT := 4410;       -- SKR 04: Umlagenerlöse (Nebenkosten)
BEGIN
    v_doc_num := 'SOLL-' || TO_CHAR(p_target_date, 'YYYY-MM');
    v_desc := 'Automatische Miet-Sollstellung (SKR 04) für ' || TO_CHAR(p_target_date, 'TMMonth YYYY');

    FOR r_lease IN 
        SELECT l.lease_id, l.unit_id, u.property_id, l.net_rent, l.service_charges
        FROM leases l
        JOIN units u ON l.unit_id = u.unit_id
        WHERE l.is_active = TRUE 
          AND l.deleted_at IS NULL
          AND p_target_date BETWEEN l.start_date AND COALESCE(l.end_date, '9999-12-31')
          AND (r_lease.net_rent > 0 OR r_lease.service_charges > 0)
    LOOP
        INSERT INTO journal_entries (entry_date, document_number, description)
        VALUES (p_target_date, v_doc_num, v_desc || ' (Vertrag ID: ' || r_lease.lease_id || ')')
        RETURNING entry_id INTO v_entry_id;

        INSERT INTO entry_lines (entry_id, account_id, property_id, unit_id, lease_id, amount, direction)
        VALUES (v_entry_id, v_acc_forderungs_miete, r_lease.property_id, r_lease.unit_id, r_lease.lease_id, (r_lease.net_rent + r_lease.service_charges), 'DEBIT');

        IF r_lease.net_rent > 0 THEN
            INSERT INTO entry_lines (entry_id, account_id, property_id, unit_id, lease_id, amount, direction)
            VALUES (v_entry_id, v_acc_erloese_kalt, r_lease.property_id, r_lease.unit_id, r_lease.lease_id, r_lease.net_rent, 'CREDIT');
        END IF;

        IF r_lease.service_charges > 0 THEN
            INSERT INTO entry_lines (entry_id, account_id, property_id, unit_id, lease_id, amount, direction)
            VALUES (v_entry_id, v_acc_umlagen_nk, r_lease.property_id, r_lease.unit_id, r_lease.lease_id, r_lease.service_charges, 'CREDIT');
        END IF;
    END LOOP;
END;
$$;
