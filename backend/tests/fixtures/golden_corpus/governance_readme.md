# Security Governance Readme

## 1. Scope and Objective
All engineers must complete secure code training within 60 days of onboarding.

## 2. Automated Pipeline
- Static code analysis (SAST) in CI
- Dependency vulnerability scanning

Refer to [Security Guidelines](https://internal.trulin.io/security) for details.

```python
def verify_signature(payload, secret):
    return hmac.compare_digest(payload, secret)
```
