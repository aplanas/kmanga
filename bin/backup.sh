# !/bin/sh

# Load the configuration file if exist
if [ ! -f "bin/kmanga.conf" ]; then
    echo "Please, create a bin/kmanga.conf configuration file."
    exit 1
fi
. bin/kmanga.conf

# Database backup
BACKUP=$BACKUP_PATH/kmanga-$(date "+%Y-%m-%d-%T").sql.gz
pg_dump kmanga | gzip > $BACKUP
