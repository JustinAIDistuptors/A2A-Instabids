"""
Defines ADK Flows for the Homeowner Agent, such as project creation.
"""

import logging
from typing import Any, Dict, Optional, Tuple, Callable, Union
import json
import re  # For basic validation later

# Assuming ADK and LLM types are accessible
from google.adk.flows import LLMFlow
from google.adk.models import Llm
from google.adk.memory import Memory  # Import Memory

logger = logging.getLogger(__name__)

# --- Constants for Required Fields ---
REQUIRED_FIELDS = [
    "title",
    "description",
    "project_type",
    "category",
    "location_description",
    "timeline",
]

# Define states globally or pass them around if needed by helpers outside the build function
states = [
    "START",
    "GATHER_TITLE",
    "GATHER_DESCRIPTION",
    "GATHER_PROJECT_TYPE",
    "GATHER_CATEGORY",
    "GATHER_LOCATION",
    "GATHER_TIMELINE",
    "GATHER_DESIRED_OUTCOME",  # New state
    "CONFIRM_GROUP_BIDDING",
    "HANDLE_CURRENT_PHOTOS",  # Renamed from HANDLE_PHOTOS
    "HANDLE_INSPIRATION_PHOTOS",  # New state
    "CONFIRM_DETAILS",
    "AWAIT_CONFIRMATION",
    "HANDLE_CORRECTION",
    "DONE",
    "FAILED",
]


# --- Helper to check if required fields are gathered ---
def _all_required_fields_gathered(gathered_data: Dict) -> bool:
    """Checks if all essential project details have been gathered."""
    return all(
        field in gathered_data and gathered_data.get(field) for field in REQUIRED_FIELDS
    )


# --- Helper to find the next state to gather a missing field ---
def _find_next_gather_state(gathered_data: Dict) -> str:
    """Finds the state corresponding to the first missing required field or optional step."""
    state_map = {
        "title": "GATHER_TITLE",
        "description": "GATHER_DESCRIPTION",
        "project_type": "GATHER_PROJECT_TYPE",
        "category": "GATHER_CATEGORY",
        "location_description": "GATHER_LOCATION",
        "timeline": "GATHER_TIMELINE",
        "desired_outcome_description": "GATHER_DESIRED_OUTCOME",  # Added
        "allow_group_bidding": "CONFIRM_GROUP_BIDDING",
        "current_photos_handled": "HANDLE_CURRENT_PHOTOS",  # Renamed flag
        "inspiration_photos_handled": "HANDLE_INSPIRATION_PHOTOS",  # Added flag
    }
    # Check required fields first
    for field in REQUIRED_FIELDS:
        if not gathered_data.get(field):
            gather_state = state_map.get(field)
            if gather_state in states:
                return gather_state
            else:
                logger.error(
                    f"Logic error: Field '{field}' has no valid GATHER state mapped."
                )
                return "FAILED"

    # Then check optional fields before confirmation
    if "desired_outcome_description" not in gathered_data:
        return "GATHER_DESIRED_OUTCOME"
    if "allow_group_bidding" not in gathered_data:
        return "CONFIRM_GROUP_BIDDING"
    if gathered_data.get("current_photos_handled") is not True:
        return "HANDLE_CURRENT_PHOTOS"
    if gathered_data.get("inspiration_photos_handled") is not True:
        return "HANDLE_INSPIRATION_PHOTOS"

    # If all required and optional steps done, go to confirm
    return "CONFIRM_DETAILS"


def build_project_creation_flow(
    llm_service: Llm, memory_service: Optional[Memory] = None
) -> LLMFlow:
    """
    Builds the ADK LLMFlow for gathering project details.

    Args:
        llm_service: The configured ADK LLM service instance.
        memory_service: The configured ADK Memory service instance (optional).

    Returns:
        An initialized LLMFlow instance.
    """
    if not llm_service:
        raise ValueError("Cannot build LLMFlow without an LLM service.")

    initial_state = "START"
    final_states = ["DONE", "FAILED"]

    # --- Define Prompts (Refining GATHER_CATEGORY) ---
    prompt_templates = {
        "START": """
            You are the InstaBids Homeowner Agent, helping users create project requests.
            Current Gathered Data: {gathered_data}
            Initial Context (from photo/quote analysis, if any): {initial_context}

            Task:
            1. Greet the user warmly.
            2. If initial_context contains 'photo_analysis', mention seeing the photo (e.g., "Thanks for the photo!").
            3. If initial_context contains 'quote_analysis', mention seeing the quote details (e.g., "Okay, I see the details from the quote about [scope].").
            4. If initial_context contains 'description', use that as the starting description and add it to extracted_data.
            5. Determine the next logical step using _find_next_gather_state({gathered_data}). The first missing field is usually 'title' unless provided in context.
            6. Ask the first question based on the determined next state.

            **Output Format:** Respond ONLY with a valid JSON object:
            {{
                "prompt_to_user": "Welcome to InstaBids! [Acknowledge context if present]. To start, what would you like to call this project?",
                "next_state": "GATHER_TITLE",
                "extracted_data": {{ "description": "{initial_context.get('description', '')}" }}
            }}
            """,
        "GATHER_TITLE": """
            You are the InstaBids Homeowner Agent, gathering project details.
            Current Gathered Data: {gathered_data}
            User Input: {user_message}

            Task: Extract a short, descriptive project title from the user input (e.g., "Leaky Roof Repair", "Kitchen Backsplash Install", "Weekly Lawn Mowing"). Avoid generic answers like 'yes' or 'ok'.
            - If a reasonable title (e.g., 2-10 words) is extracted, update 'title' in extracted_data.
            - Determine the next state using _find_next_gather_state({gathered_data}).
            - Formulate the prompt for the next state (e.g., asking for description).
            - If no title is extracted or the input seems irrelevant/too short/too long, ask the user again clearly for a short project title. Set next_state back to GATHER_TITLE.

            **Output Format:** Respond ONLY with a valid JSON object:
            {{
                "prompt_to_user": "Got it. Now, could you please describe the project or issue in more detail?",
                "next_state": "GATHER_DESCRIPTION",
                "extracted_data": {{ "title": "Extracted Title" }}
            }}
            """,
        "GATHER_DESCRIPTION": """
            You are the InstaBids Homeowner Agent, gathering project details.
            Current Gathered Data: {gathered_data}
            User Input: {user_message}

            Task: Extract or refine the project description based on user input and context (like photo/quote analysis in gathered_data). Aim for a clear, concise description (at least a few words) of the problem or desired work.
            - If a reasonable description is extracted/refined, update 'description' in extracted_data.
            - Determine the next state using _find_next_gather_state({gathered_data}).
            - Formulate the prompt for the next state.
            - If no description is extracted or it's too short/generic (like 'fix it'), ask the user again clearly for more details about the project. Set next_state back to GATHER_DESCRIPTION.

            **Output Format:** Respond ONLY with a valid JSON object:
            {{
                "prompt_to_user": "Thanks! What type of project is this?",
                "next_state": "GATHER_PROJECT_TYPE",
                "extracted_data": {{ "description": "Extracted/Refined Description" }}
            }}
            """,
        "GATHER_PROJECT_TYPE": """
            You are the InstaBids Homeowner Agent, gathering project details.
            Current Gathered Data: {gathered_data}
            User Input: {user_message}

            Task: Extract the project type from the user input. Valid types are 'one-time', 'recurring', 'repair', 'handyman', 'labor-only', 'multi-step'.
            - If a valid type is extracted (from text or payload), update 'project_type' in extracted_data. Determine the next missing field using _find_next_gather_state({gathered_data}) and ask for it. Set next_state accordingly.
            - If no valid type is extracted, ask the user again, providing the options as quick replies. Set next_state to GATHER_PROJECT_TYPE.

            **Output Format:** Respond ONLY with a valid JSON object:
            {{
                "prompt_to_user": {{
                    "text": "Okay, got it. What category does this '{project_type}' project fall under? (e.g., Roofing, Plumbing, Painting)",
                    "quick_replies": [] // Quick replies can be added dynamically in state_mapper if needed
                }},
                "next_state": "GATHER_CATEGORY",
                "extracted_data": {{ "project_type": "Extracted Type" }}
            }}
            // OR if extraction failed:
            {{
                "prompt_to_user": {{
                    "text": "Sorry, I didn't catch that. What type of project is this?",
                    "quick_replies": [
                        {{"title": "One-Time (e.g., Install)", "payload": "one-time"}},
                        {{"title": "Recurring (e.g., Cleaning)", "payload": "recurring"}},
                        {{"title": "Repair", "payload": "repair"}},
                        {{"title": "Handyman", "payload": "handyman"}},
                        {{"title": "Labor Help", "payload": "labor-only"}},
                        {{"title": "Multi-Step/Remodel", "payload": "multi-step"}}
                    ]
                }},
                "next_state": "GATHER_PROJECT_TYPE",
                "extracted_data": {{}}
            }}
            """,
        "GATHER_CATEGORY": """
            You are the InstaBids Homeowner Agent, gathering project details.
            Current Gathered Data: {gathered_data} // Includes 'project_type'
            User Input: {user_message}

            Task: Extract the specific project category based on the user input and project type ('{project_type}'). Examples: Roofing, Plumbing, Electrical, Painting, Lawn Care, Cleaning, Moving Help, Drywall Repair, Kitchen Remodel. Be specific if possible (e.g., 'Interior Painting' instead of just 'Painting').
            - If a category is extracted, update 'category' in extracted_data.
            - Determine the next state using _find_next_gather_state({gathered_data}).
            - Formulate the prompt for the next state.
            - If no category is extracted, ask again. If project_type is 'repair', suggest 'Plumbing, Electrical, Drywall, Appliance'. If 'recurring', suggest 'Lawn Care, Cleaning, Pool Service'. Otherwise, give general examples. Set next_state to GATHER_CATEGORY.

            **Output Format:** Respond ONLY with a valid JSON object:
            {{
                "prompt_to_user": "Great. What's the 5-digit zip code for the project location?",
                "next_state": "GATHER_LOCATION",
                "extracted_data": {{ "category": "Extracted Category" }}
            }}
            """,
        "GATHER_LOCATION": """
            You are the InstaBids Homeowner Agent, gathering project details.
            Current Gathered Data: {gathered_data}
            User Input: {user_message}

            Task: Extract the project location (5-digit zip code) from the user input.
            - If a 5-digit zip code is extracted, validate it. If valid, update 'location_description' in extracted_data.
            - Determine the next state using _find_next_gather_state({gathered_data}).
            - Formulate the prompt for the next state.
            - If invalid format or no zip code extracted, ask again clearly for the 5-digit zip code. Set next_state to GATHER_LOCATION.

            **Output Format:** Respond ONLY with a valid JSON object:
            {{
                "prompt_to_user": "Got it. And what's your ideal timeframe? (e.g., Emergency, Within a week, Within a month, Just budgeting)",
                "next_state": "GATHER_TIMELINE",
                "extracted_data": {{ "location_description": "Extracted Zip" }}
            }}
            // OR if invalid:
            {{
                "prompt_to_user": "That doesn't look like a valid 5-digit US zip code. Could you please provide the zip code for the project location?",
                "next_state": "GATHER_LOCATION",
                "extracted_data": {{}}
            }}
            """,
        "GATHER_TIMELINE": """
            You are the InstaBids Homeowner Agent, gathering project details.
            Current Gathered Data: {gathered_data}
            User Input: {user_message}

            Task: Extract the user's desired timeline/urgency. Map it to one of: 'emergency', 'few_days_week', 'within_month', 'budgeting', 'dream_project'.
            - If a valid timeline category is extracted (from text or payload), update 'timeline' in extracted_data. Determine the next state using _find_next_gather_state({gathered_data}). Formulate the prompt for the next state.
            - If no valid timeline is extracted, ask again, providing the options as quick replies. Set next_state to GATHER_TIMELINE.

            **Output Format:** Respond ONLY with a valid JSON object:
            {{
                "prompt_to_user": {{
                     "text": "Understood. Now, could you describe your desired outcome for this project? What does 'done' look like?",
                     "quick_replies": []
                 }},
                "next_state": "GATHER_DESIRED_OUTCOME",
                "extracted_data": {{ "timeline": "Extracted Timeline" }}
            }}
            // OR if extraction failed:
            {{
                "prompt_to_user": {{
                    "text": "What's your ideal timeframe for this project?",
                    "quick_replies": [
                        {{"title": "Emergency (ASAP)", "payload": "emergency"}},
                        {{"title": "Within Days/Week", "payload": "few_days_week"}},
                        {{"title": "Within a Month", "payload": "within_month"}},
                        {{"title": "Budgeting/Planning", "payload": "budgeting"}},
                        {{"title": "Dream Project (Flexible)", "payload": "dream_project"}}
                    ]
                }},
                "next_state": "GATHER_TIMELINE",
                "extracted_data": {{}}
            }}
            """,
        "GATHER_DESIRED_OUTCOME": """
            You are the InstaBids Homeowner Agent, gathering project details.
            Current Gathered Data: {gathered_data}
            User Input: {user_message}

            Task: Extract the user's description of the desired outcome (what 'done' looks like). This is an open-ended description.
            - If a description is extracted (at least a few words), update 'desired_outcome_description' in extracted_data.
            - Determine the next state using _find_next_gather_state({gathered_data}).
            - Formulate the prompt for the next state.
            - If no description is extracted or it's too short, ask again for more detail about the desired outcome. Set next_state to GATHER_DESIRED_OUTCOME.

            **Output Format:** Respond ONLY with a valid JSON object:
            {{
                "prompt_to_user": "Okay. Would you be open to potentially grouping this job with nearby similar projects for a discount? (yes/no)",
                "next_state": "CONFIRM_GROUP_BIDDING",
                "extracted_data": {{ "desired_outcome_description": "Extracted Outcome" }}
            }}
            """,
        "CONFIRM_GROUP_BIDDING": """
            You are the InstaBids Homeowner Agent, gathering project details.
            Current Gathered Data: {gathered_data}
            User Input: {user_message}

            Task: Extract the user's preference for group bidding (yes/no). Use 'yes' or 'no' text or payload 'confirm_yes'/'confirm_no'.
            - If preference is extracted ('yes'/'confirm_yes' -> true, 'no'/'confirm_no' -> false), update 'allow_group_bidding' (boolean) in extracted_data.
            - Determine the next state using _find_next_gather_state({gathered_data}).
            - Formulate the prompt for the next state.
            - If preference is unclear, ask again clearly, providing quick replies. Set next_state to CONFIRM_GROUP_BIDDING.

            **Output Format:** Respond ONLY with a valid JSON object:
            {{
                "prompt_to_user": {{
                    "text": "Photos of the current situation really help contractors understand the job. Would you like to add some now? You can also add them later.",
                    "quick_replies": [{{"title": "Yes, add photos", "payload": "add_current_photos_yes"}}, {{"title": "No, skip for now", "payload": "add_current_photos_no"}}]
                }},
                "next_state": "HANDLE_CURRENT_PHOTOS",
                "extracted_data": {{ "allow_group_bidding": true/false }}
            }}
            // OR if extraction failed:
            {{
                "prompt_to_user": {{
                    "text": "Sorry, I need a clear yes or no. Would you be open to grouping this job for potential discounts?",
                    "quick_replies": [{{"title": "Yes", "payload": "confirm_yes"}}, {{"title": "No", "payload": "confirm_no"}}]
                }},
                "next_state": "CONFIRM_GROUP_BIDDING",
                "extracted_data": {{}}
            }}
            """,
        "HANDLE_CURRENT_PHOTOS": """
             You are the InstaBids Homeowner Agent, gathering project details.
             Current Gathered Data: {gathered_data}
             User Input: {user_message} // User might say 'yes'/'no' or provide photo info/links or payload 'add_current_photos_yes'/'add_current_photos_no'

             Task: Acknowledge the user's response about current photos (e.g., "Okay, got it."). Set 'current_photos_handled' to true in extracted_data regardless of the answer. Determine the next state using _find_next_gather_state({gathered_data}). Formulate the prompt for the next state (asking about inspiration photos).
             (Note: The actual photo upload happens via the UI/backend. This step just tracks if the user was asked/responded).

             **Output Format:** Respond ONLY with a valid JSON object:
             {{
                 "prompt_to_user": {{
                     "text": "Okay. Do you have any inspiration photos showing the look you're going for? (Optional)",
                     "quick_replies": [{{"title": "Yes, add inspiration", "payload": "add_inspiration_photos_yes"}}, {{"title": "No inspiration photos", "payload": "add_inspiration_photos_no"}}]
                 }},
                 "next_state": "HANDLE_INSPIRATION_PHOTOS",
                 "extracted_data": {{ "current_photos_handled": true }}
             }}
             """,
        "HANDLE_INSPIRATION_PHOTOS": """
             You are the InstaBids Homeowner Agent, gathering project details.
             Current Gathered Data: {gathered_data}
             User Input: {user_message} // User might say 'yes'/'no' or provide photo info/links or payload 'add_inspiration_photos_yes'/'add_inspiration_photos_no'

             Task: Acknowledge the user's response about inspiration photos. Set 'inspiration_photos_handled' to true in extracted_data regardless of the answer. Determine the next state using _find_next_gather_state({gathered_data}). Formulate the prompt for the next state (reviewing details).

             **Output Format:** Respond ONLY with a valid JSON object:
             {{
                 "prompt_to_user": "Okay, let's review all the details to make sure I got everything right.",
                 "next_state": "CONFIRM_DETAILS",
                 "extracted_data": {{ "inspiration_photos_handled": true }}
             }}
             """,
        "CONFIRM_DETAILS": """
            You are the InstaBids Homeowner Agent.
            Current Gathered Data: {gathered_data}

            Task: Format a summary of all gathered details using the provided data. Use markdown for clarity (e.g., bullet points). Ask the user to confirm if the summary is correct and provide 'Yes'/'No' quick replies.
            Summary should include: Title, Description, Project Type, Category, Location (Zip), Timeline, Desired Outcome, Group Bidding preference, Current Photos status, Inspiration Photos status.

            **Output Format:** Respond ONLY with a valid JSON object:
            {{
                "prompt_to_user": {{
                     "text": "Okay, let's review:\\n\\n*   **Title:** {gathered_data.get('title', 'N/A')}\\n*   **Description:** {gathered_data.get('description', 'N/A')}\\n*   **Project Type:** {gathered_data.get('project_type', 'N/A')}\\n*   **Category:** {gathered_data.get('category', 'N/A')}\\n*   **Location (Zip):** {gathered_data.get('location_description', 'N/A')}\\n*   **Timeline:** {gathered_data.get('timeline', 'N/A')}\\n*   **Desired Outcome:** {gathered_data.get('desired_outcome_description', 'N/A')}\\n*   **Group Bidding OK?:** {'Yes' if gathered_data.get('allow_group_bidding') else 'No'}\\n*   **Current Photos Added?:** {'Yes' if gathered_data.get('current_photos_handled') else 'Not yet'}\\n*   **Inspiration Photos Added?:** {'Yes' if gathered_data.get('inspiration_photos_handled') else 'Not yet'}\\n\\nDoes this look right?",
                     "quick_replies": [{{"title": "Yes, looks good!", "payload": "confirm_yes"}}, {{"title": "No, needs changes", "payload": "confirm_no"}}]
                 }},
                "next_state": "AWAIT_CONFIRMATION",
                "extracted_data": {{}}
            }}
            """,
        "AWAIT_CONFIRMATION": """
            You are the InstaBids Homeowner Agent.
            Current Gathered Data: {gathered_data}
            User Input: {user_message} // Could be text or payload like 'confirm_yes'/'confirm_no'

            Task: Analyze the user's confirmation (text or payload).
            - If they confirm ('yes', 'confirm_yes', etc.), extract intent:'confirm'. Check if all REQUIRED_FIELDS ({required_fields_list}) are present in gathered_data. If yes, set next_state to "DONE". If no, find the first missing field state using _find_next_gather_state and set next_state to that. Formulate a prompt indicating confirmation but need for more info (e.g., "Okay, confirmed. We still need the [missing field]...").
            - If they deny ('no', 'confirm_no', etc.), extract intent:'deny'. Ask them specifically what needs to be corrected and set next_state to "HANDLE_CORRECTION".
            - If unclear, extract intent:'clarify'. Ask them to clarify with a 'yes' or 'no', staying in AWAIT_CONFIRMATION.

            **Output Format:** Respond ONLY with a valid JSON object:
            {{
                "prompt_to_user": "Your response/question...",
                "next_state": "DONE | HANDLE_CORRECTION | AWAIT_CONFIRMATION | GATHER_...",
                "extracted_data": {{ "intent": "confirm|deny|clarify" }}
            }}
            """.format(
            required_fields_list=REQUIRED_FIELDS
        ),
        "HANDLE_CORRECTION": """
             You are the InstaBids Homeowner Agent.
             Current Gathered Data: {gathered_data}
             User Input: {user_message}

             Task: The user indicated something was wrong with the summary. Analyze their message to understand which field needs correction (e.g., title, description, location).
             - Determine the GATHER_ state corresponding to the field mentioned (e.g., if user says "the zip code is wrong", next state is GATHER_LOCATION).
             - Extract any corrected information provided directly by the user (e.g., if they say "the zip code should be 12345", extract "12345" for "location_description").
             - Formulate a prompt asking for the corrected information if it wasn't provided directly.
             - If unclear which field needs changing, ask for clarification, staying in HANDLE_CORRECTION.

             **Output Format:** Respond ONLY with a valid JSON object:
             {{
                 "prompt_to_user": "Okay, let's fix that. What should the [field name] be?",
                 "next_state": "GATHER_FIELD_TO_CORRECT | HANDLE_CORRECTION", // e.g., GATHER_LOCATION
                 "extracted_data": {{ "field_to_correct": "corrected value" }} // If correction provided
             }}
             """,
    }

    # --- Define State Mapping Logic (Corrected) ---
    def state_mapper(
        current_state: str, llm_output: str, gathered_data: Dict
    ) -> Tuple[str, Dict, Optional[Union[str, Dict]]]:
        """
        Parses LLM output and determines the next state, updated data, and user prompt.
        Returns: (next_state, updated_data, prompt_to_user)
        """
        logger.debug(
            f"State Mapper - Current: {current_state}, LLM Output: {llm_output}"
        )
        next_state = current_state  # Default to staying in the same state on error
        updated_data = gathered_data.copy()  # Work on a copy
        prompt_to_user = "Sorry, I didn't quite understand that. Could you please rephrase?"  # Default error prompt
        prompt_to_user_from_llm = None  # Store prompt from LLM separately

        try:
            # Attempt to parse the LLM output as JSON
            output_data = json.loads(llm_output)
            next_state_suggestion = output_data.get("next_state", current_state)
            extracted = output_data.get("extracted_data", {})
            # Get prompt which might be string or dict (for quick replies)
            prompt_to_user_from_llm = output_data.get("prompt_to_user")

            # Update gathered data, prioritizing newly extracted info
            for key, value in extracted.items():
                # Handle boolean conversion specifically for allow_group_bidding if needed
                if key == "allow_group_bidding" and isinstance(value, str):
                    value = value.lower() == "true"  # Example conversion
                if value or isinstance(
                    value, bool
                ):  # Update if value is truthy or boolean false
                    updated_data[key] = value

            # --- Basic State Transition Logic ---
            if next_state_suggestion in states:
                next_state = next_state_suggestion
            else:
                # Allow LLM to suggest specific GATHER state for corrections
                if (
                    current_state == "HANDLE_CORRECTION"
                    and next_state_suggestion.startswith("GATHER_")
                    and next_state_suggestion in states
                ):
                    next_state = next_state_suggestion
                else:
                    logger.warning(
                        f"LLM suggested invalid next state: {next_state_suggestion}. Staying in {current_state}."
                    )
                    next_state = current_state  # Stay put if suggestion is invalid

            # --- Specific State Logic & Validation ---
            # Use a flag to indicate if we need to re-prompt due to validation failure
            validation_failed = False

            if current_state == "GATHER_TITLE":
                title = updated_data.get("title")  # Check updated_data
                if (
                    not title
                    or len(str(title).split()) > 10
                    or len(str(title).split()) < 1
                    or str(title).lower() in ["yes", "no", "ok", "okay"]
                ):
                    logger.warning(
                        f"Title extraction failed or invalid in state {current_state}. Asking again."
                    )
                    next_state = "GATHER_TITLE"
                    prompt_to_user = "Sorry, I need a short, descriptive title for the project (e.g., 'Fix Leaky Faucet'). What would you like to call it?"
                    updated_data.pop("title", None)
                    validation_failed = True
                elif (
                    next_state == "GATHER_TITLE"
                ):  # If valid but LLM didn't suggest moving on
                    next_state = _find_next_gather_state(updated_data)

            elif current_state == "GATHER_DESCRIPTION":
                desc = updated_data.get("description")
                if not desc or len(str(desc).split()) < 3:
                    logger.warning(
                        f"Description extraction failed or too short in state {current_state}. Asking again."
                    )
                    next_state = "GATHER_DESCRIPTION"
                    prompt_to_user = (
                        "Could you please provide a bit more detail about the project?"
                    )
                    updated_data.pop("description", None)
                    validation_failed = True
                elif next_state == "GATHER_DESCRIPTION":
                    next_state = _find_next_gather_state(updated_data)

            elif current_state == "GATHER_PROJECT_TYPE":
                proj_type = updated_data.get("project_type")
                valid_types = [
                    "one-time",
                    "recurring",
                    "repair",
                    "handyman",
                    "labor-only",
                    "multi-step",
                ]
                if not proj_type or proj_type not in valid_types:
                    logger.warning(
                        f"Project type extraction failed or invalid in state {current_state}. Asking again with options."
                    )
                    next_state = "GATHER_PROJECT_TYPE"
                    prompt_to_user = {
                        "text": "Sorry, I didn't catch that. What type of project is this?",
                        "quick_replies": [
                            {
                                "title": "One-Time (e.g., Install)",
                                "payload": "one-time",
                            },
                            {
                                "title": "Recurring (e.g., Cleaning)",
                                "payload": "recurring",
                            },
                            {"title": "Repair", "payload": "repair"},
                            {"title": "Handyman", "payload": "handyman"},
                            {"title": "Labor Help", "payload": "labor-only"},
                            {"title": "Multi-Step/Remodel", "payload": "multi-step"},
                        ],
                    }
                    updated_data.pop("project_type", None)
                    validation_failed = True
                elif next_state == "GATHER_PROJECT_TYPE":
                    next_state = _find_next_gather_state(updated_data)

            elif current_state == "GATHER_CATEGORY":
                category = updated_data.get("category")
                if not category:
                    logger.warning(
                        f"Category extraction failed in state {current_state}. Asking again."
                    )
                    next_state = "GATHER_CATEGORY"
                    # Refined re-prompt based on project type
                    ptype = updated_data.get("project_type", "project")
                    examples = "(e.g., Roofing, Plumbing, Painting)"
                    if ptype == "repair":
                        examples = "(e.g., Plumbing, Electrical, Drywall, Appliance)"
                    elif ptype == "recurring":
                        examples = "(e.g., Lawn Care, Cleaning, Pool Service)"
                    prompt_to_user = f"Sorry, what category would you put this '{ptype}' in? {examples}"
                    updated_data.pop("category", None)
                    validation_failed = True
                elif next_state == "GATHER_CATEGORY":
                    next_state = _find_next_gather_state(updated_data)

            elif current_state == "GATHER_LOCATION":
                zip_code = updated_data.get("location_description")
                if not zip_code or not re.match(r"^\d{5}$", str(zip_code)):
                    logger.warning(f"Invalid zip code format detected: {zip_code}")
                    next_state = "GATHER_LOCATION"
                    updated_data["last_error"] = (
                        "Invalid zip code format. Please provide a 5-digit zip code."
                    )
                    prompt_to_user = "That doesn't look like a valid 5-digit US zip code. Could you please provide the zip code for the project location?"
                    updated_data.pop("location_description", None)
                    validation_failed = True
                elif next_state == "GATHER_LOCATION":
                    next_state = _find_next_gather_state(updated_data)

            elif current_state == "GATHER_TIMELINE":
                timeline = updated_data.get("timeline")
                valid_timelines = [
                    "emergency",
                    "few_days_week",
                    "within_month",
                    "budgeting",
                    "dream_project",
                ]
                if not timeline or timeline not in valid_timelines:
                    logger.warning(
                        f"Timeline extraction failed or invalid in state {current_state}. Asking again with options."
                    )
                    next_state = "GATHER_TIMELINE"
                    prompt_to_user = {
                        "text": "What's your ideal timeframe for this project?",
                        "quick_replies": [
                            {"title": "Emergency (ASAP)", "payload": "emergency"},
                            {"title": "Within Days/Week", "payload": "few_days_week"},
                            {"title": "Within a Month", "payload": "within_month"},
                            {"title": "Budgeting/Planning", "payload": "budgeting"},
                            {
                                "title": "Dream Project (Flexible)",
                                "payload": "dream_project",
                            },
                        ],
                    }
                    updated_data.pop("timeline", None)
                    validation_failed = True
                elif next_state == "GATHER_TIMELINE":
                    next_state = _find_next_gather_state(updated_data)

            elif current_state == "GATHER_DESIRED_OUTCOME":
                outcome = updated_data.get("desired_outcome_description")
                if not outcome or len(str(outcome).split()) < 2:  # Basic check
                    logger.warning(
                        f"Desired outcome extraction failed or too short in state {current_state}. Asking again."
                    )
                    next_state = "GATHER_DESIRED_OUTCOME"
                    prompt_to_user = "Could you please describe the desired outcome in a bit more detail?"
                    updated_data.pop("desired_outcome_description", None)
                    validation_failed = True
                elif next_state == "GATHER_DESIRED_OUTCOME":
                    next_state = _find_next_gather_state(updated_data)

            elif current_state == "CONFIRM_GROUP_BIDDING":
                pref = updated_data.get("allow_group_bidding")  # Expecting boolean
                if pref is None:  # Check if LLM failed to extract boolean
                    logger.warning(
                        f"Group bidding preference extraction failed in state {current_state}. Asking again."
                    )
                    next_state = "CONFIRM_GROUP_BIDDING"
                    prompt_to_user = {
                        "text": "Sorry, I need a clear yes or no. Would you be open to grouping this job for potential discounts?",
                        "quick_replies": [
                            {"title": "Yes", "payload": "confirm_yes"},
                            {"title": "No", "payload": "confirm_no"},
                        ],
                    }
                    updated_data.pop("allow_group_bidding", None)
                    validation_failed = True
                elif next_state == "CONFIRM_GROUP_BIDDING":
                    next_state = _find_next_gather_state(updated_data)

            elif current_state == "HANDLE_CURRENT_PHOTOS":
                # Logic is simple: just mark as handled and move on
                if (
                    next_state == "HANDLE_CURRENT_PHOTOS"
                ):  # Ensure LLM didn't suggest invalid state
                    next_state = _find_next_gather_state(updated_data)

            elif current_state == "HANDLE_INSPIRATION_PHOTOS":
                # Logic is simple: just mark as handled and move on
                if (
                    next_state == "HANDLE_INSPIRATION_PHOTOS"
                ):  # Ensure LLM didn't suggest invalid state
                    next_state = _find_next_gather_state(updated_data)

            # --- Logic for Confirmation State ---
            elif current_state == "AWAIT_CONFIRMATION":
                user_intent = extracted.get("intent", "clarify")
                if user_intent == "confirm":
                    if _all_required_fields_gathered(updated_data):
                        next_state = "DONE"
                        prompt_to_user = "Great! Project details confirmed."
                        logger.info(
                            "All required fields confirmed. Transitioning to DONE."
                        )
                    else:
                        next_state = _find_next_gather_state(updated_data)
                        prompt_to_user = f"Okay, but it looks like we still need some details. Let's get the {next_state.split('_')[-1].lower()}..."
                        logger.warning(
                            f"Confirmation received, but required fields missing. Transitioning to {next_state}."
                        )
                elif user_intent == "deny":
                    next_state = "HANDLE_CORRECTION"
                    prompt_to_user = "Okay, what needs to be changed?"
                    logger.info(
                        "User denied confirmation. Moving to HANDLE_CORRECTION."
                    )
                else:  # Unclear confirmation
                    next_state = "AWAIT_CONFIRMATION"
                    prompt_to_user = "Sorry, I need a clear 'yes' or 'no'. Does the summary look correct?"
                    logger.info(
                        "User confirmation unclear. Staying in AWAIT_CONFIRMATION."
                    )
                # Don't automatically advance if confirmation was handled
                validation_failed = True  # Prevent automatic advance below

            # --- Ensure we eventually reach CONFIRM_DETAILS ---
            # Only advance if validation didn't fail and we aren't handling confirmation/correction
            if (
                not validation_failed
                and current_state.startswith("GATHER_")
                and next_state.startswith("GATHER_")
                and next_state != current_state
                and _all_required_fields_gathered(updated_data)
            ):
                next_state = _find_next_gather_state(updated_data)
                logger.info(
                    f"All required fields gathered after {current_state}. Moving check to {next_state}"
                )

            # Use the prompt from the LLM unless validation failed and set a specific one
            final_prompt = (
                prompt_to_user if validation_failed else prompt_to_user_from_llm
            )

            logger.debug(
                f"State Mapper - Final Next State: {next_state}, Updated Data: {updated_data}"
            )
            # Return the potentially modified prompt along with state and data
            return next_state, updated_data, final_prompt

        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM JSON output: {llm_output}")
            updated_data["last_error"] = "LLM output parsing failed."
            prompt_to_user = (
                "I had trouble understanding that response format. Could you try again?"
            )
            return current_state, updated_data, prompt_to_user
        except Exception as e:
            logger.error(f"Error in state mapper: {e}", exc_info=True)
            updated_data["last_error"] = f"State mapping error: {e}"
            prompt_to_user = "An internal error occurred while processing your request."
            return "FAILED", updated_data, prompt_to_user

    # --- Create LLMFlow Instance ---
    llm_flow = LLMFlow(
        llm=llm_service,
        prompt_templates=prompt_templates,
        initial_state=initial_state,
        final_states=final_states,
        state_mapper=state_mapper,  # Pass the refined mapper
        memory=memory_service,  # Pass the memory service instance
    )
    logger.info("LLMFlow for project creation built.")
    return llm_flow
