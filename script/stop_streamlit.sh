#!/bin/bash
# This script finds and kills any running Streamlit process for this project.
# Companion script to restart_streamlit.sh

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  Streamlit Process Termination Script"
echo "=========================================="
echo ""

# Find the Streamlit process
echo "🔍 Searching for running Streamlit process..."
PID=$(ps aux | grep "[s]treamlit run.*streamlit_app.py" | grep -v grep | awk '{print $2}')

if [ -z "$PID" ]; then
    echo "❌ No running Streamlit process found."
    echo ""
    echo "💡 Tip: Check if Streamlit is running with:"
    echo "   ps aux | grep streamlit"
    exit 0
fi

# Found the process
echo "✅ Found Streamlit process with PID: $PID"
echo ""

# Get process info
PROCESS_INFO=$(ps -p $PID -o pid,ppid,user,%cpu,%mem,etime,command | tail -n 1)
echo "📊 Process Information:"
echo "   $PROCESS_INFO"
echo ""

# Try graceful shutdown first
echo "🛑 Attempting graceful shutdown (SIGTERM)..."
kill $PID

# Wait for graceful shutdown
WAIT_TIME=0
MAX_WAIT=5

while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    if ! ps -p $PID > /dev/null 2>&1; then
        echo "✅ Process terminated gracefully after ${WAIT_TIME}s"
        echo ""
        echo "🎉 Streamlit successfully stopped!"
        exit 0
    fi
    sleep 1
    WAIT_TIME=$((WAIT_TIME + 1))
    echo "   Waiting... (${WAIT_TIME}/${MAX_WAIT}s)"
done

# Force kill if graceful shutdown failed
echo ""
echo "⚠️  Process did not terminate gracefully. Forcing kill (SIGKILL)..."
kill -9 $PID

# Verify force kill
sleep 1
if ps -p $PID > /dev/null 2>&1; then
    echo "❌ ERROR: Failed to terminate process $PID"
    echo "   You may need to manually kill it with: sudo kill -9 $PID"
    exit 1
else
    echo "✅ Process forcefully terminated"
    echo ""
    echo "🎉 Streamlit successfully stopped!"
    exit 0
fi
