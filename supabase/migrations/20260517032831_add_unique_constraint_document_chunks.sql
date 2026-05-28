ALTER TABLE document_chunks
ADD CONSTRAINT document_chunks_source_file_chunk_index_project_id_key
UNIQUE (source_file, chunk_index, project_id);
