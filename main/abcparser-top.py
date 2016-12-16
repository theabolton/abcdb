#!/usr/bin/env python3

import codecs
import re


class Tune(object):
    """A Tune instance holds one ABC tune, including both the raw tune, or 'instance', almost as
    found in the input, and the canonicized tune, or 'song', by which deduplication is done."""

    def __init__(self):
        self.full_tune = []   # The full text of the tune instance. Aside from some whitespace
                              # normalization and fixing of a few standard-breaking constructs,
                              # this is the tune as found in the input. This is a list of byte
                              # strings, one per line, without end-of-line characters.
        self.X = None         # The tune number, i.e. the numeric value of the X field.
        self.line_number = 0  # The line number in the input file at which this tune started.
        self.T = []           # A list of titles, in order of appearance, including mis-used P
                              # fields. Unicode strings.
        self.digest = []      # The canonicized song, containing only those header fields which
                              # effect the music itself (K, L, M, m, P, U, and V), plus the body
                              # of the tune (music code) with the following stripped: comments,
                              # stylesheet directives, and (non-inline) fields other than K, L,
                              # M, m, P, s, U, V, W, and w. This is a list of dicts of the form:
                              #    { 'sort': sortkey, 'line': line}


    def __str__(self): # !FIX! decoding is borken
        r = 'X: ' + str(self.X) + '\n'
        r += ''.join(['T: %s\n' % x.decode('utf-8', errors='ignore') for x in self.T]) # !FIX! don't decode like that!
        r += ''.join(['F| %s\n' % x.decode('utf-8', errors='ignore') for x in self.full_tune])
        self.digest.sort(key=lambda l: l['sort'])
        for l in self.digest:
            r += 'D| %s %s\n' % (l['sort'], l['line'].decode('utf-8', errors='ignore'))
        return r


    def digest_append(self, field, line):
        # The ``sort`` field is constructed so that self.digest will sort() into the canonical
        # field ordering.
        n = '%06d' % len(self.digest)
        if field in 'XT':
            key = '1' + field + n
        elif field in 'LMmPUV':
            key = '2' + field + n
        elif field == 'K':
            key = '3' + field + n
        elif field != 'body':
            key = '4' + field + n
        else:
            key = '5_' + n
        self.digest.append({ 'sort': key, 'line': line})


    def process(self):
        print(self)  # !FIX!


def split_off_comment(line):
    """Split a line (of bytes) on the comment character '%', but allow for escaping with '\\%'."""
    def encode(s):
        """
        Replace any backslash-escaped sequence '\\x' with '\\ddd', where 'ddd' is the decimal
        value of 'x'.
        """
        return re.sub(rb'\\(.)', lambda m: b'\\%03d' % ord(m.group(1)[0:1]), s)
    def decode(s):
        """
        Replace any backslash-escaped sequence '\\ddd' with '\\x', where 'x' is the ASCCI
        character whose value is decimal 'ddd'.
        """
        return re.sub(rb'\\(\d{3})',
                      lambda m: b'\\' + chr(int(m.group(1))).encode('raw_unicode_escape'), s)
    m = re.match(rb'^([^%]*?)\s*(%.*)$', encode(line))
    if m:
        return decode(m.group(1)), decode(m.group(2))
    else:
        return line, None


class Parser(object):
    """The Parser class encapsulates an ABC parser. It is expected that the caller will override
    the .process() and .log() functions to handle output of tunes and logging information.
    """

    def __init__(self):
        self.reset()


    def reset(self):
        # parser states, and what they expect:
        #  'firstline'
        #       possible UTF-8 "byte order mark" (BOM), otherwise same as 'fileheader'
        #  'fileheader'
        #      information field: 'A:'
        #      stylesheet directive: '%%' or 'I:'
        #      comment line: '%' (note that lines containing only a comment do not count as empty
        #          lines)
        #  'tuneheader'
        #      information field: 'A:'
        #      continuation line: '+:'
        #      the stupid history continuation syntax
        #      comment line
        #  'tunebody'
        #      music
        #      all 'tuneheader' possibilities
        #      a blank line to end the tune
        #  'freetext'
        #      anything not listed above
        self.state = 'firstline'

        # ABC is encoded in ASCII, except for four places where "text strings" may occur:
        #    - free text (which we ignore in this application)
        #    - typeset text (also ignored)
        #    - information fields
        #    - annotations
        # The encoding of the last two can be set with the 'I:abc-charset' field (and presumably
        # also using a '%%abc-charset' stylesheet directive). The ABC specification says this
        # encoding defaults to UTF-8, but in the wild, different encodings are often used without
        # being explicity specified in the ABC file. Here the 'default' encoding assumes that any
        # valid UTF-8 should be UTF-8, and that any invalid UTF-8 is ISO-8859-1 'Latin-1'.
        self.encoding = 'default'

        self.line_number = 0


    def log(self, severity, message, text):
        print(severity + ' | ' + str(self.line_number) + ' | ' + message + ' | ' +
                  text.decode('utf-8', errors='backslashreplace'))


    def handle_encoding(self, line):
        """
        Parse a line of the form '%%abc-charset <encoding>' or '%%encoding <number>'
        and set self.encoding to a valid Python codecs encoding.
        """
        if line.startswith(b'%%abc-charset'):
            match = re.search(b'charset\s+([-A-Za-z0-9_]+)', line)
            if match:
                new_encoding = match.group(1).decode('ascii')
                try:
                    codecs.lookup(new_encoding)  # use any encoding that python recognizes
                except LookupError:
                    new_encoding = None
                if new_encoding:
                    self.encoding = new_encoding
                    self.log('info', "Character encoding set to '%s'" % self.encoding, line)
                    return
        elif line.startswith(b'%%encoding'):  # non-standard, abcm2ps uses it to select
                                              # ISO-8859 encodings
            match = re.search(b'encoding\s+(\d{1,2})', line)
            if match:
                if int(match.group(1)) <= 16:
                    self.encoding = 'iso-8859-' + match.group(1).decode('ascii')
                    self.log('info', "Character encoding set to '%s'" % self.encoding, line)
                    return
        self.log('warn', 'Unrecognized character encoding', line)
        return


    def handle_field_K_key_signature(self, tune, line, comment):
        if self.state == 'tuneheader':
            tune.digest_append('K', line)
        else:  # tunebody
            tune.digest_append('body', line)
        tune.full_tune.append(line + comment)


    def handle_field_TP_title(self, tune, field_type, field_data, line, comment):
        if field_type == b'T' or not re.fullmatch(rb'[A-F\d().]+', field_data):
            # title field or mis-used parts field; add to titles list
            tune.T.append(field_data)  # !FIX! convert encoding
        else:  # parts field used as it should be
            if self.state == 'tuneheader':
                tune.digest_append('P', line)
            else:  # tunebody
                tune.digest_append('body', line)
        tune.full_tune.append(line + comment)


    def handle_field_X_tune_number(self, tune, field_data, line, comment):
        if self.state in ('tuneheader', 'tunebody'):
            self.log('warn', "Subsequent 'X:' field inside tune", line)
            tune.full_tune.append(b'%' + line + comment)
        else:
            tune.full_tune.append(line + comment)
            # set tune.X to the integer at the start of field_data, or zero on failure
            tune.X = int((re.findall(rb'^(\d+)', field_data) or [b'0'])[0])
            tune.line_number = self.line_number
            self.log('info', "New tune {:d}".format(tune.X), line)


    def handle_field_other(self, tune, field_type, line, comment):
        # if the "field_type in b'KLM...'" check fails, this is a field we don't want in the digest
        if self.state == 'tuneheader' and field_type in b'KLMmPUV':
            tune.digest_append(field_type.decode(), line)
        elif self.state == 'tunebody' and field_type in b'KLMmPsUVWw':
            tune.digest_append('body', line)
        tune.full_tune.append(line + comment)


    def handle_music_code(self, tune, line, comment):
        tune.full_tune.append(line + comment)
        tune.digest_append('body', line)  # !FIX! PEG it!


    def parse(self, filehandle, collection):
        last_field_type = None  # for '+:' field continuations
        tune = Tune()
        while True:
            line = filehandle.readline()
            if line == b'':  # end-of-file
                if self.state in ('tuneheader', 'tunebody'):
                    tune.full_tune.append(line)
                    tune.digest_append('body', line)
                    tune.process()
                break
            self.line_number += 1

            if self.state == 'firstline':
                if line.startswith(codecs.BOM_UTF8):  # trim UTF-8 BOM
                    line = line[3:]
                self.state = 'fileheader'

            line = line.strip()  # trim tailing space and newline

            if re.match(b'^%%', line):  # stylesheet directive
                if line.startswith(b'%%abc-charset') or line.startswith(b'%%encoding'):
                    self.handle_encoding(line)
                else:
                    self.log('ignore', 'Stylesheet directive ignored', line)
                continue

            if re.match(rb'^\s*%', line):  # comment line
                if self.state in ('tuneheader', 'tunebody'):
                    tune.full_tune.append(line)
                else:
                    self.log('ignore', 'Comment', line)
                # state and last_field_type are unchanged, since this line doesn't count as a
                # blank line
                continue

            if line == b'':  # blank line
                # !FIX! must check if a previous music-code line ended with '\'
                if self.state in ('tuneheader', 'tunebody'):
                    tune.full_tune.append(line)
                    tune.digest_append('body', line)
                    tune.process()
                    del tune
                    tune = Tune()
                else:
                    self.log('ignore', 'Blank line', line)
                self.state = 'freetext'
                last_field_type = None
                continue

            # remove comment, if any
            line, comment = split_off_comment(line)
            if comment:
                comment = b' ' + comment
            else:
                comment = b''

            # handle information fields
            m = re.match(rb'([A-Za-z+]):\s*(.*)', line)
            if m:   # information field
                field_type, field_data = m.group(1), m.group(2)
                line = field_type + b':' + field_data  # normalize (delete) whitespace

                if field_type == b'+' and last_field_type is not None: # continuation field
                    field_type = last_field_type

                if (field_type != b'X') and (self.state not in ('tuneheader', 'tunebody')):
                    # !FIX! handle 'I:abc-charset' lines in fileheader and freetext states
                    self.log('warn', "Field outside of tune", line)
                    continue

                if field_type == b'X':  # start of tune
                    self.handle_field_X_tune_number(tune, field_data, line, comment)
                    if self.state not in ('tuneheader', 'tunebody'):
                        self.state = 'tuneheader'

                elif field_type == b'K':  # key signature, change state to tune body
                    self.handle_field_K_key_signature(tune, line, comment)
                    self.state = 'tunebody'

                elif field_type in (b'T', b'P'):  # title field, or a parts field (possibly
                                                  # mis-used as a subtitle)
                    self.handle_field_TP_title(tune, field_type, field_data, line, comment)

                else:
                    self.handle_field_other(tune, field_type, line, comment)

                last_field_type = field_type
                continue

            if last_field_type == b'H':  # history continuation without '+:' (deprecated)
                if self.state in ('tuneheader', 'tunebody'):
                    tune.full_tune.append(b'+:' + line + comment)
                else:
                    pass # should be impossible
                continue


            # plain line, either freetext or musiccode
            if self.state == 'tuneheader':
                self.log('warn', "Non-field found before 'K:' field", line)
                self.state = 'tunebody'
            if self.state == 'tunebody':
                self.handle_music_code(tune, line, comment)
            else:
                self.log('ignore', self.state.title(), line + comment)

            last_field_type = None


if __name__ == '__main__':
    import sys
    p = Parser()
    for fn in sys.argv[1:]:
        try:
            fh = open(fn, 'rb')
        except OSError as err:
            print("OS error: {0}".format(err))
        except:
            raise

        p.parse(fh, collection=fn)
        fh.close()
