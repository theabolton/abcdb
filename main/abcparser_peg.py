#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ABCdb abcparser_peg.py
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

from __future__ import print_function, unicode_literals
import codecs

from arpeggio import Terminal
from arpeggio.cleanpeg import ParserPEG, PTNodeVisitor, visit_parse_tree


parser = ParserPEG(
   # This grammar is based on Henrik Norbeck's ABNF grammar for ABC v2.0, with:
   #  1) corrections for its mistakes (e.g. rests could not be generated),
   #  2) rearrangingment of the rules necessary for PEG ordered-choice parsing, and
   #  3) changes to make it more compatible with the ABC v2.1 specification.
   # Norbeck's grammar seems to have disappeared from its original location on the web, but
   # has recently been available at:
   #    https://web.archive.org/web/20120528143746/http://www.norbeck.nu/abc/bnf/abc20bnf.txt

   # The following is roughly ordered by section of the v2.1 specification. It assumes Unicode
   # encoding.
   """
   music_code_line = abc_line EOF

   abc_line = ( ( barline? element+ (barline element+)* barline? ) / barline ) abc_eol

   element = broken_rhythm / stem / WSP / chord_or_text / gracing / grace_notes / tuplet /
             slur_begin / slur_end / rollback / multi_measure_rest / measure_repeat / nth_repeat /
             end_nth_repeat / inline_field / hard_line_break / unused_char

   chord_or_text = '"' (chord / text_expression) (chord_newline (chord / text_expression))* '"'
   gracing = '.' / userdef_symbol / long_gracing
   note = pitch note_length? tie?
   unused_char = reserved_char / backquote  # -FIX- Norbeck included '+', should we?

   # ==== 3.1.6 M: - meter

   meter = meter_num / r'[Cc]\\|?' / 'none'
   meter_num = ( ( '(' WSP* DIGITS (WSP* '+' WSP* DIGITS)* WSP* ')' ) /
                   ( DIGITS (WSP* '+' WSP* DIGITS)* ) )
               WSP* '/' WSP* DIGITS

   # ==== 3.1.8 Q: - tempo

   tempo = ( tempo_spec ( WSP+ tempo_desc )? ) / ( tempo_desc ( WSP+ tempo_spec )? )
   tempo_spec = ( note_length_strict '=' DIGITS ) / ( r'[Cc]' note_length? '=' DIGITS ) / DIGITS
   tempo_desc = '"' non_quote* '"'

   # ==== 3.1.14 K: - key

   key = ( key_def ( WSP+ clef )? ) / clef / 'HP' / 'Hp'
   key_def = basenote r'[#b♯♭]'? ( WSP* mode )? ( WSP ( WSP* global_accidental )+ )*
   mode = major / lydian / ionian / mixolydian / dorian / aeolian / phrygian / locrian / minor /
          'exp'
   major = 'maj' ('o' 'r'?)?
   lydian = 'lyd' ('i' ('a' ('n')?)?)?
   ionian = 'ion' ('i' ('a' ('n')?)?)?
   mixolydian = 'mix' ('o' ('l' ('y' ('d' ('i' ('a' ('n')?)?)?)?)?)?)?
   dorian = 'dor' ('i' ('a' ('n')?)?)?
   aeolian = 'aeo' ('l' ('i' ('a' ('n')?)?)?)?
   phrygian = 'phr' ('y' ('g' ('i' ('a' ('n')?)?)?)?)?
   locrian = 'loc' ('r' ('i' ('a' ('n')?)?)?)?
   minor = 'm' ('in' ('o' 'r'?)?)?
   global_accidental = accidental basenote

   # ==== 3.2 Use of fields within the tune body

   inline_field = ifield_text / ifield_key / ifield_length / ifield_meter / ifield_part /
                  ifield_tempo / ifield_userdef / ifield_voice
   ifield_text = r'\\[[INRr]:[^\\]]+\\]'
   ifield_key = '[K:' WSP* ( 'none' / key? ) ']'
   ifield_length = '[L:' WSP* note_length_strict ']'
   ifield_meter = '[M:' WSP* meter ']'
   # -FIX- define ABC2.1 'm:' macro field
   # ifield_part: 'P:' fields are supposed to be very structured (see 3.1.9), but in the wild, they
   # are frequently abused. Accept any non-']' text:
   ifield_part = r'\\[P:[^\\]]+\\]'
   ifield_tempo = '[Q:' WSP* tempo ']'
   ifield_userdef = r'\\[U:[^\\]]+\\]'
   ifield_voice = '[V:' WSP* voice ']'

   # ==== 4.1 Pitch

   pitch = accidental? basenote octave?
   basenote = r'[A-Ga-g]'
   octave = r'\\'+' / r',+'

   # ==== 4.2 Accidentals

   accidental = '^^' / '^' / '__' / '_' / '='

   # ==== 4.3 Note lengths

   # Norbeck specified this as "(DIGITS? ('/' DIGITS)?) / '/'+", which could match the empty
   # string. We need the note_length parser to fail if it doesn't match anything. Things we
   # need to match include: '2', '/2', '3/2', '/', '//'.
   note_length = note_length_smaller / note_length_full / note_length_bigger / note_length_slashes
   note_length_bigger = DIGITS+  # DIGITS is already greedy, but this avoids an optimization (bug?)
   note_length_smaller = '/' DIGITS
   note_length_full = DIGITS '/' DIGITS
   note_length_slashes = r'/+'

   # used by various fields
   note_length_strict = ( DIGITS '/' DIGITS ) / '1'

   # ==== 4.4 Broken rhythm

   broken_rhythm = stem b_elem* r'[<>]{1,3}' b_elem* stem
   b_elem = WSP / chord_or_text / gracing / grace_notes / slur_begin / slur_end

   # ==== 4.5 Rests

   rest = r'[xyz]' note_length?
   multi_measure_rest = r'Z[0-9]*'

   # ==== 4.6 Clefs and transposition

   clef = ( clef_spec / clef_middle / clef_transpose / clef_octave / clef_stafflines )
          ( WSP+ clef )?
   clef_spec = ( ( 'clef=' ( clef_note / clef_name ) ) / clef_name ) clef_line? ( '+8' / '-8' )?
          ( WSP+ clef_middle )?
   clef_note = 'G' / 'C' / 'F' / 'P'  # non-standard, from Norbeck
   clef_name = 'treble' / 'alto' / 'tenor' / 'bass' / 'perc' / 'none'
   clef_line = r'[1-5]'
   clef_middle = 'middle=' basenote octave?
   clef_transpose = 'transpose=' '-'? DIGITS
   clef_octave = 'octave=' '-'? DIGITS
   clef_stafflines = 'stafflines=' DIGITS

   # ==== 4.7 Beams

   backquote = '`'  # used to increase legibility in groups of beamed notes, otherwise meaningless

   # ==== 4.8 Repeat/bar symbols

   barline = invisible_barline / ( ':'* '['? ( '.'? '|' )+ ( ']' / ':'+ / nth_repeat_num )? ) /
             double_repeat_barline / dashed_barline
   invisible_barline = '[|]' / '[]'  # second is non-standard, from Norbeck
   double_repeat_barline = '::'
   dashed_barline = ':'  # non-standard, from Norbeck

   # ==== 4.9 First and second repeats

   nth_repeat = '[' ( nth_repeat_num / nth_repeat_text )
   nth_repeat_num = DIGITS ( ( ',' / '-' ) DIGITS)*
   nth_repeat_text = '"' non_quote* '"'  # from Norbeck, not in the standard?
   end_nth_repeat = ']'

   # ==== 4.10 Variant endings -- see 4.8 Repeat/bar symbols

   # ==== 4.11 Ties and slurs

   # see '4.20 Order of abc constructs' for more on ties
   tie = '-'
   slur_begin = '('
   slur_end = ')'

   # ==== 4.12 Grace notes

   # -FIX- Norbeck didn't include broken rhythm here, and I haven't yet implemented it. I have seen
   # it in the wild, though rarely.
   grace_notes = "{" acciaccatura? grace_note_stem+ "}"
   grace_note_stem = grace_note / ( "[" grace_note grace_note+ "]" )  # from Norbeck; non-standard extension
   grace_note = pitch note_length?
   acciaccatura = "/"

   # ==== 4.13 Duplets, triplets, quadruplets, etc.

   # Norbeck included two or more elements as part of the tuplet, but here we'd need to tell the
   # parser to match as many elements as the value of the first DIGITS.
   tuplet = '(' DIGITS ( ':' DIGITS? ':' DIGITS? )?

   # ==== 4.14 Decorations

   # -FIX- 'I:decoration +' could change '!' to '+'
   long_gracing = ( "!" ( gracing1 / gracing2 / gracing3 / gracing4 / gracing_nonstandard ) "!" ) /
                  ( "!" gracing_catchall "!" )
   gracing1 = "<(" / "<)" / ">(" / ">)" / "D.C." / "D.S." / "accent" / "arpeggio" / "breath" /
              "coda" / "crescendo(" / "crescendo)" / "dacapo" / "dacoda" / "diminuendo("
   gracing2 = "diminuendo)" / "downbow" / "emphasis" / "fermata" / "ffff" / "fff" / "ff" / "fine" /
              "invertedfermata" / "invertedturnx" / "invertedturn" / "longphrase" / "lowermordent"
   gracing3 = "mediumphrase" / "mf" / "mordent" / "mp" / "open" / "plus" / "pppp" / "ppp" / "pp" /
              "pralltriller" / "roll" / "segno" / "sfz" / "shortphrase" / "slide" / "snap"
   gracing4 = "tenuto" / "thumb" / "trill(" / "trill)" / "trill" / "turnx" / "turn" / "upbow" /
              "uppermordent" / "wedge" / r'[+0-5<>fp]'
   gracing_nonstandard = "cresc" / "decresc" / "dimin" / "fp" /
                         ( "repeatbar" DIGITS )  # non-standard, from Norbeck
   gracing_catchall = r'[\x22-\x7e]+'  # catch-all for non-standard ABC

   # ==== 4.16 Redefinable symbols

   userdef_symbol = r'[~H-Yh-w]'  # Norbeck includes non-standard 'X' and 'Y'

   # ==== 4.17 Chords and unisons

   # Norbeck used "chord" for chord symbols, and "stem" for what the spec calls chords.
   stem = ( '[' note note+ ']' tie? ) / note / rest

   # ==== 4.18 Chord symbols

   # 'non_quote' is a catch-all for non-conforming ABC (in practice, people sometimes confuse the
   # chord symbol and annotation syntaxes.) Norbeck's grammar let it eat everything else between
   # the quotes; here we use a negative lookahead assert to make sure it doesn't eat a
   # chord_newline.
   chord = basenote chord_accidental? chord_type? ('/' basenote chord_accidental?)?
               (!chord_newline non_quote)*

   # the last three here are \\u266f sharp symbol, \\u266d flat symbol, and \\u266e natural symbol
   chord_accidental = '#' / 'b' / '=' / '♯' / '♭' / '♮'

   # chord type, e.g. m, min, maj7, dim, sus4: "programs should treat chord symbols quite liberally"
   chord_type = r'[A-Za-z\\d+\\-]+'

   # Norbeck included '\\n' and ';' as non-standard extensions indicating a newline within the
   # chord symbol or annotation. The ';' conflicts with named entities in ABC text strings, so
   # we leave that out.
   chord_newline = '\\\\n'  # from Norbeck; non-standard extension

   # ==== 4.19 Annotations

   text_expression = ( ( "^" / "<" / ">" / "_" / "@" ) (!chord_newline non_quote)+ ) /
                     bad_text_expression
   bad_text_expression = (!chord_newline non_quote)+   # no leading placement symbol

   # ==== 6.1.1 Typesetting linebreaks

   # this would include comments, if we did not strip them already:
   abc_eol = line_continuation? WSP*
   line_continuation = '\\\\'

   # -FIX- this could be changed by a 'I:linebreak' field:
   hard_line_break = '$' / '!'

   # ==== 7. Multiple voices

   voice = r'[^ \\]]+' ( WSP+ r'[^ =\\]]+' '=' ( ( '"' non_quote* '"' ) / r'[^ \\]]+' ) )*

   # ==== 7.4 Voice overlay

   rollback = '&'

   # ==== 8.1 Tune body

   reserved_char = r'[#\\*;\\?@]'

   # ==== utility rules

   measure_repeat = r'//?'        # from Norbeck; non-standard extension
   non_quote = r'[^"]'
   DIGITS = r'\\d+'
   WSP = r'[ \\t]+'  # whitespace

   """,  # --- end of grammar ---

   # " ' '''  # compensate for jed's borken syntax highlighting

   'music_code_line',  # default rule
   ws='',   # don't eat whitespace
   memoization=True,
   debug=False
)


class ABCVisitor(PTNodeVisitor):
    def __init__(self, *args, **kwargs):
        self.abc_debug = kwargs.pop('abc_debug', False)
        self.text_string_decoder = kwargs.pop('text_string_decoder', None)
        super().__init__(*args, **kwargs)

    def print_debug(self, node, children):
        print(type(node), node.rule_name, node.flat_str(), children)  # pragma: no cover

    def visit__default__(self, node, children):
        if self.abc_debug: self.print_debug(node, children)
        if isinstance(node, Terminal):
            return node.value
        else:
            return ''.join(children)

    # --- node visitors for particular rules, in case-insensitive alphabetical order by rule name

    def visit_abc_eol(self, node, children):
        if self.abc_debug: self.print_debug(node, children)
        return ''.join(children).rstrip()

    def visit_bad_text_expression(self, node, children):
        if self.abc_debug: self.print_debug(node, children)
        return '@' + ''.join(children) # add a non-specific placement symbol

    def visit_ifield_text(self, node, children):
        text = node.value
        # If this inline information field is a N:notes, R:rhythm, or r:remark field,
        # decode its text string. All other (legal) inline information field are ASCII.
        if text[1:2] in 'NRr' and self.text_string_decoder:
            text = self.text_string_decoder(text)
        return text

    def visit_invisible_barline(self, node, children):
        if self.abc_debug: self.print_debug(node, children)
        return '[|]'

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

    def visit_tempo_desc(self, node, children):
        if self.abc_debug: self.print_debug(node, children)
        text = ''.join(children)
        if self.text_string_decoder:
            text = self.text_string_decoder(text)
        return text

    def visit_text_expression(self, node, children):
        text = ''.join(children)
        if self.text_string_decoder:  # pragma: no branch
            text = self.text_string_decoder(text)
        return text

    def visit_WSP(self, node, children):
        if self.abc_debug: self.print_debug(node, children)
        return ' '


def canonify_music_code(line, text_string_decoder=None):
    parse_tree = parser.parse(line)
    return visit_parse_tree(parse_tree, ABCVisitor(text_string_decoder=text_string_decoder))


if __name__ == '__main__':  # pragma: no cover
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

