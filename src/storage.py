"""
重複投稿防止モジュール。

投稿済みの記事ID（記事URLのハッシュ）を data/posted_articles.json に記録し、
すでに投稿済みの記事は再投稿しないようにする。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Set

from .news_fetcher import Article


class PostedStore:
    """投稿済み記事の記録を読み書きする。"""

    def __init__(self, path: Path, logger, keep_max: int = 2000):
        self.path = path
        self.logger = logger
        # 記録が無限に増えないよう、保持する最大件数（古いものから削除）
        self.keep_max = keep_max
        self._records: List[dict] = []
        self._ids: Set[str] = set()
        self._load()

    def _load(self) -> None:
        """JSONファイルから投稿済みリストを読み込む。"""
        try:
            with self.path.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
            self._records = data.get("posted", [])
        except (FileNotFoundError, json.JSONDecodeError):
            # 無い／壊れている場合は空から開始する
            self._records = []
        self._ids = {rec.get("id") for rec in self._records if rec.get("id")}

    def is_posted(self, article: Article) -> bool:
        """この記事がすでに投稿済みかどうか。"""
        return article.article_id in self._ids

    def mark_posted(self, article: Article) -> None:
        """記事を投稿済みとしてメモリ上に追加する（保存は save() で行う）。"""
        if article.article_id in self._ids:
            return
        self._ids.add(article.article_id)
        self._records.append(
            {
                "id": article.article_id,
                "url": article.url,
                "title": article.title,
                "source": article.source,
                "posted_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    def save(self) -> None:
        """投稿済みリストをファイルへ書き出す。"""
        # 古い記録から間引いて上限内に収める
        if len(self._records) > self.keep_max:
            self._records = self._records[-self.keep_max :]
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("w", encoding="utf-8") as fp:
                json.dump({"posted": self._records}, fp, ensure_ascii=False, indent=2)
        except OSError as exc:
            self.logger.error("投稿済みリストの保存に失敗しました: %s", exc)

    def filter_new(self, articles: List[Article]) -> List[Article]:
        """まだ投稿していない記事だけを返す（重複・URL重複を除去）。"""
        seen_this_run: Set[str] = set()
        new_articles: List[Article] = []
        for article in articles:
            if article.article_id in seen_this_run:
                continue  # 同一実行内の重複（複数フィードに同じ記事）も除去
            if self.is_posted(article):
                continue
            seen_this_run.add(article.article_id)
            new_articles.append(article)
        return new_articles
