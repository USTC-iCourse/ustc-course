# AGIdock deployment

Runtime: Ubuntu 26.04 with an isolated Python 3.11 interpreter at /opt/python and virtual environment /opt/icourse-venv. Use deploy/requirements-agidock.lock to reproduce the tested environment. Do not use Ubuntu's default Python 3.14 for this application without a separate compatibility test.

Flask/Babel/Markup imports were updated for the patched dependency versions. Ranking PDF generation now uses WeasyPrint 70 and permits resources only from the application's static directory. Install libpango-1.0-0, libpangoft2-1.0-0 and fonts-noto-cjk. Its HTTP generation endpoint is restricted to loopback in Nginx; a systemd timer runs the export directly.

Configuration lives in config/default.py, mode 0640 root:icourse, and is excluded from Git. Generate fresh session and database credentials. Database permissions for the runtime account are SELECT/INSERT/UPDATE/DELETE only; schema migrations require a separate privileged database account.

Gunicorn uses /etc/ustc-course-gunicorn.py and listens on loopback. Application data and search indexes live under /data/icourse. Nginx fronts the service and trusts client-IP headers only from official Cloudflare networks. Staging authentication must remain enabled until cutover is approved.

Before activating production, configure and test SMTP, replace exposed integration credentials, perform a final consistent data sync, and switch certificate renewal from the temporary old-host validation hooks to the new local webroot. Review and merge this migration branch before enabling production CI deployment; the original deploy script's default Python paths target the old server.

Validation performed during migration: 97 tracked Python files compiled, 82 search tests passed, 15 HTTP routes returned 200, the schema revision matched the Alembic head, and a Chinese ranking PDF was generated. Database and transfer verification logs are under /root/migration on the destination.

Dependency audit exception: setuptools 80.10.2 is retained for pkg_resources compatibility with jieba/passlib. PYSEC-2026-3447 concerns macOS source-distribution packaging and does not apply to this Linux runtime. Do not interpret that exception as approval to use this environment for untrusted package builds.
