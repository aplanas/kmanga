# !/bin/sh

# Load the configuration file if exist
if [ ! -f "bin/kmanga.conf" ]; then
    echo "Please, create a bin/kmanga.conf configuration file."
    exit 1
fi
. bin/kmanga.conf

. $VENV/bin/activate

# Update genres
kmanga/manage.py scrapy update-genres &> $LOG_PATH/genres-$(date "+%Y-%m-%d-%T").log

# Update catalog of different spiders
spiders=$(kmanga/manage.py scrapy list --loglevel=WARNING | grep "^- " | cut -d" " -f2)
for spider in $spiders ; do
    kmanga/manage.py scrapy update-catalog --spider=$spider &> $LOG_PATH/$spider-$(date "+%Y-%m-%d-%T").log &
done

wait
