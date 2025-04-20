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
  -- Store timeline details, allow_group_bidding flag, specific project details
  metadata JSONB
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
