"""
services/ai_service.py — AI summarization, keywords, trends, research gap detection
Uses Ollama (local LLM) with HuggingFace fallback.
"""
import os
import json
import re
from typing import List, Optional
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "llama3")
HF_TOKEN        = os.getenv("HUGGINGFACE_API_TOKEN", "")


# ── Ollama helpers ────────────────────────────────────────────────────────────

def _ollama_available() -> bool:
    try:
        import requests
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
def _ollama_generate(prompt: str, system: str = "") -> str:
    import requests
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    if system:
        payload["system"] = system
    r = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    return r.json().get("response", "").strip()


# ── HuggingFace fallback ──────────────────────────────────────────────────────

def _hf_summarize(text: str, max_length: int = 200) -> str:
    """BART summarizer via HF Inference API."""
    import requests
    api_url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": text[:1024],
        "parameters": {"max_length": max_length, "min_length": 60},
    }
    try:
        r = requests.post(api_url, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and data:
            return data[0].get("summary_text", "")
    except Exception as e:
        logger.warning(f"HF summarize fallback failed: {e}")
    # Simple extractive fallback
    sentences = text.split(". ")
    return ". ".join(sentences[:3]) + "."


# ── Public API ────────────────────────────────────────────────────────────────

def summarize_paper(title: str, abstract: str) -> str:
    """Generate 3-5 sentence summary of a paper."""
    prompt = (
        f"Title: {title}\n\nAbstract: {abstract}\n\n"
        "Write a clear, concise 3-5 sentence summary of this research paper "
        "for a graduate student audience. Focus on: problem, method, key findings, impact."
    )
    if _ollama_available():
        try:
            return _ollama_generate(
                prompt,
                system="You are an expert research summarizer. Be precise and informative."
            )
        except Exception as e:
            logger.warning(f"Ollama failed, falling back to HF: {e}")
    return _hf_summarize(f"{title}. {abstract}")


def extract_keywords(text: str, top_n: int = 8) -> List[str]:
    """Extract top keywords/concepts from text."""
    prompt = (
        f"Extract the {top_n} most important technical keywords and concepts "
        f"from this text. Return ONLY a JSON array of strings, no explanation.\n\nText: {text[:800]}"
    )
    if _ollama_available():
        try:
            raw = _ollama_generate(prompt)
            # Parse JSON array from response
            match = re.search(r'\[.*?\]', raw, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            logger.warning(f"Keyword extraction via Ollama failed: {e}")

    # Simple TF-IDF-style fallback
    import re as _re
    stopwords = {"the","a","an","of","in","and","or","to","for","is","are","was",
                 "with","this","that","these","those","we","our","their","its"}
    words = _re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    freq: dict = {}
    for w in words:
        if w not in stopwords:
            freq[w] = freq.get(w, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda x: -x[1])[:top_n]]


def analyze_trends(papers: List[dict]) -> dict:
    """
    Analyze keyword/topic trends across a list of papers.
    Returns {keyword: count} mapping and top emerging themes.
    """
    all_text = " ".join(
        f"{p.get('title','')} {p.get('abstract','')}" for p in papers
    )
    keywords = extract_keywords(all_text, top_n=20)

    # Count per paper
    freq: dict = {}
    for kw in keywords:
        freq[kw] = sum(
            1 for p in papers
            if kw.lower() in (p.get("title","") + p.get("abstract","")).lower()
        )

    # Ask LLM for trend narrative
    narrative = ""
    if _ollama_available() and papers:
        titles = "\n".join(f"- {p['title']}" for p in papers[:15])
        try:
            narrative = _ollama_generate(
                f"Based on these research paper titles, describe 3 emerging trends in 2-3 sentences each:\n{titles}",
                system="You are a research trend analyst. Be specific and insightful."
            )
        except Exception:
            pass

    return {
        "keyword_frequency": dict(sorted(freq.items(), key=lambda x: -x[1])),
        "top_keywords":      keywords[:10],
        "trend_narrative":   narrative,
    }


def detect_research_gaps(papers: List[dict], topic: str) -> List[dict]:
    """
    Identify research gaps from a collection of papers.
    Returns list of {gap, confidence, explanation}.
    """
    if not papers:
        return []

    abstracts = "\n\n".join(
        f"Paper {i+1}: {p.get('title','')}\n{p.get('abstract','')[:300]}"
        for i, p in enumerate(papers[:10])
    )

    prompt = (
        f"Topic: {topic}\n\nRecent Papers:\n{abstracts}\n\n"
        "Identify 3-5 significant research gaps or open problems NOT addressed by these papers. "
        "Return a JSON array where each item has: "
        '{"gap": "...", "explanation": "...", "confidence": 0.0-1.0}'
    )

    if _ollama_available():
        try:
            raw = _ollama_generate(
                prompt,
                system="You are a senior researcher identifying novel research directions."
            )
            match = re.search(r'\[.*?\]', raw, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            logger.warning(f"Gap detection failed: {e}")

    # Fallback: static template gaps
    return [
        {
            "gap": f"Real-world deployment challenges in {topic}",
            "explanation": "Most papers focus on benchmark datasets; real-world robustness unexplored.",
            "confidence": 0.65,
        },
        {
            "gap": f"Interpretability and explainability in {topic} models",
            "explanation": "Black-box nature limits adoption in high-stakes domains.",
            "confidence": 0.72,
        },
    ]


def generate_outreach_email(
    professor_name: str,
    institution: str,
    research_area: str,
    your_background: str,
    your_name: str,
) -> dict:
    """Generate personalized outreach email. Returns {subject, body}."""
    prompt = (
        f"Write a professional academic outreach email from {your_name} "
        f"to Professor {professor_name} at {institution}. "
        f"Their research area: {research_area}. "
        f"Sender background: {your_background}. "
        "The email should: introduce the sender, show genuine interest in the professor's work, "
        "mention 1-2 specific aspects of their research, and politely ask about research opportunities. "
        "Keep it under 250 words. Return JSON: {\"subject\": \"...\", \"body\": \"...\"}"
    )

    if _ollama_available():
        try:
            raw = _ollama_generate(
                prompt,
                system="You are an expert academic writing assistant."
            )
            match = re.search(r'\{.*?\}', raw, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            logger.warning(f"Email generation failed: {e}")

    # Fallback template
    return {
        "subject": f"Research Opportunity Inquiry — {research_area}",
        "body": (
            f"Dear Professor {professor_name},\n\n"
            f"I am {your_name}, and I have been following your work at {institution} "
            f"in {research_area} with great interest.\n\n"
            f"{your_background}\n\n"
            "I would be very grateful for any opportunity to contribute to your research group "
            "as a graduate student or research assistant. I have attached my CV for your review.\n\n"
            "Thank you for your time and consideration.\n\n"
            f"Best regards,\n{your_name}"
        ),
    }
