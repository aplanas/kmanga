# !/bin/sh

# Load the configuration file if exist
if [ ! -f "bin/kmanga.conf" ]; then
    echo "Please, create a bin/kmanga.conf configuration file."
    exit 1
fi
. bin/kmanga.conf

. $VENV/bin/activate

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
# LOG=$LOG_PATH/clean-cover-$(date "+%Y-%m-%d-%T").log
# kmanga/manage.py clean cover --force &> $LOG
# bin/check-log.sh $LOG

# Clean cache of images
DAYS=5
LOG=$LOG_PATH/clean-image-cache-$(date "+%Y-%m-%d-%T").log
kmanga/manage.py clean image-cache --force -d $DAYS &> $LOG
bin/check-log.sh $LOG

# Clean cache of issues
DAYS=5
LOG=$LOG_PATH/clean-issue-cache-$(date "+%Y-%m-%d-%T").log
kmanga/manage.py clean issue-cache --force -d $DAYS &> $LOG
bin/check-log.sh $LOG

# Clean cache of MOBI
DAYS=5
LOG=$LOG_PATH/clean-mobi-cache-$(date "+%Y-%m-%d-%T").log
kmanga/manage.py clean mobi-cache --force -d $DAYS &> $LOG
bin/check-log.sh $LOG
