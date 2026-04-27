-- Widen documents.content_type so it accepts the new ContentType values
-- introduced after the table was first created (PRACTICE_NOTE, CLAUSE_SET,
-- KNOWLEDGE_MATERIAL). Without this, INSERTs from Note_controller fail
-- with: pymysql.err.DataError (1265, "Data truncated for column 'content_type'").
--
-- Run once on production:
--     mysql -u <user> -p <db> < widen_documents_content_type.sql
--
-- Safe to re-run: MODIFY COLUMN is idempotent for an identical definition.

-- 1) Inspect the current column definition (optional, for the operator):
--    SHOW COLUMNS FROM documents LIKE 'content_type';

-- 2) Widen the ENUM. The order here matches backend/models/metadata.py.
ALTER TABLE documents
    MODIFY COLUMN content_type ENUM(
        'template',
        'clause_set',
        'practice_note',
        'knowledge_material',
        'class',
        'resource',
        'case_law',
        'video',
        'other'
    ) NULL;

-- 3) (Optional) Backfill existing notes that were stored as 'other' due to
--    the fallback path in Note_controller._persist_note_and_tag.
--    A note row is identifiable by being linked to the canonical 'Note' tag.
UPDATE documents d
JOIN document_tags dt ON dt.document_id = d.id
JOIN tags t           ON t.id           = dt.tag_id
SET    d.content_type = 'practice_note'
WHERE  t.name = 'Note'
  AND  (d.content_type = 'other' OR d.content_type IS NULL);
