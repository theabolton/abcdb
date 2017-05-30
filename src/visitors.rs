// ABCdb abcparser_peg.rs – visitors.rs
//
// Copyright © 2017 Sean Bolton.
//
// Permission is hereby granted, free of charge, to any person obtaining
// a copy of this software and associated documentation files (the
// "Software"), to deal in the Software without restriction, including
// without limitation the rights to use, copy, modify, merge, publish,
// distribute, sublicense, and/or sell copies of the Software, and to
// permit persons to whom the Software is furnished to do so, subject to
// the following conditions:
//
// The above copyright notice and this permission notice shall be
// included in all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
// EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
// MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
// NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
// LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
// OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
// WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

extern crate pest;

use std::iter::FromIterator;

use pest::prelude::*;

use grammar::{Rdp,Rule};

// ======== RSlice and RString ========

// RSlice and RString form an efficient way to build up the canonified ABC while walking the
// parse tree. Since this most often involves simply concatenating adjacent slices of the input,
// the RString 'Slice' variant is used to accumulate the pieces without allocating a String. Only
// when a parse rule result needs to be changed will a String need to be allocated.

#[derive(Debug)]
struct RSlice {
    start: usize,
    end: usize
}

#[derive(Debug)]
enum RString {
    Slice(RSlice),
    Str(String)
}

impl RString {
    fn from_slice(start: usize, end: usize) -> RString {
        RString::Slice(RSlice { start, end })
    }

    #[allow(unused)]
    fn from_str(s: &str) -> RString {
        RString::Str(s.to_string())
    }

    fn to_string(self, input: &str) -> String {
        match self {
            RString::Slice(slice) => { String::from_iter(input[slice.start..slice.end].chars()) }
            RString::Str(s) => { s }
        }
    }

    fn add(self, other: RString, input: &str) -> RString {
        match (self, other) {
            (RString::Slice(mut lslice), RString::Slice(rslice)) => {
                if lslice.end == rslice.start {
                    lslice.end = rslice.end;
                    RString::Slice(lslice)
                } else {
                    let mut s = String::from_iter(input[lslice.start..lslice.end].chars());
                    s.push_str(&input[rslice.start..rslice.end]);
                    RString::Str(s)
                }
            }
            (RString::Slice(lslice), RString::Str(rstring)) => {
                let mut s = String::from_iter(input[lslice.start..lslice.end].chars());
                s.push_str(&rstring);
                RString::Str(s)
            }
            (RString::Str(mut lstring), RString::Slice(rslice)) => {
                lstring.push_str(&input[rslice.start..rslice.end]);
                RString::Str(lstring)
            }
            (RString::Str(mut lstring), RString::Str(rstring)) => {
                lstring.push_str(&rstring);
                RString::Str(lstring)
            }
        }
    }
}

// ======== Parse Tree Visitors =======

// A parse tree visitor returns a String built from the parsed text, with any necessary changes
// applied. A visitor is made from two mutually-recursive functions, gather_children() and a
// RulerFn, driven by the top visitor function, visit_parse_tree(). The RulerFn is responsible
// for matching on the parser rules, and taking correspondingly appropriate actions.

// The immutable context passed between the RulerFn and gather_children()
struct Context<'a> {
    index: usize,             // index of the current node in q
    q: &'a Vec<Token<Rule>>,  // the parser result queue
    input: &'a str,           // the original input text
    ruler: &'a RulerFn,       // the RulerFn for this visitor
}

// For the node Context.q[Context.index], a RulerFn returns a tuple, consisting of an RString of
// the processed text for that node and any of its children, and one more than the last child it
// processed (which is the index of the next node to be processed if more nodes exist.)
type RulerFn = Fn(&Context) -> (RString, usize);

fn gather_children(context: &Context) -> (RString, usize) {
    let i = context.index;
    let q = context.q;
    let qlen = q.len();
    let input = context.input;
    let mut child_i = i + 1;
    if child_i < qlen && q[child_i].start < q[i].end {
        // there are children to recurse into
        let mut text_offset = q[i].start;
        let mut rstr;
        if text_offset < q[child_i].start {
            // gather plain text before first child
            rstr = RString::from_slice(text_offset, q[child_i].start);
            // gather first child
            let (rstr2, new_i) = (context.ruler)(&Context { index: child_i, .. *context });
            rstr = rstr.add(rstr2, input);
            text_offset = q[child_i].end;
            child_i = new_i;
        } else {
            // gather first child
            let (rstr2, new_i) = (context.ruler)(&Context { index: child_i, .. *context });
            rstr = rstr2;
            text_offset = q[child_i].end;
            child_i = new_i;
        }
        while child_i < qlen && q[child_i].start < q[i].end {
            // gather plain text before child, if any
            if text_offset < q[child_i].start {
                rstr = rstr.add(RString::from_slice(text_offset, q[child_i].start), input);
            }
            // gather child
            let (rstr2, new_i) = (context.ruler)(&Context { index: child_i, .. *context });
            rstr = rstr.add(rstr2, input);
            text_offset = q[child_i].end;
            child_i = new_i;
        }
        // gather plain text after last child, if any
        if text_offset < q[i].end {
            rstr = rstr.add(RString::from_slice(text_offset, q[i].end), input);
        }
        (rstr, child_i)
    } else {
        // no children, just return the text of this match
        (RString::from_slice(q[i].start, q[i].end), i + 1)
    }
}

fn visit_parse_tree(parser: &Rdp<pest::StringInput>, ruler: &RulerFn) -> String {
    let q = parser.queue();
    let qlen = q.len();
    let ilen = parser.input().len();
    let input = parser.input().slice(0, ilen);
    let mut result = String::new();
    let mut i = 0;
    while i < qlen {
        let (rstring, new_i) = ruler(&Context { index: i, q, input, ruler });
        i = new_i;
        result.push_str(&rstring.to_string(input));
    }
    result
}

// ======== ABC Canonification ========

fn ruler_canonify_abc(context: &Context) -> (RString, usize) {
    let i = context.index;
    let q = context.q;
    let input = context.input;
    match q[i].rule {
        // !FIX! canonicize all the "non-standard, from Norbeck" things
        Rule::abc_eol => {
            let (rstr, new_i) = gather_children(context);
            // trim trailing whitespace
            let s = rstr.to_string(input).trim().to_string();
            (RString::Str(s), new_i)
        }
        Rule::chord_newline => {
            // canonicize to ';'
            (RString::Str(';'.to_string()), i + 1)
        }
        Rule::WSP => {
            // squash any whitespace to a single space
            if &input[q[i].start..q[i].end] == " " {
                // it is just a single space already
                (RString::from_slice(q[i].start, q[i].end), i + 1)
            } else {
                (RString::Str(' '.to_string()), i + 1)
            }
        }
        _ => {  // default rule, recursively gather children, if any
            gather_children(context)
        }
    }
}

pub fn canonify_abc_visitor(parser: &Rdp<pest::StringInput>) -> String {
    visit_parse_tree(parser, &ruler_canonify_abc)
}

