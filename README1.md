# zephyr-scale-mcp

Python MCP server for **Zephyr Scale Data Center / Server API v1**.
Authentication uses **Bearer token only** — no session cookies, no `verify=False` hardcoded.

-----

## Setup

```bash
pip install -r requirements.txt
```

## Environment variables

|Variable           |Required|Description                                                                                     |
|-------------------|--------|------------------------------------------------------------------------------------------------|
|`ZEPHYR_BASE_URL`  |✅       |Base URL of your Jira DC instance, e.g. `https://jira.company.com`                              |
|`ZEPHYR_API_TOKEN` |✅       |Zephyr Scale API Access Token (Jira profile → Zephyr Scale API Access Tokens)                   |
|`ZEPHYR_VERIFY_SSL`|optional|Set to `false` to disable SSL certificate verification (e.g. self-signed certs). Default: `true`|

### Token generation

1. Log in to Jira → click your profile avatar → **Zephyr Scale API Access Tokens**
1. Click **Create access token** → copy the token
1. Export it: `export ZEPHYR_API_TOKEN=<your-token>`

-----

## Running

### stdio (default — for Claude Desktop / MCP clients)

```bash
export ZEPHYR_BASE_URL=https://jira.company.com
export ZEPHYR_API_TOKEN=your_token_here
# Optional: export ZEPHYR_VERIFY_SSL=false

python server.py
```

### Claude Desktop config (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "zephyr-scale": {
      "command": "python",
      "args": ["/path/to/server.py"],
      "env": {
        "ZEPHYR_BASE_URL": "https://jira.company.com",
        "ZEPHYR_API_TOKEN": "your_token_here",
        "ZEPHYR_VERIFY_SSL": "true"
      }
    }
  }
}
```

-----

## Available tools

|Tool                           |Description                                      |
|-------------------------------|-------------------------------------------------|
|`zephyr_list_projects`         |List all Zephyr Scale projects                   |
|`zephyr_list_test_cases`       |List test cases by project key (paginated)       |
|`zephyr_get_test_case`         |Fetch a single test case by key (e.g. `QA-T42`)  |
|`zephyr_search_test_cases`     |Search test cases with TQL query                 |
|`zephyr_create_test_case`      |Create a new test case                           |
|`zephyr_update_test_case`      |Update test case fields                          |
|`zephyr_get_test_case_steps`   |Get test script / steps for a test case          |
|`zephyr_list_test_cycles`      |List test cycles (test runs) by project          |
|`zephyr_get_test_cycle`        |Fetch a single test cycle by key                 |
|`zephyr_search_test_cycles`    |Search test cycles with TQL                      |
|`zephyr_create_test_cycle`     |Create a new test cycle                          |
|`zephyr_search_test_executions`|Search test execution results by TQL             |
|`zephyr_create_test_execution` |Record a test execution result                   |
|`zephyr_list_folders`          |List folders (TEST_CASE / TEST_CYCLE / TEST_PLAN)|

-----

## API base path

All requests go to:

```
{ZEPHYR_BASE_URL}/rest/atm/1.0/{endpoint}
```

with header:

```
Authorization: Bearer <ZEPHYR_API_TOKEN>
```

## SSL note

If your Jira DC uses a **self-signed certificate**, set:

```bash
export ZEPHYR_VERIFY_SSL=false
```

This is parametrized — the code never has `verify=False` hardcoded.
