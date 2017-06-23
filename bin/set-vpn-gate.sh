#!/bin/sh

set -e

# Load the configuration file if exist
KMANGA_CONF=$(dirname $0)/kmanga.conf
if [ ! -f "$KMANGA_CONF" ]; then
    echo "Please, create a $KMANGA_CONF configuration file."
    exit 1
fi
source $KMANGA_CONF

UNPACK=$(dirname $0)/vpn-gate-unpack.py


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

OVPN_CONF="non-valid-configuration"


# Create the configuration directory and download the ovpn
function download_ovpn() {
    # If the new directory exist, recreate it
    if [ -d "$VPN_PATH.new" ]; then
	rm -fr "$VPN_PATH.new"
    fi
    mkdir "$VPN_PATH.new"

    # Download the new configuration
    pushd "$VPN_PATH.new"
    echo "Unpacking vpn-gate configuration..."
    python ../$UNPACK --host $HOST
    popd

    # Interchange the configuration directory
    if [ -d "$VPN_PATH" ]; then
	rm -fr "$VPN_PATH"
    fi
    mv "$VPN_PATH.new" "$VPN_PATH"
    echo -e "vpn\nvpn" > "$VPN_PATH/auth.txt"
}


function rnd_sleep() {
    local minutes=$(($RANDOM % $RENEW_MAX))
    minutes=$(($minutes < $RENEW_MIN ? $RENEW_MIN : $minutes))
    echo "Renew in $minutes minutes..."
    sleep $(($minutes * 60))
}


function run_openvpn() {
    local tries=30;
    for conf in $(ls $VPN_PATH/*.ovpn | sort --random-sort); do
	tries=$((tries-1))
	if [[ $tries -le 0 ]]; then
	    echo "No more tries, restarting the configuration"
	    return
	fi

	local proc="openvpn --config $OVPN_CONF"
	if pgrep --full "$proc" >/dev/null; then
	    echo "Closing $OVPN_CONF connection..."
	    pkill --signal SIGUSR1 --full "$proc"
	    sleep 30
	fi
	OVPN_CONF=$conf
	echo "Starting $OVPN_CONF connection..."
	pushd $VPN_PATH
	openvpn --config "$OVPN_CONF" &
	popd
	sleep 30

	# Check if the VPN is working
	if sudo -u $AS_USER -- sh -c "$COMMAND"; then
	    echo "VPN valid found!"
	    rnd_sleep
	else
    	    echo "VPN not valid! - reconnecting"
	fi
    done
}


# Main loop
while /bin/true; do
    download_ovpn
    run_openvpn
done
