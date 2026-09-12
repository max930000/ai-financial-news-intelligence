"""
News 資料存取層 (Repository)

負責把 RSSCollector 抓到的 NewsItem 寫入 SQLite，
並用 url 判斷是否重複，避免同一篇新聞被存兩次。

這一層刻意獨立出來（而不是把寫入邏輯塞進 RSSCollector 或 database.py），
是為了讓「抓資料」「整理資料」「存資料」三件事各自單一職責，
之後要換資料來源或換儲存方式時互不影響。
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.database import create_tables, engine
from src.database.models import News
from src.ingestion.rss_collector import NewsItem, RSSCollector


@dataclass
class SaveResult:
    """記錄一次 save_news_items() 的執行結果，方便呼叫端印出統計資訊。"""

    added: int
    skipped: int


class NewsRepository:
    """
    負責 News table 的寫入邏輯。

    使用方式:
        repository = NewsRepository(session)
        result = repository.save_news_items(news_items)
    """

    def __init__(self, session: Session) -> None:
        """
        Args:
            session: SQLAlchemy Session，由呼叫端建立與管理生命週期
                     （repository 本身不負責開關 session，職責保持單純）。
        """
        self.session: Session = session

    def save_news_items(self, news_items: list[NewsItem]) -> SaveResult:
        """
        將一批 NewsItem 寫入 News table，並跳過已存在（相同 url）的新聞。

        Args:
            news_items: RSSCollector.fetch() 回傳的新聞清單。

        Returns:
            SaveResult: 本次新增與跳過的筆數。
        """
        added_count = 0
        skipped_count = 0

        for item in news_items:
            if self._url_exists(item["url"]):
                skipped_count += 1
                continue

            news_row = self._to_news_model(item)
            self.session.add(news_row)
            added_count += 1

        # 統一在最後 commit 一次，而不是每筆都 commit：
        # 一方面效能較好，一方面萬一中途出錯，這批還沒 commit 的資料
        # 可以整批 rollback，避免存到一半的不一致狀態。
        try:
            self.session.commit()
        except:
            self.session.rollback()
            raise
        
        return SaveResult(added=added_count, skipped=skipped_count)

    def _url_exists(self, url: str) -> bool:
        """
        檢查這個 url 是否已經存在於 News table。

        用 url 而不是 title 判斷重複，是因為同一篇新聞的標題可能被
        來源方微調（例如加上更新時間），但 url 通常是穩定不變的。
        """
        statement = select(News.id).where(News.url == url)
        existing_id = self.session.execute(statement).scalar_one_or_none()
        return existing_id is not None

    def _to_news_model(self, item: NewsItem) -> News:
        """將 NewsItem (dict) 轉換成 News ORM model 物件。"""
        return News(
            title=item["title"],
            url=item["url"],
            source=item["source"],
            author=item["author"],
            published_at=item["published_at"],
            description=item["description"],
            content=item["content"],
            
        )


if __name__ == "__main__":
    # 簡單的手動測試進入點：
    #   python -m src.database.repository
    # 流程：建表 -> 抓 RSS -> 存進 SQLite -> 印出統計數字

    create_tables()

    test_feed_url = "https://feeds.bbci.co.uk/news/business/rss.xml"
    collector = RSSCollector(test_feed_url)
    fetched_items = collector.fetch()

    with Session(engine) as session:
        repository = NewsRepository(session)
        result = repository.save_news_items(fetched_items)

    print(f"RSS 抓到: {len(fetched_items)} 筆")
    print(f"新增: {result.added} 筆")
    print(f"跳過（重複）: {result.skipped} 筆")