-- 0001_ref_seed.sql
CREATE TABLE IF NOT EXISTS ref_unit_dimension (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL DEFAULT ''
);

INSERT OR IGNORE INTO ref_unit_dimension(code, label) VALUES ('resistance', 'Resistance');
