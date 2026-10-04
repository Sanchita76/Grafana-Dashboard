"""Builds grafana/dashboards/weblogs.json. Edit the panels here and re-run:  python tools/build_dashboard.py"""
import json, os

DS = {"type": "grafana-postgresql-datasource", "uid": "weblogs-pg"}
F = "$__timeFilter(ts) AND method IN ($method) AND traffic_type IN ($traffic_type)"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "grafana", "dashboards", "weblogs.json")
_id = [0]


def target(sql, fmt):
    return [{"refId": "A", "datasource": DS, "editorMode": "code", "format": fmt, "rawQuery": True, "rawSql": sql}]


def panel(ptype, title, x, y, w, h, sql, fmt="table", defaults=None, options=None, overrides=None, desc=""):
    _id[0] += 1
    return {"id": _id[0], "type": ptype, "title": title, "description": desc, "datasource": DS,
            "gridPos": {"x": x, "y": y, "w": w, "h": h}, "targets": target(sql, fmt),
            "fieldConfig": {"defaults": defaults or {}, "overrides": overrides or []}, "options": options or {}}


def color(name, c):
    return {"matcher": {"id": "byName", "options": name},
            "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": c}}]}


STAT_OPT = {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}, "colorMode": "value",
            "graphMode": "area", "textMode": "auto", "justifyMode": "center"}
PIE_OPT = {"pieType": "donut", "displayLabels": ["percent"], "legend": {"displayMode": "table", "placement": "right",
           "values": ["value"]}, "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": True},
           "tooltip": {"mode": "single"}}
BAR_OPT = {"orientation": "horizontal", "displayMode": "gradient", "showUnfilled": True, "valueMode": "color",
           "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": True}}
TS_LEGEND = {"legend": {"displayMode": "list", "placement": "bottom"}, "tooltip": {"mode": "multi", "sort": "desc"}}
STATUS_COLORS = [color("2xx", "green"), color("3xx", "blue"), color("4xx", "orange"), color("5xx", "red")]

P = []
# ---- Row 1: KPIs
P.append(panel("stat", "Total requests", 0, 0, 6, 4, f"SELECT count(*) AS requests FROM access_logs WHERE {F}",
               defaults={"unit": "short", "color": {"mode": "fixed", "fixedColor": "blue"}}, options=STAT_OPT))
P.append(panel("stat", "Unique visitors (IPs)", 6, 0, 6, 4, f"SELECT count(DISTINCT ip) AS visitors FROM access_logs WHERE {F}",
               defaults={"unit": "short", "color": {"mode": "fixed", "fixedColor": "purple"}}, options=STAT_OPT))
P.append(panel("stat", "Bandwidth served", 12, 0, 6, 4, f"SELECT COALESCE(sum(bytes),0) AS bytes FROM access_logs WHERE {F}",
               defaults={"unit": "bytes", "color": {"mode": "fixed", "fixedColor": "teal"}}, options=STAT_OPT))
P.append(panel("stat", "Error rate (status >= 400)", 18, 0, 6, 4,
               f"SELECT 100.0 * count(*) FILTER (WHERE status >= 400) / NULLIF(count(*), 0) AS error_rate FROM access_logs WHERE {F}",
               defaults={"unit": "percent", "decimals": 2, "color": {"mode": "thresholds"},
                         "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None},
                                                                      {"color": "orange", "value": 5}, {"color": "red", "value": 10}]}},
               options={**STAT_OPT, "colorMode": "background"}))
# ---- Row 2
P.append(panel("timeseries", "Requests over time by status class", 0, 4, 16, 8,
               f"SELECT $__timeGroupAlias(ts, $__interval), status_class AS metric, count(*) AS value FROM access_logs WHERE {F} GROUP BY 1, 2 ORDER BY 1",
               fmt="time_series", defaults={"unit": "short", "custom": {"drawStyle": "bars", "fillOpacity": 80, "lineWidth": 1,
                                            "stacking": {"mode": "normal", "group": "A"}}}, options=TS_LEGEND, overrides=STATUS_COLORS))
P.append(panel("piechart", "HTTP status codes", 16, 4, 8, 8,
               f"SELECT status::text AS status, count(*) AS requests FROM access_logs WHERE {F} GROUP BY 1 ORDER BY 2 DESC", options=PIE_OPT))
# ---- Row 3
P.append(panel("timeseries", "Bandwidth over time", 0, 12, 12, 8,
               f"SELECT $__timeGroupAlias(ts, $__interval), sum(bytes) AS \"bytes served\" FROM access_logs WHERE {F} GROUP BY 1 ORDER BY 1",
               fmt="time_series", defaults={"unit": "bytes", "color": {"mode": "fixed", "fixedColor": "teal"},
                                            "custom": {"drawStyle": "line", "fillOpacity": 25, "lineWidth": 2}}, options=TS_LEGEND))
P.append(panel("timeseries", "Error rate over time (%)", 12, 12, 12, 8,
               f"SELECT $__timeGroupAlias(ts, $__interval), 100.0 * count(*) FILTER (WHERE status >= 400) / count(*) AS \"errors %\", "
               f"100.0 * count(*) FILTER (WHERE status >= 500) / count(*) AS \"server errors (5xx) %\" FROM access_logs WHERE {F} GROUP BY 1 ORDER BY 1",
               fmt="time_series", defaults={"unit": "percent", "custom": {"drawStyle": "line", "fillOpacity": 15, "lineWidth": 2}},
               options=TS_LEGEND, overrides=[color("errors %", "orange"), color("server errors (5xx) %", "red")],
               desc="Watch for spikes - a burst of 5xx usually means an outage or a bad deploy."))
# ---- Row 4
P.append(panel("bargauge", "Top 10 requested paths", 0, 20, 12, 9,
               f"SELECT left(path, 60) AS path, count(*) AS requests FROM access_logs WHERE {F} GROUP BY 1 ORDER BY 2 DESC LIMIT 10",
               defaults={"color": {"mode": "continuous-BlYlRd"}}, options=BAR_OPT))
P.append(panel("piechart", "Browsers", 12, 20, 6, 9,
               f"SELECT browser, count(*) AS requests FROM access_logs WHERE {F} GROUP BY 1 ORDER BY 2 DESC LIMIT 8", options=PIE_OPT))
P.append(panel("piechart", "Bots vs humans", 18, 20, 6, 9,
               f"SELECT traffic_type, count(*) AS requests FROM access_logs WHERE {F} GROUP BY 1 ORDER BY 2 DESC", options=PIE_OPT))
# ---- Row 5
P.append(panel("barchart", "Requests by hour of day", 0, 29, 12, 8,
               f"SELECT to_char(ts, 'HH24') AS hour, count(*) AS requests FROM access_logs WHERE {F} GROUP BY 1 ORDER BY 1",
               defaults={"color": {"mode": "fixed", "fixedColor": "blue"}},
               options={"xField": "hour", "orientation": "vertical", "legend": {"displayMode": "hidden"}, "showValue": "never"}))
P.append(panel("table", "Top client IPs", 12, 29, 12, 8,
               f"SELECT ip, count(*) AS requests, sum(bytes) AS bytes, count(*) FILTER (WHERE status >= 400) AS errors, "
               f"max(traffic_type) AS type FROM access_logs WHERE {F} GROUP BY ip ORDER BY requests DESC LIMIT 15",
               overrides=[{"matcher": {"id": "byName", "options": "bytes"}, "properties": [{"id": "unit", "value": "bytes"}]},
                          {"matcher": {"id": "byName", "options": "requests"},
                           "properties": [{"id": "custom.cellOptions", "value": {"type": "gauge", "mode": "gradient"}}]}],
               options={"showHeader": True, "cellHeight": "sm"}))
# ---- Row 6
P.append(panel("bargauge", "Top 404 (not found) paths", 0, 37, 10, 9,
               f"SELECT left(path, 50) AS path, count(*) AS hits FROM access_logs WHERE {F} AND status = 404 GROUP BY 1 ORDER BY 2 DESC LIMIT 10",
               defaults={"color": {"mode": "fixed", "fixedColor": "orange"}}, options=BAR_OPT))
P.append(panel("table", "Most recent errors (status >= 400)", 10, 37, 14, 9,
               f"SELECT ts AS time, ip, method, left(path, 50) AS path, status, traffic_type AS type FROM access_logs WHERE {F} AND status >= 400 ORDER BY ts DESC LIMIT 50",
               overrides=[{"matcher": {"id": "byName", "options": "status"}, "properties": [
                   {"id": "custom.cellOptions", "value": {"type": "color-background"}},
                   {"id": "color", "value": {"mode": "thresholds"}},
                   {"id": "thresholds", "value": {"mode": "absolute", "steps": [
                       {"color": "orange", "value": None}, {"color": "red", "value": 500}]}}]}],
               options={"showHeader": True, "cellHeight": "sm"}))


def var(name, label, sql):
    return {"name": name, "label": label, "type": "query", "datasource": DS, "query": sql, "refresh": 1, "multi": True,
            "includeAll": True, "current": {"selected": True, "text": ["All"], "value": ["$__all"]}, "sort": 1}


dash = {"uid": "weblogs-overview", "title": "Web Server Logs - Traffic & Errors", "tags": ["logs", "nginx", "apache", "kaggle"],
        "timezone": "browser", "schemaVersion": 39, "version": 1, "editable": True, "refresh": "1m",
        "time": {"from": "now-7d", "to": "now"}, "annotations": {"list": []}, "graphTooltip": 1,
        "templating": {"list": [var("method", "HTTP method", "SELECT DISTINCT method FROM access_logs ORDER BY 1"),
                                var("traffic_type", "Traffic type", "SELECT DISTINCT traffic_type FROM access_logs ORDER BY 1")]},
        "panels": P}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(dash, open(OUT, "w", encoding="utf-8"), indent=2)
print("Wrote", os.path.abspath(OUT), "with", len(P), "panels")
