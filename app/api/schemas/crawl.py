"""Request/response schemas for the crawl endpoints."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class SourceMode(StrEnum):
    DOM = "dom"
    CURL = "curl"


class PaginationMode(StrEnum):
    NONE = "none"
    PAGE = "page"
    CURSOR = "cursor"
    SCROLL = "scroll"
    BUTTON = "button"


class FieldSpec(BaseModel):
    name: str = Field(..., description="Field name in output JSON")
    selector: str = Field(..., description="CSS selector")
    attribute: str = Field(default="text", description="text | href | src | data-*")
    multiple: bool = Field(default=False, description="Extract list of matching nodes")
    children: list[FieldSpec] = Field(default_factory=list, description="Nested fields")


class CrawlConfig(BaseModel):
    container: str | None = Field(default=None, description="CSS selector for repeating row containers")
    fields: list[FieldSpec] = Field(default_factory=list, description="Field definitions; empty = LLM-detected")
    llm_auto_detect: bool = Field(default=True, description="Use Groq LLM to detect structure")
    include_nested: bool = Field(default=True, description="Build cascading JSON for child elements")
    extract_all_descendants: bool = Field(default=False, description="Extract every non-SVG descendant")


class CrawlRequest(BaseModel):
    source: str = Field(..., description="Source identifier (reddit, steam, imdb, news, custom)")
    url: str = Field(..., description="Seed URL to crawl")
    mode: SourceMode = Field(default=SourceMode.DOM)
    pagination: PaginationMode = Field(default=PaginationMode.NONE)
    max_pages: int = Field(default=1, ge=1, le=50)
    config: CrawlConfig | None = None
    curl_body: str | None = Field(default=None, description="Raw cURL request body (JSON string)")
    curl_headers: dict[str, str] | None = Field(default=None, description="Additional headers for cURL mode")
    output_name: str | None = None


class HealingEvent(BaseModel):
    field: str
    old_selector: str
    new_selector: str
    strategy: str


class CrawlResponse(BaseModel):
    run_id: str
    status: str
    message: str
    records_extracted: int = 0
    pages_fetched: int = 0
    dataset_name: str | None = None
    output_path: str | None = None
    records_preview: list[dict[str, Any]] = Field(default_factory=list)
    healing_events: list[HealingEvent] = Field(default_factory=list)
    suggested_selectors: dict[str, Any] | None = Field(
        default=None, description="LLM-detected selectors for manual tuning"
    )


class AnalyzeRequest(BaseModel):
    url: str = Field(..., description="URL to fetch and analyze")
    source: str = Field(default="custom", description="Hint for LLM analysis")
    html_snippet: str | None = Field(default=None, description="Pre-fetched HTML (skips fetch step)")


class AnalyzeResponse(BaseModel):
    container: str | None = None
    fields: list[FieldSpec] = Field(default_factory=list)
    dataset_name_suggestion: str | None = None
    confidence: str = "low"
    notes: str | None = None
