“””
Zephyr Scale Data Center MCP Server
REST API v1 — token-only authentication (Bearer token)
Base URL: {jira_base_url}/rest/atm/1.0/
“””

from **future** import annotations

import json
import os
import ssl
from typing import Any, Optional

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

# —————————————————————————

# Configuration

# —————————————————————————

ZEPHYR_BASE_URL: str = os.environ.get(“ZEPHYR_BASE_URL”, “”).rstrip(”/”)
ZEPHYR_API_TOKEN: str = os.environ.get(“ZEPHYR_API_TOKEN”, “”)

# Set ZEPHYR_VERIFY_SSL=false to disable SSL certificate verification (e.g. self-signed certs)

ZEPHYR_VERIFY_SSL: bool = os.environ.get(“ZEPHYR_VERIFY_SSL”, “true”).lower() not in (“false”, “0”, “no”)

ATM_BASE: str = f”{ZEPHYR_BASE_URL}/rest/atm/1.0”

# —————————————————————————

# MCP server

# —————————————————————————

mcp = FastMCP(“zephyr_scale_mcp”)

# —————————————————————————

# HTTP client helpers

# —————————————————————————

def _build_client() -> httpx.AsyncClient:
“”“Return a configured async HTTP client with Bearer token auth.”””
if not ZEPHYR_API_TOKEN:
raise RuntimeError(
“ZEPHYR_API_TOKEN environment variable is not set. “
“Generate a token via Jira → Profile → Zephyr Scale API Access Tokens.”
)
if not ZEPHYR_BASE_URL:
raise RuntimeError(“ZEPHYR_BASE_URL environment variable is not set.”)

```
verify: bool | ssl.SSLContext = ZEPHYR_VERIFY_SSL
return httpx.AsyncClient(
    headers={
        "Authorization": f"Bearer {ZEPHYR_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    },
    verify=verify,
    timeout=60.0,
)
```

def _handle_error(e: Exception) -> str:
“”“Return a human-readable error message from an httpx exception.”””
if isinstance(e, httpx.HTTPStatusError):
code = e.response.status_code
body = e.response.text[:400]
if code == 401:
return “Error 401: Unauthorized. Check that ZEPHYR_API_TOKEN is valid.”
if code == 403:
return “Error 403: Forbidden. Your token may lack required permissions.”
if code == 404:
return “Error 404: Not Found. Verify the resource key / ID and project key.”
if code == 429:
return “Error 429: Rate limit exceeded. Wait before retrying.”
return f”Error {code}: {body}”
if isinstance(e, httpx.TimeoutException):
return “Error: Request timed out. The server took too long to respond.”
if isinstance(e, httpx.ConnectError):
return f”Error: Cannot connect to {ZEPHYR_BASE_URL}. Check ZEPHYR_BASE_URL and network access.”
return f”Error: {type(e).**name**}: {e}”

def _paginated(data: dict[str, Any], offset: int) -> dict[str, Any]:
“”“Attach pagination hints to a list response.”””
results = data.get(“results”, data.get(“values”, []))
total = data.get(“total”, len(results))
return {
“total”: total,
“count”: len(results),
“offset”: offset,
“has_more”: total > offset + len(results),
“next_offset”: offset + len(results) if total > offset + len(results) else None,
“results”: results,
}

# ===========================================================================

# Pydantic input models

# ===========================================================================

class ListInput(BaseModel):
model_config = ConfigDict(str_strip_whitespace=True, extra=“forbid”)
project_key: str = Field(…, description=“Jira project key, e.g. ‘QA’ or ‘MYPROJ’”)
max_results: int = Field(default=50, ge=1, le=200, description=“Page size (1-200)”)
start_at: int = Field(default=0, ge=0, description=“Zero-based offset for pagination”)

class TestCaseGetInput(BaseModel):
model_config = ConfigDict(str_strip_whitespace=True, extra=“forbid”)
test_case_key: str = Field(…, description=“Test case key, e.g. ‘QA-T42’”, min_length=1)

class TestCaseSearchInput(BaseModel):
model_config = ConfigDict(str_strip_whitespace=True, extra=“forbid”)
project_key: str = Field(…, description=“Jira project key”)
query: Optional[str] = Field(default=None, description=“TQL query string, e.g. ‘status = "Approved"’”)
max_results: int = Field(default=50, ge=1, le=200)
start_at: int = Field(default=0, ge=0)

class TestCaseCreateInput(BaseModel):
model_config = ConfigDict(str_strip_whitespace=True, extra=“forbid”)
project_key: str = Field(…, description=“Jira project key”)
name: str = Field(…, description=“Test case name”, min_length=1, max_length=500)
objective: Optional[str] = Field(default=None, description=“Test objective / description”)
precondition: Optional[str] = Field(default=None, description=“Preconditions text”)
status: Optional[str] = Field(default=“Draft”, description=“Status: ‘Draft’, ‘Approved’, ‘Deprecated’”)
priority: Optional[str] = Field(default=None, description=“Priority name, e.g. ‘High’”)
folder: Optional[str] = Field(default=None, description=“Folder path, e.g. ‘/Regression/Login’”)
labels: Optional[list[str]] = Field(default=None, description=“List of label strings”)
owner: Optional[str] = Field(default=None, description=“Jira username of the owner”)

class TestCaseUpdateInput(BaseModel):
model_config = ConfigDict(str_strip_whitespace=True, extra=“forbid”)
test_case_key: str = Field(…, description=“Test case key to update, e.g. ‘QA-T42’”)
name: Optional[str] = Field(default=None, description=“New name”)
objective: Optional[str] = Field(default=None, description=“New objective”)
status: Optional[str] = Field(default=None, description=“New status”)
priority: Optional[str] = Field(default=None, description=“New priority”)
folder: Optional[str] = Field(default=None, description=“New folder path”)
labels: Optional[list[str]] = Field(default=None, description=“New labels (replaces existing)”)

class TestCycleGetInput(BaseModel):
model_config = ConfigDict(str_strip_whitespace=True, extra=“forbid”)
test_cycle_key: str = Field(…, description=“Test cycle key, e.g. ‘QA-R1’”, min_length=1)

class TestCycleSearchInput(BaseModel):
model_config = ConfigDict(str_strip_whitespace=True, extra=“forbid”)
project_key: str = Field(…, description=“Jira project key”)
query: Optional[str] = Field(default=None, description=“TQL query string”)
max_results: int = Field(default=50, ge=1, le=200)
start_at: int = Field(default=0, ge=0)

class TestCycleCreateInput(BaseModel):
model_config = ConfigDict(str_strip_whitespace=True, extra=“forbid”)
project_key: str = Field(…, description=“Jira project key”)
name: str = Field(…, description=“Test cycle name”, min_length=1, max_length=500)
description: Optional[str] = Field(default=None)
status: Optional[str] = Field(default=“Not Started”, description=“Status name, e.g. ‘In Progress’”)
folder: Optional[str] = Field(default=None, description=“Folder path”)
planned_start_date: Optional[str] = Field(default=None, description=“ISO-8601 date, e.g. ‘2025-01-01’”)
planned_end_date: Optional[str] = Field(default=None, description=“ISO-8601 date”)

class TestExecutionSearchInput(BaseModel):
model_config = ConfigDict(str_strip_whitespace=True, extra=“forbid”)
query: str = Field(…, description=“TQL query, e.g. ‘testCycle = "QA-R1" AND status = "Fail"’”)
max_results: int = Field(default=50, ge=1, le=200)
start_at: int = Field(default=0, ge=0)

class TestExecutionCreateInput(BaseModel):
model_config = ConfigDict(str_strip_whitespace=True, extra=“forbid”)
project_key: str = Field(…, description=“Jira project key”)
test_case_key: str = Field(…, description=“Test case key to execute, e.g. ‘QA-T42’”)
test_cycle_key: str = Field(…, description=“Test cycle key, e.g. ‘QA-R1’”)
status_name: str = Field(…, description=“Execution status, e.g. ‘Pass’, ‘Fail’, ‘In Progress’”)
environment_name: Optional[str] = Field(default=None, description=“Environment name”)
comment: Optional[str] = Field(default=None, description=“Execution comment”)
actual_end_date: Optional[str] = Field(default=None, description=“ISO-8601 datetime”)
executed_by: Optional[str] = Field(default=None, description=“Jira username of executor”)

class FolderListInput(BaseModel):
model_config = ConfigDict(str_strip_whitespace=True, extra=“forbid”)
project_key: str = Field(…, description=“Jira project key”)
folder_type: str = Field(
default=“TEST_CASE”,
description=“Folder type: ‘TEST_CASE’, ‘TEST_CYCLE’, or ‘TEST_PLAN’”,
)
max_results: int = Field(default=50, ge=1, le=200)
start_at: int = Field(default=0, ge=0)

class ProjectListInput(BaseModel):
model_config = ConfigDict(extra=“forbid”)
max_results: int = Field(default=50, ge=1, le=200)
start_at: int = Field(default=0, ge=0)

# ===========================================================================

# Tool: list_test_cases

# ===========================================================================

@mcp.tool(
name=“zephyr_list_test_cases”,
annotations={
“title”: “List Test Cases”,
“readOnlyHint”: True,
“destructiveHint”: False,
“idempotentHint”: True,
“openWorldHint”: False,
},
)
async def zephyr_list_test_cases(params: ListInput) -> str:
“”“List test cases for a Jira project from Zephyr Scale Data Center API v1.

```
Args:
    params (ListInput): project_key, max_results, start_at

Returns:
    str: JSON with total, count, offset, has_more, next_offset, results (list of test cases)
"""
async with _build_client() as client:
    try:
        r = await client.get(
            f"{ATM_BASE}/testcase/search",
            params={
                "query": f'projectKey = "{params.project_key}"',
                "maxResults": params.max_results,
                "startAt": params.start_at,
            },
        )
        r.raise_for_status()
        return json.dumps(_paginated(r.json(), params.start_at), indent=2)
    except Exception as e:
        return _handle_error(e)
```

# ===========================================================================

# Tool: get_test_case

# ===========================================================================

@mcp.tool(
name=“zephyr_get_test_case”,
annotations={
“title”: “Get Test Case”,
“readOnlyHint”: True,
“destructiveHint”: False,
“idempotentHint”: True,
“openWorldHint”: False,
},
)
async def zephyr_get_test_case(params: TestCaseGetInput) -> str:
“”“Fetch a single test case by its key from Zephyr Scale DC v1.

```
Args:
    params (TestCaseGetInput): test_case_key

Returns:
    str: JSON object with test case fields (key, name, status, priority, steps, etc.)
"""
async with _build_client() as client:
    try:
        r = await client.get(f"{ATM_BASE}/testcase/{params.test_case_key}")
        r.raise_for_status()
        return json.dumps(r.json(), indent=2)
    except Exception as e:
        return _handle_error(e)
```

# ===========================================================================

# Tool: search_test_cases

# ===========================================================================

@mcp.tool(
name=“zephyr_search_test_cases”,
annotations={
“title”: “Search Test Cases”,
“readOnlyHint”: True,
“destructiveHint”: False,
“idempotentHint”: True,
“openWorldHint”: False,
},
)
async def zephyr_search_test_cases(params: TestCaseSearchInput) -> str:
“”“Search test cases using a TQL query (Zephyr Scale DC API v1).

```
TQL examples:
  - 'status = "Approved"'
  - 'labels IN ("smoke") AND priority = "High"'
  - 'folder = "/Regression"'

Args:
    params (TestCaseSearchInput): project_key, query (TQL), max_results, start_at

Returns:
    str: Paginated JSON list of matching test cases
"""
base_query = f'projectKey = "{params.project_key}"'
if params.query:
    base_query = f"{base_query} AND {params.query}"

async with _build_client() as client:
    try:
        r = await client.get(
            f"{ATM_BASE}/testcase/search",
            params={
                "query": base_query,
                "maxResults": params.max_results,
                "startAt": params.start_at,
            },
        )
        r.raise_for_status()
        return json.dumps(_paginated(r.json(), params.start_at), indent=2)
    except Exception as e:
        return _handle_error(e)
```

# ===========================================================================

# Tool: create_test_case

# ===========================================================================

@mcp.tool(
name=“zephyr_create_test_case”,
annotations={
“title”: “Create Test Case”,
“readOnlyHint”: False,
“destructiveHint”: False,
“idempotentHint”: False,
“openWorldHint”: False,
},
)
async def zephyr_create_test_case(params: TestCaseCreateInput) -> str:
“”“Create a new test case in Zephyr Scale DC (API v1).

```
Args:
    params (TestCaseCreateInput): project_key, name, objective, precondition,
        status, priority, folder, labels, owner

Returns:
    str: JSON with the new test case key and full object
"""
body: dict[str, Any] = {
    "projectKey": params.project_key,
    "name": params.name,
    "status": params.status or "Draft",
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

async with _build_client() as client:
    try:
        r = await client.post(f"{ATM_BASE}/testcase", content=json.dumps(body))
        r.raise_for_status()
        return json.dumps(r.json(), indent=2)
    except Exception as e:
        return _handle_error(e)
```

# ===========================================================================

# Tool: update_test_case

# ===========================================================================

@mcp.tool(
name=“zephyr_update_test_case”,
annotations={
“title”: “Update Test Case”,
“readOnlyHint”: False,
“destructiveHint”: False,
“idempotentHint”: True,
“openWorldHint”: False,
},
)
async def zephyr_update_test_case(params: TestCaseUpdateInput) -> str:
“”“Update fields of an existing test case (Zephyr Scale DC API v1 PUT).

```
Only provided fields are included in the request body.

Args:
    params (TestCaseUpdateInput): test_case_key plus optional fields to change

Returns:
    str: JSON with updated test case object
"""
body: dict[str, Any] = {}
if params.name is not None:
    body["name"] = params.name
if params.objective is not None:
    body["objective"] = params.objective
if params.status is not None:
    body["status"] = params.status
if params.priority is not None:
    body["priority"] = {"name": params.priority}
if params.folder is not None:
    body["folder"] = params.folder
if params.labels is not None:
    body["labels"] = params.labels

async with _build_client() as client:
    try:
        r = await client.put(
            f"{ATM_BASE}/testcase/{params.test_case_key}",
            content=json.dumps(body),
        )
        r.raise_for_status()
        return json.dumps(r.json(), indent=2)
    except Exception as e:
        return _handle_error(e)
```

# ===========================================================================

# Tool: get_test_case_steps

# ===========================================================================

@mcp.tool(
name=“zephyr_get_test_case_steps”,
annotations={
“title”: “Get Test Case Steps”,
“readOnlyHint”: True,
“destructiveHint”: False,
“idempotentHint”: True,
“openWorldHint”: False,
},
)
async def zephyr_get_test_case_steps(params: TestCaseGetInput) -> str:
“”“Fetch the test script steps for a test case (Zephyr Scale DC API v1).

```
Args:
    params (TestCaseGetInput): test_case_key

Returns:
    str: JSON with testScript type and steps list
"""
async with _build_client() as client:
    try:
        r = await client.get(f"{ATM_BASE}/testcase/{params.test_case_key}")
        r.raise_for_status()
        data = r.json()
        script = data.get("testScript", {})
        return json.dumps({"key": params.test_case_key, "testScript": script}, indent=2)
    except Exception as e:
        return _handle_error(e)
```

# ===========================================================================

# Tool: list_test_cycles

# ===========================================================================

@mcp.tool(
name=“zephyr_list_test_cycles”,
annotations={
“title”: “List Test Cycles”,
“readOnlyHint”: True,
“destructiveHint”: False,
“idempotentHint”: True,
“openWorldHint”: False,
},
)
async def zephyr_list_test_cycles(params: ListInput) -> str:
“”“List test cycles (test runs) for a Jira project (Zephyr Scale DC API v1).

```
Args:
    params (ListInput): project_key, max_results, start_at

Returns:
    str: Paginated JSON list of test cycles
"""
async with _build_client() as client:
    try:
        r = await client.get(
            f"{ATM_BASE}/testrun/search",
            params={
                "query": f'projectKey = "{params.project_key}"',
                "maxResults": params.max_results,
                "startAt": params.start_at,
            },
        )
        r.raise_for_status()
        return json.dumps(_paginated(r.json(), params.start_at), indent=2)
    except Exception as e:
        return _handle_error(e)
```

# ===========================================================================

# Tool: get_test_cycle

# ===========================================================================

@mcp.tool(
name=“zephyr_get_test_cycle”,
annotations={
“title”: “Get Test Cycle”,
“readOnlyHint”: True,
“destructiveHint”: False,
“idempotentHint”: True,
“openWorldHint”: False,
},
)
async def zephyr_get_test_cycle(params: TestCycleGetInput) -> str:
“”“Fetch a single test cycle by key (Zephyr Scale DC API v1).

```
Args:
    params (TestCycleGetInput): test_cycle_key (e.g. 'QA-R1')

Returns:
    str: JSON object with cycle fields, linked test cases, status counts, etc.
"""
async with _build_client() as client:
    try:
        r = await client.get(f"{ATM_BASE}/testrun/{params.test_cycle_key}")
        r.raise_for_status()
        return json.dumps(r.json(), indent=2)
    except Exception as e:
        return _handle_error(e)
```

# ===========================================================================

# Tool: search_test_cycles

# ===========================================================================

@mcp.tool(
name=“zephyr_search_test_cycles”,
annotations={
“title”: “Search Test Cycles”,
“readOnlyHint”: True,
“destructiveHint”: False,
“idempotentHint”: True,
“openWorldHint”: False,
},
)
async def zephyr_search_test_cycles(params: TestCycleSearchInput) -> str:
“”“Search test cycles using TQL (Zephyr Scale DC API v1).

```
TQL examples:
  - 'status = "In Progress"'
  - 'folder = "/Sprint 10"'

Args:
    params (TestCycleSearchInput): project_key, query (TQL), max_results, start_at

Returns:
    str: Paginated JSON list of test cycles
"""
base_query = f'projectKey = "{params.project_key}"'
if params.query:
    base_query = f"{base_query} AND {params.query}"

async with _build_client() as client:
    try:
        r = await client.get(
            f"{ATM_BASE}/testrun/search",
            params={
                "query": base_query,
                "maxResults": params.max_results,
                "startAt": params.start_at,
            },
        )
        r.raise_for_status()
        return json.dumps(_paginated(r.json(), params.start_at), indent=2)
    except Exception as e:
        return _handle_error(e)
```

# ===========================================================================

# Tool: create_test_cycle

# ===========================================================================

@mcp.tool(
name=“zephyr_create_test_cycle”,
annotations={
“title”: “Create Test Cycle”,
“readOnlyHint”: False,
“destructiveHint”: False,
“idempotentHint”: False,
“openWorldHint”: False,
},
)
async def zephyr_create_test_cycle(params: TestCycleCreateInput) -> str:
“”“Create a new test cycle in Zephyr Scale DC (API v1).

```
Args:
    params (TestCycleCreateInput): project_key, name, description, status,
        folder, planned_start_date, planned_end_date

Returns:
    str: JSON with new test cycle key and full object
"""
body: dict[str, Any] = {
    "projectKey": params.project_key,
    "name": params.name,
    "status": params.status or "Not Started",
}
if params.description:
    body["description"] = params.description
if params.folder:
    body["folder"] = params.folder
if params.planned_start_date:
    body["plannedStartDate"] = params.planned_start_date
if params.planned_end_date:
    body["plannedEndDate"] = params.planned_end_date

async with _build_client() as client:
    try:
        r = await client.post(f"{ATM_BASE}/testrun", content=json.dumps(body))
        r.raise_for_status()
        return json.dumps(r.json(), indent=2)
    except Exception as e:
        return _handle_error(e)
```

# ===========================================================================

# Tool: search_test_executions

# ===========================================================================

@mcp.tool(
name=“zephyr_search_test_executions”,
annotations={
“title”: “Search Test Executions”,
“readOnlyHint”: True,
“destructiveHint”: False,
“idempotentHint”: True,
“openWorldHint”: False,
},
)
async def zephyr_search_test_executions(params: TestExecutionSearchInput) -> str:
“”“Search test executions by TQL query (Zephyr Scale DC API v1).

```
TQL examples:
  - 'testCycle = "QA-R1"'
  - 'testCase = "QA-T42" AND status = "Fail"'
  - 'projectKey = "QA" AND status IN ("Fail","Blocked")'

Args:
    params (TestExecutionSearchInput): query (TQL), max_results, start_at

Returns:
    str: Paginated JSON list of execution records
"""
async with _build_client() as client:
    try:
        r = await client.get(
            f"{ATM_BASE}/testresult/search",
            params={
                "query": params.query,
                "maxResults": params.max_results,
                "startAt": params.start_at,
            },
        )
        r.raise_for_status()
        return json.dumps(_paginated(r.json(), params.start_at), indent=2)
    except Exception as e:
        return _handle_error(e)
```

# ===========================================================================

# Tool: create_test_execution

# ===========================================================================

@mcp.tool(
name=“zephyr_create_test_execution”,
annotations={
“title”: “Create Test Execution”,
“readOnlyHint”: False,
“destructiveHint”: False,
“idempotentHint”: False,
“openWorldHint”: False,
},
)
async def zephyr_create_test_execution(params: TestExecutionCreateInput) -> str:
“”“Record a test execution result in Zephyr Scale DC (API v1 POST /testresult).

```
Args:
    params (TestExecutionCreateInput): project_key, test_case_key, test_cycle_key,
        status_name, environment_name, comment, actual_end_date, executed_by

Returns:
    str: JSON with created execution record including ID
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

async with _build_client() as client:
    try:
        r = await client.post(f"{ATM_BASE}/testresult", content=json.dumps(body))
        r.raise_for_status()
        return json.dumps(r.json(), indent=2)
    except Exception as e:
        return _handle_error(e)
```

# ===========================================================================

# Tool: list_folders

# ===========================================================================

@mcp.tool(
name=“zephyr_list_folders”,
annotations={
“title”: “List Folders”,
“readOnlyHint”: True,
“destructiveHint”: False,
“idempotentHint”: True,
“openWorldHint”: False,
},
)
async def zephyr_list_folders(params: FolderListInput) -> str:
“”“List folders for test cases, test cycles, or test plans in a project (DC API v1).

```
Args:
    params (FolderListInput): project_key, folder_type ('TEST_CASE'|'TEST_CYCLE'|'TEST_PLAN'),
        max_results, start_at

Returns:
    str: Paginated JSON list of folder objects with id, name, parentId, folderType
"""
async with _build_client() as client:
    try:
        r = await client.get(
            f"{ATM_BASE}/folder",
            params={
                "projectKey": params.project_key,
                "folderType": params.folder_type,
                "maxResults": params.max_results,
                "startAt": params.start_at,
            },
        )
        r.raise_for_status()
        return json.dumps(_paginated(r.json(), params.start_at), indent=2)
    except Exception as e:
        return _handle_error(e)
```

# ===========================================================================

# Tool: list_projects

# ===========================================================================

@mcp.tool(
name=“zephyr_list_projects”,
annotations={
“title”: “List Projects”,
“readOnlyHint”: True,
“destructiveHint”: False,
“idempotentHint”: True,
“openWorldHint”: False,
},
)
async def zephyr_list_projects(params: ProjectListInput) -> str:
“”“List Zephyr Scale projects available in this Data Center instance (API v1).

```
Args:
    params (ProjectListInput): max_results, start_at

Returns:
    str: Paginated JSON list of project objects with id, key, name
"""
async with _build_client() as client:
    try:
        r = await client.get(
            f"{ATM_BASE}/project",
            params={"maxResults": params.max_results, "startAt": params.start_at},
        )
        r.raise_for_status()
        return json.dumps(_paginated(r.json(), params.start_at), indent=2)
    except Exception as e:
        return _handle_error(e)
```

# ===========================================================================

# Entry point

# ===========================================================================

if **name** == “**main**”:
mcp.run()
