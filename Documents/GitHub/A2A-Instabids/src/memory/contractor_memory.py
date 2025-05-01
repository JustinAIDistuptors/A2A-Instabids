"""
ContractorMemory implementation extending PersistentMemory with contractor-specific features.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
import json
import datetime

from .persistent_memory import PersistentMemory
from supabase import Client

logger = logging.getLogger(__name__)


class ContractorMemory(PersistentMemory):
    """
    Contractor-specific memory implementation.
    Adds bid pattern tracking and project recommendation intelligence.
    """

    def __init__(self, db: Client, contractor_id: str):
        """Initialize with database client and contractor ID."""
        super().__init__(db, contractor_id)
        self.contractor_id = contractor_id
        self._bid_metrics = None

    async def load(self) -> bool:
        """Load contractor's memory and bid metrics from database."""
        success = await super().load()
        if not success:
            return False

        try:
            # Load contractor-specific bid metrics
            result = (
                await self.db.table("contractor_bid_metrics")
                .select("*")
                .eq("contractor_id", self.contractor_id)
                .maybe_single()
                .execute()
            )

            if result.data:
                self._bid_metrics = result.data
                logger.info(f"Loaded bid metrics for contractor {self.contractor_id}")
            else:
                # Initialize new bid metrics
                self._bid_metrics = {
                    "contractor_id": self.contractor_id,
                    "total_bids": 0,
                    "successful_bids": 0,
                    "avg_bid_amount": 0,
                    "bid_history": {},
                    "win_rates": {},
                    "updated_at": datetime.datetime.utcnow().isoformat(),
                }
                # Create initial record
                await self.db.table("contractor_bid_metrics").insert(
                    self._bid_metrics
                ).execute()
                logger.info(
                    f"Initialized new bid metrics for contractor {self.contractor_id}"
                )

            return True

        except Exception as e:
            logger.error(f"Error loading contractor bid metrics: {e}", exc_info=True)
            return False

    async def save(self) -> bool:
        """Save memory and bid metrics to database."""
        success = await super().save()

        if self._bid_metrics and self._is_loaded:
            try:
                # Update timestamp
                self._bid_metrics["updated_at"] = datetime.datetime.utcnow().isoformat()

                # Save bid metrics
                result = (
                    await self.db.table("contractor_bid_metrics")
                    .upsert(self._bid_metrics)
                    .execute()
                )

                if result.data:
                    logger.info(
                        f"Saved bid metrics for contractor {self.contractor_id}"
                    )
                    return success and True
                else:
                    logger.error(
                        f"Failed to save bid metrics for contractor {self.contractor_id}"
                    )
                    return False

            except Exception as e:
                logger.error(f"Error saving contractor bid metrics: {e}", exc_info=True)
                return False

        return success

    async def record_bid(self, project_id: str, bid_data: Dict[str, Any]) -> bool:
        """Record a new bid and update metrics."""
        if not self._is_loaded and not await self.load():
            return False

        try:
            # Add to interactions record
            bid_interaction = {
                "project_id": project_id,
                "bid_amount": bid_data.get("amount"),
                "bid_date": datetime.datetime.utcnow().isoformat(),
            }

            await self.add_interaction("bid_submission", bid_interaction)

            # Update bid metrics
            if self._bid_metrics:
                self._bid_metrics["total_bids"] += 1
                self._bid_metrics["last_bid_date"] = (
                    datetime.datetime.utcnow().isoformat()
                )

                # Update average bid amount
                total_amount = (
                    self._bid_metrics["avg_bid_amount"]
                    * (self._bid_metrics["total_bids"] - 1)
                ) + bid_data.get("amount", 0)
                self._bid_metrics["avg_bid_amount"] = (
                    total_amount / self._bid_metrics["total_bids"]
                )

                # Update bid history by project type
                project_res = (
                    await self.db.table("projects")
                    .select("category, metadata")
                    .eq("id", project_id)
                    .maybe_single()
                    .execute()
                )

                if project_res.data:
                    project_type = project_res.data.get("metadata", {}).get(
                        "project_type"
                    )
                    category = project_res.data.get("category")

                    if not "bid_history" in self._bid_metrics:
                        self._bid_metrics["bid_history"] = {}

                    # By project type
                    if project_type:
                        if project_type not in self._bid_metrics["bid_history"]:
                            self._bid_metrics["bid_history"][project_type] = {
                                "count": 0,
                                "total_amount": 0,
                            }

                        self._bid_metrics["bid_history"][project_type]["count"] += 1
                        self._bid_metrics["bid_history"][project_type][
                            "total_amount"
                        ] += bid_data.get("amount", 0)

                    # By category
                    if category:
                        if category not in self._bid_metrics["bid_history"]:
                            self._bid_metrics["bid_history"][category] = {
                                "count": 0,
                                "total_amount": 0,
                            }

                        self._bid_metrics["bid_history"][category]["count"] += 1
                        self._bid_metrics["bid_history"][category][
                            "total_amount"
                        ] += bid_data.get("amount", 0)

                await self.save()

            return True

        except Exception as e:
            logger.error(f"Error recording bid: {e}", exc_info=True)
            return False

    async def record_bid_result(
        self, project_id: str, bid_id: str, status: str
    ) -> bool:
        """Record the outcome of a bid (accepted, rejected) and update success metrics."""
        if not self._is_loaded and not await self.load():
            return False

        if status not in ["accepted", "rejected"]:
            logger.error(f"Invalid bid status: {status}")
            return False

        try:
            # Record result in interactions
            result_interaction = {
                "project_id": project_id,
                "bid_id": bid_id,
                "status": status,
                "result_date": datetime.datetime.utcnow().isoformat(),
            }

            await self.add_interaction("bid_result", result_interaction)

            # Update success metrics
            if self._bid_metrics:
                if status == "accepted":
                    self._bid_metrics["successful_bids"] += 1

                # Get project details for win rate updates
                project_res = (
                    await self.db.table("projects")
                    .select("category, location_description, metadata")
                    .eq("id", project_id)
                    .maybe_single()
                    .execute()
                )

                if project_res.data:
                    project_type = project_res.data.get("metadata", {}).get(
                        "project_type"
                    )
                    category = project_res.data.get("category")
                    location = project_res.data.get("location_description")

                    # Initialize win_rates structure if needed
                    if "win_rates" not in self._bid_metrics:
                        self._bid_metrics["win_rates"] = {}

                    # Update by project type
                    if project_type:
                        self._update_win_rate(
                            "project_type", project_type, status == "accepted"
                        )

                    # Update by category
                    if category:
                        self._update_win_rate(
                            "category", category, status == "accepted"
                        )

                    # Update by location
                    if location:
                        self._update_win_rate(
                            "location", location, status == "accepted"
                        )

                await self.save()

            return True

        except Exception as e:
            logger.error(f"Error recording bid result: {e}", exc_info=True)
            return False

    def _update_win_rate(self, dimension: str, value: str, won: bool):
        """Update win rate statistics for a specific dimension (project_type, category, location)."""
        if "win_rates" not in self._bid_metrics:
            self._bid_metrics["win_rates"] = {}

        if dimension not in self._bid_metrics["win_rates"]:
            self._bid_metrics["win_rates"][dimension] = {}

        if value not in self._bid_metrics["win_rates"][dimension]:
            self._bid_metrics["win_rates"][dimension][value] = {"bids": 0, "wins": 0}

        self._bid_metrics["win_rates"][dimension][value]["bids"] += 1
        if won:
            self._bid_metrics["win_rates"][dimension][value]["wins"] += 1

    async def record_recommendation_reaction(
        self, project_id: str, reaction: str, score: Optional[int] = None
    ) -> bool:
        """Record contractor's reaction to a recommended project."""
        if not self.db:
            return False

        try:
            # Get existing recommendation record
            result = (
                await self.db.table("recommendation_feedback")
                .select("*")
                .eq("contractor_id", self.contractor_id)
                .eq("project_id", project_id)
                .maybe_single()
                .execute()
            )

            now = datetime.datetime.utcnow().isoformat()

            if result.data:
                # Update existing record
                update_data = {"contractor_reaction": reaction, "feedback_at": now}

                if score is not None:
                    update_data["feedback_score"] = score

                await self.db.table("recommendation_feedback").update(update_data).eq(
                    "contractor_id", self.contractor_id
                ).eq("project_id", project_id).execute()
            else:
                # Create new record (for manually discovered projects)
                insert_data = {
                    "contractor_id": self.contractor_id,
                    "project_id": project_id,
                    "recommendation_strength": 0.0,  # Not recommended by system
                    "contractor_reaction": reaction,
                    "feedback_at": now,
                }

                if score is not None:
                    insert_data["feedback_score"] = score

                await self.db.table("recommendation_feedback").insert(
                    insert_data
                ).execute()

            # Record as interaction too
            await self.add_interaction(
                "project_reaction",
                {
                    "project_id": project_id,
                    "reaction": reaction,
                    "feedback_score": score,
                    "timestamp": now,
                },
            )

            return True

        except Exception as e:
            logger.error(f"Error recording recommendation reaction: {e}", exc_info=True)
            return False

    def get_bid_preferences(self) -> Dict[str, Any]:
        """Get bidding preferences inferred from bid history and win rates."""
        preferences = {}

        if not self._is_loaded or not self._bid_metrics:
            return preferences

        # Extract preferred project types based on highest win rates
        if (
            "win_rates" in self._bid_metrics
            and "project_type" in self._bid_metrics["win_rates"]
        ):
            project_types = self._bid_metrics["win_rates"]["project_type"]

            # Filter to types with at least 3 bids
            valid_types = {
                k: v for k, v in project_types.items() if v.get("bids", 0) >= 3
            }

            # Calculate win rates
            type_win_rates = {
                k: v.get("wins", 0) / v.get("bids", 1) for k, v in valid_types.items()
            }

            # Get top 3 by win rate
            preferred_types = sorted(
                type_win_rates.items(), key=lambda x: x[1], reverse=True
            )[:3]
            preferences["preferred_project_types"] = [
                t[0] for t in preferred_types if t[1] > 0.3
            ]  # Only include if win rate > 30%

        # Extract preferred locations
        if (
            "win_rates" in self._bid_metrics
            and "location" in self._bid_metrics["win_rates"]
        ):
            locations = self._bid_metrics["win_rates"]["location"]

            # Filter to locations with at least 2 bids
            valid_locations = {
                k: v for k, v in locations.items() if v.get("bids", 0) >= 2
            }

            # Get locations with good win rates
            good_locations = [
                k
                for k, v in valid_locations.items()
                if v.get("wins", 0) / v.get("bids", 1) > 0.4
            ]  # Win rate > 40%

            preferences["preferred_locations"] = good_locations

        # Extract typical bid amounts by category
        if "bid_history" in self._bid_metrics:
            bid_history = self._bid_metrics["bid_history"]

            bid_amounts = {}
            for category, data in bid_history.items():
                if (
                    data.get("count", 0) >= 3
                ):  # Need at least 3 bids to establish pattern
                    avg_amount = data.get("total_amount", 0) / data.get("count", 1)
                    bid_amounts[category] = avg_amount

            preferences["typical_bid_amounts"] = bid_amounts

        return preferences

    # Additional helper methods for ContractorAgent
    async def get_win_rate(self, dimension: str, value: str) -> float:
        """Get the win rate for a specific dimension value (e.g., project type='bathroom')."""
        if not self._is_loaded and not await self.load():
            return 0.0

        if "win_rates" not in self._bid_metrics:
            return 0.0

        if dimension not in self._bid_metrics["win_rates"]:
            return 0.0

        if value not in self._bid_metrics["win_rates"][dimension]:
            return 0.0

        data = self._bid_metrics["win_rates"][dimension][value]
        bids = data.get("bids", 0)

        if bids == 0:
            return 0.0

        return data.get("wins", 0) / bids
