#!/bin/bash
# This script finds and kills any running Streamlit process for this project
# and then restarts it.

# Find and kill the old Streamlit process
echo "Searching for running Streamlit process..."
# The grep pattern is adjusted to match the new way of running from within the presentation directory
PID=$(ps aux | grep "[s]treamlit run streamlit_app.py" | grep -v grep | awk '{print $2}')

if [ -n "$PID" ]; then
  echo "Found Streamlit process with PID: $PID. Terminating..."
  kill $PID
  sleep 2 # Wait for graceful shutdown
  if ps -p $PID > /dev/null; then
    echo "Process did not terminate gracefully. Forcing kill..."
    kill -9 $PID
  fi
  echo "Process terminated."
else
  echo "No running Streamlit process found."
fi

# Set locale for Korean
export LANG=ko_KR.UTF-8
export LC_ALL=ko_KR.UTF-8

# Start the new Streamlit process from within the presentation directory
echo "Starting new Streamlit process..."
cd presentation
../.venv/bin/streamlit run streamlit_app.py > streamlit.log 2>&1 &
