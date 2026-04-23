"""
services/ai_service.py — AI summarization, keyword extraction, trend analysis,
research gap detection, and outreach email generation.

Primary engine: HuggingFace Inference API (cloud, free-tier compatible)
  - Summarization : facebook/bart-large-cnn
  - Chat / reasoning: mistralai/Mistral-7B-Instruct-v0.3

All functions include robust extractive/template fallbacks so the platform
remains fully functional even when the HF API is rate-limited or unavailable.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────

HF_TOKEN: str = os.getenv("HUGGINGFACE_API_TOKEN", "")
HF_MODEL_SUMMARIZE: str = os.getenv(
    "HF_MODEL_SUMMARIZE", "facebook/bart-large-cnn"
)
HF_MODEL_CHAT: str = os.getenv(
    "HF_MODEL_CHAT", "mistralai/Mistral-7B-Instruct-v0.3"
)
HF_API_BASE = "https://api-inference.huggingface.co/models"

_HEADERS: Dict[str, str] = {"Authorization": f"Bearer {HF_TOKEN}"}

# Common English stopwords for extractive fallbacks
_STOPWORDS = {
    "the", "a", "an", "of", "in", "and", "or", "to", "for", "is", "are",
    "was", "were", "with", "this", "that", "these", "those", "we", "our",
    "their", "its", "be", "by", "on", "at", "from", "as", "it", "has",
    "have", "had", "not", "but", "can", "will", "would", "which", "than",
    "into", "also", "more", "use", "used", "using", "show", "shows",
    "based", "both", "each", "such", "when", "than", "about",
}


# ── Low-level HuggingFace helpers ─────────────────────────────────────────────

class HFRateLimitError(Exception):
    """Raised when the HuggingFace API returns 429 or 503."""


@retry(
    retry=retry_if_exception_type(HFRateLimitError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=3, max=20),
)
def _hf_post(model: str, payload: dict, timeout: int = 45) -> Any:
    """
    POST to HuggingFace Inference API with retry on rate-limit.
    Returns parsed JSON response.
    """
    if not HF_TOKEN:
        raise ValueError("HUGGINGFACE_API_TOKEN is not set in environment.")

    url = f"{HF_API_BASE}/{model}"
    resp = requests.post(url, headers=_HEADERS, json=payload, timeout=timeout)

    if resp.status_code in (429, 503):
        retry_after = int(resp.headers.get("Retry-After", 5))
        logger.warning(
            f"HF API rate-limited on {model}. Retrying in {retry_after}s."
        )
        time.sleep(retry_after)
        raise HFRateLimitError(f"Rate limit: {resp.status_code}")

    if resp.status_code == 503:
        # Model loading — wait and retry
        est = resp.json().get("estimated_time", 10)
        logger.info(f"Model {model} loading, waiting {est:.0f}s.")
        time.sleep(min(float(est), 20))
        raise HFRateLimitError("Model loading")

    resp.raise_for_status()
    return resp.json()


# ── Summarization ─────────────────────────────────────────────────────────────

def _hf_summarize(text: str, max_length: int = 220, min_length: int = 60) -> str:
    """
    Abstractive summarization via BART-large-CNN.
    Falls back to extractive if API fails.
    """
    try:
        data = _hf_post(
            HF_MODEL_SUMMARIZE,
            {
                "inputs": text[:1024],
                "parameters": {
                    "max_length": max_length,
                    "min_length": min_length,
                    "do_sample": False,
                },
            },
        )
        if isinstance(data, list) and data:
            return data[0].get("summary_text", "").strip()
    except Exception as exc:
        logger.warning(f"HF summarize failed, using extractive fallback: {exc}")

    # Extractive fallback: first 3 sentences
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(sentences[:3]).strip()


# ── Chat / Instruction following ──────────────────────────────────────────────

def _hf_chat(prompt: str, system: str = "", max_tokens: int = 512) -> str:
    """
    Instruction-following generation via Mistral-7B-Instruct.
    Formats prompt using the [INST] template expected by Mistral.
    Falls back to empty string on failure (callers handle gracefully).
    """
    if system:
        full_prompt = f"<s>[INST] {system}\n\n{prompt} [/INST]"
    else:
        full_prompt = f"<s>[INST] {prompt} [/INST]"

    try:
        data = _hf_post(
            HF_MODEL_CHAT,
            {
                "inputs": full_prompt,
                "parameters": {
                    "max_new_tokens": max_tokens,
                    "temperature": 0.3,
                    "do_sample": True,
                    "return_full_text": False,
                },
            },
        )
        if isinstance(data, list) and data:
            return data[0].get("generated_text", "").strip()
    except Exception as exc:
        logger.warning(f"HF chat failed: {exc}")

    return ""


def _extract_json_array(text: str) -> Optional[list]:
    """Extract the first JSON array found in an LLM response."""
    match = re.search(r"\[.*?\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def _extract_json_object(text: str) -> Optional[dict]:
    """Extract the first JSON object found in an LLM response."""
    match = re.search(r"\{.*?\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


# ── Extractive keyword helper ─────────────────────────────────────────────────

def _extractive_keywords(text: str, top_n: int = 8) -> List[str]:
    """Simple TF-IDF-style frequency-based keyword extractor."""
    words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
    freq: Dict[str, int] = {}
    for w in words:
        if w not in _STOPWORDS:
            freq[w] = freq.get(w, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda x: -x[1])[:top_n]]


# ── Public API ────────────────────────────────────────────────────────────────

def summarize_paper(title: str, abstract: str) -> str:
    """
    Generate a 3-5 sentence AI summary of a research paper.

    Uses BART-large-CNN for abstractive summarization with automatic
    extractive fallback.
    """
    combined = f"{title}. {abstract}"
    logger.info(f"Summarizing: {title[:60]}...")
    return _hf_summarize(combined, max_length=220, min_length=60)


def extract_keywords(text: str, top_n: int = 8) -> List[str]:
    """
    Extract the top N technical keywords/concepts from text.

    Attempts LLM-based extraction first; falls back to TF-IDF.
    """
    prompt = (
        f"Extract the {top_n} most important technical keywords and concepts "
        f"from the following research text. Return ONLY a JSON array of strings "
        f"with no explanation.\n\nText:\n{text[:800]}"
    )
    raw = _hf_chat(prompt)
    if raw:
        parsed = _extract_json_array(raw)
        if parsed and isinstance(parsed, list):
            return [str(k) for k in parsed[:top_n]]

    logger.info("Keyword extraction: using TF-IDF fallback.")
    return _extractive_keywords(text, top_n=top_n)


def analyze_trends(papers: List[dict]) -> dict:
    """
    Analyze keyword/topic trends across a collection of papers.

    Returns:
        {
            "keyword_frequency": {keyword: count, ...},
            "top_keywords":      [str, ...],
            "trend_narrative":   str,
        }
    """
    all_text = " ".join(
        f"{p.get('title', '')} {p.get('abstract', '')}" for p in papers
    )
    keywords = extract_keywords(all_text, top_n=20)

    # Count keyword occurrences per paper
    freq: Dict[str, int] = {}
    for kw in keywords:
        freq[kw] = sum(
            1
            for p in papers
            if kw.lower() in (p.get("title", "") + p.get("abstract", "")).lower()
        )

    # LLM trend narrative
    narrative = ""
    if papers:
        titles_block = "\n".join(f"- {p['title']}" for p in papers[:15])
        prompt = (
            f"Based on the following research paper titles, describe 3 emerging "
            f"research trends in 2-3 sentences each. Be specific and cite patterns "
            f"you observe across titles.\n\nTitles:\n{titles_block}"
        )
        narrative = _hf_chat(
            prompt,
            system="You are a senior research analyst identifying emerging scientific trends.",
            max_tokens=400,
        )

    return {
        "keyword_frequency": dict(
            sorted(freq.items(), key=lambda x: -x[1])
        ),
        "top_keywords": keywords[:10],
        "trend_narrative": narrative,
    }


def detect_research_gaps(papers: List[dict], topic: str) -> List[dict]:
    """
    Identify research gaps from a collection of papers.

    Returns list of:
        {"gap": str, "explanation": str, "confidence": float}
    """
    if not papers:
        return _default_gaps(topic)

    abstracts_block = "\n\n".join(
        f"Paper {i + 1}: {p.get('title', '')}\n"
        f"{p.get('abstract', '')[:300]}"
        for i, p in enumerate(papers[:10])
    )

    prompt = (
        f"Topic: {topic}\n\n"
        f"Recent papers:\n{abstracts_block}\n\n"
        f"Identify 3-5 significant research gaps or open problems NOT addressed "
        f"by these papers. Return a JSON array where each element has exactly "
        f'these keys: "gap" (string), "explanation" (string), "confidence" '
        f"(float 0.0-1.0)."
    )

    raw = _hf_chat(
        prompt,
        system=(
            "You are a senior researcher identifying novel directions for future work. "
            "Respond ONLY with a valid JSON array."
        ),
        max_tokens=600,
    )

    if raw:
        parsed = _extract_json_array(raw)
        if parsed and isinstance(parsed, list) and len(parsed) > 0:
            # Validate and clean each entry
            cleaned = []
            for item in parsed:
                if isinstance(item, dict) and "gap" in item:
                    cleaned.append(
                        {
                            "gap": str(item.get("gap", "")),
                            "explanation": str(item.get("explanation", "")),
                            "confidence": float(
                                max(0.0, min(1.0, item.get("confidence", 0.6)))
                            ),
                        }
                    )
            if cleaned:
                return cleaned

    logger.info("Gap detection: using static template fallback.")
    return _default_gaps(topic)


def _default_gaps(topic: str) -> List[dict]:
    """Static fallback research gaps when LLM is unavailable."""
    return [
        {
            "gap": f"Real-world deployment and robustness in {topic}",
            "explanation": (
                "Most published work evaluates on benchmark datasets. "
                "Performance under distribution shift and noisy real-world "
                "conditions remains underexplored."
            ),
            "confidence": 0.68,
        },
        {
            "gap": f"Interpretability and explainability in {topic} models",
            "explanation": (
                "Black-box nature of state-of-the-art models limits adoption "
                "in safety-critical and regulated domains."
            ),
            "confidence": 0.74,
        },
        {
            "gap": f"Computational efficiency and resource constraints in {topic}",
            "explanation": (
                "Current SOTA methods require large compute budgets. "
                "Efficient, lightweight alternatives suitable for edge "
                "deployment are scarce."
            ),
            "confidence": 0.61,
        },
    ]


def generate_outreach_email(
    professor_name: str,
    institution: str,
    research_area: str,
    your_background: str,
    your_name: str,
) -> dict:
    """
    Generate a personalized academic outreach email.

    Returns:
        {"subject": str, "body": str}
    """
    prompt = (
        f"Write a professional academic outreach email from {your_name} "
        f"to Professor {professor_name} at {institution}. "
        f"Their research area: {research_area}. "
        f"Sender background: {your_background}. "
        f"Requirements: introduce the sender warmly, show genuine knowledge of "
        f"the professor's research area, mention 1-2 specific aspects, and "
        f"politely inquire about research opportunities. Keep it under 250 words. "
        f'Respond ONLY with a JSON object with keys "subject" and "body".'
    )

    raw = _hf_chat(
        prompt,
        system="You are an expert academic writing assistant. Output valid JSON only.",
        max_tokens=512,
    )

    if raw:
        parsed = _extract_json_object(raw)
        if parsed and "subject" in parsed and "body" in parsed:
            return {
                "subject": str(parsed["subject"]),
                "body": str(parsed["body"]),
            }

    logger.info("Outreach email: using template fallback.")
    return {
        "subject": f"Research Opportunity Inquiry — {research_area}",
        "body": (
            f"Dear Professor {professor_name},\n\n"
            f"I am {your_name}, and I have been following your work at "
            f"{institution} in {research_area} with great interest.\n\n"
            f"{your_background}\n\n"
            f"I would be very grateful for any opportunity to contribute to "
            f"your research group as a graduate student or research assistant. "
            f"I have attached my CV for your review.\n\n"
            f"Thank you for your time and consideration.\n\n"
            f"Best regards,\n{your_name}"
        ),
    }
