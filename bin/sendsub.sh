# !/bin/sh

# Load the configuration file if exist
if [ ! -f "bin/kmanga.conf" ]; then
    echo "Please, create a bin/kmanga.conf configuration file."
    exit 1
fi
. bin/kmanga.conf

. $VENV/bin/activate

LOG=$LOG_PATH/sendsub-$(date "+%Y-%m-%d-%T").log
kmanga/manage.py scrapy sendsub &> $LOG
bin/check-log.sh $LOG
