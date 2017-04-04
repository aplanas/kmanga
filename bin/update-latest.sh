# !/bin/sh

# Load the configuration file if exist
KMANGA_CONF=$(dirname $0)/kmanga.conf
if [ ! -f "$KMANGA_CONF" ]; then
    echo "Please, create a $KMANGA_CONF configuration file."
    exit 1
fi
source $KMANGA_CONF

source $VENV/bin/activate

spiders=$(kmanga/manage.py scrapy list | grep "^- " | cut -d" " -f2)
for spider in $spiders ; do
    LOG=$LOG_PATH/latest-$spider-$(date "+%Y-%m-%d-%T").log
    (kmanga/manage.py scrapy update-latest --spider=$spider &> $LOG ; bin/check-log.sh $LOG) &
done

wait
