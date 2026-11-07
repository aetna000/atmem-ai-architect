"""Authenticated direct invocation; no document text is logged."""
import os

MAX_INPUT_BYTES = int(os.environ.get("MAX_INPUT_BYTES", "65536"))

def handler(event, context):
    if not isinstance(event, dict) or set(event) != {"text"} or not isinstance(event["text"], str):
        raise ValueError("Expected an object containing only a text string")
    text = event["text"]
    try:
        size = len(text.encode("utf-8"))
    except UnicodeEncodeError:
        raise ValueError("Text must be valid Unicode") from None
    if size > MAX_INPUT_BYTES:
        raise ValueError("Text exceeds the configured byte limit")
    return {"wordCount": len(text.split()), "characterCount": len(text)}
