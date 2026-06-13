@echo off
rem =====================================================================
rem  AI News Digest 起動用バッチファイル
rem  Windowsタスクスケジューラーから、このファイルを実行してください。
rem
rem  処理内容:
rem    1. このバッチがある場所（プロジェクトフォルダ）へ移動
rem    2. 仮想環境(.venv)を有効化
rem    3. main.py を実行
rem  ※ 文字化け防止のため出力コードページをUTF-8(65001)にしています。
rem =====================================================================

chcp 65001 > nul

rem --- 1. プロジェクトディレクトリへ移動（%~dp0 = このバッチがあるフォルダ） ---
cd /d "%~dp0"

rem --- 2. 仮想環境を有効化 ---
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else (
    echo [警告] 仮想環境 .venv が見つかりません。グローバルのPythonで実行します。
    echo        セットアップ手順は README.md を参照してください。
)

rem --- 3. スクリプト実行 ---
python main.py

rem --- 終了コードを引き継ぐ（タスクスケジューラーで成否を判定できるように） ---
exit /b %ERRORLEVEL%
