# Security policy

## Supported version and boundary

Security fixes target the latest 0.2.x release. Version 0.1 was a trusted-local research prototype and should not be exposed to a network.

DriftLab supports a shared authenticated workspace on a single host. A workspace key grants full evidence and job access. It is not a multi-tenant service, a secure sandbox for untrusted model adapters, or a compliance certification. Python adapters and SDK callers execute trusted code. Prompts, outputs, logs, reports and backups may contain sensitive information.

Use server mode behind HTTPS, explicit hosts/origins, a strong secret, private inference endpoints, local persistent storage and network access controls. Do not commit credentials, model weights, databases or raw evaluations. Review [deployment](docs/DEPLOYMENT.md) and [operations](docs/OPERATIONS.md) before network use.

## Reporting a vulnerability

Use GitHub's **Report a vulnerability** under the repository Security tab if private vulnerability reporting is enabled. If it is unavailable, open a minimal issue requesting a private contact without exploit details, secrets or personal data. Maintainers must enable private reporting and establish their response process before offering a public service. No response-time SLA is currently promised.

Include the affected version, deployment configuration with secrets removed, reproducible steps and impact. Avoid publishing working exploits before maintainers can assess the report. Never test against someone else's deployed workspace without permission.
