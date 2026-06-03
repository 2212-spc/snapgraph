# Security Policy

SnapGraph is local-first, but it can connect to external LLM providers when the user opts in.

## Secrets

Do not commit:

- API keys
- `.env` files
- `.my_snapgraph/` workspaces
- raw user data
- evaluation reports containing private material
- screenshots that expose sensitive data

Provider keys should live in environment variables such as:

```bash
export SNAPGRAPH_LLM_API_KEY="..."
```

Configuration files store only the environment variable name, never the key value.

## Reporting Issues

For now, open a private issue or contact the repository owner if you find a security problem. Include reproduction steps, affected files, and whether any local data or provider credentials may be exposed.
