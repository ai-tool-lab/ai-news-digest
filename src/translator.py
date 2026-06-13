"""
翻訳モジュール。

英語記事のタイトルと概要を、Claude Console API（Anthropic）を使って
日本語へ翻訳する。日本語記事は翻訳しない。

- 1記事の翻訳に失敗しても全体を止めない（元の英語のまま投稿に回す）
- API呼び出し回数を減らすため、タイトルと概要を1回のリクエストでまとめて翻訳する
"""

from __future__ import annotations

import json
from typing import List

from anthropic import Anthropic

from .news_fetcher import Article
from .utils import is_japanese


class Translator:
    """Claude API を使った日本語翻訳。"""

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.settings = config.translation
        self.enabled = bool(self.settings.get("enabled", True))
        self.model = self.settings.get("model", "claude-haiku-4-5-20251001")
        self.max_tokens = int(self.settings.get("max_tokens", 1024))
        self.target_language = self.settings.get("target_language", "日本語")

        # APIキーは .env 経由で渡す（直書きしない）
        self.client = Anthropic(api_key=config.secrets.anthropic_api_key)

    def translate_articles(self, articles: List[Article]) -> None:
        """
        記事リストを順に翻訳する（Articleオブジェクトを直接書き換える）。

        翻訳が無効な設定、または日本語記事の場合はスキップする。
        """
        if not self.enabled:
            self.logger.info("翻訳は設定で無効化されています。スキップします。")
            return

        for article in articles:
            # タイトルが日本語なら翻訳不要
            if article.lang == "ja" or is_japanese(article.title):
                continue
            try:
                self._translate_one(article)
            except Exception as exc:  # 失敗しても元の英語のまま投稿へ
                self.logger.error(
                    "翻訳失敗（英語のまま投稿します）: %s -> %s", article.title, exc
                )

    def _translate_one(self, article: Article) -> None:
        """1記事のタイトルと概要をまとめて翻訳する。"""
        prompt = self._build_prompt(article.title, article.summary)

        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        ).strip()

        title_ja, summary_ja = self._parse_response(text, article)
        article.title_ja = title_ja
        article.summary_ja = summary_ja
        self.logger.info("翻訳成功: %s", article.title)

    def _build_prompt(self, title: str, summary: str) -> str:
        """翻訳指示用のプロンプトを組み立てる。JSON形式で返すよう依頼する。"""
        return (
            f"次の英語のニュース記事のタイトルと概要を自然な{self.target_language}に翻訳してください。\n"
            "翻訳結果のみを、次のJSON形式で出力してください（前後に説明文を付けないこと）:\n"
            '{"title": "翻訳したタイトル", "summary": "翻訳した概要"}\n\n'
            "固有名詞や製品名（OpenAI, Claude, Gemini など）は無理に訳さず原語のままで構いません。\n\n"
            f"タイトル: {title}\n"
            f"概要: {summary if summary else '(概要なし)'}\n"
        )

    def _parse_response(self, text: str, article: Article):
        """
        モデルの応答からタイトルと概要を取り出す。

        JSONで返ってくる前提だが、崩れていてもできる限り拾う。
        """
        # ```json ... ``` で囲まれている場合に備えて中身を抜き出す
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            # 先頭の "json" ラベルを除去
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
            title_ja = str(data.get("title", "")).strip() or article.title
            summary_ja = str(data.get("summary", "")).strip() or article.summary
            return title_ja, summary_ja
        except json.JSONDecodeError:
            # JSONとして読めない場合は、応答全文を概要訳として扱う（保険）
            self.logger.warning("翻訳応答をJSONとして解析できませんでした。原文を併用します。")
            return article.title, cleaned or article.summary
