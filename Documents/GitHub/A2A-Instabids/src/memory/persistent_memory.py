"""
PersistentMemory implementation that provides user-specific memory persistence.
"""

import logging
from typing import Dict, List, Any, Optional
import json
import datetime

from google.adk.memory import Memory
from supabase import Client

logger = logging.getLogger(__name__)


class PersistentMemory(Memory):
    """
    User-specific persistent memory implementation compatible with ADK.
    Stores and retrieves memory from Supabase database.
    """

    def __init__(self, db: Client, user_id: str):
        """Initialize with database client and user ID."""
        super().__init__()  # Initialize base Memory class
        self.db = db
        self.user_id = user_id
        self._memory_cache: Dict[str, Any] = {}  # In-memory cache
        self._is_loaded = False
        self._is_dirty = False  # Track if memory needs to be saved

    async def load(self) -> bool:
        """Load user's memory from database."""
        if self._is_loaded:
            return True

        try:
            logger.info(f"Loading memory for user {self.user_id}")
            result = (
                await self.db.table("user_memories")
                .select("memory_data")
                .eq("user_id", self.user_id)
                .maybe_single()
                .execute()
            )

            if result.data:
                self._memory_cache = result.data.get("memory_data", {})
                self._is_loaded = True
                logger.info(f"Successfully loaded memory for user {self.user_id}")
                return True
            else:
                # Initialize new memory
                logger.info(
                    f"No existing memory found for user {self.user_id}. Initializing."
                )
                self._memory_cache = {
                    "interactions": [],
                    "context": {},
                    "learned_preferences": {},
                    "creation_date": datetime.datetime.utcnow().isoformat(),
                }
                self._is_loaded = True
                self._is_dirty = True
                await self.save()  # Create initial memory record
                return True

        except Exception as e:
            logger.error(
                f"Error loading memory for user {self.user_id}: {e}", exc_info=True
            )
            return False

    async def save(self) -> bool:
        """Save current memory state to database."""
        if not self._is_dirty:
            return True

        try:
            logger.info(f"Saving memory for user {self.user_id}")
            # Update timestamp before saving
            self._memory_cache["last_updated"] = datetime.datetime.utcnow().isoformat()

            result = (
                await self.db.table("user_memories")
                .upsert(
                    {
                        "user_id": self.user_id,
                        "memory_data": self._memory_cache,
                        "updated_at": datetime.datetime.utcnow().isoformat(),
                    }
                )
                .execute()
            )

            if result.data:
                self._is_dirty = False
                logger.info(f"Successfully saved memory for user {self.user_id}")
                return True
            else:
                logger.error(f"Failed to save memory for user {self.user_id}")
                return False

        except Exception as e:
            logger.error(
                f"Error saving memory for user {self.user_id}: {e}", exc_info=True
            )
            return False

    async def add_interaction(
        self, interaction_type: str, data: Dict[str, Any]
    ) -> bool:
        """Record a new user interaction in memory."""
        if not self._is_loaded and not await self.load():
            return False

        try:
            # Add to in-memory cache
            timestamp = datetime.datetime.utcnow().isoformat()
            interaction = {
                "type": interaction_type,
                "timestamp": timestamp,
                "data": data,
            }

            if "interactions" not in self._memory_cache:
                self._memory_cache["interactions"] = []

            self._memory_cache["interactions"].append(interaction)
            self._is_dirty = True

            # Also store in detailed interaction history table
            await self.db.table("user_memory_interactions").insert(
                {
                    "user_id": self.user_id,
                    "interaction_type": interaction_type,
                    "interaction_data": data,
                    "created_at": timestamp,
                }
            ).execute()

            # Process for potential preference learning
            await self._extract_preferences(interaction_type, data)

            return True

        except Exception as e:
            logger.error(
                f"Error adding interaction for user {self.user_id}: {e}", exc_info=True
            )
            return False

    async def _extract_preferences(self, interaction_type: str, data: Dict[str, Any]):
        """Extract and update user preferences from interaction data."""
        try:
            # Example preference extraction logic - customize based on interaction types
            if interaction_type == "project_creation":
                # Extract project type preference
                if "project_type" in data:
                    await self._update_preference(
                        "preferred_project_types",
                        data["project_type"],
                        "project_creation",
                    )

                # Extract timeline preference
                if "timeline" in data:
                    await self._update_preference(
                        "timeline_preference", data["timeline"], "project_creation"
                    )

            elif interaction_type == "contractor_selection":
                # Extract contractor preference indicators
                if "selected_contractor" in data and "contractor_attributes" in data:
                    for attr, value in data["contractor_attributes"].items():
                        await self._update_preference(
                            f"contractor_{attr}_preference",
                            value,
                            "contractor_selection",
                        )
        except Exception as e:
            logger.error(
                f"Error extracting preferences for user {self.user_id}: {e}",
                exc_info=True,
            )

    async def _update_preference(self, preference_key: str, value: Any, source: str):
        """Update a user preference in the database and memory cache."""
        try:
            # Update in-memory representation
            if "learned_preferences" not in self._memory_cache:
                self._memory_cache["learned_preferences"] = {}

            if preference_key not in self._memory_cache["learned_preferences"]:
                self._memory_cache["learned_preferences"][preference_key] = {
                    "value": value,
                    "count": 1,
                }
            else:
                # Simple counting-based preference strengthening
                current = self._memory_cache["learned_preferences"][preference_key]
                if current["value"] == value:
                    current["count"] += 1
                else:
                    # Different value - handle conflict based on count
                    if current["count"] <= 2:  # Threshold for changing preference
                        current["value"] = value
                        current["count"] = 1
                    # Else keep existing preference as it's stronger

            self._is_dirty = True

            # Store in preferences table with confidence score
            count = self._memory_cache["learned_preferences"][preference_key]["count"]
            confidence = min(0.5 + (count * 0.1), 0.95)  # Simple confidence scaling

            await self.db.table("user_preferences").upsert(
                {
                    "user_id": self.user_id,
                    "preference_key": preference_key,
                    "preference_value": value,
                    "confidence": confidence,
                    "source": source,
                    "updated_at": datetime.datetime.utcnow().isoformat(),
                }
            ).execute()

        except Exception as e:
            logger.error(
                f"Error updating preference for user {self.user_id}: {e}", exc_info=True
            )

    # Implement required Memory interface methods
    def get(self, key: str) -> Any:
        """Get a value from memory by key."""
        if not self._is_loaded:
            # Synchronous method can't await load(), so return None if not loaded
            logger.warning(
                f"Attempted to get key '{key}' from unloaded memory for user {self.user_id}"
            )
            return None
        return self._memory_cache.get("context", {}).get(key)

    def set(self, key: str, value: Any) -> None:
        """Set a value in memory by key."""
        if not self._is_loaded:
            logger.warning(
                f"Attempted to set key '{key}' to unloaded memory for user {self.user_id}"
            )
            return

        if "context" not in self._memory_cache:
            self._memory_cache["context"] = {}

        self._memory_cache["context"][key] = value
        self._is_dirty = True

    def get_recent_interactions(
        self, interaction_type: Optional[str] = None, limit: int = 10
    ) -> List[Dict]:
        """Get recent user interactions, optionally filtered by type."""
        if not self._is_loaded:
            return []

        interactions = self._memory_cache.get("interactions", [])

        if interaction_type:
            interactions = [i for i in interactions if i["type"] == interaction_type]

        # Sort by timestamp (newest first) and limit
        return sorted(interactions, key=lambda x: x["timestamp"], reverse=True)[:limit]

    def get_preference(self, preference_key: str) -> Any:
        """Get a learned user preference."""
        if not self._is_loaded:
            return None

        prefs = self._memory_cache.get("learned_preferences", {})
        if preference_key in prefs:
            return prefs[preference_key]["value"]
        return None

    def get_all_preferences(self) -> Dict[str, Any]:
        """Get all learned preferences with their values."""
        if not self._is_loaded:
            return {}

        prefs = self._memory_cache.get("learned_preferences", {})
        return {k: v["value"] for k, v in prefs.items()}
