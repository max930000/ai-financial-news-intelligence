from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session
from transformers import pipeline


# 讓 python scripts/analyze_news.py 可以找到 src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.database import engine
from src.database.models import News


MODEL_NAME = "ProsusAI/finbert"
BATCH_SIZE = 8


def build_text(news: News) -> str:
    """
    Combine useful news fields into the text sent to FinBERT.
    """
    parts = [news.title]

    if news.description:
        parts.append(news.description)

    if news.content:
        parts.append(news.content)

    return " ".join(parts)


def main() -> None:
    print("Loading FinBERT...")

    sentiment_analyzer = pipeline(
        "text-classification",
        model=MODEL_NAME,
        tokenizer=MODEL_NAME,
    )

    print("FinBERT loaded.")

    with Session(engine) as session:
        news_items = session.execute(
            select(News)
            .where(News.sentiment.is_(None))
            .order_by(News.id)
        ).scalars().all()

        if not news_items:
            print("沒有尚未分析的新聞。")
            return

        print(f"找到 {len(news_items)} 筆尚未分析的新聞。")

        texts = [
            build_text(news)
            for news in news_items
        ]

        results = sentiment_analyzer(
            texts,
            batch_size=BATCH_SIZE,
            truncation=True,
            max_length=512,
        )

        for news, result in zip(news_items, results):
            sentiment = result["label"].lower()
            score = float(result["score"])

            news.sentiment = sentiment
            news.sentiment_score = score
            news.ai_model = MODEL_NAME
            news.analyzed_at = datetime.now(timezone.utc)

            print(
                f"[{news.id}] "
                f"{sentiment.upper():8} "
                f"{score:.4f} | "
                f"{news.title}"
            )

        session.commit()

        print()
        print(f"分析完成，共更新 {len(news_items)} 筆新聞。")


if __name__ == "__main__":
    main()