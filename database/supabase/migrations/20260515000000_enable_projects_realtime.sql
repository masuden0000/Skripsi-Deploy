-- Enable Supabase Realtime for the projects table
-- This allows frontend to subscribe to status changes without polling
ALTER PUBLICATION supabase_realtime ADD TABLE projects;
