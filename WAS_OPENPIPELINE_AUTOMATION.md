# WAS OpenPipeline Automation Plan

## Purpose

Programmatically migrate the repeated parsing and reusable counting logic from the **Universal WAS Dashboard** into Dynatrace OpenPipeline while preserving the existing dashboard tile numbering.

The dashboard spreadsheet remains the source inventory for tiles **1–89**.

The implementation must create:

1. Common WAS parsing and normalization in **WAS Base**
2. WAS-specific classification in **WAS Apps**
3. A small set of reusable counter/value metrics
4. Simplified dashboard DQL that consumes normalized fields or extracted metrics
5. Backups, validation reports, and rollback artifacts

---

## Important operating rule

Do **not** create one OpenPipeline processor or metric for every dashboard tile.

The 89 dashboard tiles are outputs. They should consume a smaller reusable model consisting of:

- standardized log attributes
- classification flags
- approximately 12 foundation metrics
- dashboard-only calculations for percentages, joins, rankings, distinct counts, and tables

---

## Existing Dynatrace design

```text
Incoming WAS logs
        |
        v
Dynamic route: WAS Apps
        |
        v
Pipeline group: WAS
        |
        +-- WAS Base runs first
        |
        +-- WAS Apps runs second
        |
        v
Grail logs and extracted metrics
        |
        v
Universal WAS dashboard
```

Existing identifiers observed:

```text
Base pipeline name: WAS Base
Base pipeline custom ID: pipeline_WAS_Base_2065

Member pipeline name: WAS Apps
Member pipeline custom ID: pipeline_WAS_Apps_2229

Pipeline group name: WAS
Dynamic route name: WAS Apps
```

Do not assume the custom ID is the Settings object ID. Discover and retain the actual Settings object IDs.

---

## Tooling decision

Use the existing Dynatrace `dtctl` Docker image for:

- authentication verification
- DQL queries
- environment discovery
- inventory export
- Settings object discovery when supported
- post-deployment validation

Before applying anything, inspect the installed `dtctl` version and available commands:

```bash
dtctl version
dtctl --help
dtctl get --help
dtctl apply --help
dtctl settings --help
```

Do not invent unsupported `dtctl` commands.

### Preferred deployment method

OpenPipeline is represented by dedicated Dynatrace Settings objects. Use one of these methods, in order:

1. Existing `dtctl` Settings-resource support, if the installed version exposes safe get/apply operations for the required schemas.
2. Monaco Settings configuration and `monaco deploy --dry-run`, followed by `monaco deploy`.
3. Direct Settings API only when neither option above is usable.

The agent must select the method after inspecting the actual container and exported resources.

---

# Safety requirements

## Mandatory before any write

1. Confirm the target environment is **TEST**.
2. Confirm authenticated identity and endpoint.
3. Export all current WAS-related OpenPipeline objects.
4. Export the complete Logs dynamic-routing object.
5. Save checksums of every exported file.
6. Generate a proposed diff.
7. Run schema validation or a dry run.
8. Stop before the actual apply unless the user explicitly authorizes deployment.

Never overwrite the global dynamic-routing object with a partial file.

Never delete or disable unrelated routes, pipelines, pipeline groups, processors, or permissions.

Never hardcode credentials or tokens.

Never print token values.

---

# Repository layout to create

```text
openpipeline-was/
├── README.md
├── manifest.yaml
├── environments.yaml
├── source/
│   ├── dashboard-tile-map.csv
│   └── dashboard-tile-map.xlsx
├── inventory/
│   ├── before/
│   └── after/
├── schemas/
├── generated/
│   ├── was-base/
│   ├── was-apps/
│   ├── pipeline-group/
│   ├── routing/
│   └── dashboard/
├── validation/
│   ├── sample-logs/
│   ├── query-results/
│   └── reports/
├── rollback/
└── scripts/
    ├── discover.py
    ├── export_current.py
    ├── inspect_spreadsheet.py
    ├── generate_plan.py
    ├── validate_config.py
    ├── compare_old_new.py
    └── rollback.py
```

If the existing repository has an established dated-output structure, follow that structure instead of creating a conflicting one.

---

# Spreadsheet columns

Preserve the existing `tile_#` numbering and add these columns:

```text
design_group
base_processing
apps_processing
foundation_metric
metric_type
dashboard_logic
migration_action
validation_query
migration_status
notes
```

Allowed `migration_action` values:

```text
BASE_ATTRIBUTE
APPS_ATTRIBUTE
COUNTER_METRIC
VALUE_METRIC
DASHBOARD_ONLY
HYBRID
```

Allowed `migration_status` values:

```text
NOT_STARTED
MAPPED
GENERATED
DRY_RUN_PASSED
DEPLOYED_TEST
VALIDATED
ROLLED_BACK
```

---

# Tile grouping: preserve Excel numbers

| Design group | Excel tile numbers | Area | Primary treatment |
|---|---:|---|---|
| G01 | 1–4 | Blast radius, impacted/healthy apps, total apps | Apps fields + counters + dashboard calculations |
| G02 | 5 | Hourly billed bytes | Dashboard only; system dataset |
| G03 | 6 | Correlated versus partial errors | Base fields + Apps state + counters + percentage |
| G04 | 7–10 | Splunk versus Dynatrace server comparison | Dashboard only; lookup/join |
| G05 | 11–12 | Downstream dependency count and percentage | Apps flag + counter + percentage |
| G06 | 13 | Noise-to-signal ratio | Apps signal classification + counters + ratio |
| G07 | 14–15 | Host mismatch and comparison | Dashboard only; lookup/join |
| G08 | 16 | Anomaly spike baseline | Error counter + dashboard baseline |
| G09 | 17–25 | Failure reasons, categories, hosts, apps, messages | Base fields + Apps classification + hybrid |
| G10 | 26–34 | Error rates, status, totals, velocity, severity | Counters + dashboard calculations |
| G11 | 35–46 | Execution type, intervals, activity and signal trends | Attributes + counters + dashboard trends |
| G12 | 47–51 | Overall rate, events, hosts and ingestion overview | Hybrid; inventory queries stay in dashboard |
| G13 | 52–58 | HTTP failures, statuses and timeouts | Base HTTP fields + counters |
| G14 | 59–60 | Downstream dependency percentage/count | Apps flag + counter + dashboard percentage |
| G15 | 61–64 | GUID patterns, critical failure and retry signals | Attributes; detailed analysis remains logs |
| G16 | 65–69 | Log family, correlation, HTTP summary, signals | Apps fields + counters + dashboard |
| G17 | 70–75 | Log family, signal, GUID patterns and retry rate | Apps fields + counters + dashboard |
| G18 | 76–81 | Ingestion, server/source inventory, Splunk comparison | Dashboard only or hybrid |
| G19 | 82–83 | Grail storage | Dashboard only; system buckets |
| G20 | 84–85 | Correlated/partial errors and ingestion totals | Counters + dashboard percentage |
| G21 | 86 | Retention days | Dashboard only; system metadata |
| G22 | 87–89 | Error patterns, critical failures, retry and impact rank | Attributes/counters + dashboard ranking |

All tile numbers **1–89** must appear exactly once in the generated coverage report.

---

# WAS Base responsibilities

WAS Base performs only logic that is common across the WAS estate.

## Required normalized attributes

Use a consistent namespace. Prefer the following unless existing enterprise naming standards require different names:

```text
was.log_level
was.severity
was.message
was.message_group
was.exception.name
was.exception.message
was.reporter_class
was.request_guid
was.correlation_id
was.guid
was.creation_time
was.server_name
was.host_name
was.log_type
was.http.method
was.http.status
was.http.status_family
was.duration_ms
```

## Base processing tasks

1. Parse XML once.
2. Extract common XML elements safely.
3. Preserve original `content`.
4. Normalize severity values:
   - ERROR
   - WARN
   - INFO
   - DEBUG
   - FATAL
   - UNKNOWN
5. Extract HTTP status and method when present.
6. Convert numeric fields to numeric types.
7. Add a parse-success indicator.
8. Do not remove troubleshooting fields unless there is a documented privacy requirement.
9. Do not create a metric dimension from GUIDs, full messages, stack traces, or raw content.

Suggested additional fields:

```text
was.parse.success
was.parse.format
was.is_error
was.is_warning
was.has_exception
was.has_request_guid
was.has_correlation_id
```

---

# WAS Apps responsibilities

WAS Apps performs estate-specific or application-specific derivation after Base parsing.

## Required derived attributes

```text
was.app_code
was.app_name
was.log_family
was.failure_reason
was.failure_category
was.execution_type
was.signal_type
was.timeout_flag
was.retry_flag
was.dependency_flag
was.correlation_state
was.source_class
```

## Classification rules

Generate these rules from the existing dashboard DQL rather than guessing.

For each derived attribute, document:

```text
attribute
source fields
matching logic
fallback value
tiles consuming it
expected cardinality
```

Use deterministic fallback values such as `unknown`, not null, when this improves grouping.

Do not classify a record as an error solely because an arbitrary word occurs in a long stack trace without reproducing the dashboard’s current logic.

---

# Foundation metrics

Create reusable metrics rather than tile-specific metrics.

| Metric ID | Proposed key | Type | Supports Excel tiles |
|---|---|---|---|
| M01 | `was.logs.count` | Counter | 4, 30, 35–51, 65, 70, 76–81, 85 |
| M02 | `was.errors.count` | Counter | 1–3, 16–34, 47, 84 |
| M03 | `was.warnings.count` | Counter | 34–46 |
| M04 | `was.exceptions.count` | Counter | 17–25, 61–64, 72–73, 87–89 |
| M05 | `was.http.requests.count` | Counter | 52–56, 64, 67 |
| M06 | `was.http.failures.count` | Counter | 52–56, 64, 67 |
| M07 | `was.timeouts.count` | Counter | 57–60 |
| M08 | `was.retries.count` | Counter | 62, 73–75, 88–89 |
| M09 | `was.correlated.count` | Counter | 6, 66, 84 |
| M10 | `was.partial.count` | Counter | 6, 66, 84 |
| M11 | `was.signal.count` | Counter | 13, 40–46, 69, 71 |
| M12 | `was.dependency.count` | Counter | 11–12, 59–60 |
| M13 | `was.duration` | Value | Only tiles using a real numeric duration field |

M13 must not be created unless a numeric duration field exists and its unit is confirmed.

## Candidate metric dimensions

Use only dimensions validated as reasonably low-cardinality:

```text
was.app_code
was.server_name
was.log_type
was.severity
was.failure_category
was.execution_type
was.http.status_family
was.signal_type
```

Before deployment, produce a cardinality report for every proposed dimension.

## Forbidden metric dimensions

```text
was.guid
was.request_guid
was.correlation_id
was.message
was.exception.message
content
stacktrace
```

---

# Dashboard-only logic

Keep the following in dashboard DQL:

- percentages and ratios
- rankings and top-N presentation
- distinct GUID counts and GUID lists
- correlation investigations
- recent-event tables
- full messages and stack traces
- joins and lookups
- Splunk versus Dynatrace comparisons
- host inventory comparisons
- first/last ingestion timestamps
- retention calculations
- Grail storage and billing calculations
- anomaly baselines that compare time windows
- cross-dataset calculations

OpenPipeline may supply normalized fields and counters used by these queries, but it should not attempt to reproduce collection-level query logic on each individual record.

---

# Automated discovery steps

The agent must perform the following read-only sequence.

## 1. Verify runtime

```bash
docker image ls
docker ps -a
```

Identify the existing dtctl image and the established wrapper/compose command. Reuse it.

## 2. Verify authentication without exposing secrets

Run the repository’s existing harmless authenticated command or `dtctl` identity/status command supported by the installed version.

Record:

```text
environment alias
environment URL
authenticated principal when available
dtctl version
container image digest
```

## 3. Discover Settings schemas

Search the TEST environment for current Logs OpenPipeline schemas, including schemas for:

```text
pipelines
pipeline groups
routing
```

Do not hardcode schema IDs from memory. Save the discovered schema IDs and schema definitions under `schemas/`.

## 4. Export current objects

Export:

```text
WAS Base
WAS Apps
WAS pipeline group
complete Logs dynamic-routing object
related sharing/permission objects when exposed
```

Save raw responses under:

```text
inventory/before/
```

## 5. Resolve IDs

For each object, record:

```text
display name
custom ID
Settings object ID
schema ID
owner
sharing/read status
last modified
```

A `403 No read share` is a blocker. Do not attempt a blind replacement.

---

# Spreadsheet analysis

Read the spreadsheet programmatically.

For each tile:

1. Preserve `tile_#`.
2. Read title, calculation, dataset, parsed attributes, parsing source, grouping/dimensions, and notes.
3. Detect repeated parsing logic.
4. Map repeated parsing to Base attributes.
5. Map repeated classifications to Apps attributes.
6. Map simple counts to foundation metrics.
7. Mark query-level logic as dashboard only.
8. Produce a complete tile-to-implementation matrix.

Generate:

```text
generated/tile-coverage.csv
generated/tile-coverage.xlsx
generated/tile-coverage.md
```

Required coverage columns:

```text
tile_#
tile_title
design_group
base_fields
apps_fields
foundation_metrics
dashboard_only_logic
migration_action
covered
validation_method
```

Validation must fail if:

- a tile from 1–89 is missing
- a tile appears more than once
- `covered` is false
- a foundation metric references an undefined normalized field

---

# Configuration generation

Generate the proposed Settings configuration from the exported TEST objects.

## Merge behavior

Perform a structural merge:

- retain existing object IDs when updating
- retain unrelated processors
- retain unrelated routes
- retain existing order unless a documented dependency requires a change
- add new processors with deterministic custom IDs
- update processors by custom ID rather than appending duplicates
- retain existing sharing and ownership metadata where supported

Suggested deterministic IDs:

```text
processor_was_base_normalize_xml_v1
processor_was_apps_classification_v1

metric_was_logs_count_v1
metric_was_errors_count_v1
metric_was_warnings_count_v1
metric_was_exceptions_count_v1
metric_was_http_requests_count_v1
metric_was_http_failures_count_v1
metric_was_timeouts_count_v1
metric_was_retries_count_v1
metric_was_correlated_count_v1
metric_was_partial_count_v1
metric_was_signal_count_v1
metric_was_dependency_count_v1
```

Do not add duplicate processors when an equivalent processor already exists.

---

# Validation before deployment

## Static validation

Validate:

- JSON/YAML syntax
- Settings schema compatibility
- unique custom IDs
- processor ordering
- references between group, Base and member pipeline
- complete routing object
- allowed metric keys
- allowed dimension names
- absence of secrets

## Sample-log validation

Use representative records for:

```text
valid XML error
valid XML warning
XML with exception
XML with request GUID
XML with correlation ID
HTTP 2xx
HTTP 4xx
HTTP 5xx
timeout message
retry message
non-XML WAS log
malformed XML
unknown application
```

For each record, generate expected versus actual normalized attributes.

## Dry run

Use the supported deployment tool:

```bash
monaco deploy --dry-run manifest.yaml
```

or the actual installed dtctl validation/diff operation when it supports these Settings resources.

Save output under:

```text
validation/reports/dry-run.txt
```

A dry-run failure must stop the workflow.

---

# Deployment gate

The agent must stop after producing:

```text
backup location
proposed files
diff summary
tile coverage report
dimension-cardinality report
sample-log validation report
dry-run result
rollback instructions
```

Wait for explicit user authorization before applying to TEST.

The authorization must be unambiguous, for example:

```text
Apply the validated WAS OpenPipeline changes to TEST.
```

Do not interpret “continue,” “looks good,” or similar language as production authorization.

Never apply directly to PROD as part of this workflow.

---

# Post-deployment validation

After authorized TEST deployment:

1. Export the objects again to `inventory/after/`.
2. Confirm Base, Apps, group and routing objects are readable.
3. Confirm the route still targets WAS Apps.
4. Confirm the group still runs WAS Base before WAS Apps.
5. Confirm new logs contain normalized attributes.
6. Confirm each counter begins producing data.
7. Compare old dashboard logic against new fields/metrics.

## Parallel comparison period

Keep existing dashboard queries intact initially.

For each migrated tile, compare old and new results over matching windows:

```text
15 minutes
1 hour
24 hours
```

Produce:

```text
old value
new value
absolute difference
percentage difference
reason for expected difference
pass/fail
```

Suggested tolerance:

```text
counts: exact where logic is equivalent
percentages: within 0.5 percentage points
time-series buckets: document ingestion and bucket-boundary differences
```

Do not replace a dashboard tile until its comparison passes.

---

# Rollback

Rollback must restore the exact exported `inventory/before/` objects.

Rollback triggers include:

- routing loss
- processor errors
- unexpected drop in log volume
- excessive metric cardinality
- parsing regression
- material disagreement with existing dashboard calculations

Generate a rollback command/script but do not run it unless instructed or an approved automated safety condition is met.

---

# Agent deliverables

The coding agent must create:

1. `implementation-plan.md`
2. `tile-coverage.xlsx`
3. `tile-coverage.md`
4. exported before-state objects
5. generated proposed Settings objects
6. a human-readable diff
7. dry-run output
8. sample-log test results
9. cardinality analysis
10. deployment command
11. rollback command
12. post-deployment comparison report template

---

# Prompt for the coding agent

Use the following instruction in PyCharm Copilot/ChatGPT Agent mode:

```text
Read WAS_OPENPIPELINE_AUTOMATION.md completely before taking action.

Use the existing repository conventions, existing virtual environment, existing Dynatrace dtctl Docker image, and existing TEST/PROD authentication setup. Do not create or expose credentials.

This is a guarded configuration-as-code task for Dynatrace OpenPipeline Logs.

First perform read-only discovery:
1. Inspect the installed dtctl version and supported commands.
2. Identify the exact TEST environment.
3. Discover the current Settings schemas for Logs pipelines, pipeline groups, and routing.
4. Export and back up WAS Base, WAS Apps, the WAS pipeline group, and the complete Logs dynamic-routing object.
5. Resolve their actual Settings object IDs and report any 403 sharing blockers.
6. Read the dashboard spreadsheet and preserve tile numbers 1 through 89.
7. Produce a complete tile coverage matrix using the G01–G22 and M01–M13 mappings in this document.
8. Generate proposed Base parsing, Apps classification, and metric-extraction configuration by structurally merging with the exported objects.
9. Validate schemas, IDs, ordering, routing completeness, sample logs, and proposed metric cardinality.
10. Run a dry run or supported no-write validation.
11. Produce a diff, validation summary, and rollback plan.

Do not apply any Dynatrace changes yet. Stop after the dry-run report and ask for explicit authorization.

Do not invent dtctl commands. Inspect --help and use only commands supported by the installed image. If dtctl cannot safely deploy these OpenPipeline Settings objects, generate and validate a Monaco Settings project instead. Never deploy a deprecated monolithic OpenPipeline configuration over existing custom configuration.

Do not replace the global dynamic-routing object with a partial object. Preserve all unrelated routes and their order.

Do not create one metric per dashboard tile. Implement the reusable normalized attributes and foundation metrics defined in this document. Keep joins, distinct GUID logic, rankings, percentages, storage, retention, billing, and inventory comparisons in dashboard DQL.

Run only focused tests, save all command output to the dated output folder, and summarize every generated or modified file.
```

---

# Definition of success

The project is successful when:

- all Excel tiles 1–89 are mapped and accounted for
- common XML parsing occurs once in WAS Base
- WAS-specific classifications occur once in WAS Apps
- reusable counters are created without high-cardinality dimensions
- dashboard-only logic remains in DQL
- current routing and unrelated configuration are preserved
- a repeatable configuration-as-code deployment exists
- TEST validation matches the current dashboard
- rollback is proven before PROD promotion
