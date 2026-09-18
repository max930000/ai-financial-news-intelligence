"""
Pydantic response models for the FastAPI layer (Sprint 3 Step 2).

These are pure output schemas: they describe what the API returns,
and are built directly from the existing `News` ORM model via
`from_attributes` — no new DB concepts introduced here.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

class AnalyzeRequest(BaseModel):
    """User-submitted news article for AI analysis."""

    title: str
    description: str | None = None
    content: str | None = None


class AnalyzeResponse(BaseModel):
    """AI analysis result for a submitted news article."""

    language: str
    sentiment: str | None
    sentiment_score: float | None
    category: str | None
    summary: str | None

    
class NewsListItem(BaseModel):
    """回傳給 GET /news 的單筆新聞摘要格式。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    url: str
    source: str
    language: str | None
    published_at: datetime | None
    sentiment: str | None
    sentiment_score: float | None
    ai_model: str | None
    analyzed_at: datetime | None
    


class NewsDetail(BaseModel):
    """回傳給 GET /news/{news_id} 的完整新聞格式。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    url: str
    source: str
    author: str | None
    published_at: datetime | None
    description: str | None
    content: str | None
    category: str | None
    created_at: datetime
    sentiment: str | None
    sentiment_score: float | None
    ai_model: str | None
    analyzed_at: datetime | None
    language: str | None


class SentimentAnalytics(BaseModel):
    """回傳給 GET /analytics/sentiment 的統計格式。"""

    total: int
    analyzed: int
    unanalyzed: int
    positive: int
    neutral: int
    negative: int
    average_score: float | None