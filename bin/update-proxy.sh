# !/bin/sh

# Load the configuration file if exist
KMANGA_CONF=$(dirname $0)/kmanga.conf
if [ ! -f "$KMANGA_CONF" ]; then
    echo "Please, create a $KMANGA_CONF configuration file."
    exit 1
fi
source $KMANGA_CONF

source $VENV/bin/activate

LOG=$LOG_PATH/update-proxy-$(date "+%Y-%m-%d-%T").log
kmanga/manage.py proxy update-proxy --clean > $LOG ; bin/check-log.sh $LOG
