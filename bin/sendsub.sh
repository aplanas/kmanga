# !/bin/sh

# Load the configuration file if exist
if [ ! -f "bin/kmanga.conf" ]; then
    echo "Please, create a bin/kmanga.conf configuration file."
    exit 1
fi
. bin/kmanga.conf

. $VENV/bin/activate
kmanga/manage.py scrapy sendsub &> $LOG_PATH/sendsub-$(date "+%Y-%m-%d-%T").log
