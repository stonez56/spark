"""
weather.py — 中央氣象署 (CWA) Open Data 天氣模組
==================================================
Uses the official CWA Open Data API for accurate, structured weather data.
API: F-C0032-001 (36-hour city forecast)
Registration (free): https://opendata.cwa.gov.tw/user/authkey

The public demo key 'rdec-key-123-45678-011121314' works without registration
but may be rate-limited. Set CWA_API_KEY in .env for a dedicated key.

City name mapping: Taiwan counties/cities → CWA locationName format.
"""

import os
import json
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Optional

# ── Public demo key works without registration (rate-limited) ────────────────
CWA_API_BASE   = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"
CWA_DATASET_36H = "F-C0032-001"   # 36-hour city forecast
CWA_DEMO_KEY   = "rdec-key-123-45678-011121314"

# City aliases: map from common shorthand → CWA locationName
CITY_ALIAS = {
    "台北":   "臺北市",
    "臺北":   "臺北市",
    "新北":   "新北市",
    "基隆":   "基隆市",
    "桃園":   "桃園市",
    "新竹市": "新竹市",
    "新竹":   "新竹市",
    "苗栗":   "苗栗縣",
    "台中":   "臺中市",
    "臺中":   "臺中市",
    "彰化":   "彰化縣",
    "南投":   "南投縣",
    "雲林":   "雲林縣",
    "嘉義市": "嘉義市",
    "嘉義":   "嘉義縣",
    "台南":   "臺南市",
    "臺南":   "臺南市",
    "高雄":   "高雄市",
    "屏東":   "屏東縣",
    "宜蘭":   "宜蘭縣",
    "花蓮":   "花蓮縣",
    "台東":   "臺東縣",
    "臺東":   "臺東縣",
    "澎湖":   "澎湖縣",
    "金門":   "金門縣",
    "馬祖":   "連江縣",
}

def _resolve_city(city_hint: str) -> str:
    """Resolve common city shorthand to CWA locationName."""
    for k, v in CITY_ALIAS.items():
        if k in city_hint:
            return v
    return city_hint

def _get_api_key() -> str:
    """Return the configured CWA API key, falling back to the public demo key."""
    key = os.getenv("CWA_API_KEY", "").strip()
    if not key:
        try:
            import settings_manager
            s = settings_manager.load_settings()
            key = s.get("cwa_api_key", "").strip()
        except Exception:
            pass
    return key if key else CWA_DEMO_KEY


def _cwa_get(url: str) -> dict:
    """
    HTTP GET wrapper for the CWA API.
    Uses `requests` with automatic SSL fallback.

    Taiwan government servers (opendata.cwa.gov.tw) use a CA chain that
    omits the 'Subject Key Identifier' extension — this triggers strict
    verification failures in OpenSSL 3.x.  We try verified first, then
    fall back to unverified for THIS trusted government endpoint only.
    """
    try:
        import requests as _req
    except ImportError:
        # Final fallback: urllib with disabled verification
        import urllib.request, ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(url, timeout=8, context=ctx) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # Try with SSL verification first
    try:
        r = _req.get(url, timeout=8, verify=True)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        err_msg = str(e).lower()
        if "ssl" in err_msg or "certificate" in err_msg or "verify" in err_msg:
            print(f"[Weather] SSL verify failed ({type(e).__name__}), retrying without verification for CWA gov endpoint...")
            # Suppress the InsecureRequestWarning — opendata.cwa.gov.tw is a
            # trusted Taiwan government server; the error is a CA chain issue on
            # their side (Missing Subject Key Identifier), not a MITM risk.
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            except Exception:
                pass
            r = _req.get(url, timeout=8, verify=False)
            r.raise_for_status()
            return r.json()
        raise



def get_weather(city: str) -> Optional[dict]:
    """
    Fetch 36-hour weather forecast for the given city from CWA Open Data.

    Returns a structured dict:
        {
          "city": "新竹市",
          "updated_at": "2026-06-09 18:00",
          "periods": [
              {
                "label": "今晚至明晨",
                "start": "2026-06-09 18:00",
                "end":   "2026-06-10 06:00",
                "wx":    "陰陣雨或雷雨",
                "pop":   "100",   # % probability of precipitation
                "min_t": "23",    # °C
                "max_t": "24",    # °C
                "ci":    "舒適",
              },
              ...
          ]
        }
    Returns None on error.
    """
    api_key  = _get_api_key()
    cwa_city = _resolve_city(city)

    # Build URL with properly encoded parameters
    params = urllib.parse.urlencode({
        "Authorization": api_key,
        "locationName":  cwa_city,
        "format":        "JSON",
    })
    url = f"{CWA_API_BASE}/{CWA_DATASET_36H}?{params}"
    print(f"[Weather] Requesting: {CWA_API_BASE}/{CWA_DATASET_36H}?locationName={cwa_city}&key={api_key[:8]}...")

    try:
        data = _cwa_get(url)
    except Exception as e:
        print(f"[Weather] CWA API request failed: {e}")
        return None

    if data.get("success") != "true":
        print(f"[Weather] CWA API returned success=false for city '{cwa_city}'")
        return None

    locations = data.get("records", {}).get("location", [])
    if not locations:
        print(f"[Weather] No location data for '{cwa_city}'")
        return None

    loc = locations[0]
    elements = {el["elementName"]: el["time"] for el in loc.get("weatherElement", [])}

    def _val(el_name: str, idx: int, key: str = "parameterName") -> str:
        try:
            return elements[el_name][idx]["parameter"][key]
        except (KeyError, IndexError):
            return ""

    def _start(el_name: str, idx: int) -> str:
        try:
            return elements[el_name][idx]["startTime"]
        except (KeyError, IndexError):
            return ""

    def _end(el_name: str, idx: int) -> str:
        try:
            return elements[el_name][idx]["endTime"]
        except (KeyError, IndexError):
            return ""

    # Build period labels relative to now
    now = datetime.now()
    def _period_label(start_str: str, end_str: str) -> str:
        try:
            s = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
            e = datetime.strptime(end_str,   "%Y-%m-%d %H:%M:%S")
            sh = s.hour
            if sh >= 18 or sh < 6:
                time_label = "今晚至明晨" if (s.date() == now.date()) else "明晚至後日凌晨"
            elif 6 <= sh < 12:
                time_label = "今日上午" if (s.date() == now.date()) else "明日上午"
            else:
                time_label = "今日下午" if (s.date() == now.date()) else "明日下午"
            return time_label
        except Exception:
            return start_str

    n_periods = len(elements.get("Wx", []))
    periods = []
    for i in range(n_periods):
        s = _start("Wx", i)
        e = _end("Wx", i)
        periods.append({
            "label": _period_label(s, e),
            "start": s,
            "end":   e,
            "wx":    _val("Wx",  i),
            "pop":   _val("PoP", i),
            "min_t": _val("MinT", i),
            "max_t": _val("MaxT", i),
            "ci":    _val("CI",  i),
        })

    return {
        "city":       loc["locationName"],
        "updated_at": periods[0]["start"] if periods else "",
        "periods":    periods,
    }


def format_weather_for_llm(weather: dict) -> str:
    """
    Format CWA weather data into a compact, LLM-readable summary (Traditional Chinese).
    This is injected into the LLM prompt as structured context, replacing DDG web search
    for weather queries.
    """
    if not weather or not weather.get("periods"):
        return ""

    city   = weather["city"]
    lines  = [f"【{city} 36小時天氣預報】（資料來源：中央氣象署）"]
    now    = datetime.now()

    for p in weather["periods"]:
        start_str = p.get("start", "")
        try:
            s = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
            is_current = (s <= now <= datetime.strptime(p["end"], "%Y-%m-%d %H:%M:%S"))
            tag = "▶ 現在" if is_current else p["label"]
        except Exception:
            tag = p["label"]

        line = (
            f"  {tag}：{p['wx']}，"
            f"氣溫 {p['min_t']}～{p['max_t']}度，"
            f"降雨機率 {p['pop']}%，"
            f"體感 {p['ci']}"
        )
        lines.append(line)

    return "\n".join(lines)


# ── Weather-intent keyword detection ─────────────────────────────────────────
WEATHER_KEYWORDS = [
    "天氣", "下雨", "氣溫", "溫度", "氣候", "降雨", "晴", "陰", "颱風", "颳風",
    "風速", "濕度", "體感", "紫外線", "PM2.5", "空氣品質", "寒流", "梅雨",
    "weather", "forecast", "rain", "temperature", "humidity", "typhoon"
]

def is_weather_query(query: str) -> bool:
    """Heuristic: does this query ask about weather?"""
    q_lower = query.lower()
    return any(kw in q_lower for kw in WEATHER_KEYWORDS)
