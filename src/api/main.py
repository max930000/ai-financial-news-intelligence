"""
FastAPI app (Sprint 3 Step 2 + Step 3)

提供三個唯讀 JSON endpoint，以及一個 HTML Dashboard，
全部直接查詢既有的 data/news.db：
    GET /news
    GET /news/{news_id}
    GET /analytics/sentiment
    GET /dashboard

這一層刻意不建立 service layer 或 repository layer——
邏輯量很小，直接在 endpoint 裡用 SQLAlchemy 查詢即可，
之後如果邏輯變複雜，再抽也不遲。

啟動方式（在專案根目錄）：
    uvicorn src.api.main:app --reload
"""

from collections.abc import Generator
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.api.schemas import NewsDetail, NewsListItem, SentimentAnalytics
from src.database.database import engine
from src.database.models import News

app = FastAPI(
    title="AI Financial News Intelligence Platform",
    description="Sprint 3：唯讀 API + Dashboard，查詢新聞與情緒分析統計。",
    version="0.1.0",
)

# Dashboard 用的 templates / static 檔案位置，都相對這個檔案所在目錄，
# 這樣不管從哪個工作目錄啟動 uvicorn，路徑都是一致的。
_API_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(_API_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(_API_DIR / "static")), name="static")


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency：每個 request 取得一個獨立的 Session，
    request 結束後自動關閉。這是 FastAPI + SQLAlchemy 的標準寫法。
    """
    with Session(engine) as session:
        yield session


@app.get("/news", response_model=list[NewsListItem])
def list_news(db: Session = Depends(get_db)) -> list[News]:
    """
    取得新聞列表，依 id 由大到小排序。

    目前資料量只有 52 筆，所以不做 pagination；
    未來資料量變大時，可以在這裡加 limit/offset 參數，
    endpoint 的簽名不需要大改。
    """
    statement = select(News).order_by(News.id.desc())
    return list(db.execute(statement).scalars().all())


@app.get("/news/{news_id}", response_model=NewsDetail)
def get_news_detail(news_id: int, db: Session = Depends(get_db)) -> News:
    """取得單篇新聞完整資訊，找不到時回傳 404。"""
    news = db.get(News, news_id)
    if news is None:
        raise HTTPException(status_code=404, detail="News not found")
    return news


@app.get("/analytics/sentiment", response_model=SentimentAnalytics)
def get_sentiment_analytics(db: Session = Depends(get_db)) -> SentimentAnalytics:
    """回傳目前新聞的情緒分析統計（JSON，給 API 使用者/程式呼叫）。"""
    stats = _compute_sentiment_stats(db)
    return SentimentAnalytics(**stats)


@app.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    """
    Sprint 3 Step 3：Dashboard 頁面。

    後端一次算好 KPI 統計 + 最近 10 筆新聞，直接傳給 Jinja2 template 渲染，
    瀏覽器端不再另外呼叫 /news 或 /analytics/sentiment，
    這樣資料來源單一、也比較容易在面試時解釋整個流程。
    """
    stats = _compute_sentiment_stats(db)

    recent_statement = select(News).order_by(News.id.desc()).limit(10)
    recent_news = db.execute(recent_statement).scalars().all()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={**stats, "recent_news": recent_news},
    )


def _compute_sentiment_stats(db: Session) -> dict:
    """
    計算 total / analyzed / unanalyzed / positive / neutral / negative / average_score。

    抽成共用函式是因為 /analytics/sentiment 和 /dashboard 需要完全一樣的統計數字，
    避免同一段查詢邏輯在兩個地方各寫一次、之後容易兜不起來。
    """
    total = db.execute(select(func.count()).select_from(News)).scalar_one()

    analyzed = db.execute(
        select(func.count()).select_from(News).where(News.sentiment.is_not(None))
    ).scalar_one()
    unanalyzed = total - analyzed

    sentiment_counts = _get_sentiment_counts(db)

    average_score = db.execute(
        select(func.avg(News.sentiment_score)).where(
            News.sentiment_score.is_not(None)
        )
    ).scalar_one_or_none()

    return {
        "total": total,
        "analyzed": analyzed,
        "unanalyzed": unanalyzed,
        "positive": sentiment_counts.get("positive", 0),
        "neutral": sentiment_counts.get("neutral", 0),
        "negative": sentiment_counts.get("negative", 0),
        "average_score": round(average_score, 4) if average_score is not None else None,
    }


def _get_sentiment_counts(db: Session) -> dict[str, int]:
    """
    依 sentiment 分組計數，key 統一轉小寫，
    確保不論資料庫存的是 "positive" 還是 "POSITIVE" 都能正確對應，
    且缺少的分類由呼叫端用 .get(key, 0) 補 0，不會漏掉「0 筆也要回傳」的需求。
    """
    statement = (
        select(News.sentiment, func.count())
        .where(News.sentiment.is_not(None))
        .group_by(News.sentiment)
    )
    results = db.execute(statement).all()

    counts: dict[str, int] = {}
    for sentiment_value, count in results:
        key = sentiment_value.lower()
        counts[key] = counts.get(key, 0) + count
    return counts   