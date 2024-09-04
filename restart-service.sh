#/bin/bash

getpid()
{
  PID=$(systemctl show --property=MainPID --value ustc-course.service)
}

getpid
echo "Original PID: $PID"
systemctl restart ustc-course.service
echo "Original process killed, spawning new process..."
sleep 3
getpid
echo "New PID: $PID"
