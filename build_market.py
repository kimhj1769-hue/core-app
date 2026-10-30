#!/usr/bin/env python3
"""코어 ETF 앱 1단계 — 「시장」 지표 화면 정적 HTML 생성기 (2026-10-29 부장 「지표의 정보 전달이 주된 목적」).

화면(휴대폰 세로 우선):
  ① 요약 카드: S&P500·나스닥(전일 대비·전고점 대비 낙폭·200일선 위/아래) · VIX · CNN 공포탐욕 · 미 10년물 · 원/달러
  ② S&P500·나스닥 일봉 + 20·60·120·240일 이동평균 + 거래량(상승일 빨강·하락일 파랑, 한국식)
  ③ VIX 1년 추이(20·30 기준선) · 공포탐욕 30일 추이
  ④ 내 코어(월 100만 원, SPYM 70 : QQQM 30) — 이번 달 매수 수량 제안(1주 단위, 잔액 이월)
데이터: yfinance(무료) · CNN dataviz API. 계산은 여기서 끝내고 HTML은 읽기만(1GB VM 부담 최소).
사용: python3 build_market.py [출력.html]   (GitHub Actions 평일 2회 → GitHub Pages 배포, 기본 출력=site/index.html)
외부 조회가 하나 실패해도 그 칸만 「확인 불가」로 두고 빌드는 성공한다(data["errors"]에 사유 기록).
키·토큰·개인 보유내역 없음(보유=0 가정, 공개 페이지).
※ SPLG는 2026-10 기준 SPYM으로 티커 변경(yfinance SPLG 404, SPYM 정상 — 10-29 실측).
"""
import json, sys, datetime, math
from pathlib import Path
import requests
import yfinance as yf

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("site") / "index.html"
MONTHLY_KRW = 1_000_000
TARGET = {"SPYM": 0.70, "QQQM": 0.30}
MAS = [20, 60, 120, 240]


def hist(t, period="2y"):
    h = yf.Ticker(t).history(period=period, auto_adjust=False)
    h = h[h["Close"].notna()]
    return h


def series_payload(h, show_days=260):
    close = h["Close"]
    ma = {n: close.rolling(n).mean() for n in MAS}
    rows = h.tail(show_days)
    idx = rows.index
    t = [d.strftime("%Y-%m-%d") for d in idx]
    candles = [{"time": t[i], "open": round(r.Open, 2), "high": round(r.High, 2), "low": round(r.Low, 2), "close": round(r.Close, 2)}
               for i, r in enumerate(rows.itertuples())]
    vols = [{"time": t[i], "value": float(r.Volume or 0), "up": bool(r.Close >= r.Open)} for i, r in enumerate(rows.itertuples())]
    mas = {n: [{"time": t[i], "value": round(float(v), 2)} for i, v in enumerate(ma[n].loc[idx]) if not math.isnan(v)] for n in MAS}
    last, prev = float(close.iloc[-1]), float(close.iloc[-2])
    peak = float(close.tail(252 * 2).max())
    ma200 = float(close.rolling(200).mean().iloc[-1])
    vol20 = float(h["Volume"].tail(20).mean() or 0)
    return {"candles": candles, "volume": vols, "ma": mas,
            "last": round(last, 2), "chg": round((last / prev - 1) * 100, 2), "date": t[-1],
            "dd": round((last / peak - 1) * 100, 1), "above200": last >= ma200, "ma200": round(ma200, 2),
            "vol_ratio": round(float(h["Volume"].iloc[-1]) / vol20, 2) if vol20 else None,
            "ma_last": {n: (mas[n][-1]["value"] if mas[n] else None) for n in MAS}}


def _clean(rows):
    """lightweight-charts 는 시간 오름차순·중복 없음이 필수 — 같은 날짜는 마지막 값만."""
    m = {}
    for r in rows: m[r["time"]] = r
    return [m[k] for k in sorted(m)]


def fear_greed():
    H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
         "Accept": "application/json, text/plain, */*", "Referer": "https://www.cnn.com/markets/fear-and-greed", "Origin": "https://www.cnn.com"}
    try:
        d = requests.get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata", headers=H, timeout=15).json()
        cur = d["fear_and_greed"]
        hs = d["fear_and_greed_historical"]["data"][-30:]
        pc = d.get("put_call_options", {}).get("data", [])[-120:]   # CBOE 풋/콜 비율 5일 평균(CNN 구성지표)
        ts = lambda x: datetime.datetime.fromtimestamp(x / 1000, datetime.timezone.utc).strftime("%Y-%m-%d")
        return {"score": round(cur["score"]), "rating": cur["rating"], "date": str(cur.get("timestamp", ""))[:10],
                "pc": {"last": round(pc[-1]["y"], 3), "rating": pc[-1].get("rating", ""),
                       "hist": _clean([{"time": ts(x["x"]), "value": round(x["y"], 3)} for x in pc])} if pc else None,
                "hist": _clean([{"time": datetime.datetime.fromtimestamp(x["x"] / 1000, datetime.timezone.utc).strftime("%Y-%m-%d"), "value": round(x["y"], 1)} for x in hs])}
    except Exception as e:
        return {"error": str(e)[:80]}


FG_KO = {"extreme fear": "극단적 공포", "fear": "공포", "neutral": "중립", "greed": "탐욕", "extreme greed": "극단적 탐욕"}


def core_plan(px, krw, held=None, carry_usd=0.0):
    """월 100만 원(+이월금)으로 1주씩, 「보유+이번 매수」가 목표 70:30에서 가장 모자란 쪽을 먼저 산다(매도 없음).
    단순 70/30 분할은 QQQM 1주($300)가 30% 몫($225)보다 비싸 영영 0주가 되는 문제가 있어(10-29 실측) 이 방식으로."""
    held = dict(held or {t: 0 for t in TARGET})
    usd = MONTHLY_KRW / krw + carry_usd
    plan, left = {t: 0 for t in TARGET}, usd
    while True:
        val = {t: (held[t] + plan[t]) * px[t] for t in TARGET}
        tot = sum(val.values())
        cands = [t for t in TARGET if px[t] <= left]
        if not cands: break
        t = max(cands, key=lambda k: TARGET[k] * (tot + px[k]) - val[k])   # 이번 1주를 넣었을 때 목표 대비 가장 모자란 쪽
        plan[t] += 1; left -= px[t]
    val = {t: (held[t] + plan[t]) * px[t] for t in TARGET}; tot = sum(val.values()) or 1
    return {"usd": round(usd, 2), "plan": plan, "carry_usd": round(left, 2), "carry_krw": round(left * krw),
            "px": {k: round(v, 2) for k, v in px.items()}, "weight": {k: round(v / tot * 100, 1) for k, v in val.items()}}


def main():
    errors = {}

    def safe(name, fn):
        try:
            return fn()
        except Exception as e:  # 한 지표 실패 → 그 칸만 「확인 불가」
            errors[name] = f"{type(e).__name__}: {str(e)[:100]}"
            print("[실패]", name, errors[name], file=sys.stderr)
            return None

    def last_chg(h, nd):
        return {"last": round(float(h["Close"].iloc[-1]), nd), "chg": round(float(h["Close"].iloc[-1] - h["Close"].iloc[-2]), nd)}

    data = {"built": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M") + " KST", "fg_ko": FG_KO}
    for k, t in [("spx", "^GSPC"), ("ndx", "^IXIC"), ("dji", "^DJI"), ("sox", "^SOX")]:
        data[k] = safe(k, lambda t=t: series_payload(hist(t)))

    def vix():
        h = hist("^VIX", "1y")
        return {"last": round(float(h["Close"].iloc[-1]), 2), "date": h.index[-1].strftime("%Y-%m-%d"),
                "line": [{"time": d.strftime("%Y-%m-%d"), "value": round(float(v), 2)} for d, v in h["Close"].items()]}
    data["vix"] = safe("vix", vix)
    data["tnx"] = safe("tnx", lambda: last_chg(hist("^TNX", "1mo"), 2))
    data["krw"] = safe("krw", lambda: last_chg(hist("KRW=X", "1mo"), 1))
    fg = fear_greed()
    if "error" in fg:
        errors["fg"] = fg["error"]; fg = None
    elif not fg.get("pc"):
        errors["pc"] = "풋/콜 데이터 없음"
    data["fg"] = fg
    def core():
        px = {t: float(hist(t, "5d")["Close"].iloc[-1]) for t in TARGET}
        return core_plan(px, data["krw"]["last"])
    data["core"] = safe("core", core) if data["krw"] else None
    if not data["krw"]: errors["core"] = "원/달러 조회 실패로 계산 불가"
    data["errors"] = errors

    html = Path(__file__).with_name("market_template.html").read_text(encoding="utf-8")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False)), encoding="utf-8")
    g = lambda k: (data[k] or {}).get("last", "확인 불가")
    print("저장:", OUT, "| S&P", g("spx"), "| 나스닥", g("ndx"), "| VIX", g("vix"),
          "| 공포탐욕", (fg or {}).get("score", "확인 불가"), "| 코어", (data["core"] or {}).get("plan"), "| 실패:", list(errors) or "없음")


if __name__ == "__main__":
    main()
