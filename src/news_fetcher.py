"""
ニュース取得モジュール。

設定ファイル feeds.json に書かれた情報源からRSS/Atomを取得し、
記事（タイトル・URL・公開日・概要）を Article オブジェクトのリストで返す。

- RSSが使えるサイト（type: "rss"）を優先して処理する
- type が "html" / "sns" のものは、将来の拡張ポイントとして枠だけ用意してある
  （現状はRSSHub等のフィードURLが設定されていればRSSと同じ流れで取得を試みる）
- 1つのフィードの取得に失敗しても、他のフィードの処理は止めない
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import feedparser
import requests

from .utils import parse_entry_datetime, strip_html, truncate


@dataclass
class Article:
    """1件の記事を表すデータ構造。"""

    title: str
    url: str
    summary: str
    source: str
    lang: str
    published: Optional[datetime] = None
    # 翻訳後の値（英語記事のみ後で埋まる）
    title_ja: Optional[str] = None
    summary_ja: Optional[str] = None
    article_id: str = field(default="")

    def __post_init__(self):
        # 重複判定に使うID。URLがあればURL、無ければタイトルのハッシュ。
        key = self.url or self.title
        self.article_id = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    @property
    def display_title(self) -> str:
        """投稿に使うタイトル（翻訳があればそれを優先）。"""
        return self.title_ja or self.title

    @property
    def display_summary(self) -> str:
        """投稿に使う概要（翻訳があればそれを優先）。"""
        return self.summary_ja or self.summary


class NewsFetcher:
    """フィードを巡回して記事を集める。"""

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger

    def fetch_all(self) -> List[Article]:
        """有効なすべてのフィードから記事を集めて返す。"""
        articles: List[Article] = []
        for feed in self.config.enabled_feeds:
            name = feed.get("name", "(no name)")
            try:
                fetched = self._fetch_one(feed)
                self.logger.info("取得成功: %s （%d件）", name, len(fetched))
                articles.extend(fetched)
            except Exception as exc:  # 1フィードの失敗で全体を止めない
                self.logger.error("取得失敗: %s -> %s", name, exc)
        return articles

    def _fetch_one(self, feed: dict) -> List[Article]:
        """1つのフィードを取得し、記事リストを返す。"""
        url = feed.get("url", "")
        name = feed.get("name", "(no name)")
        lang = feed.get("lang", "en")
        feed_type = feed.get("type", "rss")

        if not url:
            raise ValueError("url が設定されていません")

        # html / sns タイプは将来の専用実装ポイント。
        # 現状はフィードURL（RSSHub等）が設定されていればRSSとして取得を試みる。
        if feed_type in ("html", "sns"):
            self.logger.info(
                "%s は type=%s です。RSSフィードとして取得を試みます。", name, feed_type
            )

        # User-Agent を付けて取得（一部サイトはUA無しだと弾く）
        raw = self._download(url)
        parsed = feedparser.parse(raw)

        if parsed.bozo and not parsed.entries:
            # パースに失敗し、かつ記事が1件も無い場合はエラー扱い
            raise ValueError(f"フィードを解析できませんでした（{parsed.bozo_exception}）")

        cutoff = datetime.now(timezone.utc) - timedelta(
            hours=self.config.fetch_within_hours
        )
        max_per_feed = self.config.max_articles_per_feed
        summary_len = self.config.summary_max_length

        articles: List[Article] = []
        for entry in parsed.entries:
            if len(articles) >= max_per_feed:
                break

            published = parse_entry_datetime(entry)
            # 公開日が分かっていて、かつ古すぎる記事はスキップ
            if published is not None and published < cutoff:
                continue

            title = strip_html(entry.get("title", "")).strip()
            link = entry.get("link", "").strip()
            if not title or not link:
                continue

            # 概要はsummary→descriptionの順で拾い、HTMLを除去して短くする
            raw_summary = entry.get("summary", "") or entry.get("description", "")
            summary = truncate(strip_html(raw_summary), summary_len)

            articles.append(
                Article(
                    title=title,
                    url=link,
                    summary=summary,
                    source=name,
                    lang=lang,
                    published=published,
                )
            )

        return articles

    def _download(self, url: str) -> bytes:
        """
        フィードURLの中身を取得してバイト列で返す。

        feedparser に直接URLを渡すこともできるが、UAやタイムアウトを
        細かく制御するため requests を経由する。
        """
        headers = {"User-Agent": self.config.user_agent}
        resp = requests.get(
            url, headers=headers, timeout=self.config.request_timeout
        )
        resp.raise_for_status()
        return resp.content
