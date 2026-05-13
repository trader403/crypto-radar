import requests
import json
import os
from datetime import datetime, timezone

# ========== 配置 ==========
# 监控的合约标的（大写，会匹配包含这些关键词的交易对）
TARGETS = ["ANTHROPIC", "SPACEX", "OPENAI"]
# 高APY新池最低阈值
MIN_APY = 50
# 输出文件
OUTPUT_FILE = "data.json"

# ========== 1. 资金费率 (CoinGecko) ==========
def get_funding_rates():
    url = "https://api.coingecko.com/api/v3/derivatives/exchanges"
    try:
        resp = requests.get(url, timeout=15)
        data = resp.json()
        results = []
        for exchange in data:
            for ticker in exchange.get("tickers", []):
                sym = ticker.get("symbol", "").upper()
                if any(t in sym for t in TARGETS):
                    results.append({
                        "exchange": exchange.get("name"),
                        "symbol": ticker.get("symbol"),
                        "funding_rate": ticker.get("funding_rate"),
                        "index_price": ticker.get("index_price")
                    })
        return results
    except Exception as e:
        return [{"error": str(e)}]

# ========== 2. DeFi 新池/高APY (DeFiLlama) ==========
def get_high_apy_pools():
    url = "https://yields.llama.fi/pools"
    try:
        resp = requests.get(url, timeout=20)
        data = resp.json()
        fresh = []
        now = datetime.now(timezone.utc)
        for pool in data.get("data", []):
            apy = pool.get("apy", 0)
            if apy < MIN_APY:
                continue
            created_str = pool.get("created_at")
            if created_str:
                created = datetime.strptime(created_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                if (now - created).total_seconds() < 86400:  # 24小时内
                    fresh.append({
                        "chain": pool["chain"],
                        "project": pool["project"],
                        "symbol": pool["symbol"],
                        "apy": apy,
                        "tvlUsd": pool.get("tvlUsd")
                    })
        return sorted(fresh, key=lambda x: x["apy"], reverse=True)
    except Exception as e:
        return [{"error": str(e)}]

# ========== 3. 安全快讯 (PANews RSS) ==========
def get_security_news():
    url = "https://panewslab.com/zh/rss"
    try:
        resp = requests.get(url, timeout=15)
        # 简单解析XML
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
        return [{"error": str(e)}]

# ========== 主函数 ==========
if __name__ == "__main__":
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "funding_rates": get_funding_rates(),
        "high_apy_pools": get_high_apy_pools(),
        "security_news": get_security_news()
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"✅ 数据已保存到 {OUTPUT_FILE}")
