import requests
import json
import os
import yfinance as yf
from datetime import datetime, timezone

# ============================================================
# 全局输出文件
OUTPUT_FILE = "data.json"

# ============================================================
# 1. Hyperliquid 资金费率
# ============================================================
def get_hyperliquid_funding():
    url = "https://api.hyperliquid.xyz/info"
    payload = {"type": "metaAndAssetCtxs"}
    try:
        resp = requests.post(url, json=payload, timeout=15)
        data = resp.json()
        universe = data[0]["universe"]
        asset_ctxs = data[1]
        results = []
        for i, item in enumerate(universe):
            name = item["name"]
            ctx = asset_ctxs[i]
            results.append({
                "symbol": name,
                "funding_rate": ctx.get("funding"),
                "mark_price": ctx.get("markPx"),
                "open_interest": ctx.get("openInterest"),
                "premium": ctx.get("premium"),
                "day_volume": ctx.get("dayNtlVlm")
            })
        results.sort(key=lambda x: abs(float(x["funding_rate"]) if x["funding_rate"] else 0), reverse=True)
        return results[:30]
    except Exception as e:
        return [{"error": f"Hyperliquid: {str(e)}"}]

# ============================================================
# 2. DeFiLlama 高 APY 新池
# ============================================================
def get_defi_high_apy():
    url = "https://yields.llama.fi/pools"
    try:
        resp = requests.get(url, timeout=20)
        data = resp.json()
        fresh = []
        now = datetime.now(timezone.utc)
        for pool in data.get("data", []):
            apy = pool.get("apy", 0)
            if apy < 50:
                continue
            created_str = pool.get("created_at")
            if created_str:
                created = datetime.strptime(created_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                if (now - created).total_seconds() < 86400:
                    fresh.append({
                        "chain": pool["chain"],
                        "project": pool["project"],
                        "symbol": pool["symbol"],
                        "apy": apy,
                        "tvlUsd": pool.get("tvlUsd")
                    })
        return sorted(fresh, key=lambda x: x["apy"], reverse=True)[:10]
    except Exception as e:
        return [{"error": f"DeFiLlama: {str(e)}"}]

# ============================================================
# 3. The Block 安全快讯
# ============================================================
def get_theblock_news():
    url = "https://www.theblock.co/api/news/feed"
    try:
        resp = requests.get(url, timeout=15)
        data = resp.json()
        items = []
        keywords = ["hack", "exploit", "security", "attack", "depegged"]
        for article in data.get("articles", []):
            title = article.get("title", "")
            if any(kw in title.lower() for kw in keywords):
                items.append({"title": title, "url": article.get("url", "")})
        return items[:5]
    except Exception as e:
        return [{"error": f"TheBlock: {str(e)}"}]

# ============================================================
# 4. PANews 中文快讯
# ============================================================
def get_panews_news():
    url = "https://panewslab.com/zh/rss"
    try:
        resp = requests.get(url, timeout=15)
        items = []
        content = resp.text
        parts = content.split("<item>")
        for part in parts[1:]:
            title_start = part.find("<title>") + 7
            title_end = part.find("</title>")
            title = part[title_start:title_end]
            if any(kw in title for kw in ["攻击", "漏洞", "脱锚", "黑客", "盗取"]):
                link_start = part.find("<link>") + 6
                link_end = part.find("</link>")
                link = part[link_start:link_end]
                items.append({"title": title, "link": link})
        return items[:5]
    except Exception as e:
        return [{"error": f"PANews: {str(e)}"}]

# ============================================================
# 5. 美股行情 – 使用 market‑feed (无需 API Key)
# ============================================================
def get_us_stocks():
    symbols = ["AAPL", "TSLA", "MSFT", "SPY", "QQQ"]
    quotes = []
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            info = ticker.info
            quotes.append({
                "symbol": sym,
                "price": info.get("regularMarketPrice") or info.get("currentPrice"),
                "change_percent": info.get("regularMarketChangePercent") or info.get("currentPercentChange"),
                "volume": info.get("regularMarketVolume") or info.get("volume"),
                "market_state": info.get("marketState")
            })
        except Exception as e:
            quotes.append({"symbol": sym, "error": str(e)})
    return quotes

# ============================================================
# 6. 港股行情 – 腾讯财经接口
# ============================================================
def get_hk_stocks():
    symbols = ["hk00700", "hk09988", "hk00388", "hk02318", "hk00005"]
    url = "http://qt.gtimg.cn/q=" + ",".join(symbols)
    try:
        resp = requests.get(url, timeout=10)
        resp.encoding = "gbk"
        text = resp.text
        results = []
        for line in text.strip().split("\n"):
            if "=" not in line:
                continue
            var_name, content = line.split("=", 1)
            content = content.strip('" ')
            parts = content.split("~")
            if len(parts) > 10:
                results.append({
                    "symbol": var_name.strip("v_"),
                    "name": parts[1],
                    "price": parts[3],
                    "change_percent": parts[32] if len(parts) > 32 else ""
                })
        return results
    except Exception as e:
        return [{"error": f"HK Stock: {str(e)}"}]

# ============================================================
# 7. 汇率 – ExchangeRate-API
# ============================================================
def get_exchange_rates():
    url = "https://open.er-api.com/v6/latest/USD"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        major = ["CNY", "EUR", "JPY", "GBP", "HKD", "KRW", "INR", "BRL"]
        rates = data.get("rates", {})
        filtered = {k: rates[k] for k in major if k in rates}
        return {
            "base": "USD",
            "timestamp": data.get("time_last_update_utc"),
            "rates": filtered
        }
    except Exception as e:
        return {"error": f"ExchangeRate: {str(e)}"}

# ============================================================
# 8. 加密恐惧 & 贪婪指数
# ============================================================
def get_fear_greed():
    url = "https://api.alternative.me/fng/?limit=1"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        item = data.get("data", [{}])[0]
        return {
            "value": item.get("value"),
            "classification": item.get("value_classification"),
            "timestamp": item.get("timestamp")
        }
    except Exception as e:
        return {"error": f"FearGreed: {str(e)}"}

# ============================================================
# 主流程
# ============================================================
if __name__ == "__main__":
    funding = get_hyperliquid_funding()
    defi = get_defi_high_apy()
    tb = get_theblock_news()
    pan = get_panews_news()
    us_stocks = get_us_stocks()
    hk_stocks = get_hk_stocks()
    fx = get_exchange_rates()
    fg = get_fear_greed()

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "top_30_funding": funding,
        "high_apy_pools": defi,
        "us_stocks": us_stocks,
        "hk_stocks": hk_stocks,
        "fx_rates": fx,
        "fear_greed": fg,
        "theblock_news": tb,
        "panews_news": pan
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"✅ 数据已保存到 {OUTPUT_FILE}")
    print(f"  资金费率: {len(funding)} 条")
    print(f"  DeFi新池: {len(defi)} 条")
    print(f"  美股行情: {len(us_stocks) if isinstance(us_stocks, list) else '获取失败'}")
    print(f"  港股行情: {len(hk_stocks) if isinstance(hk_stocks, list) else '获取失败'}")
    print(f"  汇率: {'✅' if 'rates' in fx else '❌'}")
    print(f"  恐惧贪婪: {fg.get('value', '❌')}")
