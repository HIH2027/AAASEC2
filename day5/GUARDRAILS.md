# Guardrails

The MCP response is untrusted input even though it comes from an authenticated
service. Authentication establishes who can access the service; it does not
prove that every stored data value is safe to place in an LLM prompt.

The capstone applies these controls:

- Scope-based MCP authorization hides inventory from student credentials.
- Pydantic validates types, ranges, list size, and text length.
- Instruction-like inventory names are rejected before LLM use.
- Monetary calculations are deterministic Python, not LLM arithmetic.
- Only validated, calculated JSON reaches the model.
- The system prompt explicitly treats all JSON fields as data.
- The model receives no MCP token or other environment secrets.
- The AI call is limited to one short recommendation with a timeout and retry cap.
- Leaked reasoning, empty output, and verbose output are rejected and replaced
  by a deterministic recommendation derived from the validated analysis.
- `--offline` provides a deterministic mode for testing and rate-limit recovery.

For production, replace static tokens with an external OAuth/OIDC provider,
store inventory in a database, add audit logging, and use a network sandbox for
any future code-execution tools.
