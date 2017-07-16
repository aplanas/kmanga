# !/bin/sh

# Load the configuration file if exist
KMANGA_CONF=$(dirname $0)/kmanga.conf
if [ ! -f "$KMANGA_CONF" ]; then
    echo "Please, create a $KMANGA_CONF configuration file."
    exit 1
fi
source $KMANGA_CONF

# Clean backups
find $BACKUP_PATH/*.sql.gz -type f -mtime +2 -exec rm {} \; &> /dev/null || true

# Clean logs
find $LOG_PATH/*.log -type f -mtime +2 -exec rm {} \; &> /dev/null || true
