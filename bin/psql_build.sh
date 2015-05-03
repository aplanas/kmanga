#!/bin/sh

# Load the configuration file if exist
if [ ! -f "bin/kmanga.conf" ]; then
    echo "Please, create a bin/kmanga.conf configuration file."
    exit 1
fi
. bin/kmanga.conf

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
