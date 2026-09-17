# Deployment to AGIdock

Production target: 155.103.253.176, 32 vCPUs and 64 GB RAM. The application checkout is /srv/ustc-course; its Python 3.11 environment is /opt/icourse-venv. See [AGIDOCK.md](AGIDOCK.md) for migration details and the remaining DNS cutover gates.

Every pull request runs checks on GitHub-hosted infrastructure. Pushes to master run checks and then deploy the exact tested commit through the agidock-production environment, restricted to master. No persistent Actions runner is needed on the production VM. The deployment SSH key is fresh, has a forced command and no forwarding, and the workflow verifies the pinned server host key. GitHub environment secrets are AGIDOCK_DEPLOY_SSH_KEY and AGIDOCK_DEPLOY_KNOWN_HOSTS.

The root-owned adapter /usr/local/sbin/icourse-ci-deploy accepts only `deploy <full commit SHA>`. It runs deploy.sh as icourse. That account has only a narrowly scoped sudo permission to restart ustc-course.service. The adapter and authorized_keys must be installed independently of repository updates.

The deploy script fetches master, requires a clean checkout and a fast-forward, verifies the root-owned runtime against requirements-agidock.lock, compiles/imports the application, checks the Alembic revision, restarts the service, and waits for HTTP 200. It rolls back code on failure. A repeated deployment of the current revision is a no-op.

Dependency upgrades require administrator provisioning and validation of the locked environment before automated deployment. Database migrations require administrator review, a backup, and separate database credentials; the runtime account deliberately has no schema privileges. CI refuses a schema mismatch and never automatically downgrades the database. Keep code compatible with the schema throughout a migration.

Production configuration is excluded from Git. Do not overwrite config/default.py, /data/icourse, or system configuration during deployment. Final data synchronization, transactional mail configuration, integration credential rotation, and website DNS cutover are separate migration steps. Until cutover, the public site remains on the old server and the AGIdock site retains staging authentication.

To deploy an already approved master commit manually as an administrator, run deploy/deploy.sh as icourse with DEPLOY_REF set to its full SHA. For failures inspect `journalctl -u ustc-course.service` and the Actions job log. Do not force-reset production code to bypass the clean-tree or fast-forward checks.
