#!/usr/bin/env python3
"""GPTZero CLI - detect AI-generated text using the GPTZero web API."""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: 'requests' is not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

CONFIG_PATH = Path.home() / ".data" / "gptzero" / "config.json"
SCAN_URL = "https://api.gptzero.me/v3/scan"
API_URL  = "https://api.gptzero.me/v3/ai/text"

RESET   = "\033[0m"
BOLD    = "\033[1m"
RED     = "\033[31m"
YELLOW  = "\033[33m"
GREEN   = "\033[32m"
CYAN    = "\033[36m"
DIM     = "\033[2m"
BG_RED  = "\033[41m"
BG_YEL  = "\033[43m"


def no_color() -> bool:
    return not sys.stdout.isatty() or os.environ.get("NO_COLOR")


def c(code: str, text: str) -> str:
    if no_color():
        return text
    return f"{code}{text}{RESET}"


def load_config() -> dict:
    """Load credentials from env vars or config file."""
    token = os.environ.get("GPTZERO_ACCESS_TOKEN")
    csrf  = os.environ.get("GPTZERO_CSRF_TOKEN")

    if token and csrf:
        return {"access_token": token, "csrf_token": csrf}

    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)

    return {}


def save_config(token: str, csrf: str) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump({"access_token": token, "csrf_token": csrf}, f, indent=2)
    os.chmod(CONFIG_PATH, 0o600)
    print(f"Config saved to {CONFIG_PATH}")


def _make_headers(token: str, csrf: str, scan_id: str = "") -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
        "Accept": "*/*",
        "Referer": "https://app.gptzero.me/",
        "x-gptzero-platform": "webapp",
        "content-type": "application/json",
        "Origin": "https://app.gptzero.me",
    }
    if scan_id:
        headers["x-page"] = f"/documents/{scan_id}"
    # Raw Cookie header — requests' cookie jar silently drops __Host- prefixed cookies.
    cookie_parts = [f"accessToken4={token}", "plan=Free"]
    if csrf:
        cookie_parts.append(f"__Host-gptzero-csrf-token={csrf}")
    headers["Cookie"] = "; ".join(cookie_parts)
    return headers


def _create_scan(headers: dict) -> str:
    """Create a scan document and return its ID."""
    resp = requests.post(
        SCAN_URL, headers=headers,
        json={"title": "CLI Scan", "source": "dashboard", "author": ""},
        timeout=30,
    )
    if not resp.ok:
        print(c(RED, f"Error creating scan ({resp.status_code}):"), file=sys.stderr)
        print(resp.text[:500], file=sys.stderr)
        sys.exit(1)
    return resp.json()["data"]["id"]


def scan(text: str, config: dict) -> dict:
    token = config.get("access_token", "")
    csrf  = config.get("csrf_token", "")

    if not token:
        print(
            c(RED, "Error: credentials not configured.\n")
            + "Run with --setup, or set GPTZERO_ACCESS_TOKEN (and optionally GPTZERO_CSRF_TOKEN).",
            file=sys.stderr,
        )
        sys.exit(1)

    headers = _make_headers(token, csrf)

    scan_id = _create_scan(headers)
    headers["x-page"] = f"/documents/{scan_id}"

    payload = {
        "scanId": scan_id,
        "multilingual": True,
        "document": text,
        "interpretability_required": False,
    }

    resp = requests.post(API_URL, headers=headers, json=payload, timeout=30)

    if resp.status_code == 401:
        print(c(RED, "Error: authentication failed (401). Your tokens may be expired."), file=sys.stderr)
        print("Re-run --setup with fresh tokens from your browser.", file=sys.stderr)
        sys.exit(1)

    if not resp.ok:
        print(c(RED, f"Error {resp.status_code} from API:"), file=sys.stderr)
        print(resp.text[:1000], file=sys.stderr)
        resp.raise_for_status()
    return resp.json()


def verdict_color(predicted_class: str) -> str:
    return {
        "ai":    RED,
        "human": GREEN,
        "mixed": YELLOW,
    }.get(predicted_class.lower(), RESET)


def confidence_bar(score: float, width: int = 20) -> str:
    filled = round(score * width)
    bar = "█" * filled + "░" * (width - filled)
    return bar


def print_results(data: dict, show_sentences: bool) -> None:
    docs = data.get("documents", [])
    if not docs:
        print(c(RED, "No results returned."))
        return

    doc = docs[0]
    predicted   = doc.get("predicted_class", "unknown")
    confidence  = doc.get("confidence_score", 0)
    category    = doc.get("confidence_category", "unknown")
    result_msg  = doc.get("result_message", "")
    class_probs = doc.get("class_probabilities", {})

    vc = verdict_color(predicted)

    print()
    print(c(BOLD, "━━━ GPTZero Analysis ━━━"))
    print()
    print(f"  Verdict:     {c(BOLD + vc, predicted.upper())}")
    print(f"  Confidence:  {c(vc, f'{confidence:.1%}')}  [{confidence_bar(confidence)}]  ({category})")
    print()

    if class_probs:
        print(c(BOLD, "  Class probabilities:"))
        labels = [
            ("AI",     "ai",    RED),
            ("Human",  "human", GREEN),
            ("Mixed",  "mixed", YELLOW),
        ]
        for label, key, color in labels:
            p = class_probs.get(key, 0)
            print(f"    {label:<8} {c(color, f'{p:.1%}')}  {c(DIM, confidence_bar(p, 15))}")
        print()

    if result_msg:
        print(f"  {c(DIM, result_msg)}")
        print()

    subclass = doc.get("subclass", {}).get("ai", {})
    if predicted == "ai" and subclass:
        sc_class = subclass.get("predicted_class", "")
        sc_conf  = subclass.get("confidence_score", 0)
        if sc_class:
            label = "Pure AI" if sc_class == "pure_ai" else "AI-Paraphrased"
            print(f"  Subclass:    {c(BOLD, label)}  ({sc_conf:.1%} confidence)")
            print()

    if show_sentences:
        sentences = doc.get("sentences", [])
        if sentences:
            print(c(BOLD, "━━━ Per-sentence breakdown ━━━"))
            print()
            for s in sentences:
                prob     = s.get("generated_prob", 0)
                text_s   = s.get("sentence", "")
                highlight = s.get("highlight_sentence_for_ai", False)

                if prob >= 0.85:
                    marker = c(RED,    "●")
                    prob_s = c(RED,    f"{prob:.0%}")
                elif prob >= 0.6:
                    marker = c(YELLOW, "●")
                    prob_s = c(YELLOW, f"{prob:.0%}")
                else:
                    marker = c(GREEN,  "○")
                    prob_s = c(GREEN,  f"{prob:.0%}")

                print(f"  {marker} [{prob_s}] {text_s}")
            print()
            print(f"  {c(DIM, 'Legend: ● high AI  ● medium AI  ○ likely human')}")
            print()


def parse_cookie_header(raw: str) -> dict[str, str]:
    """Parse a raw Cookie header string into a dict."""
    result = {}
    for part in raw.split(";"):
        part = part.strip()
        if "=" in part:
            k, _, v = part.partition("=")
            result[k.strip()] = v.strip()
    return result


def setup_wizard() -> None:
    print(c(BOLD, "GPTZero CLI Setup"))
    print()
    print("How to get your credentials (easiest method):")
    print()
    print("  1. Open https://app.gptzero.me in your browser (logged in)")
    print("  2. Open DevTools → Network tab")
    print("  3. Scan any text on the site to trigger a request")
    print(f"  4. Find a request to {c(CYAN, 'api.gptzero.me/v3/ai/text')}")
    print("  5. Click it → Headers → Request Headers")
    print(f"  6. Copy the entire {c(CYAN, 'Cookie:')} header value")
    print()
    print("Paste the full Cookie header value below (or press Enter to enter tokens individually):")

    raw = input("> ").strip()

    if raw:
        cookies = parse_cookie_header(raw)
        token = cookies.get("accessToken4", "")
        csrf  = cookies.get("__Host-gptzero-csrf-token", "")
        if not token:
            print(c(RED, "Could not find 'accessToken4' in the pasted cookie string."), file=sys.stderr)
            sys.exit(1)
        if not csrf:
            print(c(YELLOW, "Warning: '__Host-gptzero-csrf-token' not found — will try without it."))
    else:
        print()
        token = input("Paste accessToken4: ").strip()
        csrf  = input("Paste __Host-gptzero-csrf-token (leave blank to skip): ").strip()

    if not token:
        print(c(RED, "accessToken4 is required."), file=sys.stderr)
        sys.exit(1)

    save_config(token, csrf)
    print(c(GREEN, "Setup complete!"))


def read_input(args: argparse.Namespace) -> str:
    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(c(RED, f"Error: file not found: {args.file}"), file=sys.stderr)
            sys.exit(1)
        return path.read_text(encoding="utf-8")

    if args.text:
        return " ".join(args.text)

    if not sys.stdin.isatty():
        return sys.stdin.read()

    print(c(RED, "Error: provide text via argument, --file, or stdin."), file=sys.stderr)
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="gptzero",
        description="Detect AI-generated text using GPTZero.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  gptzero "Some text to analyze"
  gptzero --file essay.txt
  echo "Some text" | gptzero
  gptzero --file essay.txt --sentences
  gptzero --setup
  gptzero --json "Some text"
        """,
    )
    parser.add_argument("text", nargs="*", help="Text to analyze (or use --file / stdin)")
    parser.add_argument("--file", "-f", metavar="PATH", help="Read text from a file")
    parser.add_argument("--sentences", "-s", action="store_true", help="Show per-sentence breakdown")
    parser.add_argument("--json", "-j", action="store_true", help="Output raw JSON response")
    parser.add_argument("--setup", action="store_true", help="Configure credentials interactively")

    args = parser.parse_args()

    if args.setup:
        setup_wizard()
        return

    text = read_input(args)
    text = text.strip()
    if not text:
        print(c(RED, "Error: input text is empty."), file=sys.stderr)
        sys.exit(1)

    config = load_config()
    result = scan(text, config)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_results(result, show_sentences=args.sentences)


if __name__ == "__main__":
    main()
