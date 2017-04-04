#!/bin/sh

# Load the configuration file if exist
KMANGA_CONF=$(dirname $0)/kmanga.conf
if [ ! -f "$KMANGA_CONF" ]; then
    echo "Please, create a $KMANGA_CONF configuration file."
    exit 1
fi
source $KMANGA_CONF

PREFIX=$VENV
LOG=$PREFIX/pgsql/logfile
DATA=$PREFIX/pgsql/data

$PREFIX/bin/redis-server $PREFIX/etc/redis.conf
