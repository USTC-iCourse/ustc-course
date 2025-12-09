# Deployment Instructions for Search Token Feature

## Prerequisites

1. Database migration has been applied (search_tokens table exists)
2. You have sudo access to deploy changes

## Step 1: Deploy Code to Production

```bash
# Copy files to production directory
sudo cp -r /home/boj/test-ustc-course/app /srv/ustc-course/
sudo cp /home/boj/test-ustc-course/gunicorn_config.py /srv/ustc-course/
sudo chown -R icourse:icourse /srv/ustc-course/
```

## Step 2: Create Log Files

```bash
# Create log files with proper permissions
sudo touch /var/log/ustc-course-access.log
sudo touch /var/log/ustc-course-error.log
sudo chown icourse:icourse /var/log/ustc-course-*.log
sudo chmod 644 /var/log/ustc-course-*.log
```

## Step 3: Update Systemd Service (Optional)

Update `/etc/systemd/system/ustc-course.service`:

```ini
[Unit]
Description=USTC iCourse - a popular course rating platform for USTC students
Requires=mysql.service
After=network-online.target nss-lookup.target

[Service]
Type=notify
NotifyAccess=main
User=icourse
Group=icourse
WorkingDirectory=/srv/ustc-course
# Use the config file
ExecStart=/home/icourse/.local/bin/gunicorn -c gunicorn_config.py app:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
Restart=on-failure
TimeoutStopSec=5
PrivateTmp=true

# Capture output to journal
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Then reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart ustc-course.service
```

## Step 4: View Logs

### Real-time Monitoring

```bash
# Watch error log file
tail -f /var/log/ustc-course-error.log

# Watch access log file
tail -f /var/log/ustc-course-access.log

# Watch systemd journal (if StandardOutput configured)
sudo journalctl -u ustc-course.service -f

# Filter for search token errors
tail -f /var/log/ustc-course-error.log | grep -i "search token"
```

### Historical Logs

```bash
# View recent errors
tail -100 /var/log/ustc-course-error.log

# Search for specific errors
grep "Error.*search token" /var/log/ustc-course-error.log

# View logs from today
grep "$(date +%Y-%m-%d)" /var/log/ustc-course-error.log
```

## Step 5: Verify Deployment

1. **Test search functionality:**
   - Visit https://icourse.club
   - Try searching for a course
   - Navigate through pagination
   - Click "搜点评" / "搜课程" buttons

2. **Monitor logs:**
   ```bash
   tail -f /var/log/ustc-course-error.log
   ```

3. **Check for errors:**
   ```bash
   # Should return nothing if all is working
   grep -i "error.*token" /var/log/ustc-course-error.log
   ```

## Troubleshooting

### If logs are still empty:

```bash
# Check file permissions
ls -la /var/log/ustc-course-*.log

# Check if service is running
sudo systemctl status ustc-course.service

# Check Gunicorn process
ps aux | grep gunicorn

# Test write access
sudo -u icourse touch /var/log/ustc-course-test.log
```

### If search tokens don't work:

1. Verify database table exists:
   ```bash
   mysql -u [user] -p [database] -e "SHOW TABLES LIKE 'search_tokens';"
   ```

2. Check table structure:
   ```bash
   mysql -u [user] -p [database] -e "DESCRIBE search_tokens;"
   ```

3. Check for token generation:
   ```bash
   mysql -u [user] -p [database] -e "SELECT COUNT(*) FROM search_tokens;"
   ```

## Rollback Plan

If issues occur:

```bash
# Restore previous version
cd /srv/ustc-course
sudo -u icourse git checkout HEAD~1 app/

# Restart service
sudo systemctl restart ustc-course.service
```

## Log Rotation

Add to `/etc/logrotate.d/ustc-course`:

```
/var/log/ustc-course-*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 icourse icourse
    sharedscripts
    postrotate
        systemctl reload ustc-course.service > /dev/null 2>&1 || true
    endscript
}
```

## Success Indicators

- ✅ No 403 errors when searching
- ✅ Search works from all pages (home, navbar, error page)
- ✅ Pagination works without errors
- ✅ "搜点评"/"搜课程" buttons work
- ✅ No error messages in logs about tokens

