#!/bin/sh

set -e

# Load the configuration file if exist
KMANGA_CONF=$(dirname $0)/kmanga.conf
if [ ! -f "$KMANGA_CONF" ]; then
    echo "Please, create a $KMANGA_CONF configuration file."
    exit 1
fi
source $KMANGA_CONF


# Shows usage information
function usage() {
    echo "Usage: $0 <string>" 1>&2
    echo 1>&2
    echo "Where <string> is the host name used in the configuration file" 1>&2
    exit 1
}


# Read command line parameters
if [ $# -eq 0 ]; then
    usage
fi
# Base directory for the configuration files for hosts
HOST_CONF_PATH=$(dirname $0)/vpn.d
# Config file for the host name
HOST_CONF=$HOST_CONF_PATH/vpn_for_$1.conf

# Sourcing the configuration file will populate the variables: HOST,
# COMMAND, RENEW_MIN, RENEW_MAX
source $HOST_CONF

# List of IPs for the host
IPADDRS=$(getent hosts $HOST | awk '{ print $1 }')

# We append $HOST to $VPN_PATH, that was defined in kmanga.conf
VPN_PATH=$VPN_PATH/$HOST

# Configuration file name for OpenVPN
OVPN_CONF=$VPN_PATH/vpn.ovpn


# Create the configuration directory and download the ovpn
function download_ovpn() {
    # If the new directory exist, recreate it
    if [ -d "$VPN_PATH.new" ]; then
	rm -fr "$VPN_PATH.new"
    fi
    mkdir "$VPN_PATH.new"

    # Download the new configuration
    pushd "$VPN_PATH.new"
    wget https://www.ipvanish.com/software/configs/configs.zip
    unzip configs.zip
    rm configs.zip
    popd

    # Interchange the configuration directory
    if [ -d "$VPN_PATH" ]; then
	rm -fr "$VPN_PATH"
    fi
    mv "$VPN_PATH.new" "$VPN_PATH"
}


# Generate the OpenVPN configuration file
function generate_config() {
    # Generate remote list
    grep -h "^remote" $VPN_PATH/*.ovpn | cut -d' ' -f2 > "$VPN_PATH/_remotes"
    sort -R "$VPN_PATH/_remotes" | head -n 64 > "$VPN_PATH/_remotes64"

    # Complete the config file
    cp "$HOST_CONF_PATH/auth.txt" "$VPN_PATH"
    cp "$HOST_CONF_PATH/_template.ovpn" "$OVPN_CONF"
    sed -i "s#__PATH__#$VPN_PATH#g" "$OVPN_CONF"
    sed -i "s/__ROUTE__/$HOST/g" "$OVPN_CONF"
    while read remote; do
	echo "remote $remote" >> "$OVPN_CONF"
	echo "# tls-remote $remote" >> "$OVPN_CONF"
    done < "$VPN_PATH/_remotes64"

    rm "$VPN_PATH/_remotes" "$VPN_PATH/_remotes64"

    # Remove all the originals ovpn files
    rm $VPN_PATH/ipvanish*.ovpn
}


# Wait until there are not more active connections
function wait_no_connection() {
    # Generate the IP file
    >"$VPN_PATH/_ips"
    for ip in $IPADDRS; do
	echo $ip >> "$VPN_PATH/_ips"
    done

    while netstat -natp 2>/dev/null | grep -q -F -f "$VPN_PATH/_ips"; do
	echo "Found active connection..."
	sleep 30
    done

    rm "$VPN_PATH/_ips"
}


function reload_openvpn() {
    local proc="openvpn --config $OVPN_CONF"
    if pgrep --full "$proc" >/dev/null; then
	echo "Reloading openvpn service"
	pkill --signal SIGUSR1 --full "$proc"
    else
	echo "Starting openvpn service"
	openvpn --config "$OVPN_CONF" &
    fi

    # Check if the VPN is working
    sleep 30
    until sudo -u $AS_USER -- sh -c "$COMMAND"; do
    	echo "VPN not valid! - reconnecting"
	pkill --signal SIGUSR1 --full "$proc"
	sleep 30
    done
}


function rnd_sleep() {
    local minutes=$(($RANDOM % $RENEW_MAX))
    minutes=$(($minutes < $RENEW_MIN ? $RENEW_MIN : $minutes))
    echo "Renew in $minutes minutes..."
    sleep $(($minutes * 60))
}


# Main loop
while /bin/true; do
    download_ovpn
    generate_config
    # wait_no_connection
    reload_openvpn
    rnd_sleep
done
