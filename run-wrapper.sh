#!/bin/bash

export API_BASE=http://localhost:8000
rm /tmp/to-wrapper /tmp/from-wrapper
mkfifo /tmp/to-wrapper /tmp/from-wrapper

docker compose rm -f wrapper
docker compose up wrapper