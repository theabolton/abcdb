#!/usr/bin/env python3

# https://github.com/igordejanovic/Arpeggio
# http://igordejanovic.net/Arpeggio/

import codecs

from arpeggio import Terminal
from arpeggio.cleanpeg import ParserPEG, PTNodeVisitor, visit_parse_tree


parser = ParserPEG(
   """
   line = stem+ EOF

   # stem
   #   "Notes on a stem" – a more natural name for this would be "chord", but Norbeck used that
   #   for chord symbols.
   stem = ('[' note note+ ']') / note

   # note
   note = pitch note_length? tie?

   # note length
   #   Norbeck specified this as "(digits? ('/' digits)?) / '/'+", which could match the empty
   #   string. We need the note_length parser to fail if it doesn't match anything. Things we
   #   need to match include: '2', '/2', '3/2', '/', '//'.
   note_length = note_length_smaller / note_length_full / note_length_bigger / note_length_slashes
   note_length_bigger = digits+  # digits is already greedy, but this avoids an optimization (bug?)
   note_length_smaller = '/' digits
   note_length_full = digits '/' digits
   note_length_slashes = r'/+'

   tie = '-'

   # pitch
   pitch = accidental? basenote octave?
   accidental = '^^' / '^' / '__' / '_' / '='
   basenote = r'[A-Ga-g]'
   octave = r'\\'+' / r',+'

   # utility rules
   digits = r'\d+'

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

    def visit__default__(self, node, children):
        if self.abc_debug:
            print(type(node), node.rule_name, node.flat_str(), children)
        if isinstance(node, Terminal):
            return node.value
        else:
            return ''.join(children)

    def visit_note_length_bigger(self, node, children):
        if self.abc_debug:
            print(type(node), node.rule_name, node.flat_str(), children)
        return (int(children[0]), 1)

    def visit_note_length_smaller(self, node, children):
        if self.abc_debug:
            print(type(node), node.rule_name, node.flat_str(), children)
        return (1, int(children[1]))

    def visit_note_length_full(self, node, children):
        if self.abc_debug:
            print(type(node), node.rule_name, node.flat_str(), children)
        return (int(children[0]), int(children[2]))

    def visit_note_length_slashes(self, node, children):
        if self.abc_debug:
            print(type(node), node.rule_name, node.flat_str(), children)
        return (1, 2**len(node.flat_str()))

    def visit_note_length(self, node, children):
        if self.abc_debug:
            print(type(node), node.rule_name, node.flat_str(), children)
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

