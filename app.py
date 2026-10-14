    # 判斷是否採用「靈敏加碼門檻」（適用：高股息 ETF 或希望小跌就加碼的市值型 0050）
    # 如果您希望 0050 也是小跌就加碼，直接將門檻統一調靈敏：
    if pullback_pct <= -8:
        s_pullback = 35
        desc_pullback = f"現價 ${latest_price:.2f} 距高點 ${high_6m:.2f} 已拉回 {pullback_pct:.1f}% (顯著拉回，大特價區！)"
    elif pullback_pct <= -5:
        s_pullback = 25
        desc_pullback = f"現價 ${latest_price:.2f} 距高點 ${high_6m:.2f} 已拉回 {pullback_pct:.1f}% (中小幅修正，適合加碼)"
    elif pullback_pct <= -3:
        s_pullback = 10
        desc_pullback = f"現價 ${latest_price:.2f} 距高點 ${high_6m:.2f} 已拉回 {pullback_pct:.1f}% (微幅回檔，可定期定額+小額加碼)"
    else:
        s_pullback = 0
        desc_pullback = f"現價 ${latest_price:.2f} 距高點 ${high_6m:.2f} 拉回 {pullback_pct:.1f}% (處於相對高檔)"
