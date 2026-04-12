---
name: Security Patterns and Anti-Patterns
description: Recurring security issues and patterns observed in the ai-core-service codebase
type: feedback
---

## CORS wildcard + credentials (RESOLVED in app_config.py)

Previously, `config/app_config.py` used `allow_origins=["*"]` AND `allow_credentials=True` simultaneously. This is an invalid/insecure combination — browsers reject credentialed cross-origin requests when the server responds with `Access-Control-Allow-Origin: *`.

This was fixed: origins are now driven by an `ALLOWED_ORIGINS` env var with localhost defaults, and methods/headers are restricted to explicit allowlists.

**Remaining gap**: If `ALLOWED_ORIGINS` is unset in production and the env var is not injected by the deployment pipeline, the service silently falls back to localhost-only defaults, which will break the production frontend with no startup warning. A startup assertion should validate this in production.

**How to apply:** When reviewing CORS config, check (1) wildcard+credentials co-existence, (2) whether the production env var is enforced at startup.

## Swagger UI exposure

Previously, `/docs`, `/redoc`, and `/openapi.json` were unconditionally exposed. Now gated by `_is_production` flag derived from `APP_ENV` env var.

**Remaining gap**: The `openapi_url=None` guard still does not protect the `servers` list embedded in the FastAPI constructor — it hardcodes the production URL `https://api.tallybot.com` in plaintext. This is low-risk but constitutes information disclosure if the schema is ever exposed accidentally.

**How to apply:** When reviewing FastAPI app instantiation, check both the docs_url guards and the `servers=` list for hardcoded production hostnames.

## Module-level env var evaluation

`_is_production`, `_raw_origins`, and `_allowed_origins` are computed at import time (module level) in `app_config.py`. This means they cannot be overridden by test fixtures that set env vars after import, and any import-order issue will silently use wrong values.

**How to apply:** Flag module-level `os.getenv()` in config files as a testability concern, especially when those values gate security behavior.

## service_config.py: get_secret() exception anti-pattern (OPEN)

`get_secret()` has a bare `except Exception as e: raise e` block that adds no value — it discards the original traceback frame and re-raises. The call should not be wrapped at all, or should wrap into a meaningful EnvironmentError at the call site (which `initialize_environment()` already does). Flag bare re-raise patterns in secrets-loading code.

## service_config.py: get_api_keys() exposes live secrets to callers (OPEN)

`get_api_keys()` returns a dict of raw API key strings from `os.environ`. Any caller that logs, serializes, or passes this dict into an LLM trace will leak secrets. The function is imported into `main.py` but does not appear to be used for anything that would cause a leak currently. However the function is a risk surface — returning full key values is an anti-pattern; prefer returning boolean presence checks or masked summaries for diagnostic purposes.

## service_config.py: _apply_secrets() returns raw secrets dict (OPEN)

`_apply_secrets()` returns `required_env_vars` (the full key→value dict). `initialize_environment()` captures this as `env_vars` at module level, making the raw keys available as a module-level variable. This is low risk today (no logging of `env_vars`), but the pattern should be changed to return a presence-only summary dict.

## service_config.py: Pydantic models lack enum validation for model names (OPEN)

`ConversationRequest` and `EvaluationRequest` declare `stage1_model` and `stage2_model` as plain `str`. Validation against `MODEL_REGISTRY` happens only at runtime inside `resolve_llm()`. A user supplying an invalid model name gets a 400 at request time, not at parse time. This is adequate but not ideal — `Literal["gpt-3.5-turbo", "gpt-4o-mini", ...]` or a custom validator would catch it earlier and produce a cleaner OpenAPI schema.
