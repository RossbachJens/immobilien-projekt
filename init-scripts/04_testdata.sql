-- 1. Liegenschaft
INSERT INTO properties (name, address, total_square_meters, construction_year, description)
VALUES ('WEG Sonnenblick', 'Sonnenallee 45, 10243 Berlin', 1250.50, 1996,
        'Wohnanlage bestehend aus 3 Wohngebäuden. Teilsaniert 2018.');

-- 2. SKR 04 Finanzkonten
-- Hinweis: 03_procedures.sql verwendet SKR04-Nummern (1200, 4400, 4410, ...)
-- direkt als account_id, obwohl account_id eigentlich ein Surrogatschlüssel
-- (IDENTITY) ist und account_number die eigentliche SKR04-Nummer wäre. Bis
-- das sauber getrennt ist (03_procedures.sql müsste über account_number
-- nachschlagen), erzwingen wir hier die gewünschten IDs explizit.
INSERT INTO accounts (account_id, account_number, account_name, account_class, type, is_active)
OVERRIDING SYSTEM VALUE
VALUES
    (1800, '1800', 'Deutsche Bank - Girokonto (Laufender Betrieb)', '1', 'AKTIV', TRUE),
    (1810, '1810', 'Aareal Bank - Tagesgeld (Instandhaltungsrücklage)', '1', 'AKTIV', TRUE),
    (1820, '1820', 'DKB - Kündigungsgeldkonto (Anlage Rücklage)', '1', 'AKTIV', TRUE),
    (1830, '1830', 'MKB - Sparbrief (Festgeldanlage Rücklage)', '1', 'AKTIV', TRUE),
    (1200, '1200', 'Forderungen gegen Mieter (Sondereigentum)', '1', 'AKTIV', TRUE),
    (1220, '1220', 'Forderungen gegen Eigentümer (Hausgelder)', '1', 'AKTIV', TRUE),
    (4400, '4400', 'Erlöse aus Vermietung (Nettokaltmiete)', '4', 'ERTRAG', TRUE),
    (4410, '4410', 'Umlagenerlöse (Nebenkostenvorauszahlung)', '4', 'ERTRAG', TRUE),
    (5200, '5200', 'Kosten - Heizkosten Aufwand (umlagefähig)', '5', 'AUFWAND', TRUE);

-- Sequence weitersetzen, sonst kollidiert der nächste automatische Insert
-- (ohne OVERRIDING SYSTEM VALUE) mit den oben manuell vergebenen IDs.
SELECT setval(pg_get_serial_sequence('accounts', 'account_id'), (SELECT MAX(account_id) FROM accounts));

-- 3. Einheiten
INSERT INTO units (property_id, unit_number, floor, square_meters, unit_type) VALUES
(1, 'WE 01', 'EG links', 65.00, 'Wohnung'),
(1, 'WE 02', '1. OG rechts', 85.00, 'Wohnung'),
(1, 'WE 03', '2. OG links', 50.00, 'Wohnung');

-- 4. Eigentümer
-- iban_encrypted/bic_encrypted bleiben NULL: die Verschlüsselung braucht den
-- App-Key (PII_ENCRYPTION_KEY), den dieses SQL-Skript nicht kennt.
INSERT INTO owners (first_name, last_name, email, street_and_number, postal_code, city,
                     bank_name, iban_last4, sepa_mandate_reference, sepa_granted_at)
VALUES ('Maximilian', 'Müller', 'mueller@example.com', 'Hauptstraße 12a', '10115', 'Berlin',
        'Berliner Sparkasse', '5678', 'MANDAT-OWN-MUELLER-001', '2024-01-15');
INSERT INTO unit_owner_history (unit_id, owner_id, valid_from, valid_to) VALUES (1, 1, '2024-01-01', NULL);

-- 5. Mieter (setzt die neue email-Spalte voraus, siehe oben)
INSERT INTO tenants (first_name, last_name, email, street_and_number, postal_code, city,
                      bank_name, iban_last4, sepa_mandate_reference)
VALUES ('Andreas', 'Becker', 'becker@mieter.de', 'Sonnenallee 45', '10243', 'Berlin',
        'Commerzbank', '5432', 'MANDAT-TEN-BECKER-001');

-- tenant_id sitzt direkt auf leases - kein lease_tenants (existiert im Schema nicht).
INSERT INTO leases (unit_id, tenant_id, start_date, end_date, cold_rent, additional_costs_prepayment)
VALUES (1, 1, '2024-06-01', NULL, 750.00, 180.00);

-- 6. Umlageschlüssel
INSERT INTO unit_allocation_keys (property_id, unit_id, key_type, billing_year, numerator_value, denominator_value) VALUES
(1, 1, 'Heizkosten_Verbrauch', 2026, 3500.00, 10000.00),
(1, 2, 'Heizkosten_Verbrauch', 2026, 6500.00, 10000.00);

-- Bewusst keine User mehr hier: Der erste Admin wird per CLI angelegt
-- (app/cli.py, siehe unten), nicht mehr durch dieses Seed-Skript.