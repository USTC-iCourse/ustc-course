# AGIdock deployment

Runtime: Ubuntu 26.04 with an isolated Python 3.11 interpreter at /opt/python and virtual environment /opt/icourse-venv. Use deploy/requirements-agidock.lock to reproduce the tested environment. Do not use Ubuntu's default Python 3.14 for this application without a separate compatibility test.

Flask/Babel/Markup imports were updated for the patched dependency versions. Ranking PDF generation now uses WeasyPrint 70 and permits resources only from the application's static directory. Install libpango-1.0-0, libpangoft2-1.0-0 and fonts-noto-cjk. Its HTTP generation endpoint is restricted to loopback in Nginx; a systemd timer runs the export directly.

Configuration lives in config/default.py, mode 0640 root:icourse, and is excluded from Git. Generate fresh session and database credentials. Database permissions for the runtime account are SELECT/INSERT/UPDATE/DELETE only; schema migrations require a separate privileged database account.

Gunicorn uses /etc/ustc-course-gunicorn.py and listens on loopback. Application data and search indexes live under /data/icourse. Nginx fronts the service and trusts client-IP headers only from official Cloudflare networks. Staging authentication must remain enabled until cutover is approved.

Before activating production, configure and test SMTP, replace exposed integration credentials, perform a final consistent data sync, and switch certificate renewal from the temporary old-host validation hooks to the new local webroot. Review and merge this migration branch before enabling production CI deployment.

Validation performed during migration: 97 tracked Python files compiled, 82 search tests passed, 15 HTTP routes returned 200, the schema revision matched the Alembic head, and a Chinese ranking PDF was generated. Database and transfer verification logs are under /root/migration on the destination.

Dependency audit exception: setuptools 80.10.2 is retained for pkg_resources compatibility with jieba/passlib. PYSEC-2026-3447 concerns macOS source-distribution packaging and does not apply to this Linux runtime. Do not interpret that exception as approval to use this environment for untrusted package builds.


## Pending CI activation

The prepared workflow uses GitHub-hosted jobs and SSH to 155.103.253.176. It no longer schedules jobs on the old `icourse-prod` runner. No persistent GitHub runner is required on the replacement production VM. Pull requests run checks only; deployment requires master in USTC-iCourse/ustc-course and the agidock-production environment.

Before merging this workflow, create that GitHub environment, restrict deployment branches to master, and install a dedicated fresh SSH key restricted with `restrict,command="/usr/local/sbin/icourse-ci-deploy"` in the icourse account. The root-owned command must validate SSH_ORIGINAL_COMMAND as `deploy <40 lowercase hex characters>` and invoke the deployment script with that exact commit. Store the private key as environment secret AGIDOCK_DEPLOY_SSH_KEY and the independently verified destination host key as AGIDOCK_DEPLOY_KNOWN_HOSTS. Do not reuse a key from either incident host.

Activation is pending GitHub authentication, environment configuration, and SSH key authorization. Grant icourse only `sudo /bin/systemctl restart ustc-course.service` using a validated sudoers entry. Merge all migration commits before switching the server checkout to master, then run a controlled deployment and health check. Disable/remove the old runner after the replacement deployment succeeds. The existing staging service remains running independently of CI until activation is complete.

The AGIdock deploy.sh now defaults to the Python 3.11 virtual environment. It verifies the full dependency lock against installed distributions, leaving the environment root-owned. Dependency version changes require administrator provisioning before a deployment can pass. Schema changes similarly stop deployment and roll back code until an administrator reviews/applies the migration with separate credentials. Ordinary code-only deployments remain automated. The forced-command adapter is staged at /usr/local/sbin/icourse-ci-deploy; SSH authorization and GitHub environment secrets remain pending access.

CodeQL findings addressed before activation: upload categories map to fixed directories and generated filenames are sanitized; email validation uses bounded linear checks; third-party sign-in callbacks require an exact administrator-configured THIRD_PARTY_SIGNIN_REDIRECTS entry (empty by default, so integrations require registration).

PI Review compatibility: register its HTTPS verification callback in THIRD_PARTY_SIGNIN_REDIRECTS and map its legacy HTTP callback to that exact HTTPS URL in THIRD_PARTY_SIGNIN_REDIRECT_ALIASES. Aliases cannot authorize destinations outside the allowlist.

OpenAI SDK updated to the tested version in requirements.txt and the dependency lock. The previous SDK passed an unsupported proxies argument to httpx before requests could run. Configure the direct https://api.openai.com/v1 endpoint with a fresh key.
