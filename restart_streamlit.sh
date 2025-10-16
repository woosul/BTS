#!/bin/bash
# This script finds and kills any running Streamlit process for this project
# and then restarts it in SPA mode (st.navigation).

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Find and kill the old Streamlit process
echo "Searching for running Streamlit process..."
# Match both old multi-page and new SPA patterns
PID=$(ps aux | grep "[s]treamlit run.*streamlit_app.py" | grep -v grep | awk '{print $2}')

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
export LANGUAGE=ko_KR:ko

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Error: Virtual environment not found (.venv directory missing)"
    exit 1
fi

# Start the new Streamlit process in SPA mode using full venv path
echo "Starting new Streamlit process (SPA mode)..."
STREAMLIT_EMAIL="" "$SCRIPT_DIR/.venv/bin/python" -m streamlit run presentation/streamlit_app.py --server.headless=true > streamlit.log 2>&1 &

echo "Streamlit started. Check http://localhost:8501"
