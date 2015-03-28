#!/bin/sh

# Load the configuration file if exist
if [ ! -f "bin/kmanga.conf" ]; then
    echo "Please, create a bin/kmanga.conf configuration file."
    exit 1
fi
. bin/kmanga.conf

V=$REDIS_VER
PREFIX=$VENV

cd $REDIS

tar -xzvf redis-$V.tar.gz
cd redis-$V
make -j 4

# Manual installation
mkdir -p $PREFIX/bin $PREFIX/etc $PREFIX/var
mv src/redis-cli $PREFIX/bin/redis-cli
mv src/redis-server $PREFIX/bin/redis-server
mv src/redis-benchmark $PREFIX/bin/redis-benchmark
mv src/redis-check-aof $PREFIX/bin/redis-check-aof
mv src/redis-sentinel $PREFIX/bin/redis-sentinel
mv src/redis-check-dump $PREFIX/bin/redis-check-dump
cp redis.conf $PREFIX/etc/redis.conf
mv redis.conf $PREFIX/etc/redis.conf.sample
mv sentinel.conf $PREFIX/etc/sentine.conf.sample
cd ..
rm -fr redis-$V
