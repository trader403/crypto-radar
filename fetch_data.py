import requests
import json
import time
from datetime import datetime, timezone

# ========== 你的监控标的 (Hyperliquid 上的代币名) ==========
TARGETS = ["ANTHROPIC", "SPACEX", "OPENAI"]
OUTPUT_FILE = "data.json"

def get_funding_rates_from_hyperliquid():
    """从 Hyperliquid 公共 API 获取资金费率"""
    url = "https://api.hyperliquid.xyz/info"
    payload = {"type": "metaAndAssetCtxs"}
    try:
        resp = requests.post(url, json=payload, timeout=15)
        data = resp.json()
        
        results = []
        # 第一部分是 universe (元数据)，第二部分是 assetCtxs (实时数据)
        asset_ctxs = data[1] if len(data) > 1 else []
        
        for item in asset_ctxs:
            coin = item.get("coin", "")
            if any(t in coin.upper() for t in TARGETS):
                results.append({
                    "exchange": "Hyperliquid",
                    "symbol": coin,
                    "funding_rate": item.get("funding"),
                    "mark_price": item.get("markPx"),
                    "open_interest": item.get("openInterest"),
                    "premium": item.get("premium"),
                    "day_volume": item.get("dayNtlVlm")
                })
        return results
    except Exception as e:
        return [{"error": f"Hyperliquid: {str(e)}"}]

def get_funding_rates_from_coinglass():
    """从 CoinGlass 获取资金费率 (需要 API Key)"""
    # 你需要先在 coinglass.com 注册，获取免费 API Key
    # 免费版每月 30,000 次请求
    import os
    api_key = os.environ.get("COINGLASS_API_KEY", "")
    if not api_key:
        return [{"error": "CoinGlass: API Key 未设置 (环境变量 COINGLASS_API_KEY)"}]
    
    url = "https://open-api-v2.coinglass.com/api/funding-rate/list"
    headers = {"accept": "application/json", "coinglassSecret": api_key}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        data = resp.json()
        # CoinGlass 返回所有交易对的费率，筛选你的目标
        results = []
        if data.get("code") == "200" and "data" in data:
            for item in data["data"]:
                symbol = item.get("symbol", "").upper()
                exchange = item.get("exchangeName", "")
                rate = item.get("fundingRate", 0)
                if any(t in symbol for t in TARGETS):
                    results.append({
                        "exchange": exchange,
                        "symbol": symbol,
                        "funding_rate": rate,
                        "index_price": item.get("indexPrice")
                    })
        # 按费率降序排列，方便快速查看
        results.sort(key=lambda x: abs(float(x.get("funding_rate", 0))), reverse=True)
        return results[:20]
    except Exception as e:
        return [{"error": f"CoinGlass: {str(e)}"}]

def get_security_news():
    """从 The Block 获取安全新闻"""
    url = "https://www.theblock.co/api/news/feed"
    try:
        resp = requests.get(url, timeout=15)
        data = resp.json()
        items = []
        keywords = ["hack", "exploit", "security", "attack", "depegged"]
        for article in data.get("articles", [])[:30]:
            title = article.get("title", "")
            if any(kw in title.lower() for kw in keywords):
                items.append({
                    "title": title,
                    "url": article.get("url", "")
                })
        return items[:5]
    except Exception as e:
        return [{"error": str(e)}]

if __name__ == "__main__":
    # 先获取最靠谱的 Hyperliquid 数据
    funding_rates = get_funding_rates_from_hyperliquid()
    
    # 如果 CoinGlass Key 已设置，也获取一份做交叉验证
    coinglass_rates = get_funding_rates_from_coinglass()
    if "error" not in coinglass_rates[0] if coinglass_rates else True:
        funding_rates.extend(coinglass_rates)
    
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "funding_rates": funding_rates,
        "security_news": get_security_news()
    }
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"✅ 数据已保存到 {OUTPUT_FILE}，共 {len(funding_rates)} 条费率记录")
