#!/bin/sh

# Load the configuration file if exist
if [ ! -f "bin/kmanga.conf" ]; then
    echo "Please, create a bin/kmanga.conf configuration file."
    exit 1
fi
. bin/kmanga.conf

PREFIX=$VENV
LOG=$PREFIX/pgsql/logfile
DATA=$PREFIX/pgsql/data

$PREFIX/bin/redis-server $PREFIX/etc/redis.conf
