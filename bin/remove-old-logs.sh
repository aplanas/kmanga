# !/bin/sh

# Load the configuration file if exist
if [ ! -f "bin/kmanga.conf" ]; then
    echo "Please, create a bin/kmanga.conf configuration file."
    exit 1
fi
. bin/kmanga.conf

find $LOG_PATH/*.log -type f -mtime +15 -exec rm {} \; &> /dev/null || true
