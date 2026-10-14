import json
import os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# 1. 網頁基本設定
st.set_page_config(
    page_title="ETF 逢低加碼與資產試算儀表板", page_icon="📈", layout="centered"
)

st.title("📈 ETF 逢低加碼與資產試算觀察系統")
st.caption(
    "結合「動態加碼額度建議 + 大盤環境 + 分別儲存不同 ETF 紀錄 + 逢低加碼模擬」"
)

DATA_FILE = "dca_records_storage.json"


def load_all_records():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_all_records(records_dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(records_dict, f, ensure_ascii=False, indent=2)


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
ticker_symbol = (
    ticker
    if (ticker.endswith(".TW") or ticker.endswith(".TWO"))
    else f"{ticker}.TW"
)

df = load_data(ticker_symbol)

if df.empty:
    st.error(
        f"❌ 查無代碼 `{ticker}` 的數據，請確認代碼是否正確（例如：0050 或 00878）。"
    )
else:
    # 判斷標的類型
    high_dividend_list = ["00878", "0056", "00919", "00929", "00713", "00940"]
    is_high_dividend = any(hd in ticker for hd in high_dividend_list)

    if is_high_dividend:
        etf_type_str = "高股息型 ETF (波動較小，採靈敏加碼門檻)"
    else:
        etf_type_str = "市值型 ETF / 一般股票 (含 0050 小跌即觸發加碼門檻)"

    # 技術指標計算
    df["MA60"] = df["Close"].rolling(60).mean()
    df["MA240"] = df["Close"].rolling(240).mean()

    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["RSI14"] = 100 - (100 / (1 + rs))

    latest_price = float(df["Close"].iloc[-1])
    ma60 = float(df["MA60"].iloc[-1])
    ma240 = float(df["MA240"].iloc[-1])
    rsi14 = float(df["RSI14"].iloc[-1])

    high_6m = float(df["High"].iloc[-120:].max())
    pullback_pct = ((latest_price - high_6m) / high_6m) * 100

    first_day_month = df[df.index.month == df.index[-1].month]["Close"].iloc[0]
    monthly_change_pct = (
        (latest_price - first_day_month) / first_day_month
    ) * 100

    # 大盤指標
    market_df["MA60"] = market_df["Close"].rolling(60).mean()
    market_latest = float(market_df["Close"].iloc[-1])
    market_ma60 = float(market_df["MA60"].iloc[-1])

    m_delta = market_df["Close"].diff()
    m_gain = (m_delta.where(m_delta > 0, 0)).rolling(14).mean()
    m_loss = (-m_delta.where(m_delta < 0, 0)).rolling(14).mean()
    m_rs = m_gain / m_loss
    market_rsi14 = float((100 - (100 / (1 + m_rs))).iloc[-1])

    # 得分邏輯（含 0050 小跌即觸發）
    if pullback_pct <= -8:
        s_pullback = 35
        desc_pullback = f"現價 ${latest_price:.2f} 距高點 ${high_6m:.2f} 拉回 {pullback_pct:.1f}% (顯著拉回特價區)"
    elif pullback_pct <= -5:
        s_pullback = 25
        desc_pullback = f"現價 ${latest_price:.2f} 距高點 ${high_6m:.2f} 拉回 {pullback_pct:.1f}% (中小幅修正)"
    elif pullback_pct <= -3:
        s_pullback = 15
        desc_pullback = f"現價 ${latest_price:.2f} 距高點 ${high_6m:.2f} 拉回 {pullback_pct:.1f}% (微幅回檔，適合小額加碼)"
    else:
        s_pullback = 0
        desc_pullback = f"現價 ${latest_price:.2f} 距高點 ${high_6m:.2f} 拉回 {pullback_pct:.1f}% (處於相對高檔)"

    if rsi14 < 30:
        s_rsi = 25
        desc_rsi = f"當前 RSI 為 {rsi14:.1f} (進入 <30 極度恐慌區)"
    elif rsi14 < 40:
        s_rsi = 10
        desc_rsi = f"當前 RSI 為 {rsi14:.1f} (進入 <40 相對低檔區)"
    else:
        s_rsi = 0
        desc_rsi = f"當前 RSI 為 {rsi14:.1f} (市場情緒正常)"

    if latest_price < ma240:
        s_ma = 20
        desc_ma = (
            f"現價 ${latest_price:.2f} < 年線 ${ma240:.2f} (跌破 240日長線支撐)"
        )
    elif latest_price < ma60:
        s_ma = 10
        desc_ma = (
            f"現價 ${latest_price:.2f} < 季線 ${ma60:.2f} (跌破 60日中線支撐)"
        )
    else:
        s_ma = 0
        desc_ma = f"現價 ${latest_price:.2f} 高於季線 ${ma60:.2f} 與年線 ${ma240:.2f}"

    if market_rsi14 < 35:
        s_market = 20
        desc_market = (
            f"大盤 RSI 為 {market_rsi14:.1f} (全市場恐慌，大盤性加碼點)"
        )
    elif market_latest < market_ma60:
        s_market = 10
        desc_market = f"加權指數 {market_latest:,.0f} 跌破季線 {market_ma60:,.0f} (大盤回檔)"
    else:
        s_market = 0
        desc_market = f"大盤指數 {market_latest:,.0f} 位於季線上，市場穩定"

    total_score = s_pullback + s_rsi + s_ma + s_market

    # 計算建議加碼金額 (1000 - 5000 元)
    if total_score >= 80:
        suggested_amount = 5000
        signal_status = "🟢 【極佳加碼時機】"
        signal_msg = f"多重低點指標同時觸發！建議動用預備金 **${suggested_amount:,} 元** 進行單筆加碼。"
    elif total_score >= 65:
        suggested_amount = 4000
        signal_status = "🟢 【顯著加碼時機】"
        signal_msg = f"修正趨勢明確，建議投入 **${suggested_amount:,} 元** 積極建立低檔部位。"
    elif total_score >= 50:
        suggested_amount = 3000
        signal_status = "🟡 【適度加碼時機】"
        signal_msg = f"市場出現小幅拉回（3%–5%），建議投入 **${suggested_amount:,} 元** 分批建倉。"
    elif total_score >= 35:
        suggested_amount = 1500
        signal_status = "🟡 【小額試水溫】"
        signal_msg = f"部分指標回檔，建議可提撥小額 **${suggested_amount:,} 元** 試水溫。"
    else:
        suggested_amount = 0
        signal_status = "⚪ 【觀望期（保持定期定額）】"
        signal_msg = (
            "價格位於相對高檔，建議暫不另外加碼，保持原本的定期定額扣款即可。"
        )

    # --- 1. 大盤與個股總覽 ---
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

    # --- 2. 加碼最適時間與建議額度卡片 ---
    st.markdown("---")
    st.subheader("🚨 當前是否為「加碼最適時間」？")
    st.caption(f"🏷️ 標的類別：**{etf_type_str}**")

    s_col1, s_col2, s_col3 = st.columns([1, 1.2, 1.8])
    s_col1.metric(label="加碼時機指數", value=f"{total_score} / 100 分")
    s_col2.metric(
        label="💡 本次建議加碼額度",
        value=f"${suggested_amount:,} 元",
        delta="下單建議" if suggested_amount > 0 else "觀望不動",
    )

    if total_score >= 50:
        s_col3.success(f"**{signal_status}**\n\n{signal_msg}")
    elif total_score >= 35:
        s_col3.warning(f"**{signal_status}**\n\n{signal_msg}")
    else:
        s_col3.info(f"**{signal_status}**\n\n{signal_msg}")

    st.markdown("##### 📝 得分明細與實時診斷：")
    with st.expander("🔍 點擊查看評分標準與狀況明細", expanded=True):
        st.markdown(f"**1. 高點拉回得分：`{s_pullback} / 35分`**")
        st.caption(
            "📌 **標準**：拉回 $\ge 8\%$ 得 35分 | $\ge 5\%$ 得 25分 | $\ge 3\%$ 得 15分"
        )
        st.info(f"💡 **目前狀況**：{desc_pullback}")

        st.markdown(f"**2. 個股恐慌 (RSI) 得分：`{s_rsi} / 25分`**")
        st.caption("📌 **標準**：14日 RSI $< 30$ 得 25分 | $< 40$ 得 10分")
        st.info(f"💡 **目前狀況**：{desc_rsi}")

        st.markdown(f"**3. 均線位置得分：`{s_ma} / 20分`**")
        st.caption(
            "📌 **標準**：股價跌破 240日年線得 20分 | 跌破 60日季線得 10分"
        )
        st.info(f"💡 **目前狀況**：{desc_ma}")

        st.markdown(f"**4. 大盤環境得分：`{s_market} / 20分`**")
        st.caption(
            "📌 **標準**：大盤 RSI $< 35$ 得 20分 | 加權指數跌破季線得 10分"
        )
        st.info(f"💡 **目前狀況**：{desc_market}")

    # --- 3. 個人扣款歷史明細紀錄表 ---
    st.markdown("---")
    st.subheader(f"📝 個人每月定期定額買入明細 ({ticker})")

    all_records = load_all_records()
    default_df = pd.DataFrame(
        [
            {"買入日期": "2024-01-02", "買入單價": 22.50, "買入股數": 66},
            {"買入日期": "2024-02-01", "買入單價": 22.80, "買入股數": 65},
        ]
    )

    if ticker not in all_records or not all_records[ticker]:
        current_data = default_df.to_dict("records")
    else:
        current_data = all_records[ticker]

    current_df = pd.DataFrame(current_data)

    with st.expander(
        f"📂 點擊展開 / 修改 `{ticker}` 的歷史明細（編輯後會自動永久儲存）",
        expanded=True,
    ):
        st.caption(f"💡 您正在編輯 **{ticker}** 的專屬扣款紀錄：")

        edited_df = st.data_editor(
            current_df,
            num_rows="dynamic",
            use_container_width=True,
            key=f"editor_{ticker}",
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

        updated_records = edited_df.to_dict("records")
        if updated_records != current_data:
            all_records[ticker] = updated_records
            save_all_records(all_records)
            st.toast(f"✅ 已自動儲存 {ticker} 的最新歷史紀錄！")

        edited_df["單筆金額"] = edited_df["買入單價"] * edited_df["買入股數"]
        total_dca_principal = float(edited_df["單筆金額"].sum())
        total_dca_shares = float(edited_df["買入股數"].sum())
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

        st.markdown(f"#### 📊 {ticker} 歷史買入統計總覽：")
        a1, a2, a3 = st.columns(3)
        a1.metric("累積總投入本金", f"${total_dca_principal:,.0f} 元")
        a2.metric("累積持股總數量", f"{total_dca_shares:,.0f} 股")
        a3.metric(
            "加權平均買進成本",
            f"${avg_dca_cost:.2f} 元",
            delta=f"價差 ${latest_price - avg_dca_cost:+.2f}",
        )

        b1, b2 = st.columns(2)
        b1.metric("定期定額目前總市值", f"${current_dca_value:,.0f} 元")
        b2.metric(
            "累積投資損益",
            f"${dca_profit:+,.0f} 元",
            delta=f"{dca_roi:+.2f}% 報酬率",
        )

    # --- 4. 逢低加碼情境模擬器 ---
    st.markdown("---")
    st.subheader("💡 逢低加碼買進情境模擬器")

    with st.expander("🧮 點擊展開 / 輸入加碼試算參數", expanded=True):
        sim_col1, sim_col2 = st.columns(2)

        default_add_val = suggested_amount if suggested_amount > 0 else 3000
        add_budget = sim_col1.number_input(
            "預計加碼金額 (台幣)", value=default_add_val, step=1000
        )
        add_target_price = sim_col2.number_input(
            "預計買進成交單價", value=round(latest_price, 2), step=0.1
        )

        default_yield = 6.5 if is_high_dividend else 2.5
        est_yield_pct = st.slider(
            "預估年化殖利率 (%)",
            min_value=1.0,
            max_value=10.0,
            value=default_yield,
            step=0.5,
        )

        add_shares = (
            int(add_budget / add_target_price) if add_target_price > 0 else 0
        )
        actual_add_cost = add_shares * add_target_price

        new_principal = total_dca_principal + actual_add_cost
        new_shares = total_dca_shares + add_shares
        new_avg_cost = new_principal / new_shares if new_shares > 0 else 0

        new_value = new_shares * latest_price
        annual_div = new_value * (est_yield_pct / 100)
        quarterly_div = annual_div / 4

        st.markdown("#### 🎯 加碼後資產變化模擬：")
        s1, s2, s3 = st.columns(3)
        s1.metric(
            "加碼可買進股數",
            f"{add_shares:,} 股",
            delta=f"約需 ${actual_add_cost:,.0f} 元",
        )
        s2.metric("加碼後總持股數", f"{new_shares:,.0f} 股", delta=f"+{add_shares}")
        s3.metric(
            "加碼後新平均成本",
            f"${new_avg_cost:.2f} 元",
            delta=f"{new_avg_cost - avg_dca_cost:+.2f} 元",
            delta_color="inverse",
        )

        st.markdown("---")
        d1, d2 = st.columns(2)
        d1.metric(
            "加碼後預估年配息",
            f"${annual_div:,.0f} 元 / 年",
            delta=f"每季約 ${quarterly_div:,.0f} 元",
        )
        d2.metric(
            "加碼後預估新總市值",
            f"${new_value:,.0f} 元",
            delta=f"總投入 ${new_principal:,.0f} 元",
        )

    # --- 5. 走勢圖表 (可折疊) ---
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
