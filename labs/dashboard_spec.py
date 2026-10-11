# Databricks notebook source
# MAGIC %md
# MAGIC # dashboard_spec · 实验 09 仪表盘的定义 (the lab 09 dashboard definition)
# MAGIC
# MAGIC 实验 09b 用 `%run ./dashboard_spec` 加载本笔记本：这里只有定义，不运行任何东西。它生成与实验 09 手动搭建的相同的 AI/BI 仪表盘。
# MAGIC
# MAGIC Lab 09b loads this notebook with `%run ./dashboard_spec`: it only holds definitions; nothing runs here. It builds the same AI/BI dashboard that lab 09 builds by hand.

# COMMAND ----------

# 参考版用自己的标题，不会覆盖你在实验 09 中手动搭建的仪表盘 (the reference copy has its own title, so it never overwrites the dashboard you build by hand in lab 09)
DASHBOARD_TITLE = "MT5 交易概览 · {name} · 参考 (reference)"
USD = {"type": "number-currency", "currencyCode": "USD", "abbreviation": "compact", "decimalPlaces": {"type": "max", "places": 1}}
DAY = 'DATE_TRUNC("DAY", `deal_date`)'


def _query(dataset, fields, name="main_query"):
    return {"name": name, "query": {"datasetName": dataset, "disaggregated": False,
                                    "fields": [{"name": n, "expression": e} for n, e in fields]}}


def _counter(name, title, field, expr, x):
    return {"widget": {"name": name,
                       "queries": [_query("daily_volume", [(field, expr), ("daily(deal_date)", DAY)])],
                       "spec": {"version": 2, "widgetType": "counter",
                                "encodings": {"value": {"fieldName": field, "displayName": title, "format": USD},
                                              "period": {"fieldName": "daily(deal_date)"}},
                                "frame": {"showTitle": True, "title": title}}},
            "position": {"x": x, "y": 3, "width": 6, "height": 3}}


def trading_overview(catalog: str, schema: str) -> dict:
    """实验 09 的仪表盘：三个数据集、一个日期筛选器、两个 KPI、三张图 (the lab 09 dashboard: three datasets, a date filter, two KPIs, three charts)."""
    fq = f"`{catalog}`.`{schema}`"
    return {
        "datasets": [
            {"name": "daily_volume", "displayName": "每日成交 (Daily volume)",
             "queryLines": ["SELECT deal_date, server_id, symbol, asset_class, deals, lots, notional_usd, client_pnl_usd ",
                            f"FROM {fq}.gold_daily_symbol_volume"]},
            {"name": "funding", "displayName": "出入金 (Funding)",
             "queryLines": ["SELECT deal_date, brand, method, deposits_usd, withdrawals_usd, net_funding_usd ",
                            f"FROM {fq}.gold_funding_daily"]},
            {"name": "top_symbols", "displayName": "名义金额前 10 的品种 (Top 10 symbols)",
             "queryLines": ["SELECT deal_date, symbol, asset_class, notional_usd ",
                            f"FROM {fq}.gold_daily_symbol_volume ",
                            "WHERE symbol IN (SELECT symbol ",
                            f"FROM {fq}.gold_daily_symbol_volume ",
                            "GROUP BY symbol ORDER BY sum(notional_usd) DESC LIMIT 10)"]},
        ],
        "pages": [{
            "name": "overview", "displayName": "交易概览 (Trading overview)",
            "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1",
            "layout": [
                {"widget": {"name": "title", "multilineTextboxSpec": {"lines": ["## MT5 交易概览 (Trading overview)\n"]}},
                 "position": {"x": 0, "y": 0, "width": 12, "height": 1}},
                {"widget": {"name": "filter_dates",
                            "queries": [_query("daily_volume", [("deal_date", "`deal_date`")], "volume_dates"),
                                        _query("funding", [("deal_date", "`deal_date`")], "funding_dates"),
                                        _query("top_symbols", [("deal_date", "`deal_date`")], "top_symbol_dates")],
                            "spec": {"version": 2, "widgetType": "filter-date-range-picker",
                                     "encodings": {"fields": [
                                         {"fieldName": "deal_date", "displayName": "成交日期 (Deal date)", "queryName": "volume_dates"},
                                         {"fieldName": "deal_date", "displayName": "成交日期 (Deal date)", "queryName": "funding_dates"},
                                         {"fieldName": "deal_date", "displayName": "成交日期 (Deal date)", "queryName": "top_symbol_dates"}]},
                                     "frame": {"showTitle": True, "title": "日期 (Date range)"}}},
                 "position": {"x": 0, "y": 1, "width": 4, "height": 2}},
                {"widget": {"name": "subtitle", "multilineTextboxSpec": {"lines": [
                    "数据来自你自己的 gold 表。右上角的计算资源可以切换到 Lakehouse RT 仓库。<br>",
                    "Data from your own gold tables. Switch the compute at the top right to the Lakehouse RT warehouse."]}},
                 "position": {"x": 4, "y": 1, "width": 8, "height": 2}},
                _counter("kpi_notional", "名义金额 (Notional, USD)", "sum(notional_usd)", "SUM(`notional_usd`)", 0),
                _counter("kpi_client_pnl", "客户盈亏 (Client P&L, USD)", "sum(client_pnl_usd)", "SUM(`client_pnl_usd`)", 6),
                {"widget": {"name": "notional_trend",
                            "queries": [_query("daily_volume", [("daily(deal_date)", DAY), ("sum(notional_usd)", "SUM(`notional_usd`)"),
                                                                ("asset_class", "`asset_class`")])],
                            "spec": {"version": 3, "widgetType": "line",
                                     "encodings": {
                                         "x": {"fieldName": "daily(deal_date)", "scale": {"type": "temporal"}, "displayName": "日期 (Date)"},
                                         "y": {"fieldName": "sum(notional_usd)", "scale": {"type": "quantitative"},
                                               "displayName": "名义金额 (Notional, USD)", "format": USD},
                                         "color": {"fieldName": "asset_class", "scale": {"type": "categorical"},
                                                   "displayName": "资产类别 (Asset class)"}},
                                     "frame": {"showTitle": True, "title": "每日名义金额 · 按资产类别 (Daily notional by asset class)"}}},
                 "position": {"x": 0, "y": 6, "width": 12, "height": 6}},
                {"widget": {"name": "top_symbols",
                            "queries": [_query("top_symbols", [("symbol", "`symbol`"), ("sum(notional_usd)", "SUM(`notional_usd`)")])],
                            "spec": {"version": 3, "widgetType": "bar",
                                     "encodings": {
                                         "x": {"fieldName": "symbol", "scale": {"type": "categorical", "sort": {"by": "value"}},
                                               "displayName": "品种 (Symbol)"},
                                         "y": {"fieldName": "sum(notional_usd)", "scale": {"type": "quantitative"},
                                               "displayName": "名义金额 (Notional, USD)", "format": USD}},
                                     "frame": {"showTitle": True, "title": "名义金额最大的 10 个品种 (Top 10 symbols by notional)"}}},
                 "position": {"x": 0, "y": 12, "width": 6, "height": 6}},
                {"widget": {"name": "funding_by_method",
                            "queries": [_query("funding", [("method", "`method`"), ("sum(net_funding_usd)", "SUM(`net_funding_usd`)")])],
                            "spec": {"version": 3, "widgetType": "bar",
                                     "encodings": {
                                         "x": {"fieldName": "method", "scale": {"type": "categorical", "sort": {"by": "value"}},
                                               "displayName": "支付方式 (Method)"},
                                         "y": {"fieldName": "sum(net_funding_usd)", "scale": {"type": "quantitative"},
                                               "displayName": "净入金 (Net funding, USD)", "format": USD}},
                                     "frame": {"showTitle": True, "title": "各支付方式的净入金 (Net funding by method)"}}},
                 "position": {"x": 6, "y": 12, "width": 6, "height": 6}},
            ],
        }],
        "uiSettings": {"theme": {
            "canvasBackgroundColor": {"light": "#FCFCFC", "dark": "#1F272D"},
            "widgetBackgroundColor": {"light": "#FFFFFF", "dark": "#11171C"},
            "fontColor": {"light": "#11171C", "dark": "#E8ECF0"},
            "selectionColor": {"light": "#2272B4", "dark": "#8ACAFF"},
            "visualizationColors": ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00", "#56B4E9", "#F0E442"],
            "widgetHeaderAlignment": "LEFT"}},
    }
