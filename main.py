# ============================================================
# 🤖 STEP8：日本株AI投資チェック → LINE自動通知
# GitHub Actions版
# ============================================================

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
import yfinance as yf


# ============================================================
# ① LINE認証情報
#    GitHub Secretsから取得
# ============================================================

LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")


if not LINE_TOKEN:
    raise ValueError(
        "❌ LINE_CHANNEL_ACCESS_TOKEN が "
        "GitHub Secretsに登録されていません。"
    )

if not LINE_USER_ID:
    raise ValueError(
        "❌ LINE_USER_ID が "
        "GitHub Secretsに登録されていません。"
    )

print("✅ LINE認証情報を読み込みました")


# ============================================================
# ② 監視する20銘柄
# ============================================================

TICKERS = {
    "9432.T": "NTT",
    "8306.T": "三菱UFJフィナンシャルG",
    "7203.T": "トヨタ自動車",
    "8591.T": "オリックス",
    "9433.T": "KDDI",
    "8058.T": "三菱商事",
    "8001.T": "伊藤忠商事",
    "8766.T": "東京海上HD",
    "4502.T": "武田薬品",
    "4063.T": "信越化学",
    "8035.T": "東京エレクトロン",
    "6857.T": "アドバンテスト",
    "6501.T": "日立製作所",
    "6758.T": "ソニーG",
    "6594.T": "ニデック",
    "2914.T": "JT",
    "3382.T": "セブン＆アイ",
    "2802.T": "味の素",
    "4901.T": "富士フイルム",
    "9020.T": "JR東日本",
}


# ============================================================
# ③ RSI計算
# ============================================================

def calculate_rsi(series, period=14):

    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    rsi = 100 - (100 / (1 + rs))

    return rsi


# ============================================================
# ④ 80点満点のAIスコア計算
#
# MA5乖離       最大20点
# MA25乖離      最大20点
# 日次下落率    最大10点
# RSI           最大20点
# 出来高倍率     最大10点
#
# 合計80点
# ============================================================

def calculate_score(
    deviation5,
    deviation25,
    daily_change,
    rsi,
    volume_ratio,
):

    score = 0

    # --------------------------------------------------------
    # MA5乖離：最大20点
    # --------------------------------------------------------

    if deviation5 <= -5:
        score += 20

    elif deviation5 <= -3:
        score += 15

    elif deviation5 <= -1:
        score += 10

    elif deviation5 < 0:
        score += 5


    # --------------------------------------------------------
    # MA25乖離：最大20点
    # --------------------------------------------------------

    if deviation25 <= -8:
        score += 20

    elif deviation25 <= -5:
        score += 15

    elif deviation25 <= -2:
        score += 10

    elif deviation25 < 0:
        score += 5


    # --------------------------------------------------------
    # 日次変化率：最大10点
    # --------------------------------------------------------

    if daily_change <= -3:
        score += 10

    elif daily_change <= -1:
        score += 7

    elif daily_change < 0:
        score += 4


    # --------------------------------------------------------
    # RSI：最大20点
    # --------------------------------------------------------

    if rsi <= 30:
        score += 20

    elif rsi <= 40:
        score += 15

    elif rsi <= 50:
        score += 8


    # --------------------------------------------------------
    # 出来高倍率：最大10点
    # --------------------------------------------------------

    if volume_ratio >= 1.5:
        score += 10

    elif volume_ratio >= 1.2:
        score += 7

    elif volume_ratio >= 1.0:
        score += 3


    return score


# ============================================================
# ⑤ LINE送信
# ============================================================

def send_line_message(message):

    url = "https://api.line.me/v2/bot/message/push"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}",
    }

    data = {
        "to": LINE_USER_ID,
        "messages": [
            {
                "type": "text",
                "text": message,
            }
        ],
    }

    try:

        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=30,
        )

    except requests.RequestException as e:

        print("❌ LINE送信中に通信エラーが発生しました")
        print(e)

        return False


    if response.status_code == 200:

        print("✅ LINE送信成功")

        return True


    print("❌ LINE送信失敗")
    print("Status:", response.status_code)
    print(response.text)

    return False


# ============================================================
# ⑥ 日本時間取得
# ============================================================

def get_japan_time():

    jst = ZoneInfo("Asia/Tokyo")

    return datetime.now(jst)


# ============================================================
# ⑦ 1銘柄を分析
# ============================================================

def analyze_stock(ticker, name):

    print(
        f"📊 {name} ({ticker}) を分析中..."
    )


    # --------------------------------------------------------
    # 株価データ取得
    # --------------------------------------------------------

    hist = yf.download(
        ticker,
        period="6mo",
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
    )


    # --------------------------------------------------------
    # データが空
    # --------------------------------------------------------

    if hist.empty:

        print(
            f"⚠️ {name}: データ取得失敗"
        )

        return None


    # --------------------------------------------------------
    # MultiIndex対策
    # --------------------------------------------------------

    if isinstance(
        hist.columns,
        pd.MultiIndex
    ):

        hist.columns = (
            hist.columns
            .get_level_values(0)
        )


    # --------------------------------------------------------
    # 必要データ確認
    # --------------------------------------------------------

    required_columns = [
        "Close",
        "Volume",
    ]

    if not all(
        col in hist.columns
        for col in required_columns
    ):

        print(
            f"⚠️ {name}: 必要データなし"
        )

        return None


    # --------------------------------------------------------
    # 終値・出来高
    # --------------------------------------------------------

    close = (
        pd.to_numeric(
            hist["Close"],
            errors="coerce"
        )
        .dropna()
    )

    volume = (
        pd.to_numeric(
            hist["Volume"],
            errors="coerce"
        )
        .dropna()
    )


    # --------------------------------------------------------
    # データ数確認
    # --------------------------------------------------------

    if len(close) < 30:

        print(
            f"⚠️ {name}: データ不足"
        )

        return None


    # ========================================================
    # 移動平均
    # ========================================================

    ma5 = close.rolling(5).mean()

    ma25 = close.rolling(25).mean()


    # ========================================================
    # RSI
    # ========================================================

    rsi_series = calculate_rsi(
        close,
        14
    )


    # ========================================================
    # 現在値
    # ========================================================

    current_price = float(
        close.iloc[-1]
    )


    # ========================================================
    # MA5 / MA25
    # ========================================================

    current_ma5 = float(
        ma5.iloc[-1]
    )

    current_ma25 = float(
        ma25.iloc[-1]
    )


    # ========================================================
    # MA乖離率
    # ========================================================

    deviation5 = (
        (
            current_price /
            current_ma5
        ) - 1
    ) * 100


    deviation25 = (
        (
            current_price /
            current_ma25
        ) - 1
    ) * 100


    # ========================================================
    # 前日比
    # ========================================================

    if len(close) >= 2:

        previous_price = float(
            close.iloc[-2]
        )

        daily_change = (
            (
                current_price /
                previous_price
            ) - 1
        ) * 100

    else:

        daily_change = 0


    # ========================================================
    # RSI
    # ========================================================

    current_rsi = float(
        rsi_series.iloc[-1]
    )


    # ========================================================
    # 出来高倍率
    #
    # 現在の出来高
    # ÷ 過去20営業日の平均出来高
    #
    # 当日の出来高は平均計算から除外
    # ========================================================

    if len(volume) >= 21:

        current_volume = float(
            volume.iloc[-1]
        )

        average_volume20 = float(
            volume.iloc[-21:-1].mean()
        )

        if average_volume20 > 0:

            volume_ratio = (
                current_volume /
                average_volume20
            )

        else:

            volume_ratio = 0

    else:

        volume_ratio = 0


    # ========================================================
    # スコア計算
    # ========================================================

    score = calculate_score(

        deviation5,

        deviation25,

        daily_change,

        current_rsi,

        volume_ratio,

    )


    # ========================================================
    # 結果保存
    # ========================================================

    result = {

        "ticker": ticker,

        "name": name,

        "price": current_price,

        "ma5": current_ma5,

        "ma25": current_ma25,

        "deviation5": deviation5,

        "deviation25": deviation25,

        "daily_change": daily_change,

        "rsi": current_rsi,

        "volume_ratio": volume_ratio,

        "score": score,

    }


    print(
        f"   → {score}点 "
        f"(株価 {current_price:.1f}円)"
    )


    return result


# ============================================================
# ⑧ メイン処理
# ============================================================

def daily_ai_check():

    print("=" * 60)

    print(
        "🤖 日本株AI投資チェック開始"
    )

    print("=" * 60)


    # ========================================================
    # 日本時間
    # ========================================================

    now_jst = get_japan_time()

    date_str = now_jst.strftime(
        "%Y/%m/%d %H:%M"
    )

    print(
        "🇯🇵 日本時間:",
        date_str
    )


    # ========================================================
    # 結果格納
    # ========================================================

    results = []


    # ========================================================
    # 20銘柄を分析
    # ========================================================

    for ticker, name in TICKERS.items():

        try:

            result = analyze_stock(
                ticker,
                name
            )

            if result is not None:

                results.append(result)


        except Exception as e:

            print(
                f"❌ {name}: エラー"
            )

            print(
                type(e).__name__,
                e
            )

            continue


    # ========================================================
    # 分析結果確認
    # ========================================================

    if not results:

        print(
            "❌ 分析できた銘柄がありません。"
        )

        raise RuntimeError(
            "全銘柄の分析に失敗しました。"
        )


    # ========================================================
    # DataFrame化
    # ========================================================

    df = pd.DataFrame(
        results
    )


    # ========================================================
    # スコア順に並べる
    # ========================================================

    df = df.sort_values(
        "score",
        ascending=False
    ).reset_index(
        drop=True
    )


    # ========================================================
    # 80点シグナル
    # ========================================================

    signals_80 = df[
        df["score"] == 80
    ].copy()


    # ========================================================
    # 70～79点
    # ========================================================

    signals_70_79 = df[
        (df["score"] >= 70)
        &
        (df["score"] <= 79)
    ].copy()


    # ========================================================
    # TOP5
    # ========================================================

    top5 = df.head(5)


    # ========================================================
    # LINEメッセージ作成
    # ========================================================

    message = ""


    message += (
        "🤖 【日本株AI投資チェック】\n\n"
    )


    message += (
        f"📅 {date_str}\n"
    )


    message += (
        "━━━━━━━━━━━━━━\n\n"
    )


    # ========================================================
    # 80点シグナル
    # ========================================================

    if len(signals_80) > 0:

        message += (
            f"🔥 【80点シグナル："
            f"{len(signals_80)}銘柄】\n\n"
        )


        for _, row in signals_80.iterrows():

            message += (
                f"🔥 {row['name']} "
                f"【80点】\n"
            )


            message += (
                f"株価："
                f"{row['price']:.1f}円\n"
            )


            message += (
                f"MA5乖離："
                f"{row['deviation5']:.2f}%\n"
            )


            message += (
                f"MA25乖離："
                f"{row['deviation25']:.2f}%\n"
            )


            message += (
                f"日次変化："
                f"{row['daily_change']:.2f}%\n"
            )


            message += (
                f"RSI："
                f"{row['rsi']:.1f}\n"
            )


            message += (
                f"出来高倍率："
                f"{row['volume_ratio']:.2f}倍\n"
            )


            message += (
                "➡️ 強い買いシグナル\n"
            )


            message += (
                "➡️ 購入倍率は資金状況を見て判断\n\n"
            )


    else:

        message += (
            "⏸️ 本日は80点シグナルなし\n\n"
        )


    # ========================================================
    # 70～79点
    # ========================================================

    message += (
        "📊 【70～79点の候補】\n"
    )


    if len(signals_70_79) > 0:

        for _, row in signals_70_79.iterrows():

            message += (
                f"・{row['name']}："
                f"{row['score']}点\n"
            )


    else:

        message += (
            "該当銘柄なし\n"
        )


    message += "\n"


    # ========================================================
    # TOP5
    # ========================================================

    message += (
        "🏆 【本日のTOP5】\n"
    )


    for i, (_, row) in enumerate(
        top5.iterrows(),
        start=1
    ):

        message += (
            f"{i}. {row['name']}："
            f"{row['score']}点\n"
        )


    message += "\n"


    message += (
        "━━━━━━━━━━━━━━\n\n"
    )


    # ========================================================
    # 注意書き
    # ========================================================

    message += (
        "💡 AIは注文を実行しません。\n"
        "購入するか・何株買うかは自分で判断。\n"
    )


    message += (
        "⚠️ 80点でも損失になる場合があります。\n"
    )


    # ========================================================
    # LINE送信
    # ========================================================

    print("\n")

    print("=" * 60)

    print(
        "📱 LINE通知を送信します"
    )

    print("=" * 60)

    print()

    print(message)


    success = send_line_message(
        message
    )


    if not success:

        raise RuntimeError(
            "❌ LINE通知に失敗しました。"
        )


    # ========================================================
    # 結果表示
    # ========================================================

    print("\n")

    print("=" * 60)

    print(
        "🏆 本日のTOP5"
    )

    print("=" * 60)


    for i, (_, row) in enumerate(
        top5.iterrows(),
        start=1
    ):

        print(
            f"{i}. "
            f"{row['name']} "
            f"{row['score']}点 "
            f"株価{row['price']:.1f}円"
        )


    print("\n")

    print("=" * 60)

    print(
        "✅ STEP8 完了"
    )

    print("=" * 60)


    return df


# ============================================================
# ⑨ プログラム実行
# ============================================================

if __name__ == "__main__":

    daily_ai_check()
