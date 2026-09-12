"""
Sprint 3 Step 1：新聞統計報表

從既有的 data/news.db 讀取統計資訊，不修改任何 schema 或資料。
執行方式（在專案根目錄）：
    python scripts/news_stats.py
"""

import sys
from pathlib import Path

# 讓 script 可以直接執行並找到 src/ 底下的模組。
# 做法與 scripts/analyze_news.py 一致：把專案根目錄加進 sys.path，
# 而不是把 scripts/ 改成 package 或動 PYTHONPATH 設定。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.database import engine
from src.database.models import News


def print_news_stats() -> None:
    """查詢並印出目前 news table 的統計資訊。"""
    with Session(engine) as session:
        total_count = _get_total_count(session)
        analyzed_count = _get_analyzed_count(session)
        unanalyzed_count = total_count - analyzed_count

        sentiment_counts = _get_sentiment_counts(session)
        average_score = _get_average_sentiment_score(session)
        recent_news = _get_recent_news(session, limit=5)

    print(f"總新聞數：{total_count}")
    print(f"已分析：{analyzed_count}")
    print(f"尚未分析：{unanalyzed_count}")
    print(f"Positive：{sentiment_counts.get('positive', 0)}")
    print(f"Neutral：{sentiment_counts.get('neutral', 0)}")
    print(f"Negative：{sentiment_counts.get('negative', 0)}")

    if average_score is None:
        print("平均 sentiment score：無資料")
    else:
        print(f"平均 sentiment score：{average_score:.4f}")

    print("最近 5 筆新聞：")
    if not recent_news:
        print("（目前沒有新聞資料）")
        return

    for row in recent_news:
        sentiment_label = (row.sentiment or "UNKNOWN").upper()
        score_text = f"{row.sentiment_score:.4f}" if row.sentiment_score is not None else "N/A"
        print(f"[{row.id}] {sentiment_label} {score_text} | {row.title}")


def _get_total_count(session: Session) -> int:
    """取得 news table 總筆數。"""
    statement = select(func.count()).select_from(News)
    return session.execute(statement).scalar_one()


def _get_analyzed_count(session: Session) -> int:
    """取得已完成 sentiment analysis 的新聞筆數。"""
    statement = (
        select(func.count())
        .select_from(News)
        .where(News.sentiment.is_not(None))
    )
    return session.execute(statement).scalar_one()


def _get_sentiment_counts(session: Session) -> dict[str, int]:
    """
    依 sentiment 分組計數，回傳 key 統一轉成小寫的 dict，
    例如 {"positive": 10, "neutral": 35, "negative": 7}。

    用小寫當 key 是為了不管資料庫裡實際存的是
    "positive" 還是 "POSITIVE"，統計結果都能正確對應。
    """
    statement = (
        select(News.sentiment, func.count())
        .where(News.sentiment.is_not(None))
        .group_by(News.sentiment)
    )
    results = session.execute(statement).all()

    counts: dict[str, int] = {}
    for sentiment_value, count in results:
        key = sentiment_value.lower()
        counts[key] = counts.get(key, 0) + count
    return counts


def _get_average_sentiment_score(session: Session) -> float | None:
    """
    計算已分析新聞的平均 sentiment_score。

    如果目前完全沒有已分析的資料，func.avg() 在 SQL 層會回傳 NULL，
    對應到 Python 就是 None，這裡直接把 None 往外傳，
    交給呼叫端決定要印「無資料」還是其他訊息，而不是讓程式在這裡出錯。
    """
    statement = select(func.avg(News.sentiment_score)).where(
        News.sentiment_score.is_not(None)
    )
    return session.execute(statement).scalar_one_or_none()


def _get_recent_news(session: Session, limit: int) -> list[News]:
    """取得最近的新聞（依 id 由大到小排序）。"""
    statement = select(News).order_by(News.id.desc()).limit(limit)
    return list(session.execute(statement).scalars().all())


if __name__ == "__main__":
    print_news_stats()