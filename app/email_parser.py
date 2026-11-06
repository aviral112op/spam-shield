import html
import re
from email import policy
from email.parser import BytesParser
from typing import Tuple

_SCRIPT_STYLE = re.compile(r"<(script|style)\b.*?</\1>", re.IGNORECASE | re.DOTALL)
_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")


def html_to_text(markup: str) -> str:
    text = _SCRIPT_STYLE.sub(" ", markup)
    text = _TAG.sub(" ", text)
    return _WHITESPACE.sub(" ", html.unescape(text)).strip()


def parse_eml(data: bytes) -> Tuple[str, str]:
    """Return (subject, body text) from a raw .eml file, preferring the plain-text part."""
    msg = BytesParser(policy=policy.default).parsebytes(data)
    subject = str(msg.get("subject", "") or "").strip()

    body = ""
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is not None:
        body = part.get_content()
        if part.get_content_type() == "text/html":
            body = html_to_text(body)
    return subject, body.strip()
