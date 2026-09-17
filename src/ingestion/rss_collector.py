"""
RSS 新聞收集模組 (Sprint 1)

負責從 RSS feed 讀取新聞條目，並整理成統一的 dictionary 格式。
本檔案「只負責抓取與整理資料」，不負責寫入資料庫、不含 AI 邏輯，
保持單一職責，方便之後被 ingestion pipeline 呼叫。
"""

from datetime import datetime, timezone
from typing import Any, TypedDict
import requests
import feedparser


class NewsItem(TypedDict):
    """統一的新聞資料格式，之後可以直接對應到 News ORM model 的欄位。"""

    title: str
    url: str
    source: str
    language: str
    author: str | None
    published_at: datetime | None
    description: str | None
    content: str | None


class RSSCollector:
    """
    負責從指定的 RSS feed URL 抓取新聞，並轉換成統一格式的 dictionary。

    使用方式:
        collector = RSSCollector(
            "https://example.com/rss",
            source_name="Example News"
        )
        news_list = collector.fetch()
    """

    def __init__(
    self,
    feed_url: str,
    source_name: str | None = None,
    language: str = "en",

    ) -> None:
        """
        Args:
            feed_url: RSS feed 的網址。
            source_name:
                手動指定來源名稱。
                若沒有提供，會嘗試從 RSS metadata 自動取得。
            language:
                新聞語言，例如 "en"、"zh"。
        """
        self.feed_url = feed_url
        self.source_name = source_name
        self.language = language

    def fetch(self) -> list[NewsItem]:
        """
        抓取並解析 RSS feed，回傳整理好的新聞清單。

        如果 feed 本身格式有問題或抓取失敗，會回傳空清單，
        避免單一 RSS 來源故障造成整體流程中斷。
        """

        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                )
            }

            response = requests.get(
                self.feed_url,
                headers=headers,
                timeout=15,
            )

            response.raise_for_status()

            parsed_feed = feedparser.parse(
                response.content
            )

        except requests.RequestException as error:
            print(
                f"[RSSCollector] 無法取得 feed: "
                f"{self.feed_url} ({error})"
            )
            return []

        except Exception as error:
            print(
                f"[RSSCollector] 無法解析 feed: "
                f"{self.feed_url} ({error})"
            )
            return []

        if getattr(parsed_feed, "bozo", False):
            print(
                f"[RSSCollector] 警告：feed 格式可能有問題: "
                f"{self.feed_url} "
                f"({getattr(parsed_feed, 'bozo_exception', '未知原因')})"
            )

        print(
            f"[RSSCollector] HTTP status: "
            f"{response.status_code}"
        )

        print(
            f"[RSSCollector] Content-Type: "
            f"{response.headers.get('Content-Type')}"
        )

        print(
            f"[RSSCollector] 解析到 "
            f"{len(parsed_feed.entries)} 筆 entries"
        )

        source_name = (
            self.source_name
            or self._extract_source_name(parsed_feed)
        )

        news_items: list[NewsItem] = []

        for entry in parsed_feed.entries:
            try:
                item = self._parse_entry(
                    entry,
                    source_name,
                )

                if not item["title"] or not item["url"]:
                    print(
                        "[RSSCollector] 跳過缺少 title/url 的新聞"
                    )
                    continue

                news_items.append(item)

            except Exception as error:
                title = getattr(
                    entry,
                    "title",
                    "未知標題",
                )

                print(
                    f"[RSSCollector] 跳過無法解析的條目"
                    f"「{title}」: {error}"
                )

        return news_items

    def _extract_source_name(
        self,
        parsed_feed: Any,
    ) -> str:
        """
        嘗試從 feed metadata 取得來源名稱。

        若 RSS 本身沒有 title，
        則退回使用 feed URL。
        """

        feed_title = getattr(
            parsed_feed.feed,
            "title",
            None,
        )

        return (
            feed_title
            if feed_title
            else self.feed_url
        )

    def _parse_entry(
    self,
    entry: Any,
    source_name: str,
    ) -> NewsItem:
        """
        將單一 RSS entry 轉換成統一 NewsItem。
        """

        return {
            "title": getattr(
                entry,
                "title",
                "",
            ).strip(),

            "url": getattr(
                entry,
                "link",
                "",
            ).strip(),

            "source": source_name,

            "language": self.language,

            "author": getattr(
                entry,
                "author",
                None,
            ),

            "published_at":
                self._parse_published_at(entry),

            "description": getattr(
                entry,
                "summary",
                None,
            ),

            "content":
                self._extract_content(entry),
        }
    
    def _parse_published_at(
        self,
        entry: Any,
    ) -> datetime | None:
        """
        安全取得發布時間。

        feedparser 會將可解析時間存成
        published_parsed。
        """

        time_struct = getattr(
            entry,
            "published_parsed",
            None,
        )

        if time_struct is None:
            return None

        try:
            return datetime(
                *time_struct[:6],
                tzinfo=timezone.utc,
            )

        except (TypeError, ValueError) as error:
            print(
                f"[RSSCollector] 無法解析發布時間: "
                f"{error}"
            )
            return None

    def _extract_content(
        self,
        entry: Any,
    ) -> str | None:
        """
        嘗試取得 RSS 提供的完整內文。
        """

        content_list = getattr(
            entry,
            "content",
            None,
        )

        if content_list:
            try:
                return content_list[0].value

            except (
                IndexError,
                AttributeError,
            ):
                return None

        return None


def _print_preview(
    news_items: list[NewsItem],
    limit: int = 10,
) -> None:
    """
    印出前 N 筆新聞，
    方便確認不同 RSS 是否正常。
    """

    if not news_items:
        print("沒有抓到任何新聞。")
        return

    for index, item in enumerate(
        news_items[:limit],
        start=1,
    ):
        print(
            f"{index}. {item['title']}"
        )
        print(
            f"   來源: {item['source']}"
        )
        print(
            f"   網址: {item['url']}"
        )
        print(
            f"   語言: {item['language']}"
)
        print()


if __name__ == "__main__":

    RSS_FEEDS = [
    {
        "name": "BBC News",
        "url":
            "https://feeds.bbci.co.uk/news/business/rss.xml",
        "language": "en",
    },

    {
        "name": "Yahoo Finance Taiwan - International",
        "url":
            "https://tw.stock.yahoo.com/rss?category=intl-markets",
        "language": "zh",
    },
]

        # CNBC 可以放在這裡，
        # 但建議先實際測試 feed 是否仍可正常使用。
        # 不要先把未驗證 URL 寫死進正式 pipeline。

    all_items: list[NewsItem] = []

    for feed in RSS_FEEDS:

        print(
            f"\n正在抓取：{feed['name']}"
        )

        collector = RSSCollector(
            feed_url=feed["url"],
            source_name=feed["name"],
            language=feed["language"],
        )

        items = collector.fetch()

        print(
            f"抓取到 {len(items)} 篇新聞"
        )

        all_items.extend(items)

    print(
        f"\n全部來源共抓取到 "
        f"{len(all_items)} 篇新聞。\n"
    )

    _print_preview(
        all_items,
        limit=20,
    )