@echo off
rem =====================================================================
rem  AI News Digest 起動用バッチファイル
rem  Windowsタスクスケジューラーから、このファイルを実行してください。
rem
rem  処理内容:
rem    1. このバッチがある場所（プロジェクトフォルダ）へ移動
rem    2. 仮想環境(.venv)のPythonを直接呼び出す（PATHに依存しない）
rem    3. .venv が無ければ py ランチャー → python の順でフォールバック
rem  ※ 文字化け防止のため出力コードページをUTF-8(65001)にしています。
rem =====================================================================

chcp 65001 > nul

rem --- 1. プロジェクトディレクトリへ移動（%~dp0 = このバッチがあるフォルダ） ---
cd /d "%~dp0"

rem --- 2. 使用するPython実行ファイルを決定 ---
rem     仮想環境のpython.exeを「直接」指定する。activateを使わないため、
rem     タスクスケジューラーの実行アカウントのPATH設定に左右されない。
set "PYEXE="
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYEXE=%~dp0.venv\Scripts\python.exe"
    goto :run
)

echo [警告] 仮想環境 .venv が見つかりません: %~dp0.venv
echo        サーバー上で次を実行して仮想環境を作成してください:
echo            py -m venv .venv
echo            .venv\Scripts\python.exe -m pip install -r requirements.txt
echo.
echo        グローバルのPythonで実行を試みます...

rem --- フォールバック1: py ランチャー（System32にあるためPATHが通りやすい） ---
where py >nul 2>nul
if %ERRORLEVEL%==0 (
    set "PYEXE=py"
    goto :run
)

rem --- フォールバック2: python コマンド ---
where python >nul 2>nul
if %ERRORLEVEL%==0 (
    set "PYEXE=python"
    goto :run
)

rem --- どのPythonも見つからない ---
echo [エラー] Python が見つかりません（py / python のいずれも未検出）。
echo          Python を「全ユーザー向け」かつ「Add to PATH」でインストールするか、
echo          サーバー上で仮想環境 .venv を作成してください。
exit /b 9009

:run
echo 使用するPython: %PYEXE%
"%PYEXE%" main.py

rem --- 終了コードを引き継ぐ（タスクスケジューラーで成否を判定できるように） ---
exit /b %ERRORLEVEL%
