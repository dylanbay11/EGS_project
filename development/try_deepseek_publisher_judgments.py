"""Try DeepSeek web search on a few ambiguous publisher labels.

This is deliberately a disposable proof of concept, not pipeline code. For a
repeatable run, set DEEPSEEK_API_KEY and TAVILY_API_KEY, then run::

    uv run python development/try_deepseek_publisher_judgments.py \
        --search-provider tavily --limit 4

Without a Tavily key, ``auto`` tries DuckDuckGo's unofficial HTML interface.
That no-key fallback is useful for a one-off smoke test but is quickly bot-
limited and should not be used for a 500-row pass. Complete API responses and
their exact search evidence are written to JSONL for auditing.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

API_URL = "https://api.deepseek.com/chat/completions"
SEARCH_URL = "https://html.duckduckgo.com/html/"
TAVILY_URL = "https://api.tavily.com/search"
DEFAULT_MODEL = "deepseek-flash"

# These are real disagreements in data/egs_giveaways.csv as of 2026-09-10.
EXAMPLES = [
    {
        "title": "Cat Quest II",
        "candidate_y": "Kepler Interactive",
        "candidate_z": "PQube",
        "egs_context": "Epic currently reports Kepler Interactive",
        "wiki_context": "Wikipedia extraction reports PQube",
    },
    {
        "title": "Dark Deity",
        "candidate_y": "Freedom Games",
        "candidate_z": "indie.io",
        "egs_context": "Epic currently reports Freedom Games",
        "wiki_context": "Wikipedia extraction reports indie.io",
    },
    {
        "title": "Deceive Inc.",
        "candidate_y": "Tripwire Presents",
        "candidate_z": "Tripwire Interactive",
        "egs_context": "Epic currently reports Tripwire Presents",
        "wiki_context": "Wikipedia extraction reports Tripwire Interactive",
    },
    {
        "title": "The Stone of Madness",
        "candidate_y": "Tripwire Interactive",
        "candidate_z": "Tripwire Presents",
        "egs_context": "Epic currently reports Tripwire Interactive",
        "wiki_context": "Wikipedia extraction reports Tripwire Presents",
    },
]

OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "choice": {"type": "string", "enum": ["Y", "Z", "BOTH", "NEITHER"]},
        "preferred_publisher": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "reason": {"type": "string"},
        "caveat": {"type": "string"},
        "source_ids": {
            "type": "array",
            "items": {"type": "string", "pattern": "^S[1-5]$"},
        },
    },
    "required": [
        "title",
        "choice",
        "preferred_publisher",
        "confidence",
        "reason",
        "caveat",
        "source_ids",
    ],
}


def build_prompt(
    example: dict[str, str], evidence: list[dict[str, str]] | None = None
) -> str:
    """Build a narrowly scoped publisher reconciliation question."""
    evidence_text = ""
    if evidence:
        lines = [
            f"{item['id']} | {item['title']} | {item['url']} | {item['snippet']}"
            for item in evidence
        ]
        evidence_text = "\n\nWeb search evidence:\n" + "\n".join(lines)

    return f"""Adjudicate the publisher label for this exact video game.

Game: {example['title']}
Candidate Y: {example['candidate_y']}
Candidate Z: {example['candidate_z']}
Local context: {example['egs_context']}; {example['wiki_context']}.

For a historical game catalog, prefer the company or publishing label that
published this exact game/edition at its original release. Do not silently treat
a current storefront seller, later rights holder, parent company, developer, or
company rename as equivalent. If time, platform, region, rebranding, or a
publishing imprint explains both names, say so and use BOTH when that is more
accurate than forcing one candidate. Use only the supplied web evidence; do not
invent facts or sources. Cite the IDs of the strongest supplied results.{evidence_text}"""


def build_search_query(example: dict[str, str]) -> str:
    """Build a focused web query from a publisher disagreement."""
    return f'"{example["title"]}" original release publisher official'


def search_duckduckgo(example: dict[str, str]) -> list[dict[str, str]]:
    """Return up to five no-key DuckDuckGo HTML search results."""
    query = build_search_query(example)
    try:
        completed = subprocess.run(
            [
                "curl",
                "-fsS",
                "-A",
                "Mozilla/5.0",
                "--get",
                "--data-urlencode",
                f"q={query}",
                SEARCH_URL,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.SubprocessError) as error:
        raise RuntimeError(f"DuckDuckGo search failed: {error}") from error
    soup = BeautifulSoup(completed.stdout, "html.parser")

    results = []
    for result in soup.select(".result"):
        link = result.select_one(".result__a")
        if link is None:
            continue
        raw_url = str(link.get("href", ""))
        parsed = urllib.parse.urlparse(raw_url)
        params = urllib.parse.parse_qs(parsed.query)
        resolved_url = params.get("uddg", [raw_url])[0]
        snippet = result.select_one(".result__snippet")
        results.append(
            {
                "id": f"S{len(results) + 1}",
                "title": link.get_text(" ", strip=True),
                "url": resolved_url,
                "snippet": snippet.get_text(" ", strip=True) if snippet else "",
            }
        )
        if len(results) == 5:
            break
    if not results:
        raise RuntimeError("DuckDuckGo returned no parseable results")
    return results


def search_tavily(
    example: dict[str, str], api_key: str
) -> list[dict[str, str]]:
    """Return up to five Tavily basic-search results."""
    request = urllib.request.Request(
        TAVILY_URL,
        data=json.dumps(
            {
                "query": build_search_query(example),
                "search_depth": "basic",
                "max_results": 5,
                "include_answer": False,
                "include_raw_content": False,
            }
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Tavily returned HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not reach Tavily: {error.reason}") from error

    results = [
        {
            "id": f"S{index}",
            "title": str(item.get("title", "")),
            "url": str(item.get("url", "")),
            "snippet": str(item.get("content", "")),
        }
        for index, item in enumerate(payload.get("results", [])[:5], start=1)
    ]
    if not results:
        raise RuntimeError("Tavily returned no search results")
    return results


def post_response(api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Post one request to DeepSeek and return its decoded JSON response."""
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"DeepSeek returned HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not reach DeepSeek: {error.reason}") from error


def extract_output_text(response: dict[str, Any]) -> str:
    """Extract chat-completion text without depending on the OpenAI SDK."""
    choices = response.get("choices", [])
    if choices:
        return str(choices[0].get("message", {}).get("content", ""))
    raise ValueError("Response contained no chat-completion choice")


def estimate_max_cost_usd(response: dict[str, Any]) -> float:
    """Estimate cost using current peak Flash rates, excluding cached discounts."""
    usage = response.get("usage", {})
    input_tokens = int(usage.get("input_tokens", usage.get("prompt_tokens", 0)))
    output_tokens = int(usage.get("output_tokens", usage.get("completion_tokens", 0)))
    return input_tokens * 0.30 / 1_000_000 + output_tokens * 1.20 / 1_000_000


def validate_source_ids(
    judgment: dict[str, Any], evidence: list[dict[str, str]]
) -> None:
    """Reject malformed judgments or citations outside supplied search results."""
    required = set(OUTPUT_SCHEMA["required"])
    missing = required - set(judgment)
    if missing:
        raise ValueError(f"Judgment omitted required fields: {sorted(missing)}")
    if judgment["choice"] not in {"Y", "Z", "BOTH", "NEITHER"}:
        raise ValueError(f"Judgment returned invalid choice: {judgment['choice']}")
    if judgment["confidence"] not in {"high", "medium", "low"}:
        raise ValueError(
            f"Judgment returned invalid confidence: {judgment['confidence']}"
        )
    valid_ids = {item["id"] for item in evidence}
    cited_ids = judgment.get("source_ids")
    if not isinstance(cited_ids, list) or not cited_ids:
        raise ValueError("Judgment did not cite any search-result IDs")
    invalid_ids = set(cited_ids) - valid_ids
    if invalid_ids:
        raise ValueError(f"Judgment cited invalid source IDs: {sorted(invalid_ids)}")


def make_payload(
    example: dict[str, str], evidence: list[dict[str, str]], model: str
) -> dict[str, Any]:
    """Create a non-thinking JSON request grounded in supplied search results."""
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You reconcile video-game metadata. Return one JSON object "
                    "matching this schema: " + json.dumps(OUTPUT_SCHEMA)
                ),
            },
            {"role": "user", "content": build_prompt(example, evidence)},
        ],
        "thinking": {"type": "disabled"},
        "response_format": {"type": "json_object"},
        "max_tokens": 800,
        "user_id": "egs-publisher-poc",
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line options for this small experiment."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=2, help="Cases to run (default: 2)")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--search-provider",
        choices=["auto", "tavily", "duckduckgo"],
        default="auto",
        help="Use Tavily when its key is set; otherwise try disposable DuckDuckGo HTML",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/deepseek_publisher_poc.jsonl"),
    )
    parser.add_argument("--dry-run", action="store_true", help="Print prompts only")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between calls")
    return parser.parse_args()


def main() -> int:
    """Run a few publisher judgments and save auditable API responses."""
    args = parse_args()
    examples = EXAMPLES[: max(0, min(args.limit, len(EXAMPLES)))]
    if args.dry_run:
        for example in examples:
            print(build_prompt(example), end="\n\n")
        return 0

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("DEEPSEEK_API_KEY is not set", file=sys.stderr)
        return 2

    tavily_api_key = os.environ.get("TAVILY_API_KEY")
    search_provider = args.search_provider
    if search_provider == "auto":
        search_provider = "tavily" if tavily_api_key else "duckduckgo"
    if search_provider == "tavily" and not tavily_api_key:
        print("TAVILY_API_KEY is required for --search-provider tavily", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    total_estimated_cost = 0.0
    with args.output.open("w", encoding="utf-8") as handle:
        for index, example in enumerate(examples):
            try:
                if search_provider == "tavily":
                    evidence = search_tavily(example, tavily_api_key or "")
                else:
                    evidence = search_duckduckgo(example)
            except RuntimeError as error:
                record = {"example": example, "search_error": str(error)}
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                print(f"{example['title']}: search failed ({error})")
                continue
            response = post_response(api_key, make_payload(example, evidence, args.model))
            estimated_cost = estimate_max_cost_usd(response)
            total_estimated_cost += estimated_cost
            try:
                judgment = json.loads(extract_output_text(response))
                validate_source_ids(judgment, evidence)
            except (ValueError, json.JSONDecodeError) as error:
                record = {
                    "example": example,
                    "evidence": evidence,
                    "error": str(error),
                    "usage": response.get("usage", {}),
                    "estimated_peak_cost_usd": round(estimated_cost, 6),
                    "raw_response": response,
                }
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                print(f"{example['title']}: no usable judgment ({error})")
                continue
            record = {
                "example": example,
                "judgment": judgment,
                "evidence": evidence,
                "usage": response.get("usage", {}),
                "estimated_peak_cost_usd": round(estimated_cost, 6),
                "raw_response": response,
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(
                f"{example['title']}: {judgment['preferred_publisher']} "
                f"({judgment['confidence']}; <= ${estimated_cost:.4f})"
            )
            if index + 1 < len(examples):
                time.sleep(max(0.0, args.delay))

    print(f"Saved {len(examples)} records to {args.output}")
    print(f"Estimated peak token cost: <= ${total_estimated_cost:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
