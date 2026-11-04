-- Integration checks on real PostgreSQL; all fixtures are rolled back.
\set ON_ERROR_STOP on
BEGIN;
DO $$
DECLARE
    doc_id UUID := gen_random_uuid();
    unit_vector vector := ('[1,' || repeat('0,', 766) || '0]')::vector;
    zero_vector vector := ('[' || repeat('0,', 767) || '0]')::vector;
    stored vector;
BEGIN
    INSERT INTO documents (id, source, embedding_model)
    VALUES (doc_id, 'schema-test.pdf', 'embeddinggemma');
    INSERT INTO chunks (document_id, id, position, text, embedding, page)
    VALUES (doc_id, 'chunk-1', 0, 'Test evidence', unit_vector, 2);
    SELECT embedding INTO stored FROM chunks WHERE document_id = doc_id;
    IF vector_dims(stored) != 768 OR abs(stored <=> unit_vector) > 0.000001 THEN
        RAISE EXCEPTION 'Vector round-trip or cosine distance failed';
    END IF;
    BEGIN
        INSERT INTO chunks (document_id, id, position, text, embedding)
        VALUES (doc_id, 'bad-dimension', 1, 'Invalid', '[1,0]'::vector);
        RAISE EXCEPTION 'Wrong dimension was accepted';
    EXCEPTION WHEN data_exception THEN NULL;
    END;
    BEGIN
        INSERT INTO chunks (document_id, id, position, text, embedding)
        VALUES (doc_id, 'zero-vector', 1, 'Invalid', zero_vector);
        RAISE EXCEPTION 'Zero vector was accepted';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    BEGIN
        INSERT INTO chunks (document_id, id, position, text, embedding, page)
        VALUES (doc_id, 'bad-page', 1, 'Invalid', unit_vector, 0);
        RAISE EXCEPTION 'Invalid page was accepted';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    BEGIN
        INSERT INTO chunks (document_id, id, position, text, embedding, extraction_method)
        VALUES (doc_id, 'bad-method', 1, 'Invalid', unit_vector, 'unknown');
        RAISE EXCEPTION 'Invalid extraction method was accepted';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    DELETE FROM documents WHERE id = doc_id;
    IF EXISTS (SELECT 1 FROM chunks WHERE document_id = doc_id) THEN
        RAISE EXCEPTION 'Cascade deletion failed';
    END IF;
END $$;
ROLLBACK;
