# ABCdb main/tests_parsers.py – tests for the music code PEG parsers.
#
# Copyright © 2017 Sean Bolton.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from django.test import TestCase, tag


# ========== Test Cases ==========

TESTS = [
    # input, expected output, description
    ('abc',         'abc',         'minimal function'),
    ('dcde d2c2|',  'dcde d2c2|',  'something'),
    # 2.2.5 Comments and remarks
    ('a[r:foo]b',   'a[r:foo]b',   'remark: normal use'),
    ('[r:a\\"Ab]',  '[r:aÄb]',     'remark: interpreted as text string'),
    # 3.1.8 Q: - tempo
    ('[Q:"a\\AEb" 1/4=96]', '[Q:"aÆb" 1/4=96]', 'tempo: description interpreted as text string'),
    ('[Q:1/4=96 "a\\AEb"]', '[Q:1/4=96 "aÆb"]', 'tempo: description interpreted as text string'),
    # 3.1.11 N: - notes
    ('[N:a\\"Ab]',  '[N:aÄb]',     'note: interpreted as text string'), # according to the table in §3.
    # 3.1.15 R: - rhythm
    ('[R:a\\"Ab]',  '[R:aÄb]',     'rhythm: interpreted as text string'), # according to the table in §3.
    # 4.3 Note lengths
    ('a2b',         'a2b',         'note length bigger: normal use'),
    ('a222b',       'a222b',       'note length bigger: large numbers'),
    ('a1b',         'ab',          'note length bigger: a1 -> a'),
    ('a3/2b',       'a3/2b',       'note length full: normal use'),
    ('a333/222b',   'a333/222b',   'note length full: large numbers'),
    ('a1/1b',       'ab',          'note length full: a1/1 -> a'),
    ('a2/1b',       'a2b',         'note length full: a2/1 -> a2'),
    ('a1/2b',       'a/b',         'note length full: a1/2 -> a/'),
    ('a1/4b',       'a//b',        'note length full: a1/4 -> a//'),
    ('a1/3b',       'a/3b',        'note length full: normal fractional value'),
    ('a1/8b',       'a/8b',        'note length full: normal 1/8th'),
    ('a/b',         'a/b',         'note length slashes: normal 1/2'),
    ('a//b',        'a//b',        'note length slashes: normal 1/4'),
    ('a///b',       'a/8b',        'note length slashes: a/// -> a/8'),
    ('a//////b',    'a/64b',       'note length slashes: a////// -> a/64'),
    ('a/3b',        'a/3b',        'note length smaller: normal use'),
    ('a/2b',        'a/b',         'note length smaller: a/2 -> a/'),
    ('a/4b',        'a//b',        'note length smaller: a/4 -> a//'),
    ('a/8b',        'a/8b',        'note length smaller: a/8 unchanged'),
    # 4.8 Repeat/bar symbols
    ('[]',          '[|]',         'non-standard: invisible bar line'),
    # 4.18 Chord symbols
    ('a"Am\\nC"b',  'a"Am\\nC"b',  "non-standard: '\\n' for newline in chord symbols"),
    # 4.19 Annotations
    ('a"^text"b',   'a"^text"b',   "annotation with '^'"),
    ('a"<text"b',   'a"<text"b',   "annotation with '<'"),
    ('a">text"b',   'a">text"b',   "annotation with '>'"),
    ('a"_text"b',   'a"_text"b',   "annotation with '_'"),
    ('a"@text"b',   'a"@text"b',   "annotation with '@'"),
    ('a"text"b',    'a"@text"b',   'bad annotation with no placement symbol'),
    ('"@a\\AEb"',   '"@aÆb"',      'annotation interpreted as text string'),
    # 6.1.1 Typesetting linebreaks
    ('a\\',         'a\\',         'line continuation'),
    ('a\\ ',        'a\\',         'line continuation: trim trailing whitespace'),
    # 8.2 Text strings
    # - TeX-style mnemonics
    ('[r:\\`A]',    '[r:À]',       "text strings: TeX mnemonic 'À'"),
    ("[r:\\'A]",    '[r:Á]',       "text strings: TeX mnemonic 'Á'"),
    ('[r:\\^A]',    '[r:Â]',       "text strings: TeX mnemonic 'Â'"),
    ('[r:\\~A]',    '[r:Ã]',       "text strings: TeX mnemonic 'Ã'"),
    ('[r:\\"A]',    '[r:Ä]',       "text strings: TeX mnemonic 'Ä'"),
    ('[r:\\cC]',    '[r:Ç]',       "text strings: TeX mnemonic 'Ç'"),
    ('[r:\\cc]',    '[r:ç]',       "text strings: TeX mnemonic 'ç'"),
    ('[r:\\AA]',    '[r:Å]',       "text strings: TeX mnemonic 'Å'"),
    ('[r:\\/O]',    '[r:Ø]',       "text strings: TeX mnemonic 'Ø'"),
    ('[r:\\uE]',    '[r:Ĕ]',       "text strings: TeX mnemonic 'Ĕ'"),
    ('[r:\\vZ]',    '[r:Ž]',       "text strings: TeX mnemonic 'Ž'"),
    ('[r:\\HO]',    '[r:Ő]',       "text strings: TeX mnemonic 'Ő'"),
    ('[r:\\ss]',    '[r:ß]',       "text strings: TeX mnemonic 'ß'"),
    ('[r:\\;a]',    '[r:ą]',       "text strings: TeX mnemonic 'ą'"),
    ('[r:\\xx]',    '[r:\\xx]',    "text strings: undefined TeX mnemonic"),
    # - named HTML entities
    ('[r:&AElig;]', '[r:Æ]',       "text strings: HTML entity 'Æ'"),
    ('[r:&Omega;]', '[r:Ω]',       "text strings: HTML entity 'Ω'"),
    ('[r:&foo;]',   '[r:&foo;]',   "text strings: undefined HTML entity"),
    # - fixed width Unicode
    ('[r:\\u0041]', '[r:A]',       "text strings: short Unicode escape 'A'"),
    ('[r:\\u004a]', '[r:J]',       "text strings: short Unicode escape 'J'"),
    ('[r:\\u004A]', '[r:J]',       "text strings: short Unicode escape 'J'"),
    ('[r:\\u0000]', '[r:^u0000]',  "text strings: short Unicode escape, don't sub control characters"),
    ('[r:\\u0080]', '[r:^u0080]',  "text strings: short Unicode escape, don't sub control characters"),
    ('[r:\\u00a0]', '[r: ]',       "text strings: short Unicode escape, sub NBSP to regular space"),
    ('[r:\\udb01]', '[r:^udb01]',  "text strings: short Unicode escape, illegal value"),
    ('[r:\\U00000041]', '[r:A]',   "text strings: long Unicode escape 'A'"),
    ('[r:\\U0000004a]', '[r:J]',   "text strings: long Unicode escape 'J'"),
    ('[r:\\U0000004A]', '[r:J]',   "text strings: long Unicode escape 'J'"),
    ('[r:\\U00000000]', '[r:^U00000000]', "text strings: long Unicode escape, don't sub control characters"),
    ('[r:\\U00000080]', '[r:^U00000080]', "text strings: long Unicode escape, don't sub control characters"),
    ('[r:\\U000000a0]', '[r: ]',   "text strings: long Unicode escape, sub NBSP to regular space"),
    ('[r:\\U0000db01]', '[r:^U0000db01]', "text strings: long Unicode escape, illegal value"),
    # - double-backslash escape
    ('[r:\\\\u0041]', '[r:\\u0041]', "text strings: double-backslash escape"),
    # - backslash-ampersand escape
    ('[r:\\&AElig;]', '[r:&AElig;]', "text strings: backslash-ampersand escape"),
]

# ========== Arpeggio (Python) Parser Tests ==========

@tag('parser')
class ArpeggioTests(TestCase):
    """Tests for the Python/Arpeggio-based ABC Parser."""

    def canonify_music_code(self, s):
        """Sugar for the Python canonify_music_code() function."""
        from .abcparser import decode_abc_text_string
        from .abcparser_peg import canonify_music_code

        return canonify_music_code(s, text_string_decoder=decode_abc_text_string)

    def test_basic_function(self):
        """Test for minimal successful and unsuccessful parses."""
        from .abcparser import decode_abc_text_string
        from .abcparser_peg import canonify_music_code
        from arpeggio import NoMatch
        # test minimal successful parse
        self.assertEquals(self.canonify_music_code('abc'), 'abc')
        # test minimal unsuccessful parse
        try:
            s = canonify_music_code('aX9', text_string_decoder=decode_abc_text_string)
        except NoMatch as err:
            s = str(err)
        expected = 'Expected '
        self.assertTrue(s.startswith(expected),
                        msg="looking for '{}...', found '{}'".format(expected, s))
        expected = "at position (1, 3) => 'aX*9'."
        self.assertTrue(s.endswith(expected),
                        msg="looking for '...{}', found '{}'".format(expected, s))

    def check(self, tin, tout, message):
        """Helper function to check for correct canonification."""
        self.assertEquals(self.canonify_music_code(tin), tout,
                          msg='Testing Python parser: ' + message)

    def test_test_cases(self):
        """Verify that the Python parser correctly handles all test cases."""
        for (test_in, expected, message) in TESTS:
            self.check(test_in, expected, message)


# ========== Rust Parser Tests ==========

@tag('parser')
class RustTests(TestCase):
    """Tests for the Rust/pest-based ABC Parser."""

    def setUp(self):
        """Load the Rust parser shared library."""
        import ctypes
        from ctypes import (POINTER, c_char_p, c_int32)

        class CallResult(ctypes.Structure):
            _fields_ = [("status", c_int32), ("text", c_char_p)]

        self._peglib = ctypes.cdll.LoadLibrary("target/release/libabcparser_peg.so")

        self._canonify_music_code = self._peglib.canonify_music_code
        self._canonify_music_code.argtypes = (c_char_p, )
        self._canonify_music_code.restype = POINTER(CallResult)

        self._free_result = self._peglib.free_result
        self._free_result.argtypes = (POINTER(CallResult), )
        self._free_result.restype = None

    def canonify_music_code(self, s):
        """Python wrapper to the Rust canonify_music_code() function."""
        ptr = self._canonify_music_code(s.encode('utf-8'))
        try:
            return (ptr[0].status, ptr[0].text.decode('utf-8'))
        finally:
            self._free_result(ptr)

    def test_basic_function(self):
        """Test for minimal successful and unsuccessful parses, and Rust panic return."""
        # test minimal successful parse
        self.assertEquals(self.canonify_music_code('abc'), (0, 'abc'))
        # test minimal unsuccessful parse
        (status, message) = self.canonify_music_code('aX9')
        expected = "ABC parse failed at character 2, matched 'aX', could not match '9', expected ["
        self.assertEqual(status, 1)
        self.assertTrue(message.startswith(expected),
                        msg="looking for '{}', found '{}'".format(expected, message))
        # test that Rust panic landing pad functions, returning us an error message
        ptr = self._canonify_music_code('aña'.encode('latin-1'))  # feed it bad utf-8
        try:
            (status, message) = (ptr[0].status, ptr[0].text.decode('utf-8'))
        finally:
            self._free_result(ptr)
        self.assertEqual(status, 2)
        self.assertEquals(message, "called `Result::unwrap()` on an `Err` "
                                   "value: Utf8Error { valid_up_to: 1 }")

    def check(self, tin, tout, message):
        """Helper function to check for correct canonification."""
        self.assertEquals(self.canonify_music_code(tin), (0, tout),
                          msg='Testing Rust parser: ' + message)

    def test_test_cases(self):
        """Verify that the Rust parser correctly handles all test cases."""
        for (test_in, expected, message) in TESTS:
            self.check(test_in, expected, message)


# ========== Tests which Compare the Output of Both Parsers ==========

# -FIX- At this time, this is redundant: for any particular test input, if the individual tests
# pass, then the comparison should pass as well.

@tag('parser')
class ComparisonTests(TestCase):
    """Tests that both the Python and Rust parsers return the same results."""

    def setUp(self):
        """Load the Rust parser shared library."""
        import ctypes
        from ctypes import (POINTER, c_char_p, c_int32)

        class CallResult(ctypes.Structure):
            _fields_ = [("status", c_int32), ("text", c_char_p)]

        self._peglib = ctypes.cdll.LoadLibrary("target/release/libabcparser_peg.so")

        self._canonify_music_code = self._peglib.canonify_music_code
        self._canonify_music_code.argtypes = (c_char_p, )
        self._canonify_music_code.restype = POINTER(CallResult)

        self._free_result = self._peglib.free_result
        self._free_result.argtypes = (POINTER(CallResult), )
        self._free_result.restype = None

    def python_canonify_music_code(self, s):
        """Wrapper to the Python canonify_music_code() function, returns a tuple (0, abc) just like
        the Rust version."""
        from .abcparser import decode_abc_text_string
        from .abcparser_peg import canonify_music_code
        from arpeggio import NoMatch

        try:
            s = canonify_music_code(s, text_string_decoder=decode_abc_text_string)
            return (0, s)
        except NoMatch as err:
            return (1, str(err))

    def rust_canonify_music_code(self, s):
        """Python wrapper to the Rust canonify_music_code() function."""
        ptr = self._canonify_music_code(s.encode('utf-8'))
        try:
            return (ptr[0].status, ptr[0].text.decode('utf-8'))
        finally:
            self._free_result(ptr)

    def test_comparisons(self):
        """Verify that the output of the Python and Rust parsers is identical."""
        for (test_input, _, message) in TESTS:
            self.assertEquals(self.python_canonify_music_code(test_input),
                              self.rust_canonify_music_code(test_input),
                              msg='Comparison testing: ' + message)
