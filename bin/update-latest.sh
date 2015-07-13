# !/bin/sh

# Load the configuration file if exist
if [ ! -f "bin/kmanga.conf" ]; then
    echo "Please, create a bin/kmanga.conf configuration file."
    exit 1
fi
. bin/kmanga.conf

. $VENV/bin/activate

spiders=$(kmanga/manage.py scrapy list --loglevel=WARNING | grep "^- " | cut -d" " -f2)
for spider in $spiders ; do
    kmanga/manage.py scrapy update-latest --spider=$spider &> $LOG_PATH/latest-$spider-$(date "+%Y-%m-%d-%T").log
done
