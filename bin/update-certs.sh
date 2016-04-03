# !/bin/sh

# Load the configuration file if exist
if [ ! -f "bin/kmanga.conf" ]; then
    echo "Please, create a bin/kmanga.conf configuration file."
    exit 1
fi
. bin/kmanga.conf

LOG=$LOG_PATH/update-certs-$(date "+%Y-%m-%d-%T").log
python $ACME_PATH/acme_tiny.py \
       --account-key $CERTS_PATH/account.key \
       --csr $CERTS_PATH/domain.csr \
       --acme-dir $CHALLENGE_PATH > $CERTS_PATH/signed.crt.NEW || exit
mv $CERTS_PATH/signed.crt.NEW $CERTS_PATH/signed.crt
wget -O - https://letsencrypt.org/certs/lets-encrypt-x3-cross-signed.pem > $CERTS_PATH/intermediate.pem
cat $CERTS_PATH/signed.crt $CERTS_PATH/intermediate.pem > $CERTS_PATH/chained.pem

# Add in /etc/sudoers.d/httpd a line like:
#  <username> ALL = NOPASSWD: /usr/bin/systemctl restart httpd.service
#  Defaults   !requiretty
#  Defaults   visiblepw
sudo systemctl restart httpd.service
