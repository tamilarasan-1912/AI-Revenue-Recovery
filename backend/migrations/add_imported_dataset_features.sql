-- Adds storage for optional payment-behaviour features.
-- PostgreSQL. Existing rows remain valid and receive NULL.
ALTER TABLE imported_dataset_rows
ADD COLUMN IF NOT EXISTS features JSONB;
