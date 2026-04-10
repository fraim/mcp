# “””
Zephyr Scale Data Center MCP Server

REST API v1  ·  Bearer-token authentication only
Base URL: {ZEPHYR_BASE_URL}/rest/atm/1.0/

## Environment variables

ZEPHYR_BASE_URL   – Jira DC base URL, e.g. https://jira.company.com  (required)
ZEPHYR_API_TOKEN  – Zephyr Scale API Access Token                     (required)
ZEPHYR_VERIFY_SSL – Set to “false” to skip TLS certificate check      (default: true)
“””

from **future** import annotations

import json
import os
import ssl
from typing import Any, Optional

import httpx
from fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

# —————————————————————————

# Runtime configuration

# —————————————————————————

_BASE_URL: str = os.environ.get(“ZEPHYR_BASE_URL”, “”).rstrip(”/”)
_API_TOKEN: str = os.environ.get(“ZEPHYR_API_TOKEN”, “”)
_VERIFY_SSL: bool = (
os.environ.get(“ZEPHYR_VERIFY_SSL”, “true”).lower() not in (“false”, “0”, “no”)
)
_ATM_BASE: str = f”{_BASE_URL}/rest/atm/1.0”

# —————————————————————————

# FastMCP instance

# —————————————————————————

mcp = FastMCP(
name=“zephyr_scale_mcp”,
instructions=(
“MCP server for Zephyr Scale Data Center (API v1). “
“Provides tools to manage test cases, test cycles, test executions, “
“folders and projects. Authentication uses Bearer token only.”
),
)

# —————————————————————————

# Shared HTTP helpers

# —————————————————————————

def _client() -> httpx.AsyncClient:
“”“Build a pre-configured async HTTP client with Bearer-token auth.”””
if not _API_TOKEN:
raise RuntimeError(
“ZEPHYR_API_TOKEN is not set. “
“Generate it via Jira → Profile → Zephyr Scale API Access Tokens.”
)
if not _BASE_URL:
raise RuntimeError(
“ZEPHYR_BASE_URL is not set. “
“Set it to your Jira Data Center base URL, e.g. https://jira.company.com”
)
verify: bool | ssl.SSLContext = _VERIFY_SSL
return httpx.AsyncClient(
headers={
“Authorization”: f”Bearer {_API_TOKEN}”,
“Content-Type”: “application/json”,
“Accept”: “application/json”,
},
verify=verify,
timeout=60.0,
)

def _err(exc: Exception) -> str:
“”“Convert an httpx / generic exception into an actionable error string.”””
if isinstance(exc, httpx.HTTPStatusError):
code = exc.response.status_code
hint = {
401: “Check that ZEPHYR_API_TOKEN is valid and not expired.”,
403: “Your token lacks required permissions for this resource.”,
404: “Resource not found — verify the key / ID and project key.”,
429: “Rate limit exceeded. Wait a moment before retrying.”,
}.get(code, exc.response.text[:300])
return f”HTTP {code}: {hint}”
if isinstance(exc, httpx.TimeoutException):
return “Request timed out. The Jira server took too long to respond.”
if isinstance(exc, httpx.ConnectError):
return f”Connection failed to {_BASE_URL}. Check ZEPHYR_BASE_URL and network access.”
return f”{type(exc).**name**}: {exc}”

def _page(data: dict[str, Any], offset: int) -> dict[str, Any]:
“”“Normalise a Zephyr Scale paginated list response.”””
results: list = data.get(“results”, data.get(“values”, []))
total: int = data.get(“total”, len(results))
return {
“total”: total,
“count”: len(results),
“offset”: offset,
“has_more”: total > offset + len(results),
“next_offset”: (offset + len(results)) if total > offset + len(results) else None,
“results”: results,
}

# —————————————————————————

# Pydantic input models

# —————————————————————————

class _Base(BaseModel):
model_config = ConfigDict(str_strip_whitespace=True, extra=“forbid”)

class ProjectsListInput(_Base):
max_results: int = Field(50, ge=1, le=200, description=“Page size (1–200)”)
start_at: int = Field(0, ge=0, description=“Zero-based pagination offset”)

class ListByProjectInput(_Base):
project_key: str = Field(…, description=“Jira project key, e.g. ‘QA’”)
max_results: int = Field(50, ge=1, le=200, description=“Page size (1–200)”)
start_at: int = Field(0, ge=0, description=“Zero-based pagination offset”)

class TestCaseKeyInput(_Base):
test_case_key: str = Field(…, min_length=1, description=“Test case key, e.g. ‘QA-T42’”)

class TestCaseSearchInput(_Base):
project_key: str = Field(…, description=“Jira project key”)
query: Optional[str] = Field(None, description=“Additional TQL filter, e.g. ‘status = "Approved"’”)
max_results: int = Field(50, ge=1, le=200)
start_at: int = Field(0, ge=0)

class TestCaseCreateInput(_Base):
project_key: str = Field(…, description=“Jira project key”)
name: str = Field(…, min_length=1, max_length=500, description=“Test case name”)
objective: Optional[str] = Field(None, description=“Test objective / description”)
precondition: Optional[str] = Field(None, description=“Preconditions text”)
status: str = Field(“Draft”, description=”‘Draft’ | ‘Approved’ | ‘Deprecated’”)
priority: Optional[str] = Field(None, description=“Priority name, e.g. ‘High’”)
folder: Optional[str] = Field(None, description=“Folder path, e.g. ‘/Regression/Login’”)
labels: Optional[list[str]] = Field(None, description=“Label list”)
owner: Optional[str] = Field(None, description=“Jira username of the owner”)

class TestCaseUpdateInput(_Base):
test_case_key: str = Field(…, description=“Key of the test case to update”)
name: Optional[str] = Field(None)
objective: Optional[str] = Field(None)
status: Optional[str] = Field(None)
priority: Optional[str] = Field(None)
folder: Optional[str] = Field(None)
labels: Optional[list[str]] = Field(None)

class TestCycleKeyInput(_Base):
test_cycle_key: str = Field(…, min_length=1, description=“Test cycle key, e.g. ‘QA-R1’”)

class TestCycleSearchInput(_Base):
project_key: str = Field(…, description=“Jira project key”)
query: Optional[str] = Field(None, description=“Additional TQL filter”)
max_results: int = Field(50, ge=1, le=200)
start_at: int = Field(0, ge=0)

class TestCycleCreateInput(_Base):
project_key: str = Field(…, description=“Jira project key”)
name: str = Field(…, min_length=1, max_length=500, description=“Test cycle name”)
description: Optional[str] = Field(None)
status: str = Field(“Not Started”, description=”‘Not Started’ | ‘In Progress’ | ‘Done’”)
folder: Optional[str] = Field(None, description=“Folder path”)
planned_start_date: Optional[str] = Field(None, description=“ISO-8601 date, e.g. ‘2025-01-01’”)
planned_end_date: Optional[str] = Field(None, description=“ISO-8601 date”)

class ExecutionSearchInput(_Base):
query: str = Field(
…,
description=(
“TQL query string. Examples: “
“‘testCycle = "QA-R1"’, “
“‘testCase = "QA-T42" AND status = "Fail"’, “
“‘projectKey = "QA" AND status IN ("Fail","Blocked")’”
),
)
max_results: int = Field(50, ge=1, le=200)
start_at: int = Field(0, ge=0)

class ExecutionCreateInput(_Base):
project_key: str = Field(…, description=“Jira project key”)
test_case_key: str = Field(…, description=“Test case key, e.g. ‘QA-T42’”)
test_cycle_key: str = Field(…, description=“Test cycle key, e.g. ‘QA-R1’”)
status_name: str = Field(…, description=“Execution status, e.g. ‘Pass’ | ‘Fail’ | ‘In Progress’”)
environment_name: Optional[str] = Field(None, description=“Environment name”)
comment: Optional[str] = Field(None, description=“Free-text execution comment”)
actual_end_date: Optional[str] = Field(None, description=“ISO-8601 datetime”)
executed_by: Optional[str] = Field(None, description=“Jira username of the executor”)

class FolderListInput(_Base):
project_key: str = Field(…, description=“Jira project key”)
folder_type: str = Field(
“TEST_CASE”,
description=”‘TEST_CASE’ | ‘TEST_CYCLE’ | ‘TEST_PLAN’”,
)
max_results: int = Field(50, ge=1, le=200)
start_at: int = Field(0, ge=0)

# ===========================================================================

# Tools

# ===========================================================================

# ── Projects ────────────────────────────────────────────────────────────────

@mcp.tool(
annotations={
“title”: “List Zephyr Scale Projects”,
“readOnlyHint”: True,
“destructiveHint”: False,
“idempotentHint”: True,
“openWorldHint”: False,
}
)
async def zephyr_list_projects(params: ProjectsListInput) -> str:
“”“List all Zephyr Scale projects available in this Data Center instance.

```
Args:
    params: max_results (int, 1-200), start_at (int, ≥0)

Returns:
    str: JSON — {total, count, offset, has_more, next_offset, results: [{id, key, name}]}
"""
async with _client() as c:
    try:
        r = await c.get(
            f"{_ATM_BASE}/project",
            params={"maxResults": params.max_results, "startAt": params.start_at},
        )
        r.raise_for_status()
        return json.dumps(_page(r.json(), params.start_at), indent=2)
    except Exception as exc:
        return _err(exc)
```

# ── Test Cases ───────────────────────────────────────────────────────────────

@mcp.tool(
annotations={
“title”: “List Test Cases”,
“readOnlyHint”: True,
“destructiveHint”: False,
“idempotentHint”: True,
“openWorldHint”: False,
}
)
async def zephyr_list_test_cases(params: ListByProjectInput) -> str:
“”“List all test cases for a Jira project (paginated).

```
Args:
    params: project_key (str), max_results (int), start_at (int)

Returns:
    str: JSON — {total, count, offset, has_more, next_offset, results: [TestCase]}
"""
async with _client() as c:
    try:
        r = await c.get(
            f"{_ATM_BASE}/testcase/search",
            params={
                "query": f'projectKey = "{params.project_key}"',
                "maxResults": params.max_results,
                "startAt": params.start_at,
            },
        )
        r.raise_for_status()
        return json.dumps(_page(r.json(), params.start_at), indent=2)
    except Exception as exc:
        return _err(exc)
```

@mcp.tool(
annotations={
“title”: “Get Test Case”,
“readOnlyHint”: True,
“destructiveHint”: False,
“idempotentHint”: True,
“openWorldHint”: False,
}
)
async def zephyr_get_test_case(params: TestCaseKeyInput) -> str:
“”“Fetch a single test case by its key.

```
Args:
    params: test_case_key (str) — e.g. 'QA-T42'

Returns:
    str: JSON — full TestCase object (key, name, status, priority, folder,
         labels, owner, objective, precondition, testScript, …)
"""
async with _client() as c:
    try:
        r = await c.get(f"{_ATM_BASE}/testcase/{params.test_case_key}")
        r.raise_for_status()
        return json.dumps(r.json(), indent=2)
    except Exception as exc:
        return _err(exc)
```

@mcp.tool(
annotations={
“title”: “Search Test Cases”,
“readOnlyHint”: True,
“destructiveHint”: False,
“idempotentHint”: True,
“openWorldHint”: False,
}
)
async def zephyr_search_test_cases(params: TestCaseSearchInput) -> str:
“”“Search test cases with a TQL filter (appended to the project filter).

```
TQL examples:
  - 'status = "Approved"'
  - 'labels IN ("smoke") AND priority = "High"'
  - 'folder = "/Regression"'

Args:
    params: project_key, query (optional TQL), max_results, start_at

Returns:
    str: JSON — paginated list of matching TestCase objects
"""
base = f'projectKey = "{params.project_key}"'
tql = f"{base} AND {params.query}" if params.query else base

async with _client() as c:
    try:
        r = await c.get(
            f"{_ATM_BASE}/testcase/search",
            params={"query": tql, "maxResults": params.max_results, "startAt": params.start_at},
        )
        r.raise_for_status()
        return json.dumps(_page(r.json(), params.start_at), indent=2)
    except Exception as exc:
        return _err(exc)
```

@mcp.tool(
annotations={
“title”: “Get Test Case Steps”,
“readOnlyHint”: True,
“destructiveHint”: False,
“idempotentHint”: True,
“openWorldHint”: False,
}
)
async def zephyr_get_test_case_steps(params: TestCaseKeyInput) -> str:
“”“Return the test script (steps, BDD, or plain text) for a test case.

```
Args:
    params: test_case_key (str)

Returns:
    str: JSON — {key, testScript: {type, steps: [{index, description,
         testData, expectedResult}]}}
"""
async with _client() as c:
    try:
        r = await c.get(f"{_ATM_BASE}/testcase/{params.test_case_key}")
        r.raise_for_status()
        data = r.json()
        return json.dumps(
            {"key": params.test_case_key, "testScript": data.get("testScript", {})},
            indent=2,
        )
    except Exception as exc:
        return _err(exc)
```

@mcp.tool(
annotations={
“title”: “Create Test Case”,
“readOnlyHint”: False,
“destructiveHint”: False,
“idempotentHint”: False,
“openWorldHint”: False,
}
)
async def zephyr_create_test_case(params: TestCaseCreateInput) -> str:
“”“Create a new test case in Zephyr Scale DC.

```
Args:
    params: project_key, name, objective, precondition, status, priority,
            folder, labels, owner

Returns:
    str: JSON — newly created TestCase object including generated key
"""
body: dict[str, Any] = {
    "projectKey": params.project_key,
    "name": params.name,
    "status": params.status,
}
if params.objective:
    body["objective"] = params.objective
if params.precondition:
    body["precondition"] = params.precondition
if params.priority:
    body["priority"] = {"name": params.priority}
if params.folder:
    body["folder"] = params.folder
if params.labels:
    body["labels"] = params.labels
if params.owner:
    body["owner"] = params.owner

async with _client() as c:
    try:
        r = await c.post(f"{_ATM_BASE}/testcase", content=json.dumps(body))
        r.raise_for_status()
        return json.dumps(r.json(), indent=2)
    except Exception as exc:
        return _err(exc)
```

@mcp.tool(
annotations={
“title”: “Update Test Case”,
“readOnlyHint”: False,
“destructiveHint”: False,
“idempotentHint”: True,
“openWorldHint”: False,
}
)
async def zephyr_update_test_case(params: TestCaseUpdateInput) -> str:
“”“Update fields of an existing test case (partial update — only set fields are sent).

```
Args:
    params: test_case_key + any of: name, objective, status, priority, folder, labels

Returns:
    str: JSON — updated TestCase object
"""
body: dict[str, Any] = {}
for field, value in [
    ("name", params.name),
    ("objective", params.objective),
    ("status", params.status),
    ("folder", params.folder),
    ("labels", params.labels),
]:
    if value is not None:
        body[field] = value
if params.priority is not None:
    body["priority"] = {"name": params.priority}

async with _client() as c:
    try:
        r = await c.put(
            f"{_ATM_BASE}/testcase/{params.test_case_key}",
            content=json.dumps(body),
        )
        r.raise_for_status()
        return json.dumps(r.json(), indent=2)
    except Exception as exc:
        return _err(exc)
```

# ── Test Cycles ──────────────────────────────────────────────────────────────

@mcp.tool(
annotations={
“title”: “List Test Cycles”,
“readOnlyHint”: True,
“destructiveHint”: False,
“idempotentHint”: True,
“openWorldHint”: False,
}
)
async def zephyr_list_test_cycles(params: ListByProjectInput) -> str:
“”“List test cycles (test runs) for a Jira project (paginated).

```
Args:
    params: project_key, max_results, start_at

Returns:
    str: JSON — {total, count, offset, has_more, next_offset, results: [TestCycle]}
"""
async with _client() as c:
    try:
        r = await c.get(
            f"{_ATM_BASE}/testrun/search",
            params={
                "query": f'projectKey = "{params.project_key}"',
                "maxResults": params.max_results,
                "startAt": params.start_at,
            },
        )
        r.raise_for_status()
        return json.dumps(_page(r.json(), params.start_at), indent=2)
    except Exception as exc:
        return _err(exc)
```

@mcp.tool(
annotations={
“title”: “Get Test Cycle”,
“readOnlyHint”: True,
“destructiveHint”: False,
“idempotentHint”: True,
“openWorldHint”: False,
}
)
async def zephyr_get_test_cycle(params: TestCycleKeyInput) -> str:
“”“Fetch a single test cycle by key.

```
Args:
    params: test_cycle_key (str) — e.g. 'QA-R1'

Returns:
    str: JSON — full TestCycle object (key, name, status, folder,
         plannedStartDate, plannedEndDate, items, …)
"""
async with _client() as c:
    try:
        r = await c.get(f"{_ATM_BASE}/testrun/{params.test_cycle_key}")
        r.raise_for_status()
        return json.dumps(r.json(), indent=2)
    except Exception as exc:
        return _err(exc)
```

@mcp.tool(
annotations={
“title”: “Search Test Cycles”,
“readOnlyHint”: True,
“destructiveHint”: False,
“idempotentHint”: True,
“openWorldHint”: False,
}
)
async def zephyr_search_test_cycles(params: TestCycleSearchInput) -> str:
“”“Search test cycles with a TQL filter.

```
TQL examples:
  - 'status = "In Progress"'
  - 'folder = "/Sprint 10"'

Args:
    params: project_key, query (optional TQL), max_results, start_at

Returns:
    str: JSON — paginated list of matching TestCycle objects
"""
base = f'projectKey = "{params.project_key}"'
tql = f"{base} AND {params.query}" if params.query else base

async with _client() as c:
    try:
        r = await c.get(
            f"{_ATM_BASE}/testrun/search",
            params={"query": tql, "maxResults": params.max_results, "startAt": params.start_at},
        )
        r.raise_for_status()
        return json.dumps(_page(r.json(), params.start_at), indent=2)
    except Exception as exc:
        return _err(exc)
```

@mcp.tool(
annotations={
“title”: “Create Test Cycle”,
“readOnlyHint”: False,
“destructiveHint”: False,
“idempotentHint”: False,
“openWorldHint”: False,
}
)
async def zephyr_create_test_cycle(params: TestCycleCreateInput) -> str:
“”“Create a new test cycle in Zephyr Scale DC.

```
Args:
    params: project_key, name, description, status, folder,
            planned_start_date, planned_end_date

Returns:
    str: JSON — newly created TestCycle object including generated key
"""
body: dict[str, Any] = {
    "projectKey": params.project_key,
    "name": params.name,
    "status": params.status,
}
if params.description:
    body["description"] = params.description
if params.folder:
    body["folder"] = params.folder
if params.planned_start_date:
    body["plannedStartDate"] = params.planned_start_date
if params.planned_end_date:
    body["plannedEndDate"] = params.planned_end_date

async with _client() as c:
    try:
        r = await c.post(f"{_ATM_BASE}/testrun", content=json.dumps(body))
        r.raise_for_status()
        return json.dumps(r.json(), indent=2)
    except Exception as exc:
        return _err(exc)
```

# ── Test Executions ──────────────────────────────────────────────────────────

@mcp.tool(
annotations={
“title”: “Search Test Executions”,
“readOnlyHint”: True,
“destructiveHint”: False,
“idempotentHint”: True,
“openWorldHint”: False,
}
)
async def zephyr_search_test_executions(params: ExecutionSearchInput) -> str:
“”“Search test execution results by a TQL query.

```
TQL examples:
  - 'testCycle = "QA-R1"'
  - 'testCase = "QA-T42" AND status = "Fail"'
  - 'projectKey = "QA" AND status IN ("Fail","Blocked")'

Args:
    params: query (TQL string), max_results, start_at

Returns:
    str: JSON — {total, count, offset, has_more, next_offset,
                 results: [Execution{id, testCaseKey, testRunKey, status, …}]}
"""
async with _client() as c:
    try:
        r = await c.get(
            f"{_ATM_BASE}/testresult/search",
            params={
                "query": params.query,
                "maxResults": params.max_results,
                "startAt": params.start_at,
            },
        )
        r.raise_for_status()
        return json.dumps(_page(r.json(), params.start_at), indent=2)
    except Exception as exc:
        return _err(exc)
```

@mcp.tool(
annotations={
“title”: “Create Test Execution”,
“readOnlyHint”: False,
“destructiveHint”: False,
“idempotentHint”: False,
“openWorldHint”: False,
}
)
async def zephyr_create_test_execution(params: ExecutionCreateInput) -> str:
“”“Record a test execution result in a test cycle.

```
Args:
    params: project_key, test_case_key, test_cycle_key, status_name,
            environment_name, comment, actual_end_date, executed_by

Returns:
    str: JSON — created execution record including its numeric ID
"""
body: dict[str, Any] = {
    "projectKey": params.project_key,
    "testCaseKey": params.test_case_key,
    "testRunKey": params.test_cycle_key,
    "statusName": params.status_name,
}
if params.environment_name:
    body["environmentName"] = params.environment_name
if params.comment:
    body["comment"] = params.comment
if params.actual_end_date:
    body["actualEndDate"] = params.actual_end_date
if params.executed_by:
    body["executedBy"] = params.executed_by

async with _client() as c:
    try:
        r = await c.post(f"{_ATM_BASE}/testresult", content=json.dumps(body))
        r.raise_for_status()
        return json.dumps(r.json(), indent=2)
    except Exception as exc:
        return _err(exc)
```

# ── Folders ──────────────────────────────────────────────────────────────────

@mcp.tool(
annotations={
“title”: “List Folders”,
“readOnlyHint”: True,
“destructiveHint”: False,
“idempotentHint”: True,
“openWorldHint”: False,
}
)
async def zephyr_list_folders(params: FolderListInput) -> str:
“”“List folders for test cases, test cycles, or test plans in a project.

```
Args:
    params: project_key, folder_type ('TEST_CASE' | 'TEST_CYCLE' | 'TEST_PLAN'),
            max_results, start_at

Returns:
    str: JSON — {total, count, offset, has_more, next_offset,
                 results: [{id, name, parentId, folderType}]}
"""
async with _client() as c:
    try:
        r = await c.get(
            f"{_ATM_BASE}/folder",
            params={
                "projectKey": params.project_key,
                "folderType": params.folder_type,
                "maxResults": params.max_results,
                "startAt": params.start_at,
            },
        )
        r.raise_for_status()
        return json.dumps(_page(r.json(), params.start_at), indent=2)
    except Exception as exc:
        return _err(exc)
```

# —————————————————————————

# Entry point

# —————————————————————————

def main() -> None:
mcp.run()

if **name** == “**main**”:
main()
