#!/bin/bash

experiment_id=""
container_id=""

send_stdout() {
  local line=$1
  local json_payload=$(jq -nc --arg line "$line" '{"stdout": $line}')
  local server_url="http://130.191.161.13:5001/api/upload/$experiment_id/$container_id/stdout"
  curl -X POST -H "Content-Type: application/json" -d "$json_payload" "$server_url"
}

# Run the Python script and process its stdout
python -u main.py 2>&1 | while IFS= read -r line; do
  send_stdout "$line"
done