"""
Utility functions for the Homeowner Agent.

Contains helper functions for tasks like database interactions,
external API calls (Vision, OCR), and triggering other agents,
keeping the main agent logic cleaner.
"""

import logging
from typing import Any, Dict, Optional, List, Tuple
import uuid
import asyncio
import json  # For logging structured data
import re  # For potential redaction

# Google Cloud Vision client library
from google.cloud import vision
from supabase import Client

# Import core types and A2A client
# Assuming ADK LLM type hint is available
from google.adk.models import Llm  # Placeholder type hint
from ...a2a_types.core import (
    Artifact,
    AgentId,
    TaskId,
    MessageId,
    Agent as A2aAgentInfo,
    ArtifactType,
)
from ...a2a_comm import client as a2a_client
import os  # For environment variables

logger = logging.getLogger(__name__)


async def analyze_photo(
    vision_client: Optional[vision.ImageAnnotatorClient],
    artifacts: List[Artifact],
    initial_context: Dict = None,  # Pass initial context if needed for refinement
) -> Dict:
    """Calls vision service to analyze photo artifacts."""
    if initial_context is None:
        initial_context = {}
    logger.info(
        f"Analyzing photo artifacts: {[getattr(a, 'id', 'N/A') for a in artifacts]}"
    )
    if not vision_client:
        logger.warning("Vision client not available for photo analysis.")
        return {}

    analysis_results = {"photo_analysis": {}}
    all_labels = set()
    all_objects = set()
    all_texts = []

    image_artifacts = [
        a for a in artifacts if getattr(a, "type", None) == ArtifactType.IMAGE
    ]

    if not image_artifacts:
        logger.info("No image artifacts found to analyze.")
        return {}

    # Prepare batch request
    requests = []
    processed_identifiers = []  # Store URI or artifact ID
    for artifact in image_artifacts:
        image_uri = getattr(artifact, "uri", None)
        image_content = getattr(artifact, "content", None)
        identifier = f"artifact_{getattr(artifact, 'id', 'N/A')}"  # Default identifier

        image = vision.Image()
        valid_input = False
        # Prioritize URI if available and looks like a GCS path (common for Vision API)
        if image_uri and isinstance(image_uri, str) and image_uri.startswith("gs://"):
            image.source.image_uri = image_uri
            identifier = image_uri
            valid_input = True
        elif image_content and isinstance(image_content, bytes):
            image.content = image_content
            valid_input = True
        elif image_uri and isinstance(
            image_uri, str
        ):  # Handle non-GCS URIs if needed (might require fetching)
            logger.warning(
                f"Artifact {identifier} has non-GCS URI '{image_uri}'. Direct content preferred or implement fetching."
            )
            # TODO: Optionally fetch content from non-GCS URI if needed
            continue
        else:
            logger.warning(
                f"Skipping artifact {identifier}: Invalid or missing image URI (gs://) or content (bytes)."
            )
            continue

        if valid_input:
            features = [
                vision.Feature(
                    type_=vision.Feature.Type.LABEL_DETECTION, max_results=5
                ),
                vision.Feature(
                    type_=vision.Feature.Type.OBJECT_LOCALIZATION, max_results=5
                ),
                vision.Feature(type_=vision.Feature.Type.TEXT_DETECTION),
            ]
            requests.append(vision.AnnotateImageRequest(image=image, features=features))
            processed_identifiers.append(identifier)

    if not requests:
        logger.info("No valid image artifacts found to process.")
        return {}

    try:
        # Run synchronous batch call in executor
        loop = asyncio.get_running_loop()
        logger.info(f"Sending {len(requests)} image(s) to Vision API for analysis...")
        # Use run_in_executor for the blocking I/O call
        batch_response = await loop.run_in_executor(
            None,
            vision_client.batch_annotate_images,
            requests={"requests": requests},  # Pass as a dictionary
        )
        logger.debug(f"Vision API batch response received.")

        # Process batch response
        for i, response in enumerate(batch_response.responses):
            image_identifier = processed_identifiers[i]
            if response.error.message:
                logger.error(
                    f"Error analyzing photo {image_identifier}: {response.error.message}"
                )
                analysis_results["photo_analysis"][image_identifier] = {
                    "error": response.error.message
                }
                continue

            labels = [label.description for label in response.label_annotations]
            objects = [obj.name for obj in response.localized_object_annotations]
            texts = [text.description for text in response.text_annotations]
            full_text = (
                texts[0].strip().replace("\n", " ") if texts else ""
            )  # Clean up text

            logger.info(
                f"Analysis for {image_identifier}: Labels={labels}, Objects={objects}, Text='{full_text[:50]}...'"
            )
            analysis_results["photo_analysis"][image_identifier] = {
                "labels": labels,
                "objects": objects,
                "text": full_text,
            }
            all_labels.update(labels)
            all_objects.update(objects)
            if full_text:
                all_texts.append(full_text)

    except Exception as e:
        logger.error(
            f"Error calling Vision API batch_annotate_images: {e}", exc_info=True
        )
        # Add error entry for all processed URIs in case of batch failure
        for identifier in processed_identifiers:
            if identifier not in analysis_results.get("photo_analysis", {}):
                analysis_results.setdefault("photo_analysis", {})[identifier] = {
                    "error": f"Batch processing failed: {e}"
                }

    # Combine analysis into context
    context = {"photo_analysis_raw": analysis_results}
    derived_description_parts = []
    # Prioritize objects and text for description, then labels
    if all_objects:
        derived_description_parts.append(
            f"Detected objects include: {', '.join(list(all_objects)[:3])}."
        )
    if all_texts:
        derived_description_parts.append(
            f"Detected text includes: '{' | '.join(all_texts)}'."
        )
    if not derived_description_parts and all_labels:
        derived_description_parts.append(
            f"Image analysis suggests labels like: {', '.join(list(all_labels)[:3])}."
        )

    if derived_description_parts:
        existing_desc = initial_context.get("description", "")
        derived_desc = " ".join(derived_description_parts).strip()
        # Avoid duplicating if analysis is similar to existing description
        if derived_desc.lower() not in existing_desc.lower():
            context["description"] = f"{existing_desc} {derived_desc}".strip()
            logger.info(
                f"Updated context description based on photos: {context['description']}"
            )
        else:
            context["description"] = existing_desc

    return context


async def analyze_quote(
    ocr_service: Optional[Any],  # Could be vision_client
    llm_service: Optional[Llm],  # ADK LLM instance
    artifacts: List[Artifact],
) -> Dict:
    """Calls OCR/LLM service to analyze quote artifacts."""
    logger.info(
        f"Analyzing quote artifacts: {[getattr(a, 'id', 'N/A') for a in artifacts]}"
    )
    if not ocr_service or not llm_service:
        logger.warning("OCR or LLM service not available for quote analysis.")
        return {}

    full_text = ""
    analysis_results = {"quote_analysis": {}}
    quote_artifacts = [
        a for a in artifacts if getattr(a, "type", None) == ArtifactType.FILE
    ]

    if not quote_artifacts:
        logger.info("No quote artifacts (FILE type) found to analyze.")
        return {}

    # 1. Extract text using OCR service
    for artifact in quote_artifacts:
        doc_uri = getattr(artifact, "uri", None)
        doc_content = getattr(artifact, "content", None)
        artifact_id = getattr(artifact, "id", "N/A")

        if not doc_uri and not doc_content:
            logger.warning(
                f"Skipping quote artifact {artifact_id}: Missing URI or content."
            )
            continue

        logger.info(
            f"Processing quote artifact: {artifact_id} (URI: {doc_uri is not None}, Content: {doc_content is not None})"
        )
        try:
            extracted_text = ""
            if isinstance(ocr_service, vision.ImageAnnotatorClient):
                # Using Vision API Document Text Detection
                if doc_uri and doc_uri.startswith("gs://"):
                    gcs_source = vision.GcsSource(uri=doc_uri)
                    mime_type = "application/pdf"  # Default
                    if doc_uri.lower().endswith(".pdf"):
                        mime_type = "application/pdf"
                    elif doc_uri.lower().endswith((".png", ".jpg", ".jpeg", ".tiff")):
                        mime_type = "image/tiff"
                    else:
                        logger.warning(
                            f"Unsupported document type for GCS URI: {doc_uri}"
                        )
                        analysis_results["quote_analysis"][artifact_id] = {
                            "ocr_status": "skipped_unsupported_type"
                        }
                        continue

                    input_config = vision.InputConfig(
                        gcs_source=gcs_source, mime_type=mime_type
                    )
                    features = [
                        vision.Feature(
                            type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION
                        )
                    ]
                    # Define output config (required for async) - results go to GCS
                    gcs_destination_uri = os.getenv(
                        "OCR_RESULT_GCS_URI",
                        f"gs://your-ocr-results-bucket/results/{artifact_id}/",
                    )  # Example
                    if "your-ocr-results-bucket" in gcs_destination_uri:
                        logger.error(
                            "OCR_RESULT_GCS_URI environment variable not set. Cannot process async OCR."
                        )
                        analysis_results["quote_analysis"][artifact_id] = {
                            "ocr_status": "error_config_missing"
                        }
                        continue

                    gcs_destination = vision.GcsDestination(uri=gcs_destination_uri)
                    output_config = vision.OutputConfig(
                        gcs_destination=gcs_destination, batch_size=1
                    )

                    async_request = vision.AsyncAnnotateFileRequest(
                        requests=[
                            {
                                "input_config": input_config,
                                "features": features,
                                "output_config": output_config,
                            }
                        ]
                    )

                    loop = asyncio.get_running_loop()
                    logger.info(f"Submitting async OCR request for {doc_uri}...")
                    operation = await loop.run_in_executor(
                        None,
                        ocr_service.async_batch_annotate_files,
                        request=async_request,
                    )
                    operation_name = operation.operation.name
                    logger.info(
                        f"OCR operation started for {doc_uri}. Name: {operation_name}"
                    )

                    # --- Async Handling ---
                    # In a real system, store operation_name and poll or use Cloud Functions/PubSub.
                    # For now, we'll just log that it's pending and won't get the text this run.
                    logger.warning(
                        f"Async OCR submitted for {doc_uri}. Text extraction will require polling/callback mechanism based on operation name: {operation_name}"
                    )
                    extracted_text = None  # Indicate text is not yet available
                    analysis_results["quote_analysis"][artifact_id] = {
                        "ocr_status": "pending_async",
                        "operation_name": operation_name,
                    }
                    # --- End Async Handling ---

                elif doc_content and isinstance(doc_content, bytes):
                    logger.info(
                        f"Processing direct content for artifact {artifact_id}..."
                    )
                    image = vision.Image(content=doc_content)
                    # Use synchronous call for direct content
                    response = await asyncio.get_running_loop().run_in_executor(
                        None, ocr_service.document_text_detection, image=image
                    )
                    if response and response.full_text_annotation:
                        extracted_text = response.full_text_annotation.text
                        analysis_results["quote_analysis"][artifact_id] = {
                            "ocr_status": "success"
                        }
                    else:
                        logger.warning(
                            f"No text found in direct content for artifact {artifact_id}."
                        )
                        analysis_results["quote_analysis"][artifact_id] = {
                            "ocr_status": "no_text_found"
                        }
                else:
                    logger.warning(
                        f"Unsupported quote artifact format for OCR: {artifact_id}"
                    )
                    analysis_results["quote_analysis"][artifact_id] = {
                        "ocr_status": "skipped_unsupported_format"
                    }
                    continue

            else:
                logger.warning(f"OCR service type {type(ocr_service)} not implemented.")

            if (
                extracted_text
            ):  # Only append if text was successfully extracted synchronously
                full_text += extracted_text + "\n\n--- End of Document ---\n\n"

        except Exception as e:
            logger.error(
                f"Error during OCR for artifact {artifact_id}: {e}", exc_info=True
            )
            analysis_results["quote_analysis"][artifact_id] = {
                "error": f"OCR failed: {e}"
            }

    if not full_text:
        logger.warning("No text extracted synchronously from any quote artifacts.")
        # Return raw analysis which might contain pending/error statuses
        return {"quote_analysis_raw": analysis_results}

    # 2. Extract Scope/Materials using LLM (Price Redaction) - Only if text was extracted
    try:
        prompt = f"""
        Analyze the following text extracted from one or more contractor quotes.
        Identify the main scope of work described and list the key materials mentioned.
        Summarize these concisely.
        **CRITICAL: DO NOT include any numbers associated with prices, costs, totals, fees, or dollar amounts ($). Omit all monetary values.**
        Format the output strictly as a JSON object with keys "scope" (string summary of work) and "materials" (string summary or list of materials).

        Example Input Text:
        "Replace kitchen faucet. Labor: $150. Materials: Delta Faucet Model XYZ - $120. Total: $270."
        Example JSON Output:
        {{
            "scope": "Replace kitchen faucet",
            "materials": "Delta Faucet Model XYZ"
        }}

        Extracted Text:
        ---
        {full_text[:8000]}
        ---
        JSON Output:
        """  # Limit text length

        logger.info(
            "Calling LLM to extract scope/materials from quote text (price redacted)."
        )
        # --- Call ADK LLM Service ---
        llm_response = await llm_service.predict(
            prompt=prompt
        )  # Assumes predict is async
        llm_response_str = llm_response.text  # Assumes response has a text attribute
        logger.debug(f"LLM response for quote analysis: {llm_response_str}")

        # Parse LLM response (expecting JSON)
        cleaned_llm_response = llm_response_str.strip().strip("`").strip()
        if cleaned_llm_response.startswith("json"):
            cleaned_llm_response = cleaned_llm_response[4:].strip()

        extracted_data = json.loads(cleaned_llm_response)
        analysis_results["quote_analysis"]["llm_summary"] = extracted_data

        context = {"quote_analysis_raw": analysis_results}
        if extracted_data.get("scope"):
            # Sanitize description further just in case LLM missed something
            sanitized_scope = re.sub(
                r"\$\s?\d+([.,]\d+)?", "[PRICE REDACTED]", extracted_data["scope"]
            )
            context["description"] = f"Based on uploaded quote: {sanitized_scope}"
            logger.info(f"Derived description from quote: {context['description']}")
        return context

    except json.JSONDecodeError:
        logger.error(
            f"Failed to parse LLM JSON output for quote analysis: {cleaned_llm_response}"
        )
        analysis_results["quote_analysis"]["error"] = "LLM output parsing failed"
        return {"quote_analysis_raw": analysis_results}
    except Exception as e:
        logger.error(f"Error during LLM analysis of quote text: {e}", exc_info=True)
        analysis_results["quote_analysis"]["error"] = f"LLM analysis failed: {e}"
        return {"quote_analysis_raw": analysis_results}


async def save_project_to_db(db: Optional[Client], details: Dict) -> Optional[str]:
    """Saves the gathered project details to the Supabase database."""
    if not db:
        logger.error("Supabase client not initialized. Cannot save project.")
        return None

    logger.info(f"Attempting to save project: {details.get('title')}")

    project_data = {
        "homeowner_id": details.get("homeowner_id"),
        "title": details.get("title", "Untitled Project"),
        "description": details.get("description"),
        "category": details.get("category"),
        "location_description": details.get("location_description"),
        "status": "open",
        "desired_outcome_description": details.get(
            "desired_outcome_description"
        ),  # Added
        "metadata": {
            "project_type": details.get("project_type"),
            "timeline": details.get("timeline"),
            "allow_group_bidding": details.get("allow_group_bidding", False),
            # Add other relevant details from the gathering process
        },
    }
    if not project_data["homeowner_id"]:
        logger.error("Cannot save project: Missing homeowner_id.")
        return None

    project_data = {k: v for k, v in project_data.items() if v is not None}
    project_metadata = project_data.get("metadata", {})
    project_metadata = {k: v for k, v in project_metadata.items() if v is not None}
    project_data["metadata"] = project_metadata if project_metadata else None

    # Separate photo data based on type
    photo_paths = details.get(
        "photo_paths", []
    )  # Expecting list of dicts: {"path": "...", "type": "current|inspiration"}
    current_photo_data = []
    inspiration_photo_data = []
    if isinstance(photo_paths, list):
        for photo_info in photo_paths:
            if isinstance(photo_info, dict) and isinstance(photo_info.get("path"), str):
                photo_type = photo_info.get("type", "current")  # Default to current
                photo_entry = {
                    "storage_path": photo_info["path"],
                    "caption": photo_info.get("caption"),
                    "photo_type": photo_type,
                }
                if photo_type == "inspiration":
                    inspiration_photo_data.append(photo_entry)
                else:
                    current_photo_data.append(photo_entry)

    try:
        insert_res = await db.table("projects").insert(project_data).execute()
        logger.debug(f"Supabase project insert response: {insert_res}")

        if not insert_res.data:
            error_detail = getattr(insert_res, "error", None) or getattr(
                insert_res, "message", "Unknown error"
            )
            logger.error(
                f"Failed to insert project into Supabase. Detail: {error_detail}"
            )
            return None

        project_id = insert_res.data[0]["id"]
        logger.info(f"Project {project_id} inserted successfully.")

        # Insert photos (both types)
        all_photo_insert_data = []
        for photo_list in [current_photo_data, inspiration_photo_data]:
            for photo_data in photo_list:
                photo_data["project_id"] = project_id
                all_photo_insert_data.append(photo_data)

        if all_photo_insert_data:
            photo_res = (
                await db.table("project_photos").insert(all_photo_insert_data).execute()
            )
            logger.debug(f"Supabase photo insert response: {photo_res}")
            if not photo_res.data:
                logger.error(
                    f"Failed to insert photos for project {project_id}. Response: {photo_res}"
                )
            else:
                logger.info(
                    f"Inserted {len(photo_res.data)} photos for project {project_id}."
                )

        return project_id

    except Exception as e:
        logger.error(f"Error saving project to Supabase: {e}", exc_info=True)
        return None


async def trigger_bid_card_creation(
    creator_agent_id: AgentId,
    original_task_id: TaskId,
    project_id: str,
    project_details: Dict,
):
    """Creates a task for the BidCardAgent to process the newly created project."""
    logger.info(f"Triggering Bid Card creation for project {project_id}")

    bid_card_agent_id = os.getenv("BID_CARD_AGENT_ID", "bid-card-agent-001")
    bid_card_agent_endpoint = os.getenv(
        "BID_CARD_AGENT_ENDPOINT", "http://localhost:8002"
    )

    if not bid_card_agent_endpoint:
        logger.error("Bid Card Agent endpoint not configured. Cannot trigger task.")
        return

    target_agent_info = A2aAgentInfo(
        id=bid_card_agent_id, name="Bid Card Agent", endpoint=bid_card_agent_endpoint
    )
    task_description = (
        f"Generate standardized Bid Card artifact for project {project_id}"
    )
    task_metadata = {
        "project_id": project_id,
        "original_task_id": original_task_id,
        "project_title": project_details.get("title"),
        "project_category": project_details.get("category"),
    }

    try:
        created_task = await a2a_client.create_task(
            target_agent=target_agent_info,
            creator_agent_id=creator_agent_id,
            description=task_description,
            metadata=task_metadata,
        )
        if created_task:
            logger.info(
                f"Successfully created task {created_task.id} for BidCardAgent."
            )
        else:
            logger.error(
                f"Failed to create task for BidCardAgent for project {project_id}."
            )
    except Exception as e:
        logger.error(
            f"Error calling A2A client to create BidCardAgent task: {e}", exc_info=True
        )
