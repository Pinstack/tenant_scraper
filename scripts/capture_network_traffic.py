#!/usr/bin/env python3
"""Unified Google Maps network/protobuf capture utility."""

import argparse
import asyncio
import json
import logging
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
from playwright.async_api import async_playwright, Page


logger = logging.getLogger(__name__)


def slugify(value: str, fallback: str = "capture") -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-")
    return slug or fallback


@dataclass
class CaptureConfig:
    url: str
    output_dir: Path
    headless: bool = True
    handle_consent: bool = True
    detect_protobuf: bool = False
    include_initial_request: bool = True
    wait_after_load: float = 5.0


def write_json(destination: Path, payload: Any) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def capture_initial_request(config: CaptureConfig) -> Optional[Dict[str, Any]]:
    logger.info("Capturing initial HTTP request via requests session")
    session = requests.Session()
    try:
        response = session.get(config.url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:  # pragma: no cover - network dependent
        logger.warning("Initial request failed: %s", exc)
        return None

    html_snapshot = None
    if "text/html" in response.headers.get("content-type", ""):
        html_snapshot = config.output_dir / "initial_page.html"
        html_snapshot.write_text(response.text, encoding="utf-8")
        logger.info("Saved initial HTML to %s", html_snapshot)

    record = {
        "timestamp": time.time(),
        "url": config.url,
        "status_code": response.status_code,
        "request_headers": dict(response.request.headers),
        "response_headers": dict(response.headers),
        "response_size": len(response.content),
        "content_type": response.headers.get("content-type"),
        "redirect_history": [
            {"url": r.url, "status_code": r.status_code}
            for r in response.history
        ],
    }

    if html_snapshot:
        record["html_file"] = html_snapshot.name

    write_json(config.output_dir / "initial_request.json", record)
    return record


async def handle_consent(page: Page) -> None:
    consent_selectors = [
        "[aria-label*='Accept' i]",
        "button:has-text('Accept')",
        "button:has-text('Agree')",
        "#introAgreeButton",
    ]
    for selector in consent_selectors:
        try:
            button = page.locator(selector).first
            if await button.count() == 0:
                continue
            await button.click(timeout=3000)
            await asyncio.sleep(1)
            logger.info("Clicked consent element: %s", selector)
            return
        except Exception:  # pragma: no cover - UI dependent
            continue


def looks_like_protobuf(body: bytes, headers: Dict[str, str]) -> bool:
    if not body or len(body) < 100:
        return False
    content_type = headers.get("content-type", "").lower()
    if "protobuf" in content_type or "octet-stream" in content_type:
        return True
    text_preview = body[:512].decode("utf-8", errors="ignore")
    return "!1m" in text_preview or "!2m" in text_preview


async def capture_playwright(config: CaptureConfig) -> Dict[str, Any]:
    network_requests: List[Dict[str, Any]] = []
    protobuf_hits: List[Dict[str, Any]] = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=config.headless)
        context = await browser.new_context()
        page = await context.new_page()

        async def on_request(request):
            network_requests.append(
                {
                    "url": request.url,
                    "method": request.method,
                    "headers": dict(request.headers),
                    "timestamp": time.time(),
                }
            )

        async def on_response(response):
            record = {
                "url": response.url,
                "status": response.status,
                "headers": dict(response.headers),
                "timestamp": time.time(),
            }
            if config.detect_protobuf:
                try:
                    body = await response.body()
                except Exception:
                    body = b""

                if looks_like_protobuf(body, response.headers):
                    filename = config.output_dir / f"protobuf_{int(time.time()*1000)}.bin"
                    filename.write_bytes(body)
                    record["protobuf_file"] = filename.name
                    record["size"] = len(body)
                    protobuf_hits.append(record)
            return

        page.on("request", on_request)
        page.on("response", on_response)

        logger.info("Navigating to %s", config.url)
        await page.goto(config.url, wait_until="domcontentloaded")

        if config.handle_consent:
            await handle_consent(page)

        await page.wait_for_load_state("networkidle")
        if config.wait_after_load:
            await asyncio.sleep(config.wait_after_load)

        await browser.close()

    write_json(config.output_dir / "network_requests.json", network_requests)
    if protobuf_hits:
        write_json(config.output_dir / "protobuf_hits.json", protobuf_hits)

    return {
        "request_count": len(network_requests),
        "protobuf_count": len(protobuf_hits),
    }


async def run_capture(config: CaptureConfig) -> None:
    config.output_dir.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {"url": config.url}

    if config.include_initial_request:
        summary["initial_request"] = capture_initial_request(config)

    playwright_summary = await capture_playwright(config)
    summary.update(playwright_summary)

    write_json(config.output_dir / "capture_summary.json", summary)
    logger.info(
        "Captured %d requests%s",
        playwright_summary["request_count"],
        f"; protobuf hits: {playwright_summary['protobuf_count']}" if config.detect_protobuf else "",
    )


def default_output_dir(url: str) -> Path:
    parsed = urlparse(url)
    slug = slugify(parsed.path or parsed.netloc or "capture")
    return Path("outputs") / slug / "network-traffic"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capture Google Maps network/protobuf traffic")
    parser.add_argument("url", help="Google Maps URL to inspect")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory to store capture artifacts (default: derived from URL)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode (default)",
    )
    parser.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Disable headless mode",
    )
    parser.add_argument(
        "--skip-consent",
        action="store_true",
        help="Do not attempt to click consent banners",
    )
    parser.add_argument(
        "--detect-protobuf",
        action="store_true",
        help="Persist protobuf-like responses to disk",
    )
    parser.add_argument(
        "--no-initial-request",
        action="store_true",
        help="Skip the initial requests-based capture",
    )
    parser.add_argument(
        "--wait",
        type=float,
        default=5.0,
        help="Seconds to wait after network idle before finishing (default: 5)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    output_dir = args.output_dir or default_output_dir(args.url)
    config = CaptureConfig(
        url=args.url,
        output_dir=output_dir,
        headless=args.headless,
        handle_consent=not args.skip_consent,
        detect_protobuf=args.detect_protobuf,
        include_initial_request=not args.no_initial_request,
        wait_after_load=args.wait,
    )

    try:
        asyncio.run(run_capture(config))
    except KeyboardInterrupt:
        print("Capture interrupted", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
