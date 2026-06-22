import json
import os
import re
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

import pandas as pd
import requests

try:
    import nltk
except Exception:  # pragma: no cover - optional dependency
    nltk = None

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

try:
    from urduhack.preprocessing import normalize_whitespace
    from urduhack.tokenization import sentence_tokenizer
except Exception:  # pragma: no cover - handled at runtime in the app
    normalize_whitespace = None
    sentence_tokenizer = None

try:
    import stanza
except Exception:  # pragma: no cover - handled at runtime in the app
    stanza = None


SENTENCE_BOUNDARY_PATTERN = re.compile(r"[.\u06d4!?]+|[\r\n]+")
EDGE_PUNCTUATION_PATTERN = re.compile(r"^[\s.\u06d4!?]+|[\s.\u06d4!?]+$")


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_segment(text: str) -> str:
    return EDGE_PUNCTUATION_PATTERN.sub("", (text or "").strip())


def normalize_segments(segments: list[str]) -> list[str]:
    return [segment for segment in (normalize_segment(item) for item in segments) if segment]


def split_rule_based(text: str) -> list[str]:
    sentences = re.split(r"[.\u06d4!?]+|[\r\n]+", text or "")
    return [sentence.strip() for sentence in sentences if sentence and sentence.strip()]


def split_regex(text: str) -> list[str]:
    sentences = re.split(r"[.\u06d4!?]+|[\r\n]+", text or "")
    return [sentence.strip() for sentence in sentences if sentence and sentence.strip()]


def split_urduhack(text: str) -> list[str]:
    if sentence_tokenizer is None or normalize_whitespace is None:
        raise RuntimeError("urduhack is not available in this environment.")

    cleaned_text = normalize_whitespace(text or "")
    sentences = sentence_tokenizer(cleaned_text)
    return [sentence.strip() for sentence in sentences if sentence and sentence.strip()]


@lru_cache(maxsize=1)
def _get_stanza_pipeline():
    if stanza is None:
        raise RuntimeError("stanza is not available in this environment.")

    try:
        return stanza.Pipeline(
            lang="ur",
            processors="tokenize",
            tokenize_no_ssplit=False,
            use_gpu=False,
            verbose=False,
        )
    except Exception:
        stanza.download("ur", processors="tokenize", verbose=False)
        return stanza.Pipeline(
            lang="ur",
            processors="tokenize",
            tokenize_no_ssplit=False,
            use_gpu=False,
            verbose=False,
        )


def split_stanza(text: str) -> list[str]:
    pipeline = _get_stanza_pipeline()
    document = pipeline(text or "")
    return [sentence.text.strip() for sentence in document.sentences if sentence.text and sentence.text.strip()]


PUNKT_TRAINING_SAMPLE_SIZE = int(os.getenv("PUNKT_TRAINING_SAMPLE_SIZE", "50"))
DATASET_TRAINING_PATH = Path(__file__).resolve().parent / "data" / "processed" / "urdu_tweets_cleaned.csv"


@lru_cache(maxsize=1)
def _load_punkt_training_corpus() -> str:
    if not DATASET_TRAINING_PATH.exists():
        raise RuntimeError(f"Training dataset not found: {DATASET_TRAINING_PATH}")

    frame = pd.read_csv(DATASET_TRAINING_PATH, usecols=["clean_text"], nrows=PUNKT_TRAINING_SAMPLE_SIZE)
    texts = [normalize_text(str(item)) for item in frame["clean_text"].dropna().tolist()]
    corpus = "\n".join(text for text in texts if text)
    if not corpus.strip():
        raise RuntimeError("The Urdu tweets training corpus is empty.")
    return corpus


@lru_cache(maxsize=1)
def _get_trained_punkt_tokenizer():
    if nltk is None:
        raise RuntimeError("NLTK is not installed.")

    from nltk.tokenize.punkt import PunktSentenceTokenizer, PunktTrainer

    trainer = PunktTrainer()
    trainer.INCLUDE_ALL_COLLOCS = True
    trainer.train(_load_punkt_training_corpus())
    return PunktSentenceTokenizer(trainer.get_params())


def split_nltk_punkt(text: str) -> list[str]:
    tokenizer = _get_trained_punkt_tokenizer()
    return [sentence.strip() for sentence in tokenizer.tokenize(text or "") if sentence and sentence.strip()]


def split_nltk_punkt(text: str) -> list[str]:
    if nltk is None:
        raise RuntimeError("NLTK is not installed.")

    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt", quiet=True)

    from nltk.tokenize import sent_tokenize

    return [sentence.strip() for sentence in sent_tokenize(text or "") if sentence and sentence.strip()]


def split_hybrid(text: str) -> list[str]:
    sentences = []
    for sentence in split_urduhack(text):
        sentences.extend(split_rule_based(sentence))
    return sentences


def _extract_json_array_from_text(content: str) -> list[str]:
    cleaned_content = content.strip()
    if cleaned_content.startswith("```"):
        cleaned_content = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned_content, flags=re.IGNORECASE | re.DOTALL).strip()

    candidates = [cleaned_content]
    json_matches = re.findall(r"\[[\s\S]*?\]", cleaned_content)
    candidates.extend(json_matches)

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue
        if isinstance(parsed, list):
            return [normalize_segment(str(item)) for item in parsed if normalize_segment(str(item))]

    fallback_lines = [normalize_segment(line) for line in cleaned_content.splitlines()]
    return [line for line in fallback_lines if line]


def split_groq_llm(text: str) -> list[str]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    model_name = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
    prompt_text = normalize_text(text or "")
    if not prompt_text:
        return []

    response = requests.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model_name,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a sentence segmentation model. Return only a JSON array of sentence strings "
                        "for the text provided by the user. Do not add commentary."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Split this text into sentence segments and return a JSON array only:\n\n{prompt_text}",
                },
            ],
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    message = payload["choices"][0]["message"]["content"]
    return _extract_json_array_from_text(message)


def reference_split(text: str) -> list[str]:
    sentences = SENTENCE_BOUNDARY_PATTERN.split(text or "")
    return [sentence.strip() for sentence in sentences if sentence and sentence.strip()]


ALGORITHM_PURPOSES = {
    "Rule-Based": "Rule-based splitting is best when the text has clear sentence punctuation.",
    "Regex": "Regex splitting is a fast baseline for punctuation-heavy text and noisy formatting.",
    "UrduHack": "UrduHack is built for Urdu NLP and should handle Urdu social text well.",
    "Stanza": "Stanza is a neural NLP baseline for sentence segmentation on general text.",
    "Dataset-Trained Punkt": "This Punkt model is trained on Urdu tweets, so it learns boundary patterns from the corpus.",
    "Groq LLM": "The Groq LLM is intended for semantic segmentation and mixed or ambiguous text.",
    "Hybrid": "The hybrid method combines UrduHack with rule-based cleanup for practical Urdu segmentation.",
}


def _algorithm_purpose(algorithm_name: str) -> str:
    return ALGORITHM_PURPOSES.get(algorithm_name, "This algorithm is being evaluated against the reference split.")


def _segment_similarity(reference_segments: list[str], predicted_segments: list[str]) -> float:
    if not reference_segments and not predicted_segments:
        return 1.0
    return SequenceMatcher(a=reference_segments, b=predicted_segments).ratio()


def evaluate_algorithm(text: str, algorithm_name: str, segments: list[str], available: bool = True) -> dict:
    reference_segments = normalize_segments(reference_split(text))
    predicted_segments = normalize_segments(segments)
    segment_similarity = _segment_similarity(reference_segments, predicted_segments)
    text_similarity = SequenceMatcher(
        a=" ".join(reference_segments),
        b=" ".join(predicted_segments),
    ).ratio()
    count_similarity = 1.0 - (
        abs(len(reference_segments) - len(predicted_segments))
        / max(len(reference_segments), len(predicted_segments), 1)
    )
    similarity = 0.5 * segment_similarity + 0.3 * count_similarity + 0.2 * text_similarity
    score = round(similarity * 100)
    result_text = " | ".join(predicted_segments) if predicted_segments else "No segments returned"

    if not available:
        return {
            "algorithm": algorithm_name,
            "result": "Unavailable in this environment",
            "verdict": "Could not run",
            "reason": "The required model or package is not loaded, so this algorithm could not be executed.",
            "score": 0,
            "similarity": 0.0,
        }

    purpose = _algorithm_purpose(algorithm_name)

    if score >= 88:
        verdict = "Worked well"
        reason = (
            f"{purpose} High boundary similarity ({score}%) with the reference split. "
            f"Reference: {len(reference_segments)} segment(s); algorithm: {len(predicted_segments)} segment(s)."
        )
    elif score >= 60:
        verdict = "Partially worked"
        reason = (
            f"{purpose} Moderate boundary similarity ({score}%). "
            f"Reference: {len(reference_segments)} segment(s); algorithm: {len(predicted_segments)} segment(s)."
        )
    else:
        verdict = "Needs review"
        reason = (
            f"{purpose} Low boundary similarity ({score}%). "
            f"Reference: {len(reference_segments)} segment(s); algorithm: {len(predicted_segments)} segment(s)."
        )

    if reference_segments == predicted_segments:
        verdict = "Worked well"
        reason = f"{purpose} It matched the reference boundaries exactly."

    if len(reference_segments) != len(predicted_segments):
        reason += f" The count differs by {abs(len(reference_segments) - len(predicted_segments))}."

    return {
        "algorithm": algorithm_name,
        "result": result_text,
        "verdict": verdict,
        "reason": reason,
        "score": score,
        "similarity": similarity,
    }


def run_all_algorithms(text: str) -> list[dict]:
    text = normalize_text(text)
    if not text:
        return []

    results = []
    results.append(evaluate_algorithm(text, "Rule-Based", split_rule_based(text)))
    results.append(evaluate_algorithm(text, "Regex", split_regex(text)))

    try:
        results.append(evaluate_algorithm(text, "UrduHack", split_urduhack(text)))
    except Exception as exc:
        results.append(
            {
                "algorithm": "UrduHack",
                "result": "Unavailable in this environment",
                "verdict": "Could not run",
                "reason": str(exc),
                "score": 0,
                "similarity": 0.0,
            }
        )

    try:
        results.append(evaluate_algorithm(text, "Stanza", split_stanza(text)))
    except Exception as exc:
        results.append(
            {
                "algorithm": "Stanza",
                "result": "Unavailable in this environment",
                "verdict": "Could not run",
                "reason": str(exc),
                "score": 0,
                "similarity": 0.0,
            }
        )

    try:
        results.append(evaluate_algorithm(text, "Dataset-Trained Punkt", split_nltk_punkt(text)))
    except Exception as exc:
        results.append(
            {
                "algorithm": "Dataset-Trained Punkt",
                "result": "Unavailable in this environment",
                "verdict": "Could not run",
                "reason": str(exc),
                "score": 0,
                "similarity": 0.0,
            }
        )

    try:
        results.append(evaluate_algorithm(text, "Groq LLM", split_groq_llm(text)))
    except Exception as exc:
        results.append(
            {
                "algorithm": "Groq LLM",
                "result": "Unavailable in this environment",
                "verdict": "Could not run",
                "reason": str(exc),
                "score": 0,
                "similarity": 0.0,
            }
        )

    try:
        results.append(evaluate_algorithm(text, "Hybrid", split_hybrid(text)))
    except Exception as exc:
        results.append(
            {
                "algorithm": "Hybrid",
                "result": "Unavailable in this environment",
                "verdict": "Could not run",
                "reason": str(exc),
                "score": 0,
                "similarity": 0.0,
            }
        )

    return results

