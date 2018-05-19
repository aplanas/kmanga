import argparse
import base64
import csv
import tempfile
import urllib.request

# List of URLs that contains openvpn configurations
URLS = (
    # (URL, skip_lines)
    ('http://www.vpngate.net/api/iphone/', 2),
)

NAME_INDEX = 0
OVPN_INDEX = 14


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Unpack vpn-gate files')
    parser.add_argument('--host', required=True, help='route host for openvpn')
    args = parser.parse_args()

    cfg = '''
auth-user-pass auth.txt
route-nopull
route %s
''' % args.host

    for url, skip_lines in URLS:
        # Use a temporary file to bypass the CSV module limitation for
        # files with EOL based on Mac
        with tempfile.TemporaryFile(mode='r+') as tmpfile:
            tmpfile.write(urllib.request.urlopen(url).read().decode('utf-8'))
            # Position the cursor to the first data line
            tmpfile.seek(0)
            for _ in range(skip_lines):
                tmpfile.readline()

            reader = csv.reader(tmpfile)
            for i, row in enumerate(reader):
                try:
                    name = '%s-%03d.ovpn' % (row[NAME_INDEX], i)
                    ovpn = base64.b64decode(row[OVPN_INDEX])
                    ovpn = ovpn.decode('utf-8') + cfg
                    open(name, 'w').write(ovpn)
                except IndexError:
                    # In some cases the last line is not valid
                    pass
