import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# 1. 網頁基本設定
st.set_page_config(
    page_title="ETF 逢低加碼與資產試算儀表板", page_icon="📈", layout="centered"
)

st.title("📈 ETF 逢低加碼與資產試算觀察系統")
st.caption("結合「最適加碼細節 + 大盤趨勢 + 定期定額歷史扣款模擬」")


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

    # --- 各項得分詳細計算 ---
    s_pullback = 0
    if pullback_pct <= -10:
        s_pullback = 35
    elif pullback_pct <= -8:
        s_pullback = 25
    elif pullback_pct <= -5:
        s_pullback = 10

    s_rsi = 0
    if rsi14 < 30:
        s_rsi = 25
    elif rsi14 < 40:
        s_rsi = 10

    s_ma = 0
    if latest_price < ma240:
        s_ma = 20
    elif latest_price < ma60:
        s_ma = 10

    s_market = 0
    if market_rsi14 < 35:
        s_market = 20
    elif market_latest < market_ma60:
        s_market = 10

    total_score = s_pullback + s_rsi + s_ma + s_market

    # --- 頂部大盤與個股卡片 ---
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

    # --- 🎯 升級：基於真實歷史股價變化的定期定額與配息試算 ---
    st.markdown("---")
    st.subheader("💰 定期定額歷史扣款與資產試算")

    with st.expander("🧮 點擊展開 / 輸入個人扣款參數與歷史對照", expanded=True):
        c1, c2, c3 = st.columns(3)
        monthly_dca = c1.number_input(
            "每月定期定額金額 (台幣)", value=1500, step=500
        )
        months_count = c2.number_input(
            "已持續扣款月數",
            value=12,
            min_value=1,
            max_value=24,
            step=1,
        )
        extra_buys_count = c3.number_input(
            "逢低加碼執行次數 (每次 $1,500)",
            value=2,
            min_value=0,
            step=1,
        )

        default_yield = 6.5 if "00878" in ticker else 2.5
        est_yield_pct = st.slider(
            "預估年化殖利率 (%)",
            min_value=1.0,
            max_value=10.0,
            value=default_yield,
            step=0.5,
        )

        # === 核心升級：抓取歷史每個月的第一個交易日股價進行精準模擬 ===
        monthly_df = df.resample("MS").first().iloc[-months_count:]
        monthly_prices = monthly_df["Close"]

        # 計算定期定額累積零股數
        dca_shares_list = [monthly_dca / p for p in monthly_prices]
        total_dca_shares = sum(dca_shares_list)

        # 假設逢低加碼買在近期較低點（以近半年低點均價計算）
        recent_low_avg = (
            df["Low"].iloc[-120:].min() + df["Close"].iloc[-120:].mean()
        ) / 2
        extra_shares = (
            (monthly_dca * extra_buys_count) / recent_low_avg
            if recent_low_avg > 0
            else 0
        )

        # 總統計數據
        total_principal = (monthly_dca * months_count) + (
            monthly_dca * extra_buys_count
        )
        total_shares = total_dca_shares + extra_shares
        avg_cost_price = (
            total_principal / total_shares if total_shares > 0 else 0
        )

        est_current_value = total_shares * latest_price
        est_profit = est_current_value - total_principal
        est_roi = (
            (est_profit / total_principal) * 100 if total_principal > 0 else 0
        )

        # 預估配息
        est_annual_dividend = est_current_value * (est_yield_pct / 100)
        est_quarterly_dividend = est_annual_dividend / 4

        st.markdown("#### 📊 依歷史股價真實模擬結果：")
        r1, r2, r3 = st.columns(3)
        r1.metric(label="總投入本金", value=f"${total_principal:,.0f} 元")
        r2.metric(label="累積持股數量", value=f"{total_shares:,.1f} 股")
        r3.metric(label="您的真實平均成本", value=f"${avg_cost_price:.2f} 元")

        st.markdown("---")
        r4, r5, r6 = st.columns(3)
        r4.metric(label="目前預估總市值", value=f"${est_current_value:,.0f} 元")
        r5.metric(
            label="累積投資損益",
            value=f"${est_profit:+,.0f} 元",
            delta=f"{est_roi:+.2f}% 報酬率",
        )
        r6.metric(
            label="預估每年可領配息",
            value=f"${est_annual_dividend:,.0f} 元",
            delta=f"每季約 ${est_quarterly_dividend:,.0f} 元",
        )

    # --- 6. 走勢圖表 (可折疊) ---
    st.markdown("---")
    with st.expander("📉 點擊展開 / 折疊 K 線與均線走勢圖表"):
        chart_df = df.iloc[-120:]
        fig = go.Figure()

        fig.add_trace(
            go.Candlestick(
                x=chart_df.index,
                open=chart_df["Open"],
                high=chart_df["High"],
                low=chart_df["Low"],
                close=chart_df["Close"],
                name="K線",
                increasing_line_color="red",
                increasing_fillcolor="red",
                decreasing_line_color="green",
                decreasing_fillcolor="green",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=chart_df.index,
                y=chart_df["MA60"],
                line=dict(color="orange", width=1.5),
                name="60日季線",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=chart_df.index,
                y=chart_df["MA240"],
                line=dict(color="blue", width=2.0),
                name="240日年線",
            )
        )

        fig.update_layout(
            xaxis_rangeslider_visible=False,
            height=400,
            margin=dict(l=10, r=10, t=10, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)
