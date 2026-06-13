"""
設定読み込みモジュール。

- .env から機密情報（Webhook URL / APIキー）を読む
- config/settings.json と config/feeds.json を読む
- 必要なフォルダ・JSONファイルが無い場合は自動生成する
機密情報はソースに直書きせず、すべてここ経由で取得する。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

from .utils import PROJECT_ROOT

# 各種パス
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
SETTINGS_PATH = CONFIG_DIR / "settings.json"
FEEDS_PATH = CONFIG_DIR / "feeds.json"
POSTED_PATH = DATA_DIR / "posted_articles.json"

# settings.json が無い場合に自動生成する初期値
_DEFAULT_SETTINGS: Dict[str, Any] = {
    "max_articles_per_run": 15,
    "max_articles_per_feed": 5,
    "fetch_within_hours": 36,
    "summary_max_length": 300,
    "request_timeout_seconds": 20,
    "user_agent": "AI-News-Digest/1.0 (+https://example.com)",
    "translation": {
        "enabled": True,
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1024,
        "target_language": "日本語",
    },
    "discord": {
        "username": "AI News Digest",
        "embeds_per_message": 10,
        "show_source_footer": True,
    },
    "weekday_colors": {
        "monday": "#3498DB",
        "tuesday": "#2ECC71",
        "wednesday": "#F1C40F",
        "thursday": "#9B59B6",
        "friday": "#E67E22",
        "saturday": "#E74C3C",
        "sunday": "#95A5A6",
    },
}

_DEFAULT_FEEDS: Dict[str, Any] = {"feeds": []}


@dataclass
class Secrets:
    """.env から読み込んだ機密情報をまとめて持つ。"""

    discord_webhook_url: str
    anthropic_api_key: str


class AppConfig:
    """ツール全体の設定をまとめて保持するクラス。"""

    def __init__(self, secrets: Secrets, settings: Dict[str, Any], feeds: List[Dict[str, Any]]):
        self.secrets = secrets
        self.settings = settings
        self.feeds = feeds

    # --- よく使う設定値へのショートカット ---
    @property
    def max_articles_per_run(self) -> int:
        return int(self.settings.get("max_articles_per_run", 15))

    @property
    def max_articles_per_feed(self) -> int:
        return int(self.settings.get("max_articles_per_feed", 5))

    @property
    def fetch_within_hours(self) -> int:
        return int(self.settings.get("fetch_within_hours", 36))

    @property
    def summary_max_length(self) -> int:
        return int(self.settings.get("summary_max_length", 300))

    @property
    def request_timeout(self) -> int:
        return int(self.settings.get("request_timeout_seconds", 20))

    @property
    def user_agent(self) -> str:
        return str(self.settings.get("user_agent", "AI-News-Digest/1.0"))

    @property
    def translation(self) -> Dict[str, Any]:
        return self.settings.get("translation", {})

    @property
    def discord(self) -> Dict[str, Any]:
        return self.settings.get("discord", {})

    @property
    def weekday_colors(self) -> Dict[str, str]:
        return self.settings.get("weekday_colors", {})

    @property
    def enabled_feeds(self) -> List[Dict[str, Any]]:
        """enabled が True（未指定も True 扱い）のフィードのみ返す。"""
        return [f for f in self.feeds if f.get("enabled", True)]


def ensure_directories_and_files() -> None:
    """
    必要なフォルダとJSONファイルが無ければ自動作成する。

    初回実行や、誤って削除された場合でも動くようにするための保険。
    """
    for directory in (CONFIG_DIR, DATA_DIR, LOGS_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    if not SETTINGS_PATH.exists():
        _write_json(SETTINGS_PATH, _DEFAULT_SETTINGS)

    if not FEEDS_PATH.exists():
        _write_json(FEEDS_PATH, _DEFAULT_FEEDS)

    if not POSTED_PATH.exists():
        _write_json(POSTED_PATH, {"posted": []})


def _read_json(path: Path) -> Dict[str, Any]:
    """JSONファイルを読む。壊れている場合は分かりやすい例外にする。"""
    try:
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.name} のJSON形式が壊れています: {exc}") from exc


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)


def load_config() -> AppConfig:
    """
    .env / settings.json / feeds.json をまとめて読み込み、AppConfig を返す。

    機密情報が未設定の場合は、その場で分かりやすいエラーを出す。
    """
    # 1. フォルダ・ファイルを準備
    ensure_directories_and_files()

    # 2. .env 読み込み
    load_dotenv(PROJECT_ROOT / ".env")
    webhook = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()

    missing = []
    if not webhook or webhook.startswith("ここに"):
        missing.append("DISCORD_WEBHOOK_URL")
    if not api_key or api_key.startswith("ここに"):
        missing.append("ANTHROPIC_API_KEY")
    if missing:
        raise EnvironmentError(
            "次の環境変数が未設定です: "
            + ", ".join(missing)
            + "\n.env.example をコピーして .env を作成し、値を入力してください。"
        )

    secrets = Secrets(discord_webhook_url=webhook, anthropic_api_key=api_key)

    # 3. 設定ファイル読み込み
    settings = _read_json(SETTINGS_PATH)
    feeds_data = _read_json(FEEDS_PATH)
    feeds = feeds_data.get("feeds", [])

    return AppConfig(secrets=secrets, settings=settings, feeds=feeds)
