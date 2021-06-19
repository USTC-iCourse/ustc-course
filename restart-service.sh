#/bin/bash

getpid()
{
  PID=$(ps aux | grep gunicorn | grep -v grep | awk '{print $2}' | sort | head -n 1)
}

getpid
echo "Original PID: $PID"
cd /srv/ustc-course && kill $PID && nohup /home/icourse/.local/bin/gunicorn -w 8 -b 127.0.0.1:3000 app:app >/dev/null 2>&1 &
echo "Original process killed, spawning new process..."
sleep 3
getpid
echo "New PID: $PID"
