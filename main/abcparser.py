#!/usr/bin/env python3

import codecs
import re

import arpeggio

from .abcparser_peg import canonify_music_code


class Tune(object):
    """A Tune instance holds one ABC tune, including both the raw tune, or 'instance', as found
    in the input, and the canonicized tune, or 'song', by which deduplication is done. All
    string data in a Tune instance must already have been converted to Unicode."""

    def __init__(self):
        self.full_tune = []   # The full text of the tune instance. Aside from some whitespace
                              # normalization, this is the tune as found in the input. This is
                              # a list of strings, one per line, without end-of-line characters.
        self.X = None         # The tune number, i.e. the numeric value of the X field.
        self.line_number = 0  # The line number in the input file at which this tune started.
        self.T = []           # A list of titles, in order of appearance, including mis-used P
                              # fields.
        self.digest = []      # The canonicized song, containing only those header fields which
                              # effect the music itself (K, L, M, m, P, U, and V), plus the body
                              # of the tune (music code) with the following stripped: comments,
                              # stylesheet directives, and (non-inline) fields other than K, L,
                              # M, m, P, s, U, V, W, and w. This is a list of dicts of the form:
                              #    { 'sort': sortkey, 'line': line}


    def __str__(self):
        r = 'X: ' + str(self.X) + '\n'
        r += ''.join(['T: %s\n' % x for x in self.T])
        r += ''.join(['F| %s\n' % x for x in self.full_tune])
        self.digest.sort(key=lambda l: l['sort'])
        for l in self.digest:
            r += 'D| %s %s\n' % (l['sort'], l['line'])
        return r


    def full_tune_append(self, line):
        assert(isinstance(line, str))
        self.full_tune.append(line)


    def digest_append(self, field, line):
        # The ``sort`` field is constructed so that self.digest will sort() into the canonical
        # field ordering.
        assert(isinstance(line, str))
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
        """This is called when a complete tune has been accumulated by the parser. It is assumed
        that the caller will override this function with one that can e.g. save the tune to a
        database.
        """
        print(self)


ABC_CHARACTER_MNEMONICS = {
    # from the ABC v2.1 standard
    '\\"A': 'Ä', "\\'A": 'Á', '\\AA': 'Å', '\\^A': 'Â', '\\`A': 'À',
    '\\uA': 'Ă', '\\~A': 'Ã', '\\cC': 'Ç', '\\"E': 'Ë', "\\'E": 'É',
    '\\AE': 'Æ', '\\OE': 'Œ', '\\^E': 'Ê', '\\`E': 'È', '\\uE': 'Ĕ',
    '\\DH': 'Ð', '\\TH': 'Þ', '\\"I': 'Ï', "\\'I": 'Í', '\\^I': 'Î',
    '\\`I': 'Ì', '\\~N': 'Ñ', '\\"O': 'Ö', "\\'O": 'Ó', '\\/O': 'Ø',
    '\\HO': 'Ő', '\\^O': 'Ô', '\\`O': 'Ò', '\\~O': 'Õ', '\\vS': 'Š',
    '\\"U': 'Ü', "\\'U": 'Ú', '\\HU': 'Ű', '\\^U': 'Û', '\\`U': 'Ù',
    '\\"Y': 'Ÿ', "\\'Y": 'Ý', '\\^Y': 'Ŷ', '\\vZ': 'Ž', '\\"a': 'ä',
    "\\'a": 'á', '\\^a': 'â', '\\`a': 'à', '\\aa': 'å', '\\ua': 'ă',
    '\\~a': 'ã', '\\cc': 'ç', '\\"e': 'ë', "\\'e": 'é', '\\^e': 'ê',
    '\\`e': 'è', '\\ae': 'æ', '\\oe': 'œ', '\\ue': 'ĕ', '\\dh': 'ð',
    '\\th': 'þ', '\\"i': 'ï', "\\'i": 'í', '\\^i': 'î', '\\`i': 'ì',
    '\\~n': 'ñ', '\\"o': 'ö', "\\'o": 'ó', '\\/o': 'ø', '\\Ho': 'ő',
    '\\^o': 'ô', '\\`o': 'ò', '\\~o': 'õ', '\\ss': 'ß', '\\vs': 'š',
    '\\"u': 'ü', "\\'u": 'ú', '\\Hu': 'ű', '\\^u': 'û', '\\`u': 'ù',
    '\\"y': 'ÿ', "\\'y": 'ý', '\\^y': 'ŷ', '\\vz': 'ž',
    # from abcm2ps front.c
    '\\;A': 'Ą', '\\=A': 'Ā', '\\oA': 'Å', "\\'C": 'Ć', '\\,C': 'Ç',
    '\\.C': 'Ċ', '\\^C': 'Ĉ', '\\vC': 'Č', '\\/D': 'Đ', '\\=D': 'Đ',
    '\\vD': 'Ď', '\\.E': 'Ė', '\\;E': 'Ę', '\\=E': 'Ē', '\\vE': 'Ě',
    '\\,G': 'Ģ', '\\.G': 'Ġ', '\\^G': 'Ĝ', '\\uG': 'Ğ', '\\=H': 'Ħ',
    '\\^H': 'Ĥ', '\\.I': 'İ', '\\;I': 'Į', '\\=I': 'Ī', '\\uI': 'Ĭ',
    '\\~I': 'Ĩ', '\\^J': 'Ĵ', '\\,K': 'Ķ', "\\'L": 'Ĺ', '\\,L': 'Ļ',
    '\\/L': 'Ł', '\\vL': 'Ľ', "\\'N": 'Ń', '\\,N': 'Ņ', '\\vN': 'Ň',
    '\\:O': 'Ő', '\\=O': 'Ō', '\\uO': 'Ŏ', "\\'R": 'Ŕ', '\\,R': 'Ŗ',
    '\\vR': 'Ř', "\\'S": 'Ś', '\\,S': 'Ş', '\\^S': 'Ŝ', '\\,T': 'Ţ',
    '\\=T': 'Ŧ', '\\vT': 'Ť', '\\:U': 'Ű', '\\;U': 'Ų', '\\=U': 'Ū',
    '\\oU': 'Ů', '\\uU': 'Ŭ', '\\~U': 'Ũ', "\\'Z": 'Ź', '\\.Z': 'Ż',
    '\\;a': 'ą', '\\=a': 'ā', '\\oa': 'å', "\\'c": 'ć', '\\,c': 'ç',
    '\\.c': 'ċ', '\\^c': 'ĉ', '\\vc': 'č', '\\/d': 'đ', '\\=d': 'đ',
    '\\vd': 'ď', '\\.e': 'ė', '\\;e': 'ę', '\\=e': 'ē', '\\ve': 'ě',
    '\\,g': 'ģ', '\\.g': 'ġ', '\\^g': 'ĝ', '\\ng': 'ŋ', '\\ug': 'ğ',
    '\\=h': 'ħ', '\\^h': 'ĥ', '\\.i': 'ı', '\\;i': 'į', '\\=i': 'ī',
    '\\ui': 'ĭ', '\\~i': 'ĩ', '\\^j': 'ĵ', '\\,k': 'ķ', "\\'l": 'ĺ',
    '\\,l': 'ļ', '\\/l': 'ł', '\\vl': 'ľ', "\\'n": 'ń', '\\,n': 'ņ',
    '\\vn': 'ň', '\\:o': 'ő', '\\=o': 'ō', '\\uo': 'ŏ', "\\'r": 'ŕ',
    '\\,r': 'ŗ', '\\vr': 'ř', "\\'s": 'ś', '\\,s': 'ş', '\\^s': 'ŝ',
    '\\,t': 'ţ', '\\=t': 'ŧ', '\\vt': 'ť', '\\:u': 'ű', '\\;u': 'ų',
    '\\=u': 'ū', '\\ou': 'ů', '\\uu': 'ŭ', '\\~u': 'ũ', "\\'z": 'ź',
    '\\.z': 'ż',
    # from jcabc2ps ABCdiacrit.html
    '\\-A': 'Ā', '\\-D': 'Đ', '\\-E': 'Ē', '\\-H': 'Ħ', '\\-I': 'Ī',
    '\\IJ': 'Ĳ', '\\.L': 'Ŀ', '\\-O': 'Ō', '\\-T': 'Ŧ', '\\-U': 'Ū',
    '\\^W': 'Ŵ', '\\^Z': 'Ẑ', '\\-a': 'ā', '\\-d': 'đ', '\\-e': 'ē',
    '\\Ae': 'æ', '\\Oe': 'œ', '\\-h': 'ħ', '\\-i': 'ī', '\\Ij': 'ĳ',
    '\\ij': 'ĳ', '\\.l': 'ŀ', '\\-u': 'ū', '\\^w': 'ŵ', '\\^z': 'ẑ',
}

ABC_NAMED_ENTITIES = {
    # from the ABC v2.1 standard
    '&AElig;':   'Æ', '&Aacute;':  'Á', '&Abreve;':  'Ă', '&Acirc;':   'Â',
    '&Agrave;':  'À', '&Aring;':   'Å', '&Atilde;':  'Ã', '&Auml;':    'Ä',
    '&Ccedil;':  'Ç', '&ETH;':     'Ð', '&Eacute;':  'É', '&Ecirc;':   'Ê',
    '&Egrave;':  'È', '&Euml;':    'Ë', '&Iacute;':  'Í', '&Icirc;':   'Î',
    '&Igrave;':  'Ì', '&Iuml;':    'Ï', '&Ntilde;':  'Ñ', '&OElig;':   'Œ',
    '&Oacute;':  'Ó', '&Ocirc;':   'Ô', '&Ograve;':  'Ò', '&Oslash;':  'Ø',
    '&Otilde;':  'Õ', '&Ouml;':    'Ö', '&Scaron;':  'Š', '&THORN;':   'Þ',
    '&Uacute;':  'Ú', '&Ucirc;':   'Û', '&Ugrave;':  'Ù', '&Uuml;':    'Ü',
    '&Yacute;':  'Ý', '&Ycirc;':   'Ŷ', '&Yuml;':    'Ÿ', '&Zcaron;':  'Ž',
    '&aacute;':  'á', '&abreve;':  'ă', '&acirc;':   'â', '&aelig;':   'æ',
    '&agrave;':  'à', '&aring;':   'å', '&atilde;':  'ã', '&auml;':    'ä',
    '&ccedil;':  'ç', '&eacute;':  'é', '&ecirc;':   'ê', '&egrave;':  'è',
    '&eth;':     'ð', '&euml;':    'ë', '&iacute;':  'í', '&icirc;':   'î',
    '&igrave;':  'ì', '&iuml;':    'ï', '&ntilde;':  'ñ', '&oacute;':  'ó',
    '&ocirc;':   'ô', '&oelig;':   'œ', '&ograve;':  'ò', '&oslash;':  'ø',
    '&otilde;':  'õ', '&ouml;':    'ö', '&scaron;':  'š', '&szlig;':   'ß',
    '&thorn;':   'þ', '&uacute;':  'ú', '&ucirc;':   'û', '&ugrave;':  'ù',
    '&uuml;':    'ü', '&yacute;':  'ý', '&ycirc;':   'ŷ', '&yuml;':    'ÿ',
    '&zcaron;':  'ž',
    # from the HTML 4.0 standard
    '&Alpha;':   'Α', '&Beta;':    'Β', '&Chi;':     'Χ', '&Dagger;':  '‡',
    '&Delta;':   'Δ', '&Epsilon;': 'Ε', '&Eta;':     'Η', '&Gamma;':   'Γ',
    '&Iota;':    'Ι', '&Kappa;':   'Κ', '&Lambda;':  'Λ', '&Mu;':      'Μ',
    '&Nu;':      'Ν', '&Omega;':   'Ω', '&Omicron;': 'Ο', '&Phi;':     'Φ',
    '&Pi;':      'Π', '&Prime;':   '″', '&Psi;':     'Ψ', '&Rho;':     'Ρ',
    '&Sigma;':   'Σ', '&Tau;':     'Τ', '&Theta;':   'Θ', '&Upsilon;': 'Υ',
    '&Xi;':      'Ξ', '&Zeta;':    'Ζ', '&acute;':   '´', '&alefsym;': 'ℵ',
    '&alpha;':   'α', '&amp;':     '&', '&and;':     '⊥', '&ang;':     '∠',
    '&asymp;':   '≈', '&bdquo;':   '„', '&beta;':    'β', '&brvbar;':  '¦',
    '&bull;':    '•', '&cap;':     '∩', '&cedil;':   '¸', '&cent;':    '¢',
    '&chi;':     'χ', '&circ;':    'ˆ', '&clubs;':   '♣', '&cong;':    '≅',
    '&copy;':    '©', '&crarr;':   '↵', '&cup;':     '∪', '&curren;':  '¤',
    '&dArr;':    '⇓', '&dagger;':  '†', '&darr;':    '↓', '&deg;':     '°',
    '&delta;':   'δ', '&diams;':   '♦', '&divide;':  '÷', '&empty;':   '∅',
    '&emsp;':    ' ', '&ensp;':    ' ', '&epsilon;': 'ε', '&equiv;':   '≡',
    '&eta;':     'η', '&exist;':   '∃', '&fnof;':    'ƒ', '&forall;':  '∀',
    '&frac12;':  '½', '&frac14;':  '¼', '&frac34;':  '¾', '&frasl;':   '⁄',
    '&gamma;':   'γ', '&ge;':      '≥', '&gt;':      '>', '&hArr;':    '⇔',
    '&harr;':    '↔', '&hearts;':  '♥', '&hellip;':  '…', '&iexcl;':   '¡',
    '&image;':   'ℑ', '&infin;':   '∞', '&int;':     '∫', '&iota;':    'ι',
    '&iquest;':  '¿', '&isin;':    '∈', '&kappa;':   'κ', '&lArr;':    '⇐',
    '&lambda;':  'λ', '&lang;':    '〈', '&laquo;':   '«', '&larr;':    '←',
    '&lceil;':   '⌈', '&ldquo;':   '“', '&le;':      '≤', '&lfloor;':  '⌊',
    '&lowast;':  '∗', '&loz;':     '◊', '&lsaquo;':  '‹', '&lsquo;':   '‘',
    '&lt;':      '<', '&macr;':    '¯', '&mdash;':   '—', '&micro;':   'µ',
    '&middot;':  '·', '&minus;':   '−', '&mu;':      'μ', '&nabla;':   '∇',
    '&nbsp;':    ' ', '&ndash;':   '–', '&ne;':      '≠', '&ni;':      '∋',
    '&not;':     '¬', '&notin;':   '∉', '&nsub;':    '⊄', '&nu;':      'ν',
    '&oline;':   '‾', '&omega;':   'ω', '&omicron;': 'ο', '&oplus;':   '⊕',
    '&or;':      '⊦', '&ordf;':    'ª', '&ordm;':    'º', '&otimes;':  '⊗',
    '&para;':    '¶', '&part;':    '∂', '&permil;':  '‰', '&perp;':    '⊥',
    '&phi;':     'φ', '&pi;':      'π', '&piv;':     'ϖ', '&plusmn;':  '±',
    '&pound;':   '£', '&prime;':   '′', '&prod;':    '∏', '&prop;':    '∝',
    '&psi;':     'ψ', '&quot;':    '"', '&rArr;':    '⇒', '&radic;':   '√',
    '&rang;':    '〉', '&raquo;':   '»', '&rarr;':    '→', '&rceil;':   '⌉',
    '&rdquo;':   '”', '&real;':    'ℜ', '&reg;':     '®', '&rfloor;':  '⌋',
    '&rho;':     'ρ', '&rsaquo;':  '›', '&rsquo;':   '’', '&sbquo;':   '‚',
    '&sdot;':    '⋅', '&sect;':    '§', '&sigma;':   'σ', '&sigmaf;':  'ς',
    '&sim;':     '∼', '&spades;':  '♠', '&sub;':     '⊂', '&sube;':    '⊆',
    '&sum;':     '∑', '&sup1;':    '¹', '&sup2;':    '²', '&sup3;':    '³',
    '&sup;':     '⊃', '&supe;':    '⊇', '&tau;':     'τ', '&there4;':  '∴',
    '&theta;':   'θ', '&thetasym;': 'ϑ', '&thinsp;':  ' ', '&tilde;':   '˜',
    '&times;':   '×', '&trade;':   '™', '&uArr;':    '⇑', '&uarr;':    '↑',
    '&uml;':     '¨', '&upsih;':   'ϒ', '&upsilon;': 'υ', '&weierp;':  '℘',
    '&xi;':      'ξ', '&yen;':     '¥', '&zeta;':    'ζ',
}

RE_ABC_CHARACTER_ENCODINGS = re.compile(r"""
    ( \\\\               |  # \\ escaped backslash
      \\u[0-9A-Fa-f]{4}  |  # \uXXXX hex escape
      \\U[0-9A-Fa-f]{8}  |  # \UXXXXXXXX hex escape
      \\..               |  # \xx TeX-style mnemonic
      &[^;]+;               # HTML named entity
    )
    """, re.VERBOSE | re.UNICODE)


def split_off_comment(line):
    """Split a line (of bytes) on the comment character '%', but allow for escaping with '\\%'."""
    def escape(s):
        """
        Replace any backslash-escaped sequence '\\x' with '\\ddd', where 'ddd' is the decimal
        value of 'x'.
        """
        return re.sub(rb'\\(.)', lambda m: b'\\%03d' % ord(m.group(1)[0:1]), s)
    def unescape(s):
        """
        Replace any backslash-escaped sequence '\\ddd' with '\\x', where 'x' is the ASCCI
        character whose value is decimal 'ddd'.
        """
        return re.sub(rb'\\(\d{3})',
                      lambda m: b'\\' + chr(int(m.group(1))).encode('raw_unicode_escape'), s)
    m = re.match(rb'^([^%]*?)\s*(%.*)$', escape(line))
    if m:
        return unescape(m.group(1)), unescape(m.group(2))
    else:
        return line, None


class Parser(object):
    """The Parser class encapsulates an ABC parser. After instantiating the parser, invoke
    ``.parse()`` with a file-like argument:

    >>> p = Parser()
    >>> p.parse(open('file.abc', 'rb'), collection='file.abc')

    For each individual tune parsed, ``.parse()`` will create a ``Tune`` instance and invoke
    ``Tune.process()`` on it. Information about the parsing process is logged using
    ``Parser.log()``, a default implementation of which is provided here to simply print logging
    information. It is expected that most applications will override ``.log()`` with an
    implementation of their own.
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
        # The encoding of text stings can be specified with the 'I:abc-charset' field or the
        # '%%abc-charset' stylesheet directive (abcm2ps also uses '%%encoding <n>', where <n>
        # specifies the ISO-8859-<n> encoding). The ABC specification says that text string
        # encoding defaults to UTF-8, but in the wild, different encodings are often used without
        # being explicity specified in the ABC file. Here the 'default' encoding assumes that any
        # valid UTF-8 should be UTF-8, and that any invalid UTF-8 is ISO-8859-1 'Latin-1'.
        self.encoding = 'default'

        self.line_number = 0


    def log(self, severity, message, text):
        """A simple print()-based logger for the parser.

        Parameters
        ----------
        severity : str
            One of 'warn', 'info', 'ignore'.
        message : str
            An explanation of the log event.
        text : str or bytes
            Usually, the input which caused the log event.
        """
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='backslashreplace')
        print(severity + ' | ' + str(self.line_number) + ' | ' + message + ' | ' + text)


    def handle_encoding(self, line):
        """
        Parse a line of the form '??abc-charset <encoding>' or '??encoding <number>', where
        '??' may be '%%' or 'I:', and set self.encoding to a valid Python codecs encoding.
        """
        if line[2:13] == b'abc-charset':
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
        elif line[2:10] == b'encoding':  # non-standard, abcm2ps uses it to select
                                         # ISO-8859 encodings
            match = re.search(b'encoding\s+(\d{1,2})', line)
            if match:
                if int(match.group(1)) <= 16:
                    self.encoding = 'iso-8859-' + match.group(1).decode('ascii')
                    self.log('info', "Character encoding set to '%s'" % self.encoding, line)
                    return
        self.log('warn', 'Unrecognized character encoding', line)


    def decode_abc_text_string(self, text):
        """Decode ABC character replacements (TeX-style mnemonics, named HTML entities, or
        \\uxxxx or \\Uxxxxxxxx escapes)."""
        def decode(match):
            m = match.group(0)
            if m.startswith('&'):  # HTML named entity
                return ABC_NAMED_ENTITIES.get(m) or m
            elif len(m) in (6, 10):  # \uxxxx or \Uxxxxxxxx escape
                return codecs.decode(match.group(0), "unicode_escape")
            elif len(m) == 3:  # \xx TeX-style mnemonic
                return ABC_CHARACTER_MNEMONICS.get(m) or m
            else:  # \\ escaped backslash
                return '\\'
        return RE_ABC_CHARACTER_ENCODINGS.sub(decode, text)


    def decode_from_raw(self, raw):
        if self.encoding == 'default':
            # assume that invalid UTF-8 is Latin-1
            try:
                return raw.decode('utf-8', errors='strict')
            except:
                try:
                    return raw.decode('iso-8859-1', errors='strict')
                except:
                    return raw.decode('utf-8', errors='backslashreplace')
        else:
            return raw.decode(self.encoding, errors='backslashreplace')


    def handle_field_K_key_signature(self, tune, line, comment):
        if self.state == 'tuneheader':
            tune.digest_append('K', line)
        else:  # tunebody
            tune.digest_append('body', line)
        tune.full_tune_append(line + comment)


    def handle_field_T_title(self, tune, field_data, comment):
        title = self.decode_abc_text_string(field_data)
        tune.T.append(title)
        tune.full_tune_append('T:' + title + comment)


    def handle_field_X_tune_number(self, tune, field_data, line, comment):
        tune.full_tune_append(line + comment)
        if self.state in ('tuneheader', 'tunebody'):
            self.log('warn', "Subsequent 'X:' field inside tune", line)
        else:
            # set tune.X to the integer at the start of field_data, or zero on failure
            tune.X = int((re.findall(r'^(\d+)', field_data) or ['0'])[0])
            tune.line_number = self.line_number
            self.log('info', "New tune {:d}".format(tune.X), line)


    def handle_field_other(self, tune, field_type, line, comment):
        if field_type in 'ABCDEFGHNORrSTWwZ':  # 'abc text string' fields
            line = self.decode_abc_text_string(line)
        # if the "field_type in 'KLM...'" check fails, this is a field we don't want in the digest
        if self.state == 'tuneheader' and field_type in 'KLMmPUV':
            tune.digest_append(field_type, line)
        elif self.state == 'tunebody' and field_type in 'KLMmPsUVWw':
            tune.digest_append('body', line)
        tune.full_tune_append(line + comment)


    def handle_music_code(self, tune, line, comment):
        tune.full_tune_append(line + comment)
        try:
            line = canonify_music_code(line, text_string_decoder=self.decode_abc_text_string)
        except arpeggio.NoMatch as err:
            self.log('warn', 'Music code failed to parse', str(err))
        tune.digest_append('body', line)


    def parse(self, filehandle, collection):
        last_field_type = None  # for '+:' field continuations
        tune = Tune()
        while True:
            line = filehandle.readline()
            if line == b'':  # end-of-file
                if self.state in ('tuneheader', 'tunebody'):
                    self.log('warn', 'Unexpected end of file inside tune', '')
                    tune.full_tune_append('')
                    tune.digest_append('body', '')
                    tune.process()
                break
            self.line_number += 1

            if self.state == 'firstline':
                if line.startswith(codecs.BOM_UTF8):  # trim UTF-8 BOM
                    line = line[3:]
                self.state = 'fileheader'

            line = line.rstrip()  # trim tailing space and newline

            if re.match(b'^%%', line):  # stylesheet directive
                if line.startswith(b'%%abc-charset') or line.startswith(b'%%encoding'):
                    self.handle_encoding(line)
                else:
                    self.log('ignore', 'Stylesheet directive ignored', line)
                continue

            if re.match(rb'^\s*%', line):  # comment line
                if self.state in ('tuneheader', 'tunebody'):
                    line = self.decode_abc_text_string(self.decode_from_raw(line))
                    tune.full_tune_append(line)
                else:
                    self.log('ignore', 'Comment', line)
                # state and last_field_type are unchanged, since this line doesn't count as a
                # blank line
                continue

            if line == b'':  # blank line
                if self.state in ('tuneheader', 'tunebody'):
                    tune.full_tune_append('')
                    tune.digest_append('body', '')
                    tune.process()
                    del tune
                    tune = Tune()
                else:
                    self.log('ignore', 'Blank line', '')
                self.state = 'freetext'
                last_field_type = None
                continue

            # ==== above here, ``line`` is bytes ====

            # remove comment, if any
            line, comment = split_off_comment(line)
            line = self.decode_from_raw(line)
            if comment:
                comment = ' ' + self.decode_from_raw(comment)
            else:
                comment = ''

            # ==== below here, everything is str ====

            # handle information fields
            m = re.match(r'([A-Za-z+]):\s*(.*)', line)
            if m:   # information field
                field_type, field_data = m.group(1), m.group(2)
                line = field_type + ':' + field_data  # normalize (delete) whitespace

                if field_type == '+' and last_field_type is not None: # continuation field
                    field_type = last_field_type

                if (field_type != 'X') and (self.state not in ('tuneheader', 'tunebody')):
                    if line.startswith('I:abc-charset'):
                        self.handle_encoding(line.encode('utf-8'))
                    else:
                        self.log('warn', "Field outside of tune", line)
                    continue

                if field_type == 'X':  # start of tune
                    self.handle_field_X_tune_number(tune, field_data, line, comment)
                    if self.state not in ('tuneheader', 'tunebody'):
                        self.state = 'tuneheader'

                elif field_type == 'K':  # key signature, change state to tune body
                    self.handle_field_K_key_signature(tune, line, comment)
                    self.state = 'tunebody'

                elif field_type == 'T':  # title field
                    self.handle_field_T_title(tune, field_data, comment)

                else:
                    self.handle_field_other(tune, field_type, line, comment)

                last_field_type = field_type
                continue

            if last_field_type == 'H':  # history continuation without '+:' (deprecated)
                if self.state in ('tuneheader', 'tunebody'):
                    tune.full_tune_append('+:' + line + comment)
                else:
                    assert(False)  # this should be unreachable
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
