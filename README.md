# Project 5 - Grafana Dashboard for Web Server Logs (Kaggle)

**Dataset:** *Web Server Access Logs* (`eliasdabbas/web-server-access-logs` on Kaggle) - a real Apache "combined" access log
from an e-commerce site (~10 million requests, Jan 2019, lots of bots, 404s and 5xx errors).
**Stack:** Python parses the raw log -> **PostgreSQL** -> **Grafana** (pre-provisioned data source + 15-panel dashboard).

> Because the real log is huge (3+ GB), the loader reads the first N lines (default suggestion: 500,000). No Kaggle account?
> Generate a realistic log with `scripts/generate_sample_logs.py` - same format, includes a 5xx outage and a 404 scanner.

```
05-grafana-server-logs/
├── docker-compose.yml                       # PostgreSQL 16 + Grafana 11
├── requirements.txt
├── sql/init.sql                             # table access_logs (auto-created on first start)
├── scripts/
│   ├── download_data.py                     # Kaggle download
│   ├── generate_sample_logs.py              # synthetic Apache log
│   ├── log_parser.py                        # regex parser + bot/browser/OS classifier
│   └── load_logs.py                         # parse + bulk load (COPY) into PostgreSQL
├── tools/build_dashboard.py                 # generates the dashboard JSON (edit panels here)
└── grafana/
    ├── provisioning/datasources/datasource.yml   # auto-connects Grafana to PostgreSQL
    ├── provisioning/dashboards/dashboards.yml    # auto-loads dashboards
    └── dashboards/weblogs.json                   # the dashboard
```

## 1. Install (one time)
* **Docker Desktop** - https://www.docker.com/products/docker-desktop
* **Python 3.9+** - https://www.python.org/downloads (tick "Add Python to PATH")

## 2. Run it
```bash
docker compose up -d                        # PostgreSQL + Grafana (first time downloads images)
python -m venv venv
#   Windows: venv\Scripts\activate       Mac/Linux: source venv/bin/activate
pip install -r requirements.txt

python scripts/download_data.py             # needs Kaggle token; or download access.log manually into data/
python scripts/load_logs.py --file data/access.log --limit 500000
```
Open **http://localhost:3000** -> login `admin` / `admin` (skip the password change) -> the dashboard
**"Web Server Logs - Traffic & Errors"** is the home page. (Menu -> Dashboards if not.)

### About timestamps
The loader **shifts all timestamps so the newest log line is "now"** (default), which lets the dashboard's "last 7 days" work.
For the Kaggle file this means the dates are not the real 2019 ones. To keep real dates: add `--no-shift`, then in Grafana set the
time picker (top right) to an absolute range such as *2019-01-22 -> 2019-01-27*.

## 3. Kaggle API token (only for option B automated download)
Kaggle -> profile picture -> **Settings -> API -> Create New Token** -> save `kaggle.json` into `C:\Users\<you>\.kaggle\`
(Mac/Linux: `~/.kaggle/`). Or simply download the file in your browser from
https://www.kaggle.com/datasets/eliasdabbas/web-server-access-logs and place `access.log` in `data/`.

## 4. What the dashboard shows
| Row | Panels |
|---|---|
| KPIs | total requests, unique visitors, bandwidth, error rate (colour thresholds) |
| Traffic | requests over time stacked by 2xx/3xx/4xx/5xx, status-code donut |
| Health | bandwidth over time, error-rate % over time (spot outages) |
| Content | top 10 paths, browser share, bots vs humans |
| Patterns | requests by hour of day, top client IPs (with error counts) |
| Problems | top 404 paths (scanners / broken links), most recent errors |

Variables at the top: **HTTP method** and **Traffic type** (human / bot / unknown). Try choosing only `bot`.

## 5. Customising
* Change or add panels: edit `tools/build_dashboard.py`, run `python tools/build_dashboard.py`, then refresh Grafana
  (provisioned dashboards reload within ~10 s). Or edit in the Grafana UI ("Save as" a copy - provisioned files are read from disk).
* Add **alerts**: panel -> Alert tab -> e.g. "error rate > 10% for 5 min" (configure a contact point under Alerting).
* Query the data yourself: `docker exec -it weblogs-postgres psql -U weblogs -d weblogs` then e.g.
  `SELECT status, count(*) FROM access_logs GROUP BY 1 ORDER BY 2 DESC;`
* Want **Loki** / Elasticsearch instead of SQL? The same parser can feed them; Grafana also has Elasticsearch data sources.

## 6. Stop / clean up
```bash
docker compose down        # stop (keeps data)
docker compose down -v     # stop and delete all data
```
## Dashboard

<img width="988" height="910" alt="Screenshot 2026-10-05 020600" src="https://github.com/user-attachments/assets/1a54101f-e128-4e7d-b0b8-d498ab4a1948" />

<img width="990" height="912" alt="Screenshot 2026-10-05 020607" src="https://github.com/user-attachments/assets/54927e76-51c4-45eb-ba0f-73fbf0764c64" />


## Troubleshooting
| Problem | Fix |
|---|---|
| `Cannot connect to PostgreSQL on localhost:5433` | wait 10-20 s after `docker compose up -d`; check `docker compose ps` |
| Dashboard shows "No data" | run a loader script; then set time range to *Last 7 days* (or the original dates with `--no-shift`) |
| Panels show "datasource not found" | `docker compose logs grafana` - ensure `grafana/provisioning` mounted; restart: `docker compose restart grafana` |
| Variables empty | table has no rows yet (load data first) and refresh the page |
| Port 3000 busy | change `"3000:3000"` to e.g. `"3001:3000"` in docker-compose.yml |
| Loader slow | lower `--limit`; 500k rows takes about a minute |

> Verified in the authoring sandbox: log parser (tested on both the synthetic log and a real-format Kaggle line) and dashboard JSON validity.
> Not run there (no Docker): the Grafana/PostgreSQL containers. If a panel reports a SQL error, open it -> Edit -> the query is shown in full.
