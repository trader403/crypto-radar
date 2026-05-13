import requests
import json
from datetime import datetime, timezone

OUTPUT_FILE = "data.json"

# ========== 1. Hyperliquid 资金费率 ==========
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

# ========== 2. DeFiLlama 高 APY 新池 ==========
def get_defi_high_apy():
    url = "https://yields.llama.fi/pools"
    try:
        resp = requests.get(url, timeout=20)
        data = resp.json()
        fresh = []
        now = datetime.now(timezone.utc)
        for pool in data.get("data", []):
            apy = pool.get("apy", 0)
            if apy < 50:   # 只关注 APY > 50%
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

# ========== 3. The Block 安全/快讯 ==========
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

# ========== 4. PANews 中文快讯 ==========
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

# ========== 主流程 ==========
if __name__ == "__main__":
    funding = get_hyperliquid_funding()
    defi = get_defi_high_apy()
    tb = get_theblock_news()
    pan = get_panews_news()

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "top_30_funding": funding,
        "high_apy_pools": defi,
        "theblock_news": tb,
        "panews_news": pan
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"✅ 数据已保存到 {OUTPUT_FILE}")
