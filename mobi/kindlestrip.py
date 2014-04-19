# This script is based on a work made by Paul Durrant and Kevin
# Hendricks.
#
# The original code was released Unlicense and can be found in:
#   http://www.mobileread.com/forums/showthread.php?t=96903

import struct

# Involved address in PalmDOC database header
TYPE = 0x3c
CREATOR = 0x40
NUMBER_OF_RECORDS = 0x4c
# Every record is of 8 bytes:
#  4  record Data Offset
#  1  record Attributes
#  3  UniqueID
RECORD_INFO_LIST = 0x4e

# Involved address in MOBI header
SRCS_INDEX = 0xe0
SRCS_COUNT = 0xe4


def patch(data, offset, new):
    d = []
    d.append(data[:offset])
    d.append(new)
    d.append(data[offset+len(new):])
    return ''.join(d)


def join(data, new):
    d = []
    d.append(data)
    d.append(new)
    return ''.join(d)


class SRCSStripper(object):
    def __init__(self, data):
        self.data = data

        if not self._is_mobi():
            raise ValueError('File is not a mobi document.')

        # Get SRCS record number and count
        srcs_index, srcs_count = self._srcs_info()
        if srcs_index == 0xffffffff or srcs_count == 0:
            # File doesn't contain the sources record.
            return

        # Find its SRCS region starting offset and total length
        srcs_offset = self._record_offset(srcs_index)
        next_index = srcs_index + srcs_count
        next_offset = self._record_offset(next_index)
        srcs_length = next_offset - srcs_offset

        if not self._is_srcs(srcs_offset):
            raise ValueError('SRCS record num does not point to SRCS.')

        # First write until the SRCS.
        # We are going to make the SRCS record lengths all be 0.
        # Offsets up to and including the first SRCS record must not
        # be changed.
        # XXX TODO -- We are including the first SRCS record but do
        # not exists anymore after the patch.
        new_data = data[:RECORD_INFO_LIST+(srcs_index+1)*8]

        # For every additional record in SRCS records set start to
        # last_offset (they are all zero length).
        for record in range(srcs_index+1, srcs_index+srcs_count):
            offset, rest = self._record_info(record)
            new_info = struct.pack('>L', srcs_offset) + struct.pack('>L', rest)
            new_data = join(new_data, new_info)

        # For every record after the SRCS records we must start it
        # earlier by an amount equal to the total length of all of the
        # SRCS records.
        for record in range(srcs_index+srcs_count, self._number_of_records()):
            offset, rest = self._record_info(record)
            offset -= srcs_length
            new_info = struct.pack('>L', offset) + struct.pack('>L', rest)
            new_data = join(new_data, new_info)

        # Pad it out to begin right at the first offset typically this
        # is 2 bytes of nulls.
        first_offset = self._record_offset(0)
        pad = '\0' * (first_offset - len(new_data))
        new_data = join(new_data, pad)

        # Add on every thing up to the original src_offset and then
        # everything after it.
        new_data = join(new_data, data[first_offset:srcs_offset])
        new_data = join(new_data, data[srcs_offset+srcs_length:])

        # Update the srcs_index and srcs_count in the new MOBI header.
        offset = self._record_offset(0)
        new_srcs_info = struct.pack('>L', 0xffffffff) + struct.pack('>L', 0)
        new_data = patch(new_data, offset+SRCS_INDEX, new_srcs_info)
        self.new_data = new_data

    def _is_mobi(self):
        """Check TYPE and CREATOR fields in the header."""
        _type, creator = struct.unpack_from('>4s4s', self.data, offset=TYPE)
        return _type == 'BOOK' and creator == 'MOBI'

    def _is_srcs(self, srcs_offset):
        """Check if this is a SRCS record."""
        signature, = struct.unpack_from('>4s', self.data, offset=srcs_offset)
        return signature == 'SRCS'

    def _number_of_records(self):
        """Return the number of records."""
        nrec, = struct.unpack_from('>H', self.data, offset=NUMBER_OF_RECORDS)
        return nrec

    def _record_info(self, record):
        """Return a record (offset, rest) tuple from the index entry."""
        index = RECORD_INFO_LIST + record * 8
        offset, rest = struct.unpack_from('>2L', self.data, offset=index)
        return offset, rest

    def _record_offset(self, record):
        """Return a record offset from the index entry."""
        offset, _ = self._record_info(record)
        return offset

    def _load_record(self, record):
        """Load a record from the MOBI file."""
        number_of_records = self._number_of_records()
        if record >= number_of_records:
            raise ValueError('Record not found')

        offset = self._record_offset(record)

        # Is the last record?
        if record + 1 == number_of_records:
            return self.data[offset:]

        next_offset = self._record_offset(record+1)
        return self.data[offset:next_offset]

    def _srcs_info(self):
        """Return SRCS record index and count."""
        # The first record is special and consist of three components:
        # PalmDOC header, [MOBI section], [EXTH section]
        mobiheader = self._load_record(0)
        srcs_index, srcs_count = struct.unpack_from('>2L', mobiheader,
                                                    SRCS_INDEX)
        return srcs_index, srcs_count

    def get_result(self):
        return self.new_data


if __name__ == '__main__':
    s = SRCSStripper(open('test/fixtures/test.mobi', 'rb').read())
    open('result.mobi', 'wb').write(s.get_result())
