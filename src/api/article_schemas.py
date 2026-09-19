"""Request and response models for the article-input flow (fetch → preview → confirm)."""

from datetime import datetime

from pydantic import BaseModel, Field


class PreviewRequest(BaseModel):
    # Blank or malformed values are reported by the fetcher as `invalid_url`.
    url: str = Field(max_length=2048)


class PreviewResponse(BaseModel):
    """Result of trying to fetch one article. `ok=False` is a normal outcome."""

    ok: bool
    url: str
    final_url: str | None
    source: str | None
    title: str | None
    published_at: datetime | None
    fetched_at: datetime
    body: str
    body_hash: str | None
    paragraph_count: int
    char_count: int
    warnings: list[str]
    failure_reason: str | None
    message: str


class ConfirmRequest(BaseModel):
    """The text the user finally approved, fetched or pasted, possibly edited."""

    url: str | None = Field(default=None, max_length=2048)
    title: str = Field(max_length=2000)
    body: str = Field(max_length=200_000)
    # Returned by the preview; lets the server tell "fetched" from "edited".
    fetched_body_hash: str | None = Field(default=None, max_length=64)
    published_at: datetime | None = None
    fetched_at: datetime | None = None
    # Set when the user pasted text because the automatic fetch failed.
    fetch_failure_reason: str | None = Field(default=None, max_length=40)


class ArticleOut(BaseModel):
    id: int
    url: str | None
    title: str
    source: str | None
    published_at: datetime | None
    fetched_at: datetime | None
    body: str
    char_count: int
    paragraph_count: int
    content_hash: str
    input_origin: str
    fetch_failure_reason: str | None
    created_at: datetime


class ConfirmResponse(ArticleOut):
    # False when identical input had already been confirmed and was reused.
    created: bool
