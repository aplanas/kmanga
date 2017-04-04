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

# The first time that we start the server the $DATA directory doesn't
# exist.  In this case we need to create the `test` database, that
# also create the user as a admin.
create_test=0

if [ ! -d "$DATA" ]; then
    mkdir -p $DATA
    $PREFIX/bin/initdb -D $DATA
    create_test=1
fi
$PREFIX/bin/postgres -D $DATA >$LOG 2>&1 &
if [ $create_test -eq 1 ]; then
    sleep 1
    $PREFIX/bin/createdb test
fi
