"""
Open-source friendly reply suggestions without external API keys.
Uses lightweight heuristics over recent messages; extensible to Hugging Face / Ollama.
"""

from __future__ import annotations

from typing import Iterable

from .models import Message


def _last_peer_text(messages: Iterable[Message], current_user_id: int) -> str:
    for m in reversed(list(messages)):
        if m.sender_id != current_user_id and (m.body or "").strip():
            return m.body.strip()
    return ""


def _templates(lang: str, tone: str) -> dict[str, str]:
    is_hi = lang == "hi"
    casual = tone == "casual"
    if is_hi:
        if casual:
            return {
                "ack": "ठीक है, मैं समझ गया। चलो बाद में बात करते हैं।",
                "thanks": "धन्यवाद! इसकी सराहना है।",
                "question": "अच्छा सवाल — मैं जाँच करके जल्द ही बताता हूँ।",
                "default": "मैं यहाँ मदद के लिए हूँ। आप क्या चाहते हैं कि हम अगला कदम उठाएँ?",
            }
        return {
            "ack": "जी, मैंने नोट कर लिया। आवश्यकतानुसार अगले चरण साझा करूँगा।",
            "thanks": "आपके संदेश के लिए धन्यवाद।",
            "question": "यह बिंदु स्पष्ट करने के लिए संक्षिप्त विवरण साझा करें, ताकि मैं सटीक उत्तर दे सकूँ।",
            "default": "कृपया अपनी आवश्यकता संक्षेप में बताएँ ताकि मैं उचित प्रतिक्रिया दे सकूँ।",
        }
    if casual:
        return {
            "ack": "Got it — thanks for the heads-up!",
            "thanks": "Appreciate it!",
            "question": "Good question — let me check and get back to you shortly.",
            "default": "I'm here to help. What would you like to tackle next?",
        }
    return {
        "ack": "Noted. I will follow up with the appropriate next steps.",
        "thanks": "Thank you for your message.",
        "question": "Could you share a bit more context so I can respond precisely?",
        "default": "Please share the key details you would like addressed, and I will respond accordingly.",
    }


def suggest_reply(
    *,
    messages: list[Message],
    current_user_id: int,
    language: str = "en",
    tone: str = "professional",
) -> str:
    language = "hi" if language == "hi" else "en"
    tone = "casual" if tone == "casual" else "professional"
    t = _templates(language, tone)
    peer = _last_peer_text(messages, current_user_id)
    low = peer.lower()
    if not peer:
        return t["default"]
    if any(w in low for w in ("thank", "thanks", "धन्यवाद")):
        return t["thanks"]
    if "?" in peer or any(w in low for w in ("what", "when", "why", "how", "क्या", "कब", "क्यों", "कैसे")):
        return t["question"]
    if any(w in low for w in ("ok", "okay", "sure", "yes", "no", "please", "ठीक", "हाँ", "नहीं")):
        return t["ack"]
    if len(peer) > 200:
        return t["default"] + (" " + t["ack"] if language == "en" else " " + t["ack"])
    return t["default"]
