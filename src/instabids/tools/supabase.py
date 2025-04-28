from pathlib import Path
from google.adk.tools.openapi_tools import OpenAPIToolset

# Load the spec that sits next to this file
_SPEC_PATH = Path(__file__).with_name("openapi_supabase.yaml")

# Create the toolset once at import-time
supabase_toolset = OpenAPIToolset.from_spec_file(
    spec_path=_SPEC_PATH,
    # Inject runtime base URL & headers using lambdas so they’re evaluated per call
    base_url=lambda: "https://{}.supabase.co".format(__import__("os").environ["SUPABASE_PROJECT_REF"]),
    auth_headers=lambda: {
        "apikey": __import__("os").environ["SUPABASE_KEY"],
        "Authorization": f"Bearer {__import__('os').environ['SUPABASE_SERVICE_ROLE']}",
    },
)

# Re-export the list of tools (ADK expects list[Tool])
supabase_tools = supabase_toolset.tools
