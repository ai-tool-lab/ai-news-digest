"""
共通ユーティリティ。

- ログ設定
- 言語判定（日本語かどうか）
- HTMLタグ除去・要約の整形
- 日付パース
これらは各モジュールから共通で使われます。
"""

from __future__ import annotations

import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# プロジェクトのルートディレクトリ（このファイルの2つ上）
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 日本語（ひらがな・カタカナ・漢字）にマッチする正規表現
_JP_PATTERN = re.compile(r"[぀-ゟ゠-ヿ一-鿿]")


def setup_logger(name: str = "ai_news_digest", log_dir: Optional[Path] = None) -> logging.Logger:
    """
    画面とファイルの両方に出力するロガーを用意する。

    ログファイルは logs/ai_news_digest_YYYY-MM-DD.log に保存される。
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        # すでに設定済みなら使い回す（多重登録を防ぐ）
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # コンソール出力
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    logger.addHandler(console)

    # ファイル出力（logs ディレクトリが無ければ作成）
    if log_dir is None:
        log_dir = PROJECT_ROOT / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        file_handler = logging.FileHandler(
            log_dir / f"ai_news_digest_{today}.log", encoding="utf-8"
        )
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
    except OSError as exc:  # ファイル出力に失敗してもコンソールには出す
        logger.warning("ログファイルを作成できませんでした: %s", exc)

    return logger


def is_japanese(text: str) -> bool:
    """
    文字列に日本語が含まれていれば True を返す。

    記事タイトルに数文字でも日本語が含まれていれば日本語記事とみなし、
    翻訳をスキップする判定に使う。
    """
    if not text:
        return False
    return bool(_JP_PATTERN.search(text))


def strip_html(text: str) -> str:
    """HTMLタグを取り除き、余分な空白を整理したプレーンテキストを返す。"""
    if not text:
        return ""
    try:
        from bs4 import BeautifulSoup

        clean = BeautifulSoup(text, "html.parser").get_text(separator=" ")
    except Exception:
        # BeautifulSoup が使えない場合の簡易フォールバック
        clean = re.sub(r"<[^>]+>", " ", text)
    # 連続する空白・改行を1つにまとめる
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def truncate(text: str, max_length: int) -> str:
    """指定した文字数を超える場合は末尾を「…」で省略する。"""
    if text is None:
        return ""
    text = text.strip()
    if max_length and len(text) > max_length:
        return text[: max_length - 1].rstrip() + "…"
    return text


def parse_entry_datetime(entry) -> Optional[datetime]:
    """
    feedparser のエントリから公開日時（タイムゾーン付き）を取り出す。

    published / updated のどちらかが取れればそれを使う。取れなければ None。
    """
    for key in ("published_parsed", "updated_parsed"):
        value = getattr(entry, key, None) or (entry.get(key) if hasattr(entry, "get") else None)
        if value:
            try:
                # time.struct_time（UTC）を datetime に変換
                return datetime(*value[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
    return None


def format_date_jst(dt: Optional[datetime]) -> str:
    """
    日時を「YYYY-MM-DD HH:MM (JST)」形式の文字列にする（表示用）。

    日時が無い場合は「不明」を返す。
    """
    if dt is None:
        return "不明"
    # 日本時間（UTC+9）に変換
    from datetime import timedelta

    jst = dt.astimezone(timezone(timedelta(hours=9)))
    return jst.strftime("%Y-%m-%d %H:%M (JST)")
