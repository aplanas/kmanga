# !/bin/sh

# Load the configuration file if exist
if [ ! -f "bin/kmanga.conf" ]; then
    echo "Please, create a bin/kmanga.conf configuration file."
    exit 1
fi
. bin/kmanga.conf

. $VENV/bin/activate

# Database backup
BACKUP=$BACKUP_PATH/kmanga-$(date "+%Y-%m-%d-%T").sql.gz
pg_dump kmanga | gzip > $BACKUP

# Update genres
LOG=$LOG_PATH/genres-$(date "+%Y-%m-%d-%T").log
kmanga/manage.py scrapy update-genres &> $LOG
bin/check-log.sh $LOG

# Update catalog of different spiders
spiders=$(kmanga/manage.py scrapy list --loglevel=WARNING | grep "^- " | cut -d" " -f2)
for spider in $spiders ; do
    LOG=$LOG_PATH/$spider-$(date "+%Y-%m-%d-%T").log
    (kmanga/manage.py scrapy update-catalog --spider=$spider &> $LOG ; bin/check-log.sh $LOG) &
done

wait
