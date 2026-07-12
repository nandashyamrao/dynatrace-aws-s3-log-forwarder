# Dynatrace MCP Server Setup (Official Hosted MCP)

## Goal

Connect GitHub Copilot in VS Code to the **official Dynatrace-hosted MCP
server** (no Docker MCP server).

------------------------------------------------------------------------

## Final Architecture

``` text
GitHub Copilot Agent
        │
        ▼
VS Code MCP Client
        │
        ▼
Dynatrace Hosted MCP Gateway
        │
        ▼
Dynatrace Environment
```

No local MCP Docker container is required.

------------------------------------------------------------------------

## Prerequisites

-   VS Code with GitHub Copilot Chat
-   GitHub Copilot Agent mode
-   Dynatrace Platform Token
-   Access to the Dynatrace environment

------------------------------------------------------------------------

## Workspace Configuration

Create:

``` text
.vscode/mcp.json
```

Contents:

``` json
{
  "servers": {
    "dynatrace-mcp": {
      "type": "http",
      "url": "https://<YOUR_ENV>.apps.dynatrace.com/platform-reserved/mcp-gateway/v0.1/servers/dynatrace-mcp/mcp",
      "headers": {
        "Authorization": "Bearer ${input:dynatrace-mcp-token}"
      }
    }
  },
  "inputs": [
    {
      "id": "dynatrace-mcp-token",
      "type": "promptString",
      "description": "Dynatrace MCP authorization token",
      "password": true
    }
  ]
}
```

Replace `<YOUR_ENV>` with your Dynatrace environment ID.

------------------------------------------------------------------------

## Start the MCP Server

1.  Open the project in VS Code.
2.  Press `Ctrl+Shift+P`.
3.  Run **MCP: List Servers**.
4.  Select **dynatrace-mcp**.
5.  Click **Start Server**.
6.  Enter the Dynatrace Platform Token when prompted.

------------------------------------------------------------------------

## Verify the Connection

Open the MCP output.

A successful connection shows messages similar to:

``` text
Starting server: dynatrace-mcp
Connection state: Running
Discovered 21 tools
```

Once connected, Copilot can list and use Dynatrace MCP tools.

------------------------------------------------------------------------

## Troubleshooting

### Browser says:

``` text
GET call for server 'dynatrace-mcp' not supported
```

This is expected. The endpoint is intended for MCP clients, not web
browsers.

### OAuth popup

Ensure the Authorization header is exactly:

``` text
Bearer ${input:dynatrace-mcp-token}
```

### Dev Container issue

If VS Code opens inside a Dev Container, networking can fail.

Symptoms:

``` text
ECONNREFUSED 127.0.0.1:9000
```

Fix:

Rename

``` text
.devcontainer
```

to

``` text
.devcontainer.disabled
```

Then reopen the project locally.

------------------------------------------------------------------------

## Current Working State

-   VS Code running locally
-   Official Dynatrace-hosted MCP server
-   GitHub Copilot Agent enabled
-   MCP connection successful
-   21 Dynatrace MCP tools discovered

------------------------------------------------------------------------

## Example Prompts

-   List all available Dynatrace MCP tools.
-   Show the last 20 ERROR logs from the last hour.
-   Show all active problems.
-   Create DQL to show CloudFront requests by distribution.
-   Explain this DQL query.
-   Generate a Monaco configuration for this dashboard.
-   Help create an OpenPipeline processor from these logs.

------------------------------------------------------------------------

Generated during setup on July 2026.
