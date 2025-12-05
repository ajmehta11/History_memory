
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROCESSOR_SCRIPT="$SCRIPT_DIR/cron_processor.py"

PYTHON_PATH=$(which python3)

CRON_ENTRY="* * * * * PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin && cd $SCRIPT_DIR && $PYTHON_PATH $PROCESSOR_SCRIPT >> $SCRIPT_DIR/logs/cron.log 2>&1"

echo "Setting up cron job for history processor"
echo "=================================="
echo "Script location: $PROCESSOR_SCRIPT"
echo "Python path: $PYTHON_PATH"
echo "Cron entry: $CRON_ENTRY"
echo "=================================="
echo ""

(crontab -l 2>/dev/null | grep -F "$PROCESSOR_SCRIPT") && {
    echo "Cron job already exists!"
    echo ""
    echo "Current cron jobs:"
    crontab -l | grep -F "$PROCESSOR_SCRIPT"
    echo ""
    read -p "Do you want to replace it? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
    crontab -l 2>/dev/null | grep -vF "$PROCESSOR_SCRIPT" | crontab -
}

(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo "✅ Cron job installed successfully!"
echo ""
echo "The processor will run every hour at minute 0"
echo "Logs will be saved to: $SCRIPT_DIR/logs/"
echo ""
echo "To view your cron jobs:"
echo "  crontab -l"
echo ""
echo "To remove the cron job:"
echo "  crontab -e"
echo "  (then delete the line containing 'cron_processor.py')"
echo ""
echo "To test the processor manually:"
echo "  cd $SCRIPT_DIR"
echo "  python3 cron_processor.py"
echo ""
