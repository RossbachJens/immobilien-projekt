-- =====================================================================
-- 05_skr04_kontenrahmen.sql
-- Globaler SKR-04-Basis-Kontenrahmen (property_id = NULL), kuratierte
-- Teilmenge für Immobilien-/WEG-Verwaltung.
--
-- Quelle: DATEV-Kontenrahmen nach dem Bilanzrichtlinie-Umsetzungsgesetz,
-- Standardkontenrahmen - Abschlussgliederungsprinzip (SKR 04), gültig 2026
-- (Art.-Nr. 11175). Jeder Eintrag wurde einzeln anhand der Original-
-- Seiten-Scans geprüft (nicht per OCR-Volltextextraktion übernommen -
-- das mehrspaltige Tabellenlayout des Originaldokuments lässt sich nicht
-- zuverlässig automatisiert in saubere Kontonamen zurückverwandeln).
--
-- Bewusst NUR Klassen 0-6 (Anlage-/Umlaufvermögen, Eigen-/Fremdkapital,
-- Erträge, Aufwendungen) - Klasse 7 mischt Erträge/Aufwendungen innerhalb
-- derselben Klasse und behandelt größtenteils Konzern-/Beteiligungs-
-- themen (Ergebnisabführung, Beteiligungserträge), die für eine WEG nicht
-- relevant sind. Klasse 9 (Statistik-/Vortragskonten) verletzt zudem den
-- CHECK-Constraint auf accounts.account_number (^[0-8][0-9]{3}$).
--
-- Bewusst KEINE vollständige Übernahme aller ~800+ Konten der Klassen 0-6:
-- kuratierte, für WEG-Buchhaltung tatsächlich relevante Teilmenge. Für
-- objektspezifische Zusatzkonten (z.B. "Verwaltergebühr", die im
-- generischen SKR04 keine eigene Nummer hat) steht bereits die Funktion
-- "Eigene Konten je Liegenschaft" zur Verfügung (siehe app/routers/
-- accounts.py, POST /accounts mit property_id).
--
-- WICHTIG: property_id wird hier bewusst NICHT referenziert - diese
-- Spalte existiert erst nach der Alembic-Migration 0001_property_accounts,
-- die zum Zeitpunkt der Init-Skript-Ausführung (frischer DB-Container)
-- noch nicht gelaufen ist. Alle Zeilen bekommen property_id nach dem
-- späteren ALTER TABLE automatisch NULL (= globales Konto). Nach diesem
-- Skript daher zwingend:
--   docker compose exec backend alembic upgrade head
-- (NICHT "alembic stamp head" - das würde die Migration nur als erledigt
-- markieren, ohne die Spalte tatsächlich anzulegen, siehe README.md).
--
-- Fünf Kontonummern (1200, 1800, 1810, 1820, 1830) sind absichtlich NICHT
-- enthalten - die legt bereits 04_testdata.sql mit konkreten Namen an
-- ("Deutsche Bank - Girokonto" etc.), bevor dieses Skript läuft.
-- ON CONFLICT DO NOTHING zusätzlich als Sicherheitsnetz.
-- =====================================================================

INSERT INTO accounts (account_number, account_name, account_class, type, is_active) VALUES
    -- Klasse 0 - Anlagevermögenskonten (AKTIV)
    ('0200', 'Grundstücke, grundstücksgleiche Rechte und Bauten einschließlich der Bauten auf fremden Grundstücken', '0', 'AKTIV', TRUE),
    ('0300', 'Wohnbauten', '0', 'AKTIV', TRUE),
    ('0400', 'Technische Anlagen und Maschinen', '0', 'AKTIV', TRUE),
    ('0500', 'Andere Anlagen, Betriebs- und Geschäftsausstattung', '0', 'AKTIV', TRUE),

    -- Klasse 1 - Umlaufvermögenskonten (AKTIV)
    ('1600', 'Kasse', '1', 'AKTIV', TRUE),
    ('1610', 'Nebenkasse 1', '1', 'AKTIV', TRUE),
    ('1620', 'Nebenkasse 2', '1', 'AKTIV', TRUE),
    ('1700', 'Bank (Postbank)', '1', 'AKTIV', TRUE),
    ('1840', 'Bank 4', '1', 'AKTIV', TRUE),
    ('1850', 'Bank 5', '1', 'AKTIV', TRUE),
    ('1900', 'Aktive Rechnungsabgrenzung', '1', 'AKTIV', TRUE),

    -- Klasse 3 - Fremdkapitalkonten (PASSIV)
    ('3070', 'Sonstige Rückstellungen', '3', 'PASSIV', TRUE),
    ('3150', 'Verbindlichkeiten gegenüber Kreditinstituten', '3', 'PASSIV', TRUE),
    ('3300', 'Verbindlichkeiten aus Lieferungen und Leistungen', '3', 'PASSIV', TRUE),
    ('3700', 'Verbindlichkeiten aus Steuern und Abgaben', '3', 'PASSIV', TRUE),
    ('3900', 'Passive Rechnungsabgrenzung', '3', 'PASSIV', TRUE),

    -- Klasse 4 - Betriebliche Erträge (ERTRAG)
    ('4000', 'Umsatzerlöse', '4', 'ERTRAG', TRUE),
    ('4105', 'Steuerfreie Umsätze nach § 4 Nr. 12 UStG (Vermietung und Verpachtung)', '4', 'ERTRAG', TRUE),
    ('4830', 'Sonstige betriebliche Erträge', '4', 'ERTRAG', TRUE),
    ('4860', 'Grundstückserträge', '4', 'ERTRAG', TRUE),
    ('4861', 'Erlöse aus Vermietung und Verpachtung, umsatzsteuerfrei § 4 Nr. 12 UStG', '4', 'ERTRAG', TRUE),
    ('4862', 'Erlöse aus Vermietung und Verpachtung 19 % USt', '4', 'ERTRAG', TRUE),
    ('4970', 'Versicherungsentschädigungen und Schadenersatzleistungen', '4', 'ERTRAG', TRUE),
    ('4992', 'Erträge aus Verwaltungskostenumlagen', '4', 'ERTRAG', TRUE),

    -- Klasse 5 - Betriebliche Aufwendungen (AUFWAND)
    ('5970', 'Fremdleistungen (Miet- und Pachtzinsen bewegliche Wirtschaftsgüter)', '5', 'AUFWAND', TRUE),

    -- Klasse 6 - Betriebliche Aufwendungen (AUFWAND)
    ('6000', 'Löhne und Gehälter', '6', 'AUFWAND', TRUE),
    ('6010', 'Löhne', '6', 'AUFWAND', TRUE),
    ('6020', 'Gehälter', '6', 'AUFWAND', TRUE),
    ('6221', 'Abschreibungen auf Gebäude', '6', 'AUFWAND', TRUE),
    ('6280', 'Forderungsverluste', '6', 'AUFWAND', TRUE),
    ('6303', 'Fremdleistungen/Fremdarbeiten', '6', 'AUFWAND', TRUE),
    ('6305', 'Raumkosten', '6', 'AUFWAND', TRUE),
    ('6320', 'Heizung', '6', 'AUFWAND', TRUE),
    ('6325', 'Gas, Strom, Wasser', '6', 'AUFWAND', TRUE),
    ('6330', 'Reinigung', '6', 'AUFWAND', TRUE),
    ('6335', 'Instandhaltung betrieblicher Räume', '6', 'AUFWAND', TRUE),
    ('6350', 'Grundstücksaufwendungen, betrieblich', '6', 'AUFWAND', TRUE),
    ('6400', 'Versicherungen', '6', 'AUFWAND', TRUE),
    ('6405', 'Versicherungen für Gebäude', '6', 'AUFWAND', TRUE),
    ('6450', 'Reparaturen und Instandhaltung von Bauten', '6', 'AUFWAND', TRUE),
    ('6460', 'Reparaturen und Instandhaltung von technischen Anlagen und Maschinen', '6', 'AUFWAND', TRUE),
    ('6470', 'Reparaturen und Instandhaltung von anderen Anlagen und Betriebs- und Geschäftsausstattung', '6', 'AUFWAND', TRUE),
    ('6490', 'Sonstige Reparaturen und Instandhaltung', '6', 'AUFWAND', TRUE),
    ('6800', 'Porto', '6', 'AUFWAND', TRUE),
    ('6805', 'Telefon', '6', 'AUFWAND', TRUE),
    ('6810', 'Internetkosten', '6', 'AUFWAND', TRUE),
    ('6815', 'Bürobedarf', '6', 'AUFWAND', TRUE),
    ('6825', 'Rechts- und Beratungskosten', '6', 'AUFWAND', TRUE),
    ('6827', 'Abschluss- und Prüfungskosten', '6', 'AUFWAND', TRUE),
    ('6830', 'Buchführungskosten', '6', 'AUFWAND', TRUE),
    ('6855', 'Nebenkosten des Geldverkehrs', '6', 'AUFWAND', TRUE)
ON CONFLICT (account_number) DO NOTHING;
