-- User-specific memory storage
CREATE TABLE user_memories (
  user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  memory_data JSONB NOT NULL, -- Structured memory blobs
  vector_embedding VECTOR(1536), -- For semantic search (optional)
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User preferences (extracted from interactions)
CREATE TABLE user_preferences (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  preference_key TEXT NOT NULL, -- E.g., "project_type_preference", "communication_style"
  preference_value JSONB NOT NULL, -- Allows complex preference structures
  confidence FLOAT DEFAULT 0.5, -- Confidence score for learned preferences
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  source TEXT, -- How this preference was determined
  UNIQUE(user_id, preference_key)
);

-- Memory interaction records (for detailed history)
CREATE TABLE user_memory_interactions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  interaction_type TEXT NOT NULL, -- E.g., "project_creation", "contractor_selection"
  interaction_data JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  INDEX idx_user_interactions (user_id, interaction_type)
);

-- Trigger for updating timestamps
CREATE TRIGGER set_user_memories_timestamp
BEFORE UPDATE ON user_memories
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_user_preferences_timestamp
BEFORE UPDATE ON user_preferences
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();
