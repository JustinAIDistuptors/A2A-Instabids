-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Core User Data
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT UNIQUE NOT NULL,
  -- Expand user types later as needed (property_manager, labor_contractor)
  user_type TEXT NOT NULL CHECK (user_type IN ('homeowner', 'contractor')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  -- Store preferences, maybe last_login, etc.
  metadata JSONB
);

-- Contractor-specific information
CREATE TABLE contractor_profiles (
  -- Link to users table, ensure deletion cascades
  id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  business_name TEXT,
  -- Array of text for service categories (e.g., ['plumbing', 'electrical'])
  service_categories TEXT[],
  -- Simple text description for service area initially
  service_area_description TEXT,
  -- Store links to portfolio items/images
  portfolio_links TEXT[],
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  -- Store availability, certificates, specific details
  metadata JSONB
);

-- Projects/Bid Requests
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  homeowner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  category TEXT, -- e.g., 'Painting', 'Roofing'
  -- Simple text location description initially
  location_description TEXT,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'matched', 'in_progress', 'completed', 'cancelled')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  desired_outcome_description TEXT, -- Added for desired outcome text
  metadata JSONB -- Store timeline, project_type, allow_group_bidding etc. here
);

-- Bids
CREATE TABLE bids (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  contractor_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  -- Specify precision and scale for monetary values
  amount DECIMAL(10, 2),
  description TEXT,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected', 'withdrawn')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  -- Store bid timeline, specific inclusions/exclusions
  metadata JSONB
);

-- Project Photos (linking photos stored in Supabase Storage)
CREATE TABLE project_photos (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  -- Path within Supabase storage bucket (e.g., 'public/project-photos/project_uuid/photo_uuid.jpg')
  storage_path TEXT NOT NULL UNIQUE,
  caption TEXT,
  photo_type TEXT NOT NULL DEFAULT 'current' CHECK (photo_type IN ('current', 'inspiration')), -- Added photo type
  created_at TIMESTAMPTZ DEFAULT NOW(),
  -- Store image metadata like dimensions, file size if needed
  metadata JSONB
);

-- Function to automatically update 'updated_at' timestamp
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers to update 'updated_at' on relevant tables
CREATE TRIGGER set_contractor_profiles_timestamp
BEFORE UPDATE ON contractor_profiles
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- A2A Artifact Storage
CREATE TABLE artifacts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), -- Can use A2A ArtifactID if preferred and unique
  a2a_artifact_id TEXT UNIQUE NOT NULL, -- The actual ArtifactID from A2A protocol
  a2a_task_id TEXT NOT NULL REFERENCES tasks(a2a_task_id) ON DELETE CASCADE, -- Link to the task it belongs to
  creator_agent_id TEXT NOT NULL,
  type TEXT NOT NULL, -- e.g., 'BID_CARD', 'TEXT', 'IMAGE_ANALYSIS'
  description TEXT,
  content JSONB, -- Store JSON content directly
  storage_path TEXT, -- Or store path if content is in Supabase Storage (e.g., for large files/images)
  uri TEXT, -- Optional external URI
  created_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB
);

-- Index common query fields
CREATE INDEX idx_artifacts_task ON artifacts(a2a_task_id);
CREATE INDEX idx_artifacts_type ON artifacts(type);

CREATE TRIGGER set_projects_timestamp
BEFORE UPDATE ON projects
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_bids_timestamp
BEFORE UPDATE ON bids
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- Note: A2A specific tables like task_history and messages,
-- as well as embeddings, will be added in later phases as planned.
-- This focuses on the core application data first.

-- A2A Task Tracking
CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), -- Can use A2A TaskId if preferred and unique
  a2a_task_id TEXT UNIQUE NOT NULL, -- The actual TaskId from A2A protocol
  title TEXT,
  description TEXT,
  status TEXT NOT NULL CHECK (status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'CANCELLED')),
  creator_agent_id TEXT NOT NULL,
  assignee_agent_id TEXT NOT NULL,
  parent_task_id TEXT, -- Reference to another a2a_task_id if it's a subtask
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  result JSONB, -- Store task result data
  error_message TEXT, -- Store error details if status is FAILED
  metadata JSONB -- Store any other relevant task metadata
);

-- Index common query fields
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_assignee ON tasks(assignee_agent_id);
CREATE INDEX idx_tasks_creator ON tasks(creator_agent_id);

-- Trigger for tasks updated_at
CREATE TRIGGER set_tasks_timestamp
BEFORE UPDATE ON tasks
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();
