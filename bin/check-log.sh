# !/bin/sh

# Load the configuration file if exist
KMANGA_CONF=$(dirname $0)/kmanga.conf
if [ ! -f "$KMANGA_CONF" ]; then
    echo "Please, create a $KMANGA_CONF configuration file."
    exit 1
fi
source $KMANGA_CONF

if [ $# -eq 0 ]; then
    echo "Please, provide a log file name"
    exit 1
fi

ERROR="^[-: [:digit:]]+ \[[._a-zA-Z]+\] ERROR:"
TRACE="^Traceback \(most recent call last\)"
RE="($ERROR)|($TRACE)"
if grep -q -E "$RE" $1; then
    FILE=`basename $1`
    SUBJECT="Error found in '$FILE'"
    SENDER="admin@kmanga.net"
    RECEIVER=$EMAIL
    TEXT="Please, check '$1' in the server to find the cause."
    MAIL_TXT="Subject: $SUBJECT\nFrom: $SENDER\nTo: $RECEIVER\n\n$TEXT"
    echo -e $MAIL_TXT | /usr/sbin/sendmail -t
fi
