"""
AI News Digest - メインスクリプト。

実行の流れ:
  1. 設定（.env / settings.json / feeds.json）を読み込む
  2. 各情報源から最新記事を取得する
  3. 投稿済みの記事を除外する（重複防止）
  4. 投稿件数の上限まで絞り込む
  5. 英語記事を日本語へ翻訳する
  6. Discordへ投稿する
  7. 投稿済みリストを更新して保存する

Windowsタスクスケジューラーから run_news_bot.bat 経由で毎朝実行される想定。
"""

from __future__ import annotations

import sys

from src.config_loader import POSTED_PATH, load_config
from src.discord_poster import DiscordPoster
from src.news_fetcher import NewsFetcher
from src.storage import PostedStore
from src.translator import Translator
from src.utils import setup_logger


def main() -> int:
    logger = setup_logger()
    logger.info("=" * 60)
    logger.info("AI News Digest 実行開始")

    # 1. 設定読み込み
    try:
        config = load_config()
    except (EnvironmentError, ValueError) as exc:
        logger.error("設定の読み込みに失敗しました: %s", exc)
        return 1

    enabled = config.enabled_feeds
    logger.info("有効な情報源: %d 件", len(enabled))
    if not enabled:
        logger.warning("有効な情報源がありません。feeds.json を確認してください。")
        return 0

    # 2. ニュース取得
    fetcher = NewsFetcher(config, logger)
    articles = fetcher.fetch_all()
    logger.info("取得した記事の合計: %d 件", len(articles))
    if not articles:
        logger.info("取得できた記事がありませんでした。終了します。")
        return 0

    # 公開日が新しい順に並べ替え（公開日不明は後ろへ）
    articles.sort(
        key=lambda a: a.published.timestamp() if a.published else 0, reverse=True
    )

    # 3. 重複除外
    store = PostedStore(POSTED_PATH, logger)
    new_articles = store.filter_new(articles)
    logger.info("未投稿の新着記事: %d 件", len(new_articles))
    if not new_articles:
        logger.info("新着記事はありませんでした。終了します。")
        return 0

    # 4. 投稿件数の上限まで絞る
    limit = config.max_articles_per_run
    target = new_articles[:limit]
    logger.info("今回投稿する記事: %d 件（上限 %d）", len(target), limit)

    # 5. 翻訳（英語記事のみ）
    try:
        translator = Translator(config, logger)
        translator.translate_articles(target)
    except Exception as exc:  # 翻訳全体が落ちても原文で投稿を続ける
        logger.error("翻訳処理でエラーが発生しました（原文で続行）: %s", exc)

    # 6. Discord投稿
    poster = DiscordPoster(config, logger)
    posted = poster.post_articles(target)
    logger.info("投稿成功: %d 件", len(posted))

    # 7. 投稿済みを記録して保存
    for article in posted:
        store.mark_posted(article)
    store.save()

    logger.info("AI News Digest 実行終了")
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("中断されました。")
        sys.exit(130)
    except Exception as exc:  # 想定外の例外も握りつぶさずログだけは残す
        # ここに来る時点ではロガーが使えない可能性もあるため print も併用
        print(f"予期しないエラーで終了しました: {exc}")
        sys.exit(1)
