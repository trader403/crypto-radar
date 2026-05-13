import requests
import json
from datetime import datetime, timezone

OUTPUT_FILE = "data.json"

def get_all_funding_rates():
    """从 Hyperliquid 公共 API 获取所有交易对的资金费率及相关数据"""
    url = "https://api.hyperliquid.xyz/info"
    payload = {"type": "metaAndAssetCtxs"}
    try:
        resp = requests.post(url, json=payload, timeout=15)
        data = resp.json()
        universe = data[0]["universe"]   # 元数据列表
        asset_ctxs = data[1]            # 资产上下文列表

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

        # 按资金费率绝对值降序排列，只保留前 30 条（方便快速查看异常）
        results.sort(key=lambda x: abs(float(x["funding_rate"])) if x["funding_rate"] else 0, reverse=True)
        return results[:30]
    except Exception as e:
        return [{"error": str(e)}]

if __name__ == "__main__":
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "top_30_abnormal_funding": get_all_funding_rates()
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"✅ 已保存 top 30 异常费率数据到 {OUTPUT_FILE}")
