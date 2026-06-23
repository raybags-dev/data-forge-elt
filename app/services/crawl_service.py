"""CrawlService — Playwright DOM + httpx cURL + Groq LLM orchestration."""

from __future__ import annotations

import json
import re
import uuid
from typing import TYPE_CHECKING, Any

import httpx
from bs4 import BeautifulSoup, Tag

from app.api.schemas.crawl import (
    AnalyzeRequest,
    AnalyzeResponse,
    CrawlRequest,
    CrawlResponse,
    FieldSpec,
    PaginationMode,
    SourceMode,
)
from shared.logger import get_logger

if TYPE_CHECKING:
    from config.settings import Settings
    from datalake.manager import DataLakeManager
    from shared.notifier import Notifier

# Source-specific defaults: container selector + key field selectors
SOURCE_DEFAULTS: dict[str, dict[str, Any]] = {
    "reddit": {
        "container": "shreddit-post, [data-testid='post-container'], .Post",
        "fields": [
            {"name": "title", "selector": "h3, [slot='title']", "attribute": "text"},
            {"name": "score", "selector": "[id^='vote-arrows'] faceplate-number, .score", "attribute": "text"},
            {"name": "author", "selector": "[data-testid='post_author_link'], .author", "attribute": "text"},
            {"name": "subreddit", "selector": "[data-testid='subreddit-name'], .subreddit", "attribute": "text"},
            {"name": "link", "selector": "a[slot='full-post-link'], a.title", "attribute": "href"},
            {"name": "comments", "selector": "a[data-testid='comments-page-link-num-comments']", "attribute": "text"},
        ],
        "wait_for": "shreddit-post, .Post",
        "scroll": True,
    },
    "steam": {
        "container": ".search_result_row, .store_nav_area",
        "fields": [
            {"name": "title", "selector": ".title, .store_nav_area h2", "attribute": "text"},
            {"name": "price", "selector": ".discount_final_price, .game_purchase_price", "attribute": "text"},
            {"name": "release_date", "selector": ".search_released", "attribute": "text"},
            {"name": "review_score", "selector": ".search_reviewscore span", "attribute": "data-tooltip-html"},
            {"name": "link", "selector": "a", "attribute": "href"},
            {"name": "thumbnail", "selector": "img", "attribute": "src"},
        ],
        "wait_for": ".search_result_row",
        "scroll": False,
    },
    "imdb": {
        "container": ".lister-item, [data-testid='title-card'], li.ipc-metadata-list-summary-item",
        "fields": [
            {"name": "title", "selector": ".lister-item-header a, h3 a, [data-testid='title']", "attribute": "text"},
            {"name": "year", "selector": ".lister-item-year, .sc-f30335b4-0", "attribute": "text"},
            {"name": "rating", "selector": ".ratings-imdb-rating strong, [data-testid='ratingGroup--imdb-rating']", "attribute": "text"},
            {"name": "genre", "selector": ".genre", "attribute": "text"},
            {"name": "votes", "selector": ".sort-num_votes-visible span[data-value]", "attribute": "data-value"},
            {"name": "link", "selector": "h3 a, [data-testid='title'] a", "attribute": "href"},
        ],
        "wait_for": ".lister-item, li.ipc-metadata-list-summary-item",
        "scroll": True,
    },
    "news": {
        "container": "article, .article-card, [data-testid='article']",
        "fields": [
            {"name": "headline", "selector": "h2, h3, .headline", "attribute": "text"},
            {"name": "summary", "selector": "p, .summary, .description", "attribute": "text"},
            {"name": "published", "selector": "time, .timestamp, [datetime]", "attribute": "datetime"},
            {"name": "author", "selector": ".author, .byline, [rel='author']", "attribute": "text"},
            {"name": "link", "selector": "a", "attribute": "href"},
        ],
        "wait_for": "article",
        "scroll": False,
    },
    "custom": {
        "container": None,
        "fields": [],
        "wait_for": None,
        "scroll": False,
    },
}

_GROQ_SYSTEM = """You are a data-engineering assistant helping extract structured data from HTML.
Your job: identify repeating container elements and field selectors in the DOM.
Always respond with valid JSON only — no markdown, no explanation outside JSON."""

_GROQ_ANALYZE_PROMPT = """Given the following HTML snippet (truncated), identify:
1. The CSS selector for the repeating row/item container
2. CSS selectors for key fields within each container (title, link, price, date, etc.)
3. A short descriptive dataset_name (snake_case, no spaces, no domain TLDs)
4. A confidence level: "high" | "medium" | "low"
5. Any notes about ambiguity

Respond ONLY in this JSON format:
{{
  "container": "CSS selector string or null",
  "fields": [
    {{"name": "field_name", "selector": "css selector", "attribute": "text|href|src|data-*", "multiple": false}}
  ],
  "dataset_name_suggestion": "snake_case_name",
  "confidence": "high|medium|low",
  "notes": "optional notes"
}}

Source hint: {source}
HTML:
{html}"""

_GROQ_DATASET_NAME_PROMPT = """Given this URL and source type, suggest a snake_case dataset name (no spaces, no TLDs, max 40 chars).
Respond with ONLY the snake_case name, nothing else.
URL: {url}
Source: {source}
Records sample keys: {keys}"""


class CrawlService:
    """Runs web crawls via Playwright DOM or httpx cURL and Groq LLM analysis."""

    def __init__(
        self,
        settings: Settings,
        notifier: Notifier,
        lake: DataLakeManager,
    ) -> None:
        self._settings = settings
        self._notifier = notifier
        self._lake = lake
        self._log = get_logger(__name__)

    # ── Public API ────────────────────────────────────────────────────────────

    async def run_crawl(self, request: CrawlRequest) -> CrawlResponse:
        run_id = str(uuid.uuid4())
        self._log.info(f"CrawlService: run_id={run_id} source={request.source} mode={request.mode}")
        try:
            if request.mode == SourceMode.CURL:
                return await self._crawl_curl(run_id, request)
            return await self._crawl_dom(run_id, request)
        except Exception as exc:
            self._log.error(f"CrawlService failed: {exc}")
            return CrawlResponse(run_id=run_id, status="error", message=str(exc))

    async def analyze(self, request: AnalyzeRequest) -> AnalyzeResponse:
        try:
            if request.html_snippet:
                html = request.html_snippet
            else:
                html = await self._fetch_html(request.url)
            return await self._llm_analyze(html, request.source, request.url)
        except Exception as exc:
            self._log.error(f"analyze failed: {exc}")
            return AnalyzeResponse(notes=str(exc))

    def get_sources(self) -> dict[str, Any]:
        return {
            src: {
                "container": cfg["container"],
                "field_count": len(cfg["fields"]),
                "fields": [f["name"] for f in cfg["fields"]],
            }
            for src, cfg in SOURCE_DEFAULTS.items()
        }

    # ── DOM crawl ─────────────────────────────────────────────────────────────

    async def _crawl_dom(self, run_id: str, request: CrawlRequest) -> CrawlResponse:
        from playwright.async_api import async_playwright

        cfg = request.config
        source_defaults = SOURCE_DEFAULTS.get(request.source, SOURCE_DEFAULTS["custom"])

        container_sel = (cfg.container if cfg else None) or source_defaults["container"]
        field_specs = (cfg.fields if cfg else []) or [
            FieldSpec(**f) for f in source_defaults["fields"]
        ]

        all_records: list[dict[str, Any]] = []
        pages_fetched = 0
        healing_events = []
        suggested_selectors = None

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self._settings.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (compatible; DataForge/1.0)",
                viewport={"width": 1280, "height": 800},
            )
            page = await context.new_page()

            current_url: str | None = request.url
            page_num = 1

            while current_url and page_num <= request.max_pages:
                try:
                    await page.goto(current_url, wait_until="domcontentloaded", timeout=30_000)

                    wait_sel = source_defaults.get("wait_for")
                    if wait_sel:
                        import contextlib
                        with contextlib.suppress(Exception):
                            await page.wait_for_selector(wait_sel, timeout=8_000)

                    if (
                        request.pagination in (PaginationMode.SCROLL,)
                        or source_defaults.get("scroll")
                    ):
                        await self._auto_scroll(page)

                    html = await page.content()
                    pages_fetched += 1

                    if not container_sel and (cfg is None or cfg.llm_auto_detect):
                        analyze_resp = await self._llm_analyze(html, request.source, current_url)
                        container_sel = analyze_resp.container
                        if not field_specs and analyze_resp.fields:
                            field_specs = analyze_resp.fields
                            suggested_selectors = {
                                "container": container_sel,
                                "fields": [f.model_dump() for f in field_specs],
                                "llm_confidence": analyze_resp.confidence,
                            }

                    records = self._extract_records(html, container_sel, field_specs, cfg)
                    all_records.extend(records)

                    current_url = self._next_url(
                        current_url, html, page_num, request.pagination, page
                    )
                    page_num += 1
                except Exception as exc:
                    self._log.warning(f"Page {page_num} failed: {exc}")
                    break

            await browser.close()

        dataset_name = request.output_name or await self._suggest_dataset_name(
            request.url, request.source, all_records
        )

        output_path: str | None = None
        if all_records:
            output_path = await self._save_records(all_records, dataset_name)

        return CrawlResponse(
            run_id=run_id,
            status="success" if all_records else "empty",
            message=f"Extracted {len(all_records)} records from {pages_fetched} page(s).",
            records_extracted=len(all_records),
            pages_fetched=pages_fetched,
            dataset_name=dataset_name,
            output_path=output_path,
            records_preview=all_records[:10],
            healing_events=healing_events,
            suggested_selectors=suggested_selectors,
        )

    # ── cURL crawl ────────────────────────────────────────────────────────────

    async def _crawl_curl(self, run_id: str, request: CrawlRequest) -> CrawlResponse:
        all_records: list[dict[str, Any]] = []
        pages_fetched = 0
        headers = {"Content-Type": "application/json", **(request.curl_headers or {})}

        body_template: dict[str, Any] = {}
        if request.curl_body:
            try:
                body_template = json.loads(request.curl_body)
            except json.JSONDecodeError as exc:
                return CrawlResponse(
                    run_id=run_id, status="error",
                    message=f"curl_body is not valid JSON: {exc}"
                )

        async with httpx.AsyncClient(timeout=30, headers=headers, follow_redirects=True) as client:
            for page_num in range(1, request.max_pages + 1):
                body = self._build_curl_body(body_template, page_num, request.pagination)
                try:
                    resp = await client.post(request.url, json=body)
                    resp.raise_for_status()
                    pages_fetched += 1
                    data = resp.json()
                    records = self._flatten_curl_response(data)
                    if not records:
                        break
                    all_records.extend(records)
                    if request.pagination == PaginationMode.NONE:
                        break
                except Exception as exc:
                    self._log.warning(f"cURL page {page_num} failed: {exc}")
                    break

        dataset_name = request.output_name or await self._suggest_dataset_name(
            request.url, request.source, all_records
        )

        output_path: str | None = None
        if all_records:
            output_path = await self._save_records(all_records, dataset_name)

        return CrawlResponse(
            run_id=run_id,
            status="success" if all_records else "empty",
            message=f"Extracted {len(all_records)} records from {pages_fetched} page(s) via cURL.",
            records_extracted=len(all_records),
            pages_fetched=pages_fetched,
            dataset_name=dataset_name,
            output_path=output_path,
            records_preview=all_records[:10],
        )

    # ── Extraction helpers ────────────────────────────────────────────────────

    def _extract_records(
        self,
        html: str,
        container_sel: str | None,
        field_specs: list[FieldSpec],
        cfg: Any,
    ) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")

        if not container_sel:
            return self._extract_all_descendants(soup)

        containers = soup.select(container_sel)
        if not containers:
            return []

        records: list[dict[str, Any]] = []
        for elem in containers:
            if field_specs:
                rec = self._extract_fields(elem, field_specs)
            elif cfg and cfg.extract_all_descendants:
                rec = self._elem_to_cascading(elem)
            else:
                rec = self._extract_all_descendants_from_elem(elem)
            if rec:
                records.append(rec)
        return records

    def _extract_fields(self, container: Tag, fields: list[FieldSpec]) -> dict[str, Any]:
        rec: dict[str, Any] = {}
        for spec in fields:
            try:
                if spec.multiple:
                    nodes = container.select(spec.selector)
                    values = [self._get_attr(n, spec.attribute) for n in nodes]
                    child_recs = []
                    for n in nodes:
                        if spec.children:
                            child_recs.append(self._extract_fields(n, spec.children))
                    rec[spec.name] = child_recs if spec.children else [v for v in values if v]
                else:
                    node = container.select_one(spec.selector)
                    if node:
                        if spec.children:
                            rec[spec.name] = self._extract_fields(node, spec.children)
                        else:
                            rec[spec.name] = self._get_attr(node, spec.attribute)
                    else:
                        rec[spec.name] = None
            except Exception:
                rec[spec.name] = None
        return rec

    def _get_attr(self, elem: Tag, attribute: str) -> str | None:
        if attribute == "text":
            return elem.get_text(strip=True) or None
        val = elem.get(attribute)
        return str(val) if val else None

    def _elem_to_cascading(self, elem: Tag) -> dict[str, Any]:
        """Convert an element and its descendants to a cascading dict."""
        result: dict[str, Any] = {}
        tag_name = elem.name or "item"
        text = elem.get_text(strip=True)

        attrs = {k: v for k, v in (elem.attrs or {}).items()
                 if k not in ("class", "style") and not k.startswith("on")}

        children_data: list[dict[str, Any]] = []
        for child in elem.children:
            if isinstance(child, Tag) and child.name not in ("svg", "script", "style"):
                child_rec = self._elem_to_cascading(child)
                if child_rec:
                    children_data.append(child_rec)

        node: dict[str, Any] = {}
        if text and not children_data:
            node["text"] = text
        if attrs:
            node["attrs"] = attrs
        if children_data:
            node["children"] = children_data

        if node:
            result[tag_name] = node
        return result

    def _extract_all_descendants(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        body = soup.find("body") or soup
        records = []
        for child in body.children:
            if isinstance(child, Tag) and child.name not in ("svg", "script", "style", "head"):
                rec = self._elem_to_cascading(child)
                if rec:
                    records.append(rec)
        return records

    def _extract_all_descendants_from_elem(self, elem: Tag) -> dict[str, Any]:
        text = elem.get_text(separator=" ", strip=True)
        links = [a.get("href") for a in elem.find_all("a", href=True)]
        imgs = [i.get("src") for i in elem.find_all("img", src=True)]
        rec: dict[str, Any] = {"text": text}
        if links:
            rec["links"] = links[:5]
        if imgs:
            rec["images"] = imgs[:3]
        return rec

    # ── LLM analysis ──────────────────────────────────────────────────────────

    async def _llm_analyze(self, html: str, source: str, url: str) -> AnalyzeResponse:
        api_key = self._settings.groq_api_key
        if not api_key:
            return AnalyzeResponse(notes="GROQ_API_KEY not configured; use manual selectors")

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "svg", "noscript", "head"]):
            tag.decompose()

        snippet = str(soup)[:12_000]

        prompt = _GROQ_ANALYZE_PROMPT.format(source=source, html=snippet)
        try:
            raw = await self._groq_chat(api_key, _GROQ_SYSTEM, prompt)
            raw = re.sub(r"^```(?:json)?\n?", "", raw.strip())
            raw = re.sub(r"\n?```$", "", raw.strip())
            data = json.loads(raw)

            fields = [
                FieldSpec(
                    name=f.get("name", "field"),
                    selector=f.get("selector", ""),
                    attribute=f.get("attribute", "text"),
                    multiple=f.get("multiple", False),
                )
                for f in data.get("fields", [])
            ]

            return AnalyzeResponse(
                container=data.get("container"),
                fields=fields,
                dataset_name_suggestion=data.get("dataset_name_suggestion"),
                confidence=data.get("confidence", "low"),
                notes=data.get("notes"),
            )
        except Exception as exc:
            self._log.warning(f"LLM analyze failed: {exc}")
            return AnalyzeResponse(
                notes=f"LLM analysis failed: {exc}. Please provide selectors manually."
            )

    async def _suggest_dataset_name(
        self, url: str, source: str, records: list[dict[str, Any]]
    ) -> str:
        api_key = self._settings.groq_api_key
        if not api_key or not records:
            slug = re.sub(r"[^a-z0-9]+", "_", source.lower()).strip("_")
            return f"{slug}_dataset"

        keys = list(records[0].keys())[:6] if records else []
        prompt = _GROQ_DATASET_NAME_PROMPT.format(url=url, source=source, keys=keys)
        try:
            name = await self._groq_chat(api_key, "You name datasets.", prompt)
            name = re.sub(r"[^a-z0-9_]", "_", name.strip().lower())[:40].strip("_")
            return name or f"{source}_dataset"
        except Exception:
            return f"{source}_dataset"

    async def _groq_chat(self, api_key: str, system: str, user: str) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1024,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    # ── Pagination helpers ────────────────────────────────────────────────────

    def _next_url(
        self,
        current_url: str,
        html: str,
        page_num: int,
        mode: PaginationMode,
        page: Any,
    ) -> str | None:
        if mode == PaginationMode.NONE:
            return None

        if mode == PaginationMode.PAGE:
            from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
            parsed = urlparse(current_url)
            params = parse_qs(parsed.query, keep_blank_values=True)
            params["page"] = [str(page_num + 1)]
            flat = {k: v[0] for k, v in params.items()}
            return urlunparse(parsed._replace(query=urlencode(flat)))

        if mode == PaginationMode.CURSOR:
            soup = BeautifulSoup(html, "html.parser")
            next_link = soup.select_one("a[rel='next'], .next a, [aria-label='Next']")
            if next_link:
                href = next_link.get("href")
                if href:
                    from urllib.parse import urljoin
                    return urljoin(current_url, str(href))
            return None

        if mode == PaginationMode.BUTTON:
            soup = BeautifulSoup(html, "html.parser")
            next_link = soup.select_one(
                "a.next, a[rel='next'], button.next, [aria-label='Next page'] a"
            )
            if next_link and next_link.name == "a":
                from urllib.parse import urljoin
                return urljoin(current_url, str(next_link.get("href", "")))
            return None

        return None

    async def _auto_scroll(self, page: Any) -> None:
        """Scroll the page to trigger lazy-loaded content."""
        try:
            prev_height = 0
            for _ in range(8):
                height = await page.evaluate("document.body.scrollHeight")
                if height == prev_height:
                    break
                prev_height = height
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(800)
        except Exception:
            pass

    # ── Misc helpers ──────────────────────────────────────────────────────────

    async def _fetch_html(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 DataForge/1.0"})
            resp.raise_for_status()
            return resp.text

    async def _save_records(self, records: list[dict[str, Any]], name: str) -> str:
        import pandas as pd

        from shared.utils import ensure_directory

        out_path = self._lake.layer_path("raw", name) / "data.parquet"
        ensure_directory(out_path.parent)
        pd.DataFrame(records).to_parquet(out_path, index=False)
        return str(out_path)

    def _build_curl_body(
        self, template: dict[str, Any], page_num: int, mode: PaginationMode
    ) -> dict[str, Any]:
        body = dict(template)
        if mode == PaginationMode.PAGE:
            body["page"] = page_num
        elif mode == PaginationMode.CURSOR:
            body["offset"] = (page_num - 1) * body.get("limit", 20)
        return body

    def _flatten_curl_response(self, data: Any) -> list[dict[str, Any]]:
        if isinstance(data, list):
            return [r for r in data if isinstance(r, dict)]
        if isinstance(data, dict):
            for key in ("data", "results", "items", "records", "hits", "posts", "content"):
                if key in data and isinstance(data[key], list):
                    return [r for r in data[key] if isinstance(r, dict)]
            return [data]
        return []
