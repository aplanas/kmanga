#!/bin/sh

# Load the configuration file if exist
KMANGA_CONF=$(dirname $0)/kmanga.conf
if [ ! -f "$KMANGA_CONF" ]; then
    echo "Please, create a $KMANGA_CONF configuration file."
    exit 1
fi
source $KMANGA_CONF

V=$PSQL_VER
PREFIX=$VENV
DATA=$PREFIX/pgsql/data

if [ -d "$DATA" ]; then
    kill -INT `head -1 $DATA/postmaster.pid`
fi
