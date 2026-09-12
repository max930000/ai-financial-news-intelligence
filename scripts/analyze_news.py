from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.ai.sentiment import MODEL_NAME, analyze_sentiment
from src.database.models import News

from src.database.database import engine
from src.database.models import News
from src.ai.sentiment import analyze_sentiment

def build_news_text(news: News) -> str:
    parts = []

    for field in ("title", "description", "content"):
        value = getattr(news, field, None)

        if value:
            parts.append(value)

    return " ".join(parts)


def main():
    with Session(engine) as session:
        news_list = session.execute(
            select(News).where(News.sentiment.is_(None))
        ).scalars().all()

        print(f"找到 {len(news_list)} 筆尚未分析的新聞")

        success = 0
        failed = 0

        for news in news_list:
            text = build_news_text(news)

            if not text:
                print(f"[SKIP] News {news.id}: 沒有可分析文字")
                continue

            try:
                result = analyze_sentiment(text)

                news.sentiment = result["label"]
                news.sentiment_score = result["score"]
                news.ai_model = MODEL_NAME
                news.analyzed_at = datetime.now()

                success += 1

                print(
                    f"[{news.id}] "
                    f"{result['label']:8} "
                    f"{result['score']:.4f} | "
                    f"{getattr(news, 'title', '')[:60]}"
                )

            except Exception as e:
                failed += 1
                print(f"[ERROR] News {news.id}: {e}")

        session.commit()

        print()
        print("AI 分析完成")
        print(f"成功：{success}")
        print(f"失敗：{failed}")


if __name__ == "__main__":
    main()