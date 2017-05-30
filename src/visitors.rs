extern crate pest;

use std::iter::FromIterator;

use pest::prelude::*;

use grammar::{Rdp,Rule};

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

fn _gather_children(i: usize, q: &Vec<Token<Rule>>, qlen: usize, input: &str) -> (RString, usize) {
    let mut child_i = i + 1;
    if child_i < qlen && q[child_i].start < q[i].end {
        // there are children to recurse into
        let mut text_offset = q[i].start;
        let mut rstr;
        if text_offset < q[child_i].start {
            // gather plain text before first child
            rstr = RString::from_slice(text_offset, q[child_i].start);
            // gather first child
            let (rstr2, new_i) = _recurse_children(child_i, q, qlen, input);
            rstr = rstr.add(rstr2, input);
            text_offset = q[child_i].end;
            child_i = new_i;
        } else {
            // gather first child
            let (rstr2, new_i) = _recurse_children(child_i, q, qlen, input);
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
            let (rstr2, new_i) = _recurse_children(child_i, q, qlen, input);
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

pub fn visit_parse_tree(parser: &Rdp<pest::StringInput>) -> String {
    let q = parser.queue();
    let qlen = q.len();
    let ilen = parser.input().len();
    let input = parser.input().slice(0, ilen);
    let mut result = String::new();
    let mut i = 0;
    while i < qlen {
        let (rstring, new_i) = _recurse_children(i, q, qlen, input);
        i = new_i;
        result.push_str(&rstring.to_string(input));
    }
    result
}

fn _recurse_children(i: usize, q: &Vec<Token<Rule>>, qlen: usize, input: &str) -> (RString, usize) {
    match q[i].rule {
        // !FIX! canonicize all the "non-standard, from Norbeck" things
        Rule::abc_eol => {
            let (rstr, new_i) = _gather_children(i, q, qlen, input);
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
                (RString::from_slice(q[i].start, q[i].end), i + 1)
            } else {
                (RString::Str(' '.to_string()), i + 1)
            }
        }
        _ => {  // default rule, recursively gather children, if any
            // _gather_children(i, q, qlen, input)
            let x = _gather_children(i, q, qlen, input);
            x
        }
    }
}

