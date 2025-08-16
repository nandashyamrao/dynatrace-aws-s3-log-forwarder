# ExampleDashboard.json - Dynatrace Dashboard Tile Queries Details

_Generated on 2025-08-16. Tiles with queries: **2**. Total queries: **3**._

---

## Overview
| # | Tile | Type | Visualization | Queries | Preview |
|---:|---|---|---|---:|---|
| 1 | [5xx Errors](#5xx-errors) | data | barChart | 1 | `timeseries total = sum(...)` |
| 2 | [CPU Usage %](#cpu-usage-) | data | lineChart | 2 | `fetch dt.entity.host ...` |

---

## 5xx Errors

**Type:** `data`  
**Visualization:** `barChart`  
**Context:** `root / tiles / 21`

<details>
<summary><strong>Query 1</strong> — 16 lines</summary>

```dql
timeseries total = sum(dt.service.request.count)
| by: dt.entity.service
| filter: http.response.status_code >= 500
  and http.response.status_code < 600
```
</details>

---

## CPU Usage %

**Type:** `data`  
**Visualization:** `lineChart`  
**Context:** `root / tiles / 25`

<details>
<summary><strong>Query 1</strong> — 10 lines</summary>

```dql
fetch dt.entity.host
| fields cpu.usage, entity.name
| sort cpu.usage desc
```
</details>

<details>
<summary><strong>Query 2</strong> — 6 lines</summary>

```dql
fetch dt.entity.process_group
| fields cpu.usage, entity.name
```
</details>

---
