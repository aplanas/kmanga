# !/bin/sh

# Load the configuration file if exist
KMANGA_CONF=$(dirname $0)/kmanga.conf
if [ ! -f "$KMANGA_CONF" ]; then
    echo "Please, create a $KMANGA_CONF configuration file."
    exit 1
fi
source $KMANGA_CONF

source $VENV/bin/activate

# Clean mangas and list next candidates
# DAYS=20
# LOG=$LOG_PATH/candidates-clean-manga-$(date "+%Y-%m-%d-%T").log
# kmanga/manage.py clean manga --list -d $DAYS &> $LOG
# bin/check-log.sh $LOG

# DAYS=30
# LOG=$LOG_PATH/clean-manga-$(date "+%Y-%m-%d-%T").log
# kmanga/manage.py clean manga --force -d $DAYS &> $LOG
# bin/check-log.sh $LOG

# Clean covers
LOG=$LOG_PATH/clean-cover-$(date "+%Y-%m-%d-%T").log
kmanga/manage.py clean cover --force &> $LOG
bin/check-log.sh $LOG

# Clean cache of images
DAYS=0
HOURS=1
LOG=$LOG_PATH/clean-image-cache-$(date "+%Y-%m-%d-%T").log
if ! rqinfo -r -P bin -c rqsettings | grep -q busy; then
  kmanga/manage.py clean image-cache --force -d $DAYS -o $HOURS &> $LOG
  bin/check-log.sh $LOG
fi

# Clean cache of issues
DAYS=0
HOURS=1
LOG=$LOG_PATH/clean-issue-cache-$(date "+%Y-%m-%d-%T").log
if ! rqinfo -r -P bin -c rqsettings | grep -q busy; then
  kmanga/manage.py clean issue-cache --force -d $DAYS -o $HOURS &> $LOG
  bin/check-log.sh $LOG
fi

# Clean cache of MOBI
DAYS=0
HOURS=3
LOG=$LOG_PATH/clean-mobi-cache-$(date "+%Y-%m-%d-%T").log
if ! rqinfo -r -P bin -c rqsettings | grep -q busy; then
  kmanga/manage.py clean mobi-cache --force -d $DAYS -o $HOURS &> $LOG
  bin/check-log.sh $LOG
fi
