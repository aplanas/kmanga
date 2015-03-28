#!/bin/sh

# Load the configuration file if exist
if [ ! -f "bin/kmanga.conf" ]; then
    echo "Please, create a bin/kmanga.conf configuration file."
    exit 1
fi
. bin/kmanga.conf

V=$PSQL_VER
PREFIX=$VENV
DATA=$PREFIX/pgsql/data

if [ -d "$DATA" ]; then
    kill -INT `head -1 $DATA/postmaster.pid`
fi
