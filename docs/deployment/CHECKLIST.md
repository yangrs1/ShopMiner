# ShopMiner Deployment Checklist

> Use this checklist when deploying ShopMiner to a new production server.
> Each item includes verification steps. Check off items as you complete them.

---

## 1. Prerequisites

- [ ] **Python 3.12+ installed**
  - `python3 --version` shows `3.12.x` or higher.
  - The `pip` and `venv` modules are available.

- [ ] **PostgreSQL 16 installed and running**
  - `psql --version` shows `16.x`.
  - `systemctl status postgresql` reports active (running).
  - The server accepts TCP connections on `127.0.0.1:5432`.

- [ ] **Redis 7 installed and running**
  - `redis-server --version` shows `7.x`.
  - `systemctl status redis` reports active (running).
  - `redis-cli ping` returns `PONG`.

- [ ] **Node.js 18+ installed**
  - `node --version` shows `v18.x` or higher.
  - `npm --version` shows `9.x` or higher. Needed only for frontend builds.

- [ ] **Nginx installed**
  - `nginx -v` shows version.
  - `systemctl status nginx` reports active.

- [ ] **Required system packages**
  - `build-essential`, `libpq-dev`, `python3-dev` for psycopg2 compilation.

---

## 2. System User and Directory

- [ ] **Create shopminer system user**
  ```bash
  sudo useradd --system --user-group --home-dir /opt/shopminer --create-home shopminer
  ```

- [ ] **Create application directory structure**
  ```bash
  sudo mkdir -p /opt/shopminer/{static,logs,.venv}
  sudo chown -R shopminer:shopminer /opt/shopminer
  ```

- [ ] **Clone or copy application code**
  ```bash
  sudo -u shopminer git clone <repo-url> /opt/shopminer
  # or copy via rsync/scp
  ```

---

## 3. Environment Variables

- [ ] **Create `.env` file**
  Copy from `.env.example` at the project root:
  ```bash
  sudo -u shopminer cp /opt/shopminer/.env.example /opt/shopminer/.env
  ```

- [ ] **Set production secrets**
  - `APP_SECRET_KEY`: generate with `openssl rand -hex 32`
  - `JWT_SECRET_KEY`: generate with `openssl rand -hex 32`
  - `FLASK_ENV=production`
  - `DB_URI`: point to the production PostgreSQL database
  - `BASE_URL`: set to `https://shopminer.example.com`
  - `CORS_ORIGINS`: set to the production domain
  - `LOG_LEVEL=INFO`

- [ ] **Restrict `.env` permissions**
  ```bash
  sudo chmod 600 /opt/shopminer/.env
  sudo chown shopminer:shopminer /opt/shopminer/.env
  ```

---

## 4. Database

- [ ] **Create PostgreSQL database and user**
  ```sql
  CREATE USER shopminer WITH PASSWORD '<strong-password>';
  CREATE DATABASE shopminer OWNER shopminer;
  GRANT ALL PRIVILEGES ON DATABASE shopminer TO shopminer;
  ```

- [ ] **Run database migrations**
  ```bash
  cd /opt/shopminer
  sudo -u shopminer /opt/shopminer/.venv/bin/flask db upgrade
  ```

- [ ] **Seed demo data (optional)**
  ```bash
  sudo -u shopminer /opt/shopminer/.venv/bin/python scripts/seed_demo_data.py
  ```

- [ ] **Verify database connection**
  ```bash
  psql -U shopminer -d shopminer -c "\dt"
  ```

---

## 5. Python Dependencies

- [ ] **Create and activate virtual environment**
  ```bash
  sudo -u shopminer python3 -m venv /opt/shopminer/.venv
  ```

- [ ] **Install Python packages**
  ```bash
  sudo -u shopminer /opt/shopminer/.venv/bin/pip install -r /opt/shopminer/requirements.txt
  ```

---

## 6. Frontend Build

- [ ] **Install frontend dependencies**
  ```bash
  cd /opt/shopminer/frontend
  sudo -u shopminer npm ci
  ```

- [ ] **Build Vue 3 SPA**
  ```bash
  cd /opt/shopminer/frontend
  sudo -u shopminer npm run build
  ```
  Output goes to `/opt/shopminer/frontend/dist/`.

- [ ] **Verify build output exists**
  `ls /opt/shopminer/frontend/dist/index.html` returns a file.

---

## 7. Nginx Configuration

- [ ] **Copy nginx config**
  ```bash
  sudo cp /opt/shopminer/docs/deployment/nginx.conf /etc/nginx/sites-available/shopminer
  sudo ln -s /etc/nginx/sites-available/shopminer /etc/nginx/sites-enabled/
  ```

- [ ] **Update `server_name`**
  Replace `shopminer.example.com` with the actual domain in the nginx config.

- [ ] **Test and reload nginx**
  ```bash
  sudo nginx -t
  sudo systemctl reload nginx
  ```

---

## 8. SSL Certificate (Let's Encrypt)

- [ ] **Obtain SSL certificate**
  ```bash
  sudo apt install certbot python3-certbot-nginx
  sudo certbot --nginx -d shopminer.example.com
  ```

- [ ] **Verify auto-renewal**
  ```bash
  sudo certbot renew --dry-run
  ```
  Ensure Certbot's systemd timer is active: `systemctl status certbot.timer`.

---

## 9. Systemd Service

- [ ] **Copy systemd unit file**
  ```bash
  sudo cp /opt/shopminer/docs/deployment/shopminer.service /etc/systemd/system/
  ```

- [ ] **Reload and enable service**
  ```bash
  sudo systemctl daemon-reload
  sudo systemctl enable shopminer
  ```

- [ ] **Start and verify service**
  ```bash
  sudo systemctl start shopminer
  sudo systemctl status shopminer
  ```
  Status should show `active (running)` with no errors.

---

## 10. Health Check Verification

- [ ] **Check application HTTP response**
  ```bash
  curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/api/v1/health
  # Expected: 200
  ```

- [ ] **Check application via nginx**
  ```bash
  curl -s -o /dev/null -w "%{http_code}" https://shopminer.example.com/api/v1/health
  # Expected: 200
  ```

- [ ] **Verify static file serving**
  ```bash
  curl -s -o /dev/null -w "%{http_code}" https://shopminer.example.com/static/
  # Expected: 200 or 302
  ```

- [ ] **Verify frontend SPA loads**
  ```bash
  curl -s -o /dev/null -w "%{http_code}" https://shopminer.example.com/frontend/dist/index.html
  # Expected: 200
  ```

- [ ] **Test login flow**
  ```bash
  curl -s -X POST https://shopminer.example.com/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@shopminer.com","password":"Admin@123"}'
  # Expected: JSON response with code 200 and access_token
  ```

---

## 11. Log Rotation

- [ ] **Configure logrotate for application logs**
  Create `/etc/logrotate.d/shopminer`:
  ```
  /opt/shopminer/logs/*.log {
      daily
      rotate 14
      compress
      delaycompress
      missingok
      notifempty
      copytruncate
  }
  ```

- [ ] **Configure logrotate for nginx**
  Verify `/etc/logrotate.d/nginx` is present and includes the ShopMiner access and error logs.

- [ ] **Test logrotate configuration**
  ```bash
  sudo logrotate -d /etc/logrotate.d/shopminer
  ```

---

## 12. Firewall Rules

- [ ] **Open HTTP and HTTPS ports**
  ```bash
  sudo ufw allow 80/tcp
  sudo ufw allow 443/tcp
  sudo ufw allow 22/tcp  # SSH
  ```

- [ ] **Restrict direct access to port 5000**
  The gunicorn backend listens on `127.0.0.1:5000`. No firewall rule should expose it externally.

- [ ] **Verify firewall status**
  ```bash
  sudo ufw status verbose
  ```

---

## 13. Monitoring Setup

- [ ] **Verify systemd service monitoring**
  ```bash
  sudo systemctl status shopminer --no-pager -l
  ```
  Configure alerting for service failures (e.g., email, Slack webhook).

- [ ] **Set up basic resource monitoring**
  - Disk usage: `df -h`
  - Memory: `free -h`
  - CPU load: `uptime`
  - Nginx metrics: enable `stub_status` module
  - Consider Prometheus + node_exporter for production-grade monitoring.

- [ ] **Configure log monitoring**
  Review `journalctl -u shopminer --since "1 hour ago"` for errors.
  Consider a log aggregation tool (Loki, Graylog, or similar) for larger deployments.

---

## 14. Backup Strategy

- [ ] **Database backup**
  ```bash
  # Daily PostgreSQL dump
  0 2 * * * pg_dump -U shopminer shopminer | gzip > /opt/shopminer/backups/db_$(date +\%Y\%m\%d).sql.gz
  ```

- [ ] **Uploaded files backup**
  ```bash
  # Daily backup of uploaded media
  0 3 * * * tar czf /opt/shopminer/backups/uploads_$(date +\%Y\%m\%d).tar.gz /opt/shopminer/static/uploads/
  ```

- [ ] **Retention policy**
  - Keep daily backups for 7 days.
  - Keep weekly backups for 4 weeks.
  - Keep monthly backups for 6 months.
  - Test restore procedure quarterly.

- [ ] **Off-site backup**
  Copy backups to an off-site location (S3, rsync to another server, etc.).

---

## 15. Security Considerations

- [ ] **OS-level hardening**
  - Automatic security updates enabled: `sudo apt install unattended-upgrades`
  - SSH key-only authentication.
  - Fail2ban installed and configured for SSH and nginx.

- [ ] **Application secrets**
  - `APP_SECRET_KEY` and `JWT_SECRET_KEY` are unique and strong.
  - Secrets are NOT committed to version control.
  - `.env` file has permissions `600`.

- [ ] **Nginx security headers**
  Verify headers are present on all responses:
  ```bash
  curl -sI https://shopminer.example.com | grep -i '^\(X-Frame-Options\|X-Content-Type-Options\|Strict-Transport-Security\|Content-Security-Policy\)'
  ```

- [ ] **Rate limiting**
  Nginx rate limiting (`30r/s`) is active. Verify by sending rapid requests and checking for `503` responses with the `Retry-After` header.

- [ ] **File upload restrictions**
  - `client_max_body_size` limited to `16m` in nginx.
  - File type validation in the application code.
  - Uploaded files stored outside the application root where possible.

- [ ] **Dependency vulnerability scanning**
  ```bash
  pip-audit -r /opt/shopminer/requirements.txt
  npm audit --prefix /opt/shopminer/frontend
  ```

---

## 16. Rollback Plan

> A rollback should be executed when the health check fails or a critical bug is found post-deployment.

- [ ] **Pre-deployment snapshot**
  Before any deployment, record:
  - Current git commit hash: `git log --oneline -1`
  - Database backup: `pg_dump -U shopminer shopminer > pre_deploy_backup.sql`
  - Current static files backup.

- [ ] **Rollback application code**
  ```bash
  cd /opt/shopminer
  sudo -u shopminer git checkout <previous-stable-commit>
  sudo systemctl restart shopminer
  ```

- [ ] **Rollback database**
  ```bash
  sudo -u postgres psql -c "DROP DATABASE shopminer;"
  sudo -u postgres psql -c "CREATE DATABASE shopminer OWNER shopminer;"
  psql -U shopminer shopminer < pre_deploy_backup.sql
  ```

- [ ] **Verify rollback**
  Run the full health check (Section 10) after rollback.

---

## References

| Document | Description |
|----------|-------------|
| `docs/deployment/nginx.conf` | Production nginx reverse proxy configuration |
| `docs/deployment/shopminer.service` | Systemd unit file for gunicorn |
| `docs/ci/jenkins-setup.md` | Jenkins CI/CD pipeline setup |
| `docs/adr/ADR-001.md` | Flask 3.0 RESTful architecture decision |
| `docs/adr/ADR-002.md` | Additional architecture decisions |
| `docs/adr/ADR-003.md` | Additional architecture decisions |
| `docs/adr/ADR-004.md` | Additional architecture decisions |
| `docs/adr/ADR-005.md` | Vue 3 + Element Plus + ECharts frontend tech stack |
| `docs/api/openapi.yaml` | API specification and endpoints |
| `README.md` | Project overview and quick start |
| `Jenkinsfile` | CI/CD pipeline definition |
| `docker-compose.yml` | Local development orchestration |

---

> **Version**: 1.0  
> **Last updated**: 2026-06-15  
> **Project**: ShopMiner
