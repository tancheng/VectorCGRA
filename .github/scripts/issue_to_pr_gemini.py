#!/usr/bin/env python3
# scripts/generate_patch.py
# Refactored, robust caller for Google's Gemini generateContent API
# Exits non-zero on error so your GitHub Action fails early.

from __future__ import annotations
import os
import sys
import time
import json
import re
import logging
from typing import Optional
import requests

# Configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 2  # seconds
TIMEOUT_SECONDS = 60

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def get_env_var(name: str, required: bool = True, default: Optional[str] = None) -> Optional[str]:
    value = os.environ.get(name, default)
    if required and not value:
        logger.error("Missing required environment variable: %s", name)
        sys.exit(2)
    return value


def build_prompt(title: str, body: str) -> str:
    return (
        "You are an expert software developer and GitHub bot.\n"
        "Read the following GitHub issue and generate the code changes required to fix it.\n\n"
        f'ISSUE TITLE: "{title}"\n\n'
        "ISSUE BODY:\n"
        f'"{body}"\n\n'
        "IMPORTANT: Respond ONLY with the code changes in a 'diff' or 'patch' format, "
        "starting with '--- a/' or 'diff --git'. Do not include any other text, explanations, "
        "or markdown formatting like '```patch'. Just provide the raw patch file content."
    )


def call_gemini(api_key: str, prompt: str, model: str) -> str:
    """
    Call the Gemini (Generative Language) API and return the raw text response.
    Retries on transient network errors.
    """
    # Use the API-key-in-url approach (common for Google's simple API key usage).
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ],
        # You can tune model settings here if needed.
        # "temperature": 0.0,
        # "candidateCount": 1,
    }

    backoff = INITIAL_BACKOFF
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info("Calling Gemini API (attempt %d/%d)...", attempt, MAX_RETRIES)
            resp = requests.post(url, json=payload, timeout=TIMEOUT_SECONDS)
            resp.raise_for_status()
            return resp.text  # return raw response text; we'll parse JSON next
        except requests.exceptions.RequestException as exc:
            logger.warning("Request attempt %d failed: %s", attempt, exc)
            if attempt == MAX_RETRIES:
                logger.error("Exceeded max retries calling Gemini API.")
                logger.debug("Last response (if any): %s", getattr(exc, "response", None))
                raise
            else:
                logger.info("Sleeping %s seconds before retrying...", backoff)
                time.sleep(backoff)
                backoff *= 2

    raise RuntimeError("Unreachable code in call_gemini")


def parse_gemini_response_text(response_text: str) -> str:
    """
    Parse the JSON returned by the Gemini API and extract the candidate text.
    Be defensive about the JSON structure and report helpful debug info on failure.
    """
    try:
        response_json = json.loads(response_text)
    except json.JSONDecodeError:
        logger.exception("Failed to decode Gemini response as JSON.")
        raise

    # The expected structure (based on the API shape used) is:
    # { "candidates": [ { "content": { "parts": [ {"text": "..."}, ... ] } }, ... ] }
    try:
        candidates = response_json.get("candidates")
        if not candidates or not isinstance(candidates, list):
            raise KeyError("No 'candidates' list in response")

        first = candidates[0]
        content = first.get("content")
        parts = content.get("parts")
        if not parts or not isinstance(parts, list):
            raise KeyError("No 'content.parts' list in response")

        text = parts[0].get("text")
        if not isinstance(text, str):
            raise KeyError("'text' field missing or not a string")

        return text
    except Exception as e:
        logger.error("Unexpected Gemini response structure: %s", e)
        logger.debug("Full response JSON: %s", json.dumps(response_json, indent=2)[:2000])
        raise


def extract_patch(raw_text: str) -> Optional[str]:
    """
    Try to extract a diff/patch from the model output.
    Acceptable starts: 'diff --git', '--- a/'.
    If wrapped in triple-backticks, remove them.
    """
    text = raw_text.strip()

    # If the model returned the JSON string (rare), ensure it's string
    # Remove common triple-backtick fences with optional language
    # Use non-greedy match so we can handle additional text before/after.
    code_block_match = re.search(r"```(?:patch|diff|\s)?\n([\s\S]+?)\n```", text, re.IGNORECASE)
    if code_block_match:
        candidate = code_block_match.group(1).strip()
        logger.debug("Extracted content from fenced code block.")
    else:
        candidate = text

    # If the content contains multiple sections, try to find the diff portion
    diff_match = re.search(r"(diff --git[\s\S]+)$", candidate, re.MULTILINE)
    if diff_match:
        return diff_match.group(1).strip()

    # Alternative start
    alt_match = re.search(r"(^--- a/[\s\S]+)$", candidate, re.MULTILINE)
    if alt_match:
        return alt_match.group(1).strip()

    # If candidate itself begins with a patch-like header, accept it
    if candidate.startswith("diff --git") or candidate.startswith("--- a/"):
        return candidate.strip()

    # No clear patch found
    return None


def save_patch(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    logger.info("Wrote patch to %s (size %d bytes).", path, len(content.encode("utf-8")))


def main() -> None:
    api_key = get_env_var("GEMINI_API_KEY")
    issue_title = get_env_var("ISSUE_TITLE", required=True)
    issue_body = get_env_var("ISSUE_BODY", required=True)
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")  # override with env var if desired

    prompt = build_prompt(issue_title, issue_body)

    try:
        raw_response_text = call_gemini(api_key, prompt, model)
    except Exception as exc:
        logger.exception("Failed to get a response from Gemini: %s", exc)
        sys.exit(1)

    try:
        candidate_text = parse_gemini_response_text(raw_response_text)
    except Exception:
        logger.error("Could not parse Gemini JSON response.")
        sys.exit(1)

    patch = extract_patch(candidate_text)

    if not patch:
        # Provide helpful debug output but do not print the API key or long raw responses
        snippet = candidate_text.strip()[:1000] + ("..." if len(candidate_text) > 1000 else "")
        logger.error("Response did not contain a recognizable patch/diff header.")
        logger.debug("Model output (first 1000 chars):\n%s", snippet)
        # Save the raw output for inspection (avoid leaking secrets). This can help debugging.
        fallback_path = "ai_fix_raw_output.txt"
        try:
            save_patch(fallback_path, candidate_text)
            logger.info("Saved raw model output to %s for inspection.", fallback_path)
        except Exception:
            logger.exception("Failed to save raw model output.")
        sys.exit(3)

    # Save validated patch
    try:
        save_patch("ai_fix.patch", patch)
    except Exception:
        logger.exception("Failed to write ai_fix.patch")
        sys.exit(1)

    logger.info("Successfully generated ai_fix.patch.")
    # Exit 0 on success
    sys.exit(0)


if __name__ == "__main__":
    main()

