"""
Discord投稿モジュール。

Webhook URL を使って、取得・翻訳済みの記事を Discord へ投稿する。

- 曜日ごとにEmbedの色を変える（色は settings.json で変更可能）
- 見出しに曜日を表示する
- Embedには タイトル / 概要 / URL / 情報元 / 公開日 を含める
- 1メッセージあたりのEmbed数の上限（Discord仕様は10）を守って分割投稿する
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import List

import requests

from .news_fetcher import Article
from .utils import format_date_jst, truncate

# 曜日の日本語表記（0=月曜 ... 6=日曜、Python の weekday() に合わせる）
_WEEKDAY_JA = ["月", "火", "水", "木", "金", "土", "日"]
# settings.json のキー（weekday() のインデックス順）
_WEEKDAY_KEYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]

# Discordの各種上限
_EMBED_TITLE_MAX = 256
_EMBED_DESC_MAX = 4096


class DiscordPoster:
    """Discord Webhook への投稿を担当する。"""

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.webhook_url = config.secrets.discord_webhook_url
        self.discord_settings = config.discord
        self.username = self.discord_settings.get("username", "AI News Digest")
        self.embeds_per_message = int(self.discord_settings.get("embeds_per_message", 10))
        self.show_footer = bool(self.discord_settings.get("show_source_footer", True))
        self.timeout = config.request_timeout

    def post_articles(self, articles: List[Article]) -> List[Article]:
        """
        記事を投稿し、投稿に成功した記事のリストを返す。

        まず曜日見出しを投稿し、その後で記事Embedを分割投稿する。
        """
        if not articles:
            self.logger.info("投稿対象の新着記事はありませんでした。")
            return []

        now = datetime.now()
        color = self._weekday_color(now)

        # 1) 曜日見出しメッセージ
        self._post_header(now, len(articles))

        # 2) 記事Embedを embeds_per_message 件ずつまとめて投稿
        posted: List[Article] = []
        for i in range(0, len(articles), self.embeds_per_message):
            chunk = articles[i : i + self.embeds_per_message]
            embeds = [self._build_embed(a, color) for a in chunk]
            if self._send({"username": self.username, "embeds": embeds}):
                posted.extend(chunk)
            else:
                self.logger.error("%d件のEmbed投稿に失敗しました。", len(chunk))
            # レート制限対策に少し待つ
            time.sleep(1.0)

        return posted

    def _post_header(self, now: datetime, count: int) -> None:
        """曜日が分かる見出しメッセージを投稿する。"""
        weekday_ja = _WEEKDAY_JA[now.weekday()]
        content = (
            f"📰 **{now.strftime('%Y年%m月%d日')}（{weekday_ja}）のAIニュースダイジェスト**\n"
            f"本日の新着 {count} 件をお届けします。"
        )
        self._send({"username": self.username, "content": content})
        time.sleep(0.5)

    def _build_embed(self, article: Article, color: int) -> dict:
        """1記事分のEmbedを組み立てる。"""
        title = truncate(article.display_title, _EMBED_TITLE_MAX)
        description = truncate(article.display_summary, _EMBED_DESC_MAX)

        embed = {
            "title": title or "(タイトルなし)",
            "url": article.url,
            "description": description,
            "color": color,
            "fields": [
                {"name": "情報元", "value": article.source, "inline": True},
                {
                    "name": "公開日",
                    "value": format_date_jst(article.published),
                    "inline": True,
                },
            ],
        }
        if self.show_footer:
            embed["footer"] = {"text": f"{article.source} / AI News Digest"}
        return embed

    def _weekday_color(self, now: datetime) -> int:
        """その日の曜日に対応するEmbedカラー（整数）を返す。"""
        key = _WEEKDAY_KEYS[now.weekday()]
        hex_color = self.config.weekday_colors.get(key, "#5865F2")
        return self._hex_to_int(hex_color)

    @staticmethod
    def _hex_to_int(hex_color: str) -> int:
        """"#3498DB" のような16進カラーをDiscord用の整数に変換する。"""
        try:
            return int(str(hex_color).lstrip("#"), 16)
        except (ValueError, AttributeError):
            return 0x5865F2  # 変換できない場合はDiscordブランドカラー

    def _send(self, payload: dict) -> bool:
        """Webhookへ実際にPOSTする。成功で True。"""
        try:
            resp = requests.post(
                self.webhook_url, json=payload, timeout=self.timeout
            )
            # 429（レート制限）は待って1度だけ再試行する
            if resp.status_code == 429:
                retry_after = float(resp.json().get("retry_after", 2))
                self.logger.warning(
                    "Discordレート制限。%.1f秒待って再試行します。", retry_after
                )
                time.sleep(retry_after + 0.5)
                resp = requests.post(
                    self.webhook_url, json=payload, timeout=self.timeout
                )
            resp.raise_for_status()
            return True
        except requests.RequestException as exc:
            self.logger.error("Discord投稿エラー: %s", exc)
            return False
