from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.database import engine
from src.database.models import News


with Session(engine) as session:
    count = session.scalar(
        select(func.count()).select_from(News)
    )

    print(f"資料庫目前共有 {count} 筆新聞")

    news = session.execute(
        select(News)
        .order_by(News.id)
        .limit(5)
    ).scalars().all()

    print("\n前 5 筆新聞：")

    for item in news:
        print(f"{item.id} | {item.source} | {item.title}")