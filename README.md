# AI News Digest 📰

毎朝、指定したWebサイトから最新の **AIニュース・AI関連情報** を自動取得し、
英語記事は **Claude APIで日本語に翻訳** したうえで、**Discordの指定チャンネルへ自動投稿** するツールです。

Windowsタスクスケジューラーで毎朝8時に動かすことを想定しています。

---

## ✨ 主な機能

- 複数の情報源（公式ブログ・研究機関・ニュースメディア・日本語メディアなど）からRSSで記事を取得
- 英語記事のタイトル・概要をClaude APIで日本語に翻訳（日本語記事はそのまま）
- Discordへ見やすいEmbed形式で投稿（タイトル / 概要 / URL / 情報元 / 公開日）
- **曜日ごとにEmbedの色を変更**（色は設定ファイルで変更可能）
- **同じ記事は二度投稿しない**（重複防止）
- 取得先・投稿件数などは設定ファイルを書き換えるだけで調整可能
- 1記事の失敗で全体が止まらないエラー処理＆ログ出力

---

## 🧰 必要なもの

| 必要なもの | 説明 |
| --- | --- |
| Windows 10 / 11 | 動作確認環境 |
| Python 3.10 以上 | [python.org](https://www.python.org/downloads/) からインストール（**「Add python.exe to PATH」にチェック**） |
| Discord Webhook URL | 投稿先チャンネルの「連携サービス」→「ウェブフック」から作成 |
| Claude Console APIキー | [console.anthropic.com](https://console.anthropic.com/) で取得 |

---

## 🚀 セットアップ手順

### 1. ファイルを配置

このフォルダ一式を任意の場所（例: `I:\Project\ai-news-digest`）に置きます。

### 2. コマンドプロンプト／PowerShellでフォルダへ移動

```powershell
cd I:\Project\ai-news-digest
```

### 3. 仮想環境を作成して有効化

```powershell
python -m venv .venv
.venv\Scripts\activate
```

> 有効化に成功すると、行頭に `(.venv)` と表示されます。

### 4. 必要なライブラリをインストール

```powershell
pip install -r requirements.txt
```

### 5. `.env` ファイルを作成（後述）

### 6. 動作テスト

```powershell
python main.py
```

Discordに投稿されれば成功です 🎉

---

## 🔑 `.env` の作成方法

機密情報（Webhook URL・APIキー）は **ソースコードに直接書かず `.env` から読み込みます。**

1. このフォルダにある `.env.example` をコピーして、ファイル名を `.env` に変更します。

   PowerShellなら次の1行でコピーできます。

   ```powershell
   Copy-Item .env.example .env
   ```

2. `.env` をメモ帳などで開き、実際の値に書き換えます。

   ```env
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxxxxxxx/yyyyyyyy
   ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
   ```

> ⚠️ `.env` は秘密情報です。GitHubなどに**絶対にアップロードしないでください**（`.gitignore`で除外済み）。

---

## 🌐 対象URL（情報源）の追加・変更方法

情報源は `config/feeds.json` で管理しています。
ここを編集するだけで、取得先の追加・削除・変更ができます。

```jsonc
{
  "name": "OpenAI News",          // 情報元の表示名
  "url": "https://openai.com/news/rss.xml",  // RSS/AtomフィードのURL
  "lang": "en",                    // 言語: "en"=英語(翻訳する) / "ja"=日本語(翻訳しない)
  "type": "rss",                   // 種別: "rss" はそのまま動作。"html"/"sns" は将来拡張枠
  "priority": "highest",           // 優先度の覚書（動作には影響しません）
  "enabled": true                  // false にすると取得対象から外れます
}
```

### よくある編集

- **一時的に止めたい** → その情報源の `"enabled"` を `false` にする
- **新しいサイトを追加したい** → 上の形をコピーして `feeds` 配列に追加する
- **取得件数を変えたい** → `config/settings.json` の `max_articles_per_feed` / `max_articles_per_run` を変更

### `type` が `html` / `sns` の情報源について

公式に安定したRSSが存在しない情報源（Anthropic Newsroom / 各社のX(旧Twitter) など）は、
初期状態で `"enabled": false` にしています。これらは以下のいずれかで対応できます。

- **RSSHub** を使う（`url` にRSSHubのフィードURLを設定し、`enabled` を `true` に）
- 専用のHTML取得処理を `src/news_fetcher.py` に追加実装する

無理に有効化すると取得エラーが増えるため、まずはRSSが使える情報源だけで運用するのがおすすめです。

---

## ⚙️ 設定ファイル（`config/settings.json`）

| 項目 | 説明 |
| --- | --- |
| `max_articles_per_run` | 1回の実行で投稿する**最大記事数** |
| `max_articles_per_feed` | 1つの情報源から取る最大件数 |
| `fetch_within_hours` | 「何時間以内に公開された記事」を対象にするか |
| `summary_max_length` | 概要文の最大文字数（超えたら省略） |
| `translation.enabled` | 翻訳のON/OFF（`false`で翻訳停止＝API料金ゼロ） |
| `translation.model` | 翻訳に使うClaudeモデル名 |
| `discord.embeds_per_message` | 1メッセージあたりのEmbed数（Discord上限は10） |
| `weekday_colors` | **曜日ごとの色**（16進カラーコードで自由に変更可） |

### 曜日カラーの初期設定

| 曜日 | 色 |
| --- | --- |
| 月 | 青 (`#3498DB`) |
| 火 | 緑 (`#2ECC71`) |
| 水 | 黄 (`#F1C40F`) |
| 木 | 紫 (`#9B59B6`) |
| 金 | オレンジ (`#E67E22`) |
| 土 | 赤 (`#E74C3C`) |
| 日 | グレー (`#95A5A6`) |

---

## ▶️ 手動実行方法

```powershell
cd I:\Project\ai-news-digest
.venv\Scripts\activate
python main.py
```

または、用意済みのバッチファイルをダブルクリックでもOKです。

```text
run_news_bot.bat
```

---

## ⏰ Windowsタスクスケジューラーへの登録方法

毎朝8時に自動実行する手順です。

1. スタートメニューで「**タスク スケジューラ**」を検索して起動
2. 右側の「**基本タスクの作成**」をクリック
3. **名前**: `AI News Digest`（任意）→「次へ」
4. **トリガー**: 「毎日」を選択 →「次へ」
5. **開始時刻**: `8:00:00` に設定 →「次へ」
6. **操作**: 「**プログラムの開始**」を選択 →「次へ」
7. 設定内容:
   - **プログラム/スクリプト**: `run_news_bot.bat` のフルパス
     （例: `I:\Project\ai-news-digest\run_news_bot.bat`）
   - **開始（オプション）**: プロジェクトフォルダのパス
     （例: `I:\Project\ai-news-digest`）← **ここの設定が重要です**
8. 「次へ」→「完了」

### 補足設定（推奨）

作成したタスクを右クリック →「プロパティ」で以下を確認しておくと安定します。

- 「全般」タブ:「**ユーザーがログオンしているかどうかにかかわらず実行する**」
- 「条件」タブ:「コンピューターをAC電源で使用している場合のみ〜」のチェックを外す（ノートPCの場合）
- 「設定」タブ:「タスクを要求時に実行する」にチェック（手動テスト用）

### 登録後のテスト

タスクを右クリック →「**実行する**」で、その場で動作確認できます。

---

## ✅ 動作確認方法

1. `.env` に正しいWebhook URLとAPIキーが入っているか確認
2. `python main.py` を実行
3. Discordチャンネルに、曜日見出し＋記事Embedが投稿されるか確認
4. **もう一度** `python main.py` を実行 → 同じ記事が**再投稿されない**ことを確認（重複防止の確認）
5. `logs/` フォルダに当日のログファイルが作られているか確認

---

## 🛠️ トラブルシューティング / よくあるエラー

| 症状・エラー | 原因 | 対処 |
| --- | --- | --- |
| `次の環境変数が未設定です: ...` | `.env` が無い／値が未入力 | `.env` を作成し、Webhook URLとAPIキーを入力 |
| `'python' は…認識されていません` | PythonにPATHが通っていない | Pythonを再インストール時に「Add to PATH」にチェック |
| `ModuleNotFoundError: No module named 'feedparser'` | ライブラリ未インストール | 仮想環境を有効化して `pip install -r requirements.txt` |
| Discordに投稿されない / `Discord投稿エラー` | Webhook URLが間違い／チャンネル削除 | Webhook URLを再確認。ブラウザでURLを開きエラーが出ないか確認 |
| 翻訳されない（英語のまま） | APIキー誤り／残高不足／翻訳が無効 | APIキーを確認。`settings.json` の `translation.enabled` を確認 |
| `401 Unauthorized`（翻訳時） | Claude APIキーが無効 | console.anthropic.com でキーを再発行 |
| `429`（Discord/翻訳） | レート制限 | 自動で待機・再試行します。頻発する場合は投稿件数を減らす |
| 特定サイトだけ `取得失敗` | サイト側の仕様変更／RSS廃止 | そのフィードを `enabled:false` にするか、URLを修正 |
| バッチ実行で文字化け | コンソールの文字コード | `run_news_bot.bat` 内で `chcp 65001` 済み。ログファイルで内容確認可 |
| タスクスケジューラーで動かない | 「開始（オプション）」未設定 | 操作の「開始（オプション）」にプロジェクトフォルダのパスを設定 |

### ログの確認

実行のたびに `logs/ai_news_digest_YYYY-MM-DD.log` が作られます。
うまく動かないときは、まずこのログを開いてエラー内容を確認してください。

---

## 📁 ファイル構成

```text
ai-news-digest/
├─ main.py                 … メイン処理（実行の入口）
├─ requirements.txt        … 必要ライブラリ一覧
├─ .env.example            … 環境変数のサンプル（コピーして .env を作る）
├─ run_news_bot.bat        … タスクスケジューラー用の起動バッチ
├─ README.md               … このファイル
├─ config/
│  ├─ feeds.json           … 情報源リスト（取得先の設定）
│  └─ settings.json        … 動作設定（件数・色・翻訳など）
├─ data/
│  └─ posted_articles.json … 投稿済み記録（重複防止用・自動更新）
└─ src/
   ├─ news_fetcher.py      … ニュース取得
   ├─ translator.py        … Claude APIによる翻訳
   ├─ discord_poster.py    … Discord投稿（曜日カラー含む）
   ├─ storage.py           … 重複投稿防止
   ├─ config_loader.py     … 設定・.env読み込み
   └─ utils.py             … 共通処理（ログ・言語判定など）
```

---

## 💡 補足

- 翻訳には [Claude Haiku](https://www.anthropic.com/) など軽量モデルを既定で使用しており、1日数十件程度なら費用はごくわずかです。費用を完全にゼロにしたい場合は `settings.json` の `translation.enabled` を `false` にしてください（英語のまま投稿されます）。
- APIキー・Webhook URLは絶対に他人へ共有しないでください。
