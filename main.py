name: 🤖 日本株AI投資チェック

on:

  # GitHub Actions画面から手動実行できるようにする
  workflow_dispatch:

  # 毎日自動実行
  schedule:

    # UTC 02:30
    # = 日本時間 11:30
    - cron: "30 2 * * 1-5"


jobs:

  daily-check:

    runs-on: ubuntu-latest


    steps:

      # ------------------------------------------------------
      # ① GitHubリポジトリを取得
      # ------------------------------------------------------

      - name: 📥 Checkout repository

        uses: actions/checkout@v4


      # ------------------------------------------------------
      # ② Pythonセットアップ
      # ------------------------------------------------------

      - name: 🐍 Setup Python

        uses: actions/setup-python@v5

        with:

          python-version: "3.11"


      # ------------------------------------------------------
      # ③ ライブラリインストール
      # ------------------------------------------------------

      - name: 📦 Install dependencies

        run: |

          python -m pip install --upgrade pip

          pip install -r requirements.txt


      # ------------------------------------------------------
      # ④ AI投資チェック実行
      # ------------------------------------------------------

      - name: 🤖 Run AI investment check

        env:

          LINE_CHANNEL_ACCESS_TOKEN: ${{ secrets.LINE_CHANNEL_ACCESS_TOKEN }}

          LINE_USER_ID: ${{ secrets.LINE_USER_ID }}

        run: |

          python main.py
