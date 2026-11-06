"""Explicit Developer API settings for structured generation and vision."""


def create_gemini_client(api_key):
    from google import genai
    from google.genai import types
    # JSON output must not inherit a stable-v1 client default from the SDK/env.
    return genai.Client(api_key=api_key, http_options=types.HttpOptions(api_version="v1beta"))
