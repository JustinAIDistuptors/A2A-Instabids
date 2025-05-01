-- ======================================================================
-- FULL DATABASE SCHEMA – APRIL 2025 (INSTABIDS, POST CLEANUP)
-- ----------------------------------------------------------------------
-- ✅ Includes:
--   - Core entities: users, contractors, projects, bids
--   - Project photos + A2A support (artifacts, tasks)
--   - Triggers and updated_at management
--   - Memory schema: user_memories, preferences, interaction logs
-- ======================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Core User Data
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT UNIQUE NOT NULL,
  user_type TEXT NOT NULL CHECK (user_type IN ('homeowner', 'contractor')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB
);

-- Contractor-specific information
CREATE TABLE contractor_profiles (
  id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  business_name TEXT,
  service_categories TEXT[],
  service_area_description TEXT,
  portfolio_links TEXT[],
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB
);

-- Projects/Bid Requests
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  homeowner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  category TEXT,
  location_description TEXT,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'matched', 'in_progress', 'completed', 'cancelled')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  desired_outcome_description TEXT,
  metadata JSONB
);

-- Bids
CREATE TABLE bids (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  contractor_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  amount DECIMAL(10, 2),
  description TEXT,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected', 'withdrawn')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB
);

-- Project Photos
CREATE TABLE project_photos (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  storage_path TEXT NOT NULL UNIQUE,
  caption TEXT,
  photo_type TEXT NOT NULL DEFAULT 'current' CHECK (photo_type IN ('current', 'inspiration')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB
);

-- Function to update updated_at
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers
CREATE TRIGGER set_contractor_profiles_timestamp
BEFORE UPDATE ON contractor_profiles
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_projects_timestamp
BEFORE UPDATE ON projects
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_bids_timestamp
BEFORE UPDATE ON bids
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- A2A Task Tracking
CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  a2a_task_id TEXT UNIQUE NOT NULL,
  title TEXT,
  description TEXT,
  status TEXT NOT NULL CHECK (status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'CANCELLED')),
  creator_agent_id TEXT NOT NULL,
  assignee_agent_id TEXT NOT NULL,
  parent_task_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  result JSONB,
  error_message TEXT,
  metadata JSONB
);

CREATE TRIGGER set_tasks_timestamp
BEFORE UPDATE ON tasks
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_assignee ON tasks(assignee_agent_id);
CREATE INDEX idx_tasks_creator ON tasks(creator_agent_id);

-- A2A Artifact Storage
CREATE TABLE artifacts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  a2a_artifact_id TEXT UNIQUE NOT NULL,
  a2a_task_id TEXT NOT NULL REFERENCES tasks(a2a_task_id) ON DELETE CASCADE,
  creator_agent_id TEXT NOT NULL,
  type TEXT NOT NULL,
  description TEXT,
  content JSONB,
  storage_path TEXT,
  uri TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB
);

CREATE INDEX idx_artifacts_task ON artifacts(a2a_task_id);
CREATE INDEX idx_artifacts_type ON artifacts(type);

-- Memory Tables
CREATE TABLE user_memories (
  user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  memory_data JSONB NOT NULL,
  -- vector_embedding VECTOR(1536),  -- Removed due to unsupported type error
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE user_preferences (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  preference_key TEXT NOT NULL,
  preference_value JSONB NOT NULL,
  confidence FLOAT DEFAULT 0.5,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  source TEXT,
  UNIQUE(user_id, preference_key)
);

CREATE TABLE user_memory_interactions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  interaction_type TEXT NOT NULL,
  interaction_data JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER set_user_memories_timestamp
BEFORE UPDATE ON user_memories
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_user_preferences_timestamp
BEFORE UPDATE ON user_preferences
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();
