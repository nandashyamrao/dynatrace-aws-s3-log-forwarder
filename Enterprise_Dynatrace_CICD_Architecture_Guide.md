# Enterprise CI/CD Architecture for Dynatrace

## Hosted MCP + GitLab + Monaco + dtctl

## Executive Summary

This document describes a recommended GitOps-based deployment
architecture for Dynatrace configuration management. The objective is to
combine AI-assisted development with controlled, repeatable deployments
using GitLab CI/CD, Monaco, and `dtctl`.

**Key principle:**

> **Hosted Dynatrace MCP is an AI engineering assistant---not the
> deployment engine.**

Hosted MCP helps engineers create, review, explain, and troubleshoot
Dynatrace configurations. Deployments are performed through CI/CD using
Monaco, while `dtctl` provides operational validation and automation.

------------------------------------------------------------------------

# Reference Architecture

``` text
                 Developer / AI Assistant
                           │
                           ▼
              Hosted Dynatrace MCP
      (Generate • Explain • Review • Validate)
                           │
                           ▼
                  Git Feature Branch
                           │
                     Merge Request
                           │
                           ▼
                    GitLab Repository
                           │
                           ▼
                    GitLab CI Pipeline
                           │
      ┌────────────────────┼────────────────────┐
      │                    │                    │
 Validate          Deploy TEST          Verify TEST
(Monaco Dry Run)      (Automatic)      (dtctl + DQL)
                                              │
                                              ▼
                                      Manual Approval
                                              │
                                              ▼
                                      Deploy PROD
                                          (Monaco)
                                              │
                                              ▼
                                Production Verification
                             (dtctl + Hosted MCP Analysis)
```

------------------------------------------------------------------------

# Component Responsibilities

  -----------------------------------------------------------------------
  Component              Primary Responsibility
  ---------------------- ------------------------------------------------
  Hosted Dynatrace MCP   AI-assisted generation, DQL authoring,
                         explanations, troubleshooting, deployment
                         analysis

  GitLab                 Source control, merge requests, approvals, CI/CD
                         orchestration

  Monaco                 Configuration-as-Code deployment to Dynatrace

  dtctl                  Validation, scripting, smoke testing,
                         operational automation

  Dynatrace Platform     Hosts and applies deployed configurations
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# End-to-End Workflow

## 1. AI-Assisted Development

Use Hosted Dynatrace MCP to:

-   Generate dashboard JSON
-   Generate notebook content
-   Create or improve DQL
-   Modify OpenPipeline configurations
-   Explain deployment failures
-   Review configuration changes

The AI assists developers but does not deploy directly.

------------------------------------------------------------------------

## 2. Version Control

Commit all changes to a feature branch.

Create a GitLab Merge Request.

Benefits include:

-   Peer review
-   Audit history
-   Rollback capability
-   Change tracking

------------------------------------------------------------------------

## 3. Code Review

Review AI-generated content before merging.

Typical review includes:

-   DQL correctness
-   Dashboard variables
-   Environment-specific references
-   Naming standards
-   Security review

------------------------------------------------------------------------

## 4. CI Validation

Run Monaco validation before deployment.

Example:

``` bash
monaco deploy --dry-run manifest.yaml
```

Validation checks:

-   Syntax
-   Dependencies
-   Configuration references
-   Deployment plan

No changes are applied.

------------------------------------------------------------------------

## 5. Automatic TEST Deployment

After approval and merge:

-   GitLab CI deploys automatically.
-   Monaco applies the configuration.
-   TEST credentials are used.
-   No manual intervention is required.

------------------------------------------------------------------------

## 6. Automated Verification

Verify the deployment using:

-   dtctl
-   Platform APIs
-   DQL queries
-   Smoke tests
-   Dashboard validation
-   Notebook validation

Hosted MCP can help explain failures and recommend fixes.

------------------------------------------------------------------------

## 7. Manual Production Approval

Protect the production environment by requiring manual approval before
deployment.

This ensures only validated configurations are promoted.

------------------------------------------------------------------------

## 8. Production Deployment

Deploy the exact configuration tested in TEST.

Do **not** regenerate or modify the deployment artifact.

------------------------------------------------------------------------

## 9. Post-Deployment Verification

Run:

-   dtctl validation
-   Representative DQL queries
-   Health checks
-   Dashboard verification

Hosted MCP can investigate anomalies and explain unexpected behavior.

------------------------------------------------------------------------

# Authentication

Store deployment credentials securely in GitLab CI/CD variables.

Example:

``` text
DT_TEST_CLIENT_ID
DT_TEST_CLIENT_SECRET
DT_PROD_CLIENT_ID
DT_PROD_CLIENT_SECRET
```

Recommendations:

-   Separate deployment identities for TEST and PROD
-   Never commit secrets to Git
-   Use least-privilege permissions
-   Protect production variables

------------------------------------------------------------------------

# Recommended GitLab Pipeline

``` text
Validate
    │
Dry Run
    │
Deploy TEST (Automatic)
    │
Verify TEST
    │
Manual Approval
    │
Deploy PROD
    │
Verify Production
```

------------------------------------------------------------------------

# Security Best Practices

-   Use GitOps for all configuration changes.
-   Require merge requests before deployment.
-   Protect production branches and environments.
-   Keep deployment credentials in GitLab protected variables.
-   Deploy the same tested artifact to production.
-   Perform automated verification after every deployment.

------------------------------------------------------------------------

# Recommended Enterprise Pattern

``` text
AI proposes
      │
Git records
      │
CI validates
      │
Monaco deploys to TEST
      │
dtctl verifies
      │
Human approves
      │
Monaco deploys to PROD
      │
dtctl verifies
      │
Hosted MCP investigates and explains
```

------------------------------------------------------------------------

# Key Takeaways

-   Hosted Dynatrace MCP improves developer productivity through
    AI-assisted engineering.
-   Monaco remains the preferred deployment mechanism for
    Configuration-as-Code.
-   dtctl complements Monaco with scripting, automation, and validation.
-   GitLab CI orchestrates the deployment lifecycle, approvals, and
    secrets.
-   A GitOps workflow provides traceability, repeatability, and
    governance while allowing AI to accelerate development.
