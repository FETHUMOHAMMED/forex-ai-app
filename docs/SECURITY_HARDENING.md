# Security Hardening Checklist

> Status: Validation environment - basic security only
> Production requires ALL items below

## CURRENT STATUS

| # | Requirement | Current | Production Needed |
|---|-------------|---------|-------------------|
| 1 | API keys rotated | ? Not rotated | ? Every 30-90 days |
| 2 | Secrets encrypted at rest | ? Plain .env | ? Vault/AWS KMS |
| 3 | MT5 credentials protected | ?? Environment vars | ? Vault/HSM |
| 4 | OS permissions restricted | ? Dev machine | ? Dedicated VM |
| 5 | DB access restricted | ? Local file | ? Network isolation |
| 6 | Docker secrets | ? Not using | ? Docker secrets |
| 7 | Firewall rules | ? None | ? UFW/NSG |
| 8 | HTTPS | ? HTTP only | ? TLS 1.3 |
| 9 | Audit trail | ? Decision ledger | ? Immutable audit |
| 10 | Dependency scanning | ? None | ? Snyk/OWASP |
| 11 | Supply-chain scanning | ? None | ? pip-audit |
| 12 | Least privilege | ?? Full admin | ? Restricted user |
| 13 | Emergency revocation | ? None | ? Kill switch |

## IMMEDIATE (Validation Phase)

- [x] Environment-based secrets (SecretsManager)
- [x] .gitignore includes .env, *.key, *.pem
- [x] API key authentication
- [x] Rate limiting
- [x] Idempotency keys
- [ ] Rotate existing hardcoded credentials (P0)
- [ ] Add pip-audit to CI pipeline
- [ ] Add dependency scanning to CI

## PRODUCTION (Before Real Money)

- [ ] Dedicated VM (not dev machine)
- [ ] OS firewall (allow only ports 3000, 3001, 8001, 8002)
- [ ] HTTPS with TLS certificates
- [ ] Secrets in Vault or AWS KMS
- [ ] MT5 credentials in Vault
- [ ] Database access restricted to local process
- [ ] Docker secrets for containerized deployment
- [ ] Emergency kill switch (disable all trading)
- [ ] Full audit trail with immutable logs
- [ ] Least privilege OS user
- [ ] Regular security scanning
