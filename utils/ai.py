import os
import logging
from typing import Optional

try:
    import requests
except Exception:
    requests = None

logger = logging.getLogger(__name__)

# Try to import the modern OpenAI client
_OPENAI_AVAILABLE = False
try:
    from openai import OpenAI

    _OPENAI_AVAILABLE = True
except Exception:
    OpenAI = None


def _get_api_key() -> Optional[str]:
    return os.environ.get("OPENAI_API_KEY")


def _make_client(api_key: str):
    """Create and return an OpenAI client instance (modern SDK).

    Returns None if the SDK isn't available.
    """
    if not _OPENAI_AVAILABLE or not api_key:
        return None
    try:
        return OpenAI(api_key=api_key)
    except Exception as e:
        logger.exception("Failed to construct OpenAI client: %s", e)
        return None


def _hf_inference(prompt: str, model: Optional[str] = None) -> str:
    """Call Hugging Face Inference API using HUGGINGFACE_API_KEY.

    Returns the generated text or raises on failure.
    """
    key = os.environ.get("HUGGINGFACE_API_KEY")
    if not key or requests is None:
        raise RuntimeError("Hugging Face API key not set or 'requests' not available")

    model = model or os.environ.get("HUGGINGFACE_MODEL", "google/flan-t5-small")
    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 400}}

    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"HF Inference failed: {resp.status_code} {resp.text}")
    data = resp.json()
    # HF returns a list of generated outputs for text models, or dict for some endpoints
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
        return data[0].get("generated_text") or str(data[0])
    if isinstance(data, dict) and "generated_text" in data:
        return data["generated_text"]
    # Fallback: try first string element
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], str):
        return data[0]
    return str(data)


def _extract_chat_response(resp) -> str:
    """Try to robustly extract assistant text from a chat completion response."""
    try:
        choices = getattr(resp, "choices", None) or resp.get("choices")
        if choices and len(choices) > 0:
            first = choices[0]
            # choice.message may be an object or dict
            msg = getattr(first, "message", None) or first.get("message")
            if msg:
                content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
                if content:
                    return content.strip()
        # Fallback: try top-level 'text' or str()
        text = getattr(resp, "text", None) or resp.get("text") if isinstance(resp, dict) else None
        if text:
            return str(text).strip()
        return str(resp)
    except Exception:
        return str(resp)


def convert_gateway_script(script: str) -> str:
    """Attempt to convert a gateway script (IBM style) into an AWS API Gateway
    compatible integration snippet using an AI model. If OpenAI is not
    configured, returns the original script.

    This function is best-effort and should be reviewed by a human.
    """
    api_key = _get_api_key()
    client = _make_client(api_key)

    prompt = (
        "You are an expert in converting IBM API Connect gateway assembly scripts"
        " to AWS API Gateway compatible integration/transform code.\n"
        "Convert the following IBM gateway script or invocation into an equivalent"
        " AWS API Gateway integration or mapping template where possible. Be concise"
        " and include only the converted script. If the script cannot be converted,"
        " explain briefly why.\n\nScript:\n" + script
    )

    # Try OpenAI first if available
    if client is not None:
        try:
            resp = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                temperature=0.2,
            )
            content = _extract_chat_response(resp)
            return content
        except Exception as e:
            logger.exception("AI conversion failed (OpenAI): %s", e)

    # Fallback: try Hugging Face Inference API if configured
    try:
        hf_out = _hf_inference(prompt)
        return hf_out
    except Exception as e:
        logger.info("HF fallback not available or failed: %s", e)

    # No AI conversion available; return original script
    return script


def review_and_comment_yaml(yaml_text: str) -> str:
    """Ask an AI model to review the transformed YAML and return a commented
    version (YAML with comments) or a human-readable review. If AI is not
    available, returns an empty string.
    """
    api_key = _get_api_key()
    client = _make_client(api_key)

    prompt = (
        "You are an experienced API engineer. Review the following OpenAPI/Swagger"
        " YAML that has been transformed for AWS API Gateway. Provide a commented"
        " version of the YAML (add helpful inline comments beginning with '#') and"
        " a short summary of any potential runtime issues or recommended improvements.\n\n"
        "YAML:\n" + yaml_text
    )

    if client is not None:
        try:
            resp = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.2,
            )
            content = _extract_chat_response(resp)
            return content
        except Exception as e:
            logger.exception("AI review failed (OpenAI): %s", e)

    # Fallback to Hugging Face if available
    try:
        return _hf_inference(prompt, model=os.environ.get("HUGGINGFACE_MODEL"))
    except Exception as e:
        logger.info("HF review fallback not available or failed: %s", e)
        return ""
