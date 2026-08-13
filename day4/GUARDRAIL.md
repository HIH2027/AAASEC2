# Day 4 Guardrail Note

Local shell execution is intentionally unsafe for the lab: the agent can run commands as the current user. The prompt-injection defense is not a stronger system prompt; it is moving execution into an infrastructure boundary.

Use one of these settings for the challenge evidence when credentials are available:

```env
SANDBOX_PROVIDER=daytona
```

or

```env
SANDBOX_PROVIDER=langsmith
```

Keep only the needed values in the shell backend environment. MCP data access remains protected by bearer tokens and scopes: student tokens can call public tools, while admin tokens are required for `read:internal` tools such as `get_internal_report` and `get_lab_inventory`.
