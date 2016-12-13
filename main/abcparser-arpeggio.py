#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# https://github.com/igordejanovic/Arpeggio
# http://igordejanovic.net/Arpeggio/

from __future__ import print_function, unicode_literals
import codecs

from arpeggio import Terminal
from arpeggio.cleanpeg import ParserPEG, PTNodeVisitor, visit_parse_tree


parser = ParserPEG(
   # This grammar is based on Henrik Norbeck's ABNF grammar for ABC v2.0, with changes
   # to make it more compatible with the ABC v2.1 specification. It is roughly ordered
   # by section of the v2.1 specification. It assumes Unicode encoding.
   """
   line = element+ EOF

   # element !FIX!
   element = stem / WSP / chord_or_text
   chord_or_text = '"' (chord / text_expression) (chord_newline (chord / text_expression))* '"'

   # note
   # see '4.11 Ties and slurs' and '4.20 Order of abc constructs' for more on ties
   note = pitch note_length? tie?
   tie = '-'

   # ==== 4.1 Pitch

   pitch = accidental? basenote octave?
   basenote = r'[A-Ga-g]'
   octave = r'\\'+' / r',+'

   # ==== 4.2 Accidentals

   accidental = '^^' / '^' / '__' / '_' / '='

   # ==== 4.3 Note lengths

   #   Norbeck specified this as "(DIGITS? ('/' DIGITS)?) / '/'+", which could match the empty
   #   string. We need the note_length parser to fail if it doesn't match anything. Things we
   #   need to match include: '2', '/2', '3/2', '/', '//'.
   note_length = note_length_smaller / note_length_full / note_length_bigger / note_length_slashes
   note_length_bigger = DIGITS+  # DIGITS is already greedy, but this avoids an optimization (bug?)
   note_length_smaller = '/' DIGITS
   note_length_full = DIGITS '/' DIGITS
   note_length_slashes = r'/+'

   # ==== 4.17 Chords and unisons

   # Norbeck used "chord" for chord symbols, and "stem" for what the spec calls chords.
   stem = ('[' note note+ ']') / note

   # ==== 4.18 Chord symbols

   # 'non_quote' is a catch-all for non-conforming ABC (in practice, people sometimes confuse the
   # chord symbol and annotation syntaxes.) Norbeck's grammar let it east everything else between
   # the quotes; here we use a negative lookahead assert to make sure it doesn't eat a
   # chord_newline.
   chord = basenote chord_accidental? chord_type? ('/' basenote chord_accidental?)? \
               (!chord_newline non_quote)*

   # the last three here are \u266f sharp symbol, \u266d flat symbol, and \u266e natural symbol
   chord_accidental = '#' / 'b' / '=' / '♯' / '♭' / '♮'

   # chord type, e.g. m, min, maj7, dim, sus4: "programs should treat chord symbols quite liberally"
   chord_type = r'[A-Za-z\d+\-]+'

   # ==== 4.19 Annotations

   text_expression = ( "^" / "<" / ">" / "_" / "@" ) (!chord_newline non_quote)+

   # ==== utility rules

   chord_newline = '\\\\n' / ';'  # from Norbeck; non-standard extension
   non_quote = r'[^"]'
   DIGITS = r'\d+'
   WSP = r'[ \t]+'  # whitespace

   """,  # --- end of grammar ---

   # " ' '''  # compensate for jed's borken syntax highlighting

   'line',  # default rule
   ws='',   # don't eat whitespace
   memoization=True,
   debug=False
)


class ABCVisitor(PTNodeVisitor):
    def __init__(self, *args, **kwargs):
        self.abc_debug = kwargs.pop('abc_debug', False)
        super().__init__(*args, **kwargs)

    def print_debug(self, node, children):
        print(type(node), node.rule_name, node.flat_str(), children)

    def visit__default__(self, node, children):
        if self.abc_debug: self.print_debug(node, children)
        if isinstance(node, Terminal):
            return node.value
        else:
            return ''.join(children)

    # --- node visitors for particular rules, in case-insensitive alphabetical order by rule name

    def visit_chord_newline(self, node, children):
        return ';'

    def visit_note_length(self, node, children):
        if self.abc_debug: self.print_debug(node, children)
        numerator, denominator = children[0]
        if denominator == 1:
            if numerator == 1:
                return ''
            else:
                return str(numerator)
        else:  # denominator != 1
            if numerator == 1 and denominator == 2:
                return '/'
            elif numerator == 1 and denominator == 4:
                return '//'
            elif numerator == 1:
                return "/%d" % denominator
            else:
                return "%d/%d" % (numerator, denominator)

    def visit_note_length_bigger(self, node, children):
        if self.abc_debug: self.print_debug(node, children)
        return (int(children[0]), 1)

    def visit_note_length_full(self, node, children):
        if self.abc_debug: self.print_debug(node, children)
        return (int(children[0]), int(children[2]))

    def visit_note_length_slashes(self, node, children):
        if self.abc_debug: self.print_debug(node, children)
        return (1, 2**len(node.flat_str()))

    def visit_note_length_smaller(self, node, children):
        if self.abc_debug: self.print_debug(node, children)
        return (1, int(children[1]))

    def visit_WSP(self, node, children):
        if self.abc_debug: self.print_debug(node, children)
        return ' '

if __name__ == '__main__':
    import pprint
    import sys
    pp = pprint.PrettyPrinter(indent=2)

    result = parser.parse(sys.argv[1])

    print(result)  # not useful if one is interested in literal terminals
    pp.pprint(result)
    print('==================================================')

    v = visit_parse_tree(result, ABCVisitor(abc_debug=True))
    print('==================================================')
    pp.pprint(v)
    for c in v:
        print(hex(ord(c)))

