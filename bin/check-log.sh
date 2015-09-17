# !/bin/sh

# Load the configuration file if exist
if [ ! -f "bin/kmanga.conf" ]; then
    echo "Please, create a bin/kmanga.conf configuration file."
    exit 1
fi
. bin/kmanga.conf

if [ $# -eq 0 ]; then
    echo "Please, provide a log file name"
    exit 1
fi

ERROR="^[-: [:digit:]]+ \[\w+\] ERROR:"
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
