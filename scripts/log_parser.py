"""Parse Apache/Nginx 'combined' access log lines and classify user agents. Pure Python (no DB needed)."""
import re
from datetime import datetime

LINE_RE = re.compile(r'^(?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] "(?P<req>[^"]*)" (?P<status>\d{3}) (?P<bytes>\S+)'
                     r'(?: "(?P<ref>[^"]*)" "(?P<ua>[^"]*)")?')
TS_RE = re.compile(r'\[([^\]]+)\]')
TS_FMT = "%d/%b/%Y:%H:%M:%S %z"

BOT_NAMES = [("googlebot", "Googlebot"), ("bingbot", "Bingbot"), ("ahrefsbot", "AhrefsBot"), ("semrushbot", "SemrushBot"),
             ("mj12bot", "MJ12bot"), ("yandex", "YandexBot"), ("baiduspider", "Baiduspider"),
             ("facebookexternalhit", "Facebook"), ("dotbot", "DotBot"), ("petalbot", "PetalBot")]
BOT_WORDS = ("bot", "spider", "crawl", "slurp", "python-requests", "curl/", "wget", "scrapy", "headless",
             "http-client", "java/", "go-http-client", "okhttp", "libwww", "monitor")


def parse_ts(s):
    return datetime.strptime(s, TS_FMT)


def peek_ts(line):
    m = TS_RE.search(line)
    if not m:
        return None
    try:
        return parse_ts(m.group(1))
    except ValueError:
        return None


def classify_ua(ua):
    """returns (browser, os, device, traffic_type)"""
    u = (ua or "").strip().lower()
    if u in ("", "-"):
        return "Unknown", "Unknown", "Unknown", "unknown"
    if "android" in u: os_ = "Android"
    elif "iphone" in u or "ipad" in u or "ios" in u: os_ = "iOS"
    elif "windows" in u: os_ = "Windows"
    elif "mac os" in u or "macintosh" in u: os_ = "macOS"
    elif "linux" in u or "x11" in u: os_ = "Linux"
    else: os_ = "Other"
    if any(w in u for w in BOT_WORDS):
        name = next((n for k, n in BOT_NAMES if k in u), "Other bot")
        return name, os_, "Bot", "bot"
    if "edg/" in u or "edge/" in u: br = "Edge"
    elif "opr/" in u or "opera" in u: br = "Opera"
    elif "firefox" in u: br = "Firefox"
    elif "chrome" in u or "crios" in u: br = "Chrome"
    elif "safari" in u: br = "Safari"
    elif "msie" in u or "trident" in u: br = "IE"
    else: br = "Other"
    if "ipad" in u or "tablet" in u: dev = "Tablet"
    elif "mobile" in u or "android" in u or "iphone" in u: dev = "Mobile"
    else: dev = "Desktop"
    return br, os_, dev, "human"


def parse_line(line):
    """returns dict or None"""
    m = LINE_RE.match(line)
    if not m:
        return None
    try:
        ts = parse_ts(m.group("ts"))
    except ValueError:
        return None
    parts = m.group("req").split(" ")
    if len(parts) >= 3:
        method, protocol, path = parts[0], parts[-1], " ".join(parts[1:-1])
    else:
        method, protocol, path = (parts[0] if parts else "-"), "", (parts[1] if len(parts) > 1 else "")
    path = path.split("?", 1)[0][:300]
    status = int(m.group("status"))
    b = m.group("bytes")
    ref, ua = m.group("ref"), m.group("ua")
    browser, os_, device, ttype = classify_ua(ua)
    clean = lambda x: x.replace("\x00", "") if x else None
    return {"ts": ts, "ip": m.group("ip"), "method": clean(method)[:16] if method else "-", "path": clean(path),
            "protocol": clean(protocol), "status": status, "status_class": f"{status // 100}xx",
            "bytes": int(b) if b.isdigit() else 0, "referrer": None if ref in (None, "-") else clean(ref)[:300],
            "user_agent": None if ua in (None, "-") else clean(ua)[:300], "browser": browser, "os": os_,
            "device": device, "traffic_type": ttype}
