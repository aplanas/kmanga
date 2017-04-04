# Load the configuration file if exist
# NOTE: this file is sourced, so `dirname $0` will not work
KMANGA_CONF=bin/kmanga.conf
if [ ! -f "$KMANGA_CONF" ]; then
    echo "Please, create a $KMANGA_CONF configuration file."
    #exit 1
fi
source $KMANGA_CONF

if [ ! -d $VENV ]; then
    echo "Virtual environment $VENV not found."
    exit 1
fi

export LD_LIBRARY_PATH=$VENV/lib
export PYTHONPATH=`pwd`:`pwd`/kmanga:`pwd`/scraper

source $VENV/bin/activate
