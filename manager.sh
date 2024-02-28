#!/bin/sh

exec -a manager.sh env PYTHONPATH=. flask "$@"
