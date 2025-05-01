"""
ProjectRecommendationEngine for ContractorAgent.
Analyzes projects and generates personalized recommendations.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
import datetime
import json

from supabase import Client

logger = logging.getLogger(__name__)


class ProjectRecommendationEngine:
    """
    Engine for generating personalized project recommendations for contractors.
    """

    def __init__(self, db: Client, contractor_id: str, contractor_memory=None):
        """Initialize with database and contractor info."""
        self.db = db
        self.contractor_id = contractor_id
        self.memory = contractor_memory

    async def get_recommendations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Generate personalized project recommendations based on contractor profile and bid history.

        Returns a list of project objects with a recommendation_score and explanation.
        """
        try:
            # 1. Get contractor profile with service categories and area
            profile_res = (
                await self.db.table("contractor_profiles")
                .select("service_categories, service_area_description")
                .eq("id", self.contractor_id)
                .maybe_single()
                .execute()
            )

            if not profile_res.data:
                logger.error(f"Contractor profile not found for {self.contractor_id}")
                return []

            profile = profile_res.data
            service_categories = profile.get("service_categories", [])
            service_area = profile.get("service_area_description")

            # 2. Get bid preferences if memory is available
            preferences = {}
            if self.memory:
                preferences = self.memory.get_bid_preferences()

            preferred_types = preferences.get("preferred_project_types", [])
            preferred_locations = preferences.get("preferred_locations", [])

            # 3. Build base query for open projects
            query = (
                self.db.table("projects")
                .select(
                    "*, (SELECT COUNT(*) FROM bids WHERE bids.project_id = projects.id) as bid_count"
                )
                .eq("status", "open")
            )

            # 4. Apply basic filtering based on service categories
            if service_categories:
                query = query.in_("category", service_categories)

            # 5. Apply location filtering (more complex in real implementation)
            if service_area:
                query = query.eq("location_description", service_area)

            # Execute the base query
            projects_res = await query.execute()

            if not projects_res.data:
                logger.info(
                    f"No matching open projects found for contractor {self.contractor_id}"
                )
                return []

            projects = projects_res.data

            # 6. Score and rank projects
            scored_projects = []
            for project in projects:
                score, explanation = await self._calculate_project_score(
                    project,
                    preferred_types=preferred_types,
                    preferred_locations=preferred_locations,
                )

                # Add score and explanation to project
                project["recommendation_score"] = score
                project["recommendation_explanation"] = explanation
                scored_projects.append(project)

            # 7. Sort by score and limit
            ranked_projects = sorted(
                scored_projects, key=lambda p: p["recommendation_score"], reverse=True
            )[:limit]

            # 8. Record recommendations in feedback table
            await self._record_recommendations(ranked_projects)

            return ranked_projects

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}", exc_info=True)
            return []

    async def _calculate_project_score(
        self,
        project: Dict[str, Any],
        preferred_types: List[str] = None,
        preferred_locations: List[str] = None,
    ) -> Tuple[float, str]:
        """
        Calculate a personalized recommendation score for a project.
        Returns a tuple of (score, explanation).
        """
        score = 0.5  # Base score
        score_factors = []

        # Factor 1: Project type match
        project_type = project.get("metadata", {}).get("project_type")
        if project_type and preferred_types and project_type in preferred_types:
            type_boost = 0.2
            score += type_boost
            score_factors.append(
                f"Matches your preferred project type ({project_type})"
            )

            # If we have memory, check win rate for this type
            if self.memory:
                win_rate = await self.memory.get_win_rate("project_type", project_type)
                if win_rate > 0.5:  # Good win rate
                    score += 0.1
                    score_factors.append(
                        f"You have a {int(win_rate*100)}% success rate with this type of project"
                    )

        # Factor 2: Location match
        location = project.get("location_description")
        if location and preferred_locations and location in preferred_locations:
            location_boost = 0.15
            score += location_boost
            score_factors.append(f"In your preferred work area ({location})")

            # Check win rate for this location
            if self.memory:
                win_rate = await self.memory.get_win_rate("location", location)
                if win_rate > 0.5:
                    score += 0.1
                    score_factors.append(
                        f"You have a {int(win_rate*100)}% success rate in this location"
                    )

        # Factor 3: Competition level
        bid_count = project.get("bid_count", 0)
        if bid_count == 0:
            competition_boost = 0.15
            score += competition_boost
            score_factors.append("No bids yet - be the first to bid")
        elif bid_count < 3:
            competition_boost = 0.1
            score += competition_boost
            score_factors.append(f"Low competition ({bid_count} bids so far)")

        # Factor 4: Category expertise
        category = project.get("category")
        if category and self.memory:
            win_rate = await self.memory.get_win_rate("category", category)
            if win_rate > 0.6:  # Very good win rate
                category_boost = 0.2
                score += category_boost
                score_factors.append(
                    f"You excel at {category} projects ({int(win_rate*100)}% success rate)"
                )

        # Cap the score at 1.0
        score = min(score, 1.0)

        # Build explanation
        if score_factors:
            explanation = "Recommended because: " + "; ".join(score_factors)
        else:
            explanation = "Matches your service categories"

        return score, explanation

    async def _record_recommendations(self, projects: List[Dict[str, Any]]) -> None:
        """Record the recommendations for future analysis."""
        now = datetime.datetime.utcnow().isoformat()

        for project in projects:
            try:
                # Check if there's an existing record
                existing = (
                    await self.db.table("recommendation_feedback")
                    .select("id")
                    .eq("contractor_id", self.contractor_id)
                    .eq("project_id", project["id"])
                    .maybe_single()
                    .execute()
                )

                if existing.data:
                    # Update existing record
                    await self.db.table("recommendation_feedback").update(
                        {
                            "recommendation_strength": project["recommendation_score"],
                            "recommended_at": now,
                        }
                    ).eq("contractor_id", self.contractor_id).eq(
                        "project_id", project["id"]
                    ).execute()
                else:
                    # Insert new record
                    await self.db.table("recommendation_feedback").insert(
                        {
                            "contractor_id": self.contractor_id,
                            "project_id": project["id"],
                            "recommendation_strength": project["recommendation_score"],
                            "contractor_reaction": "recommended",
                            "recommended_at": now,
                        }
                    ).execute()
            except Exception as e:
                logger.error(
                    f"Error recording recommendation for project {project['id']}: {e}"
                )
                # Continue with other recommendations
