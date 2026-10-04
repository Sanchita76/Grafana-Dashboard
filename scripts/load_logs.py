"""Parse an access log and bulk-load it into PostgreSQL (table access_logs).

Examples:
  python scripts/load_logs.py --file data/sample_access.log
  python scripts/load_logs.py --file data/access.log --limit 500000          # Kaggle file, first 500k lines
By default timestamps are SHIFTED so the newest log line is 'now' (so Grafana's default 'last 7 days' view works).
Use --no-shift to keep original timestamps (then set Grafana's time range to the original dates).
"""
import argparse, csv, io, os, sys
from datetime import datetime, timedelta, timezone
from log_parser import parse_line, peek_ts

COLS = ["ts", "ip", "method", "path", "protocol", "status", "status_class", "bytes", "referrer", "user_agent",
        "browser", "os", "device", "traffic_type"]


def lines(path, limit):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break
            yield line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "sample_access.log"))
    ap.add_argument("--limit", type=int, default=0, help="max lines to read (0 = all)")
    ap.add_argument("--batch", type=int, default=50000)
    ap.add_argument("--no-shift", dest="shift", action="store_false", default=True)
    ap.add_argument("--truncate", action="store_true", default=True, help="empty the table first (default)")
    ap.add_argument("--host", default=os.getenv("PGHOST", "localhost")); ap.add_argument("--port", default=os.getenv("PGPORT", "5433"))
    ap.add_argument("--db", default="weblogs"); ap.add_argument("--user", default="weblogs"); ap.add_argument("--password", default="weblogs_pw")
    a = ap.parse_args()
    if not os.path.exists(a.file):
        sys.exit(f"File not found: {a.file}\nRun python scripts/generate_sample_logs.py first (or download the Kaggle file).")
    import psycopg2

    offset = timedelta(0)
    if a.shift:
        last = None
        for ln in lines(a.file, a.limit):
            t = peek_ts(ln)
            if t and (last is None or t > last):
                last = t
        if last is None:
            sys.exit("No parsable timestamps found - is this an Apache/Nginx combined log?")
        offset = datetime.now(timezone.utc) - last
        print(f"Shifting timestamps by {offset.days} days so the newest entry is 'now'.")

    try:
        conn = psycopg2.connect(host=a.host, port=a.port, dbname=a.db, user=a.user, password=a.password)
    except psycopg2.OperationalError as e:
        sys.exit(f"Cannot connect to PostgreSQL on {a.host}:{a.port}: {e}\nIs 'docker compose up -d' running?")
    cur = conn.cursor()
    if a.truncate:
        cur.execute("TRUNCATE access_logs"); conn.commit()

    def flush(buf):
        if not buf.tell():
            return
        buf.seek(0)
        cur.copy_expert(f"COPY access_logs ({','.join(COLS)}) FROM STDIN WITH (FORMAT csv)", buf)
        conn.commit()

    total = bad = 0
    buf = io.StringIO(); w = csv.writer(buf); n_in_batch = 0
    for ln in lines(a.file, a.limit):
        rec = parse_line(ln)
        if rec is None:
            bad += 1; continue
        rec["ts"] = (rec["ts"] + offset).isoformat()
        w.writerow([rec[c] for c in COLS]); n_in_batch += 1; total += 1
        if n_in_batch >= a.batch:
            flush(buf); buf = io.StringIO(); w = csv.writer(buf); n_in_batch = 0
            print(f"  loaded {total:,} rows...")
    flush(buf)
    cur.execute("ANALYZE access_logs"); conn.commit()
    cur.execute("SELECT count(*), min(ts), max(ts) FROM access_logs")
    cnt, mn, mx = cur.fetchone()
    print(f"Done: {cnt:,} rows in table (skipped {bad:,} unparsable lines). Time range: {mn} -> {mx}")
    conn.close()


if __name__ == "__main__":
    main()
