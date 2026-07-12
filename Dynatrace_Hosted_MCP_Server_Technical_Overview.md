# Dynatrace Hosted MCP Server -- Technical Overview

## Technical Background

Modern AI assistants (GitHub Copilot, Claude, Cursor, VS Code AI,
ChatGPT, etc.) become significantly more powerful when they can interact
with enterprise systems instead of relying solely on static knowledge.
The **Model Context Protocol (MCP)** provides a standardized mechanism
for AI clients to securely discover and invoke external tools.

Rather than every AI client implementing custom integrations for each
product (Dynatrace, GitHub, Jira, Kubernetes, AWS, etc.), MCP defines a
common protocol that allows AI clients to communicate with remote tools
through a consistent interface.

Conceptually:

``` text
AI Client
    │
    │ Model Context Protocol (MCP)
    ▼
MCP Server
    │
    ├── Tools
    ├── Resources
    └── Prompts
    │
    ▼
Enterprise Platform APIs
```

The MCP server acts as a secure gateway between an AI client and an
enterprise platform. It exposes capabilities ("tools") that the AI can
invoke without requiring the AI to understand the platform's internal
REST APIs.

Benefits include: - Standardized protocol for AI integrations - Secure
authentication - Tool discovery - Consistent request/response format -
Extensible architecture - Vendor-independent AI integrations

------------------------------------------------------------------------

# Dynatrace MCP Evolution

Dynatrace originally provided an open-source MCP server that customers
hosted themselves. The latest architecture introduces a **fully managed
MCP server hosted inside the Dynatrace Platform**, eliminating the need
to operate a local Node.js service.

## Previous Architecture (Self-Hosted OSS MCP Server)

``` text
GitHub Copilot / PyCharm / VS Code
                │
                ▼
      Local Docker Container
(@dynatrace-oss/dynatrace-mcp-server)
                │
                ▼
          Dynatrace REST APIs
                │
                ▼
          Dynatrace Platform
```

Customers managed Node.js, Docker, upgrades, tokens, and availability.

## New Architecture (Hosted Dynatrace MCP Server)

``` text
GitHub Copilot
Claude
Cursor
VS Code
PyCharm
        │
        │ HTTPS + OAuth / Platform Token
        ▼
Dynatrace MCP Gateway
        │
        ▼
Hosted Dynatrace MCP Server
        │
        ├── Grail Query Agent
        ├── Data Analysis Agent
        ├── DQL Explanation Agent
        ├── Documentation Agent
        ├── Problem Investigation
        ├── Kubernetes Analysis
        ├── Vulnerability Analysis
        ├── Entity Resolution
        └── Additional Platform Tools
        │
        ▼
Grail / Davis AI / Smartscape / OpenPipeline
```

Dynatrace now manages infrastructure, scaling, updates, security, and
availability.

## Operational Comparison

  Capability     OSS MCP    Hosted MCP
  -------------- ---------- ------------
  Installation   Required   None
  Docker         Required   No
  Node.js        Required   No
  Updates        Customer   Dynatrace
  Scaling        Customer   Dynatrace
  Maintenance    Customer   Dynatrace

## Relationship with dtctl and Monaco

### Hosted MCP

-   AI investigations
-   DQL generation
-   Documentation
-   Troubleshooting
-   Interactive analysis

### dtctl

-   Administrative automation
-   API scripting
-   CI/CD automation
-   Bulk operations

### Monaco

-   Configuration as Code
-   Git-based deployments
-   Dashboard promotion
-   Environment consistency

## Recommended Architecture

``` text
             AI Clients
(Copilot, Cursor, Claude, ChatGPT)
                │
                ▼
     Hosted Dynatrace MCP Server
                │
      Grail / Davis / Smartscape
                │
                ▼
        Dynatrace Platform

GitLab CI/CD
     │
 ┌───┴────┐
 │        │
dtctl   Monaco
 │        │
 └────────┘
     │
Dynatrace Platform
```

## Recommendation

Use the **Hosted Dynatrace MCP Server** for AI-powered observability and
investigations, **dtctl** for scripting and operational automation, and
**Monaco** for Infrastructure-as-Code and repeatable deployments.
Together they provide a complete enterprise observability workflow.
