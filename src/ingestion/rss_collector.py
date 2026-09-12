"""
RSS 新聞收集模組 (Sprint 1)

負責從單一 RSS feed 讀取新聞條目，並整理成統一的 dictionary 格式。
本檔案「只負責抓取與整理資料」，不負責寫入資料庫、不含 AI 邏輯，
保持單一職責，方便之後被 ingestion pipeline 呼叫。
"""
from datetime import datetime, timezone
from typing import Any, TypedDict

import feedparser


class NewsItem(TypedDict):
    """統一的新聞資料格式，之後可以直接對應到 News ORM model 的欄位。"""

    title: str
    url: str
    source: str
    author: str | None
    published_at: datetime | None
    description: str | None
    content: str | None


class RSSCollector:
    """
    負責從指定的 RSS feed URL 抓取新聞，並轉換成統一格式的 dictionary。

    使用方式:
        collector = RSSCollector("https://example.com/rss")
        news_list = collector.fetch()
    """

    def __init__(self, feed_url: str) -> None:
        """
        Args:
            feed_url: RSS feed 的網址。
        """
        self.feed_url: str = feed_url

    def fetch(self) -> list[NewsItem]:
        """
        抓取並解析 RSS feed，回傳整理好的新聞清單。

        如果 feed 本身格式有問題或抓取失敗，會回傳空清單，
        而不是讓整支程式直接 crash（因為 RSS 來源常常不穩定）。

        Returns:
            list[NewsItem]: 整理後的新聞資料清單。
        """
        try:
            parsed_feed = feedparser.parse(self.feed_url)
        except Exception as error:
            # feedparser 本身很少直接拋例外（它多半把錯誤放在 bozo_exception），
            # 但還是保留這層 try/except 以防網路層或底層函式庫出錯。
            print(f"[RSSCollector] 無法解析 feed: {self.feed_url} ({error})")
            return []

        # feedparser 用 bozo 標記「格式是否有問題」，而不是直接丟例外。
        # 這裡選擇不直接放棄，因為很多「格式稍微不標準」的 feed 仍然可以正常解析出內容，
        # 只印出警告，讓開發者知道，但不中斷流程。
        if getattr(parsed_feed, "bozo", False):
            print(
                f"[RSSCollector] 警告：feed 格式可能有問題: {self.feed_url} "
                f"({getattr(parsed_feed, 'bozo_exception', '未知原因')})"
            )

        source_name: str = self._extract_source_name(parsed_feed)

        news_items: list[NewsItem] = []
        for entry in parsed_feed.entries:
            try:
                news_items.append(self._parse_entry(entry, source_name))
            except Exception as error:
                # 單一篇文章解析失敗不應該影響其他文章，所以個別 catch，
                # 略過這篇並繼續處理下一篇。
                title = getattr(entry, "title", "未知標題")
                print(f"[RSSCollector] 跳過無法解析的條目「{title}」: {error}")
                continue

        return news_items

    def _extract_source_name(self, parsed_feed: Any) -> str:
        """
        嘗試從 feed 的 metadata 取得來源名稱（例如「BBC News」），
        如果沒有提供，就退回使用 feed_url 本身。
        """
        feed_title = getattr(parsed_feed.feed, "title", None)
        return feed_title if feed_title else self.feed_url

    def _parse_entry(self, entry: Any, source_name: str) -> NewsItem:
        """
        將單一 RSS entry 轉換成統一格式的 NewsItem。

        Args:
            entry: feedparser 解析出來的單一條目物件。
            source_name: 這個 feed 的來源名稱。

        Returns:
            NewsItem: 整理後的新聞資料。
        """
        return {
            "title": getattr(entry, "title", "").strip(),
            "url": getattr(entry, "link", "").strip(),
            "source": source_name,
            "author": getattr(entry, "author", None),
            "published_at": self._parse_published_at(entry),
            "description": getattr(entry, "summary", None),
            # 不同 feed 可能用 "content" 或只有 "summary"，這裡優先取較完整的內容，
            # 沒有的話退回 None，交由後續流程決定要不要用 description 代替。
            "content": self._extract_content(entry),
        }

    def _parse_published_at(self, entry: Any) -> datetime | None:
        """
        安全地取得發布時間。

        RSS 標準沒有強制要求提供發布時間，很多 feed 也常常缺漏或格式不一致，
        所以這裡用 getattr + try/except 雙重保護，任何情況都不應該讓程式 crash，
        取不到時間就回傳 None，交給資料庫的 nullable 欄位處理。
        """
        # feedparser 會把可解析的時間轉成 time.struct_time，欄位名稱通常是
        # published_parsed，找不到就直接回傳 None。
        time_struct = getattr(entry, "published_parsed", None)
        if time_struct is None:
            return None

        try:
            return datetime(*time_struct[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError) as error:
            print(f"[RSSCollector] 無法解析發布時間: {error}")
            return None

    def _extract_content(self, entry: Any) -> str | None:
        """
        嘗試取得完整內文（部分 feed 會提供 entry.content），
        沒有的話回傳 None，而不是強行塞入不存在的欄位。
        """
        content_list = getattr(entry, "content", None)
        if content_list:
            try:
                return content_list[0].value
            except (IndexError, AttributeError):
                return None
        return None


def _print_preview(news_items: list[NewsItem], limit: int = 10) -> None:
    """印出前 N 筆新聞的 title / source / url，方便快速驗證抓取結果。"""
    if not news_items:
        print("沒有抓到任何新聞。")
        return

    for index, item in enumerate(news_items[:limit], start=1):
        print(f"{index}. {item['title']}")
        print(f"   來源: {item['source']}")
        print(f"   網址: {item['url']}")
        print()


if __name__ == "__main__":
    # 簡單的手動測試進入點：
    #   python -m src.ingestion.rss_collector
    # 這裡先用一個公開的示範 feed，之後可以換成任何財經新聞 RSS。
    test_feed_url = "https://feeds.bbci.co.uk/news/business/rss.xml"

    collector = RSSCollector(test_feed_url)
    items = collector.fetch()

    print(f"共抓取到 {len(items)} 篇新聞，顯示前 10 筆：\n")
    _print_preview(items, limit=10)