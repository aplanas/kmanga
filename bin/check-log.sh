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

ERROR="(ERROR|Traceback \(most recent call last\))"
if grep -q -E "$ERROR" $1; then
    SUBJECT="Error found in '$1'"
    SENDER="admin@kmanga.net"
    RECEIVER=$EMAIL
    TEXT="Please, check '$1' in the server to find the cause."
    MAIL_TXT="Subject: $SUBJECT\nFrom: $SENDER\nTo: $RECEIVER\n\n$TEXT"
    echo -e $MAIL_TXT | /usr/sbin/sendmail -t
fi
