-- Create project_logs table for real-time log streaming
CREATE TABLE IF NOT EXISTS project_logs (
    id BIGSERIAL PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    step VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for fast log retrieval by project
CREATE INDEX IF NOT EXISTS idx_project_logs_project_id ON project_logs(project_id);
CREATE INDEX IF NOT EXISTS idx_project_logs_timestamp ON project_logs(timestamp);

-- Enable Row Level Security (allow all operations for service role)
ALTER TABLE project_logs ENABLE ROW LEVEL SECURITY;

-- Service role can do anything (AI backend uses service role key)
CREATE POLICY "Service role full access" ON project_logs
    FOR ALL USING (true) WITH CHECK (true);