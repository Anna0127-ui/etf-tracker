import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# 1. 網頁基本設定
st.set_page_config(
    page_title="ETF 逢低加碼與個人資產試算儀表板", page_icon="📈", layout="centered"
)

st.title("📈 ETF 逢低加碼與個人資產試算系統")
st.caption("結合「最適加碼細節 + 大盤趨勢 + 個人扣款明細記帳 + 逢低加碼模擬器」")


# 2. 數據抓取
@st.cache_data(ttl=3600)
def load_data(symbol):
    df = yf.download(symbol, period="2y", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


market_df = load_data("^TWII")

stock_input = st.text_input("請輸入台股代碼 (例如: 0050, 00878, 2330)", value="0050")
ticker = stock_input.strip()

if not ticker.endswith(".TW") and not ticker.endswith(".TWO"):
    ticker_symbol = f"{ticker}.TW"
else:
    ticker_symbol = ticker

df = load_data(ticker_symbol)

if df.empty:
    st.error(
        f"❌ 查無代碼 `{ticker}` 的數據，請確認代碼是否正確（例如：0050 或 00878）。"
    )
else:
    # --- 指標計算 ---
    df["MA60"] = df["Close"].rolling(window=60).mean()
    df["MA240"] = df["Close"].rolling(window=240).mean()

    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["RSI14"] = 100 - (100 / (1 + rs))

    latest_price = df["Close"].iloc[-1]
    ma60 = df["MA60"].iloc[-1]
    ma240 = df["MA240"].iloc[-1]
    rsi14 = df["RSI14"].iloc[-1]

    high_6m = df["High"].iloc[-120:].max()
    pullback_pct = ((latest_price - high_6m) / high_6m) * 100

    first_day_month_price = (
        df[df.index.month == df.index[-1].month]["Close"].iloc[0]
    )
    monthly_change_pct = (
        (latest_price - first_day_month_price) / first_day_month_price
    ) * 100

    # 大盤指標
    market_df["MA60"] = market_df["Close"].rolling(window=60).mean()
    market_latest = market_df["Close"].iloc[-1]
    market_ma60 = market_df["MA60"].iloc[-1]

    m_delta = market_df["Close"].diff()
    m_gain = (m_delta.where(m_delta > 0, 0)).rolling(window=14).mean()
    m_loss = (-m_delta.where(m_delta < 0, 0)).rolling(window=14).mean()
    m_rs = m_gain / m_loss
    market_rsi14 = (100 - (100 / (1 + m_rs))).iloc[-1]

    # --- 得分計算 ---
    s_pullback = (
        35 if pullback_pct <= -10 else (25 if pullback_pct <= -8 else (10 if pullback_pct <= -5 else 0))
    )
    s_rsi = 25 if rsi14 < 30 else (10 if rsi14 < 40 else 0)
    s_ma = 20 if latest_price < ma240 else (10 if latest_price < ma60 else 0)
    s_market = (
        20 if market_rsi14 < 35 else (10 if market_latest < market_ma60 else 0)
    )
    total_score = s_pullback + s_rsi + s_ma + s_market

    # --- 頂部總覽 ---
    st.subheader("🌐 大盤與個股總覽")
    m1, m2 = st.columns(2)
    m1.metric(
        label="加權指數 (大盤現價)",
        value=f"{market_latest:,.0f} 點",
        delta="大盤跌破季線 ⚠️" if market_latest < market_ma60 else "大盤在季線上 🟢",
        delta_color="inverse" if market_latest < market_ma60 else "normal",
    )
    m2.metric(
        label="大盤 14日 RSI 恐慌度",
        value=f"{market_rsi14:.1f}",
        delta="進入恐慌區 🚨" if market_rsi14 < 35 else "情緒正常 ⚪",
        delta_color="inverse" if market_rsi14 < 35 else "off",
    )

    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    col1.metric(
        label=f"{ticker} 最新股價",
        value=f"${latest_price:.2f}",
        delta=f"{monthly_change_pct:+.2f}% (當月)",
    )
    col2.metric(label="14日 RSI 指標", value=f"{rsi14:.1f}")
    col3.metric(
        label="60日季線",
        value=f"${ma60:.2f}",
        delta="跌破 ⚠️" if latest_price < ma60 else "線上 🟢",
        delta_color="inverse" if latest_price < ma60 else "normal",
    )

    # --- 加碼最適時間 ---
    st.markdown("---")
    st.subheader("🚨 當前是否為「加碼最適時間」？")

    s_col1, s_col2 = st.columns([1, 2])
    s_col1.metric(label="加碼最適時機指數", value=f"{total_score} / 100 分")

    if total_score >= 75:
        s_col2.success(
            "🟢 **【極佳加碼時機！】**\n\n個股深度拉回 + 大盤同步修正恐慌。建議動用加碼預備金買入！"
        )
    elif total_score >= 45:
        s_col2.warning(
            "🟡 **【適度關注 / 適合分批小額加碼】**\n\n市場已出現部分修正訊號，可準備好預備金或先投入小額試水溫。"
        )
    else:
        s_col2.info(
            "⚪ **【觀望期（維持定期定額）】**\n\n未達顯著低點與安全邊際，請保持原本的「定期定額」固定扣款即可。"
        )

    st.markdown("##### 📝 各項加碼指標得分明細：")
    d1, d2, d3, d4 = st.columns(4)
    d1.metric(
        label="高點拉回",
        value=f"{s_pullback} / 35分",
        delta=f"拉回 {pullback_pct:.1f}%",
    )
    d2.metric(label="個股恐慌", value=f"{s_rsi} / 25分", delta=f"RSI {rsi14:.1f}")
    d3.metric(
        label="季線/年線",
        value=f"{s_ma} / 20分",
        delta="破季線/年線" if s_ma > 0 else "線上",
    )
    d4.metric(
        label="大盤環境",
        value=f"{s_market} / 20分",
        delta="大盤同步修正" if s_market > 0 else "大盤正常",
    )

    # ==========================================
    # 🎯 升級 1：個人定期定額買入歷史明細記帳表
    # ==========================================
    st.markdown("---")
    st.subheader("📝 個人每月定期定額買入明細與資產彙整")

    with st.expander(
        "📂 點擊展開 / 點擊表格可直接新增、修改您的買入價格與股數", expanded=True
    ):
        # 初始化預設表格數據 (提供範例資料)
        if "dca_records" not in st.session_state:
            st.session_state.dca_records = pd.DataFrame(
                [
                    {"買入日期": "2024-01-02", "買入單價": 22.50, "買入股數": 66},
                    {"買入日期": "2024-02-01", "買入單價": 22.80, "買入股數": 65},
                    {"買入日期": "2024-03-01", "買入單價": 23.10, "買入股數": 64},
                    {"買入日期": "2024-04-01", "買入單價": 22.20, "買入股數": 67},
                ]
            )

        st.caption("💡 可在下方表格直接點擊編輯數值，或點選表格下方 `+` 新增扣款紀錄：")

        # 使用可編輯表格 st.data_editor
        edited_df = st.data_editor(
            st.session_state.dca_records,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "買入日期": st.column_config.TextColumn("扣款日期"),
                "買入單價": st.column_config.NumberColumn(
                    "買入成交單價 ($)", format="$%.2f", min_value=0.0
                ),
                "買入股數": st.column_config.NumberColumn(
                    "成交股數 (股)", format="%d 股", min_value=0
                ),
            },
        )

        # 計算歷史扣款總數據
        edited_df["單筆投入金額"] = edited_df["買入單價"] * edited_df["買入股數"]
        total_dca_principal = edited_df["單筆投入金額"].sum()
        total_dca_shares = edited_df["買入股數"].sum()
        avg_dca_cost = (
            total_dca_principal / total_dca_shares
            if total_dca_shares > 0
            else 0
        )

        current_dca_value = total_dca_shares * latest_price
        dca_profit = current_dca_value - total_dca_principal
        dca_roi = (
            (dca_profit / total_dca_principal) * 100
            if total_dca_principal > 0
            else 0
        )

        st.markdown("#### 📊 個人歷史買入統計總覽：")
        a1, a2, a3 = st.columns(3)
        a1.metric(
            label="累積總投入本金", value=
