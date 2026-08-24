-- 1. Liegenschaft mit erweiterten Asset-Management Feldern
INSERT INTO properties (name, address, total_square_meters, construction_year, description) 
VALUES ('WEG Sonnenblick', 'Sonnenallee 45, 10243 Berlin', 1250.50, 1996, 'Wohnanlage bestehend aus 3 Wohngebäuden. Teilsaniert 2018.');

-- 2. SKR 04 Finanzkonten
INSERT INTO accounts (account_id, name, type) VALUES
(1800, 'Deutsche Bank - Girokonto (Laufender Betrieb)', 'Asset'),
(1810, 'Aareal Bank - Tagesgeld (Instandhaltungsrücklage)', 'Asset'),
(1820, 'DKB - Kündigungsgeldkonto (Anlage Rücklage)', 'Asset'),
(1830, 'MKB - Sparbrief (Festgeldanlage Rücklage)', 'Asset'),
(1200, 'Forderungen gegen Mieter (Sondereigentum)', 'Asset'),
(1220, 'Forderungen gegen Eigentümer (Hausgelder)', 'Asset'),
(4400, 'Erlöse aus Vermietung (Nettokaltmiete)', 'Revenue'),
(4410, 'Umlagenerlöse (Nebenkostenvorauszahlung)', 'Revenue'),
(5200, 'Kosten - Heizkosten Aufwand (umlagefähig)', 'Expense');

-- 3. Getrennte Bankkonten
INSERT INTO bank_accounts (property_id, account_id, account_holder, iban, bic, bank_name, purpose) VALUES
(1, 1800, 'WEG Sonnenblick', 'DE89370400440001111111', 'DBANKDEMMXXX', 'Deutsche Bank', 'Girokonto (Laufend)'),
(1, 1810, 'WEG Sonnenblick - Rücklage', 'DE22370400440002222222', 'AAREALDEFFXXX', 'Aareal Bank', 'Tagesgeld (Rücklage)'),
(1, 1820, 'WEG Sonnenblick - Rücklage', 'DE45370400440003333333', 'DKBBDEDDXXX', 'DKB', 'Kündigungsgeld (Rücklage)'),
(1, 1830, 'WEG Sonnenblick - Rücklage', 'DE66370400440004444444', 'MKBBDEDDXXX', 'Mittelbrandenburgische Sparkasse', 'Sparbrief (Rücklage)');

-- 4. Einheiten
INSERT INTO units (property_id, unit_number, floor, square_meters, unit_type) VALUES
(1, 'WE 01', 'EG links', 65.00, 'Wohnung'),
(1, 'WE 02', '1. OG rechts', 85.00, 'Wohnung'),
(1, 'WE 03', '2. OG links', 50.00, 'Wohnung');

-- 5. Eigentümer & SEPA
INSERT INTO owners (first_name, last_name, email, street_and_number, postal_code, city, bank_name, iban, bic, sepa_mandate_reference, sepa_granted_at) 
VALUES ('Maximilian', 'Müller', 'mueller@example.com', 'Hauptstraße 12a', '10115', 'Berlin', 'Berliner Sparkasse', 'DE45100500000012345678', 'PBNKDEBBXXX', 'MANDAT-OWN-MUELLER-001', '2024-01-15');
INSERT INTO unit_owner_history (unit_id, owner_id, valid_from, valid_to) VALUES (1, 1, '2024-01-01', NULL);

-- 6. Mieter & SEPA
INSERT INTO tenants (first_name, last_name, email, street_and_number, postal_code, city, bank_name, iban, bic, sepa_mandate_reference, sepa_granted_at) 
VALUES ('Andreas', 'Becker', 'becker@mieter.de', 'Sonnenallee 45', '10243', 'Berlin', 'Commerzbank', 'DE12200800000098765432', 'COBA DEFFXXX', 'MANDAT-TEN-BECKER-001', '2024-05-20');
INSERT INTO leases (unit_id, start_date, end_date, net_rent, service_charges) VALUES (1, '2024-06-01', NULL, 750.00, 180.00);
INSERT INTO lease_tenants (lease_id, tenant_id, is_main_tenant) VALUES (1, 1, TRUE);

-- 7. Umlageschlüssel
INSERT INTO unit_allocation_keys (property_id, unit_id, key_type, billing_year, numerator_value, denominator_value) VALUES
(1, 1, 'Heizkosten_Verbrauch', 2026, 3500.00, 10000.00),
(1, 2, 'Heizkosten_Verbrauch', 2026, 6500.00, 10000.00);

-- 8. Generischer Admin für Erstanmeldung (Login: admin@hausverwaltung-plattform.de / StartPasswort123!)
INSERT INTO users (email, password_hash, must_change_password) 
VALUES ('admin@hausverwaltung-plattform.de', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36Yg/Z9uTjZ3qD8Xg.6QBy2', TRUE);
INSERT INTO user_roles (user_id, role_id) VALUES (currval('users_user_id_seq'), 1);
