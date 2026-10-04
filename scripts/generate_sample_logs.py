"""Generate a realistic Apache 'combined' access log (same format as the Kaggle dataset) for the last N days.
Includes daily traffic patterns, bots, a 404 scanner and a 5xx incident - so the dashboard has a story to tell.
Usage: python scripts/generate_sample_logs.py [--rows 300000] [--days 7] [--out data/sample_access.log]
"""
import argparse, math, os, random
from datetime import datetime, timedelta, timezone

PAGES = [("/", 18), ("/products", 12), ("/products/laptops", 6), ("/products/phones", 6), ("/cart", 5), ("/checkout", 3),
         ("/login", 4), ("/search", 7), ("/blog/top-10-gadgets", 3), ("/blog/how-to-choose-a-laptop", 2),
         ("/api/v1/items", 9), ("/api/v1/cart", 4), ("/api/v1/orders", 3), ("/static/app.js", 8), ("/static/style.css", 8),
         ("/static/logo.png", 6), ("/contact", 1), ("/about", 1)]
HUMAN_UA = [
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", 34),
    ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15", 14),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0", 9),
    ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36", 22),
    ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1", 17),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 Edg/124.0", 7)]
BOT_UA = ["Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
          "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
          "Mozilla/5.0 (compatible; AhrefsBot/7.0; +http://ahrefs.com/robot/)",
          "Mozilla/5.0 (compatible; SemrushBot/7~bl; +http://www.semrush.com/bot.html)",
          "python-requests/2.31.0", "curl/8.4.0"]
REFS = ["-", "-", "-", "https://www.google.com/", "https://www.bing.com/", "https://twitter.com/", "https://news.ycombinator.com/"]


def wchoice(r, pairs):
    return r.choices([p for p, _ in pairs], [w for _, w in pairs])[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=300000)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "sample_access.log"))
    a = ap.parse_args()
    r = random.Random(11)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    end = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    start = end - timedelta(days=a.days)
    minutes = a.days * 1440
    shape = []
    for i in range(minutes):
        t = start + timedelta(minutes=i)
        diurnal = 0.35 + 0.65 * (0.5 + 0.5 * math.sin((t.hour + t.minute / 60 - 9) / 24 * 2 * math.pi))
        shape.append(diurnal * (0.8 if t.weekday() >= 5 else 1.0))
    scale = a.rows / sum(shape)
    human_ips = [f"{r.randint(11, 223)}.{r.randint(0, 255)}.{r.randint(0, 255)}.{r.randint(1, 254)}" for _ in range(4000)]
    bot_ips = [f"66.249.{r.randint(60, 79)}.{r.randint(1, 254)}" for _ in range(6)] + \
              [f"157.55.39.{r.randint(1, 254)}" for _ in range(3)] + [f"54.36.{r.randint(140, 150)}.{r.randint(1, 254)}" for _ in range(4)]
    scanner_ip = "185.220.101.7"
    incident_start = start + timedelta(days=a.days * 0.72, hours=3)       # 5xx incident: 90 minutes
    incident_end = incident_start + timedelta(minutes=90)
    scan_start = start + timedelta(days=a.days * 0.4, hours=14)           # 404 scanner: 40 minutes
    scan_end = scan_start + timedelta(minutes=40)
    n = 0
    with open(a.out, "w", encoding="utf-8") as f:
        for i in range(minutes):
            t = start + timedelta(minutes=i)
            lam = shape[i] * scale
            cnt = int(lam) + (1 if r.random() < lam - int(lam) else 0)
            for _ in range(cnt):
                ts = t + timedelta(seconds=r.randint(0, 59))
                bot = r.random() < 0.16
                ip = r.choice(bot_ips) if bot else r.choice(human_ips)
                ua = r.choice(BOT_UA) if bot else wchoice(r, HUMAN_UA)
                path = wchoice(r, PAGES)
                method = "POST" if path in ("/login", "/checkout", "/api/v1/cart", "/api/v1/orders") and r.random() < 0.6 else "GET"
                x = r.random()
                status = 200 if x < 0.90 else 304 if x < 0.94 else 301 if x < 0.955 else 404 if x < 0.985 else 403 if x < 0.993 else 500 if x < 0.997 else 503
                if incident_start <= ts < incident_end and path.startswith(("/api", "/checkout", "/cart")) and r.random() < 0.45:
                    status = r.choice([500, 502, 503, 504])
                if status == 404: path = f"/{r.choice(['old-page', 'wp-login.php', 'img', 'missing'])}/{r.randint(1, 900)}"
                size = int(r.lognormvariate(8.4 if path.startswith("/static") else 7.6, 0.9)) if status in (200, 500) else r.randint(0, 600)
                if scan_start <= ts < scan_end and r.random() < 0.12:
                    ip, ua, method, status, size = scanner_ip, "python-requests/2.31.0", "GET", 404, 196
                    path = f"/{r.choice(['admin', 'phpmyadmin', '.env', 'wp-admin', 'backup.zip', 'config.php'])}"
                f.write(f'{ip} - - [{ts.strftime("%d/%b/%Y:%H:%M:%S +0000")}] "{method} {path} HTTP/1.1" {status} {size} '
                        f'"{r.choice(REFS)}" "{ua}" "-"\n')
                n += 1
    print(f"Wrote {n:,} log lines to {os.path.abspath(a.out)}")


if __name__ == "__main__":
    main()
