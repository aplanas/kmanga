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

cd $PSQL

tar -xjvf postgresql-$V.tar.bz2
cd postgresql-$V
./configure --prefix=$PREFIX
make world -j 4 && make install
cd ..
rm -fr postgresql-$V

# DATA=$PREFIX/pgsql/data
# mkdir -p $DATA
# $PREFIX/bin/initdb -D $DATA
# $PREFIX/bin/createdb test
