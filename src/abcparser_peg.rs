// ABCdb abcparser_peg.rs
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

#![recursion_limit="256"]
#![allow(non_snake_case)]  // otherwise the compiler complains about the 'WSP' rule.

#[macro_use]
extern crate pest;

mod grammar;
mod visitors;

use pest::prelude::*;

// xx use std::iter::FromIterator;

use grammar::Rdp;
use visitors::visit_parse_tree;

fn parse_get_error_message(parser: &mut Rdp<pest::StringInput>) -> String {
    let expected = parser.expected();
    let mut message = format!("ABC parse failed at character {}, ", expected.1);
    if expected.1 > 10 {
        message.push_str(&format!("matched '...{}', ", parser.input().slice(expected.1 - 10, expected.1)));
    } else {
        message.push_str(&format!("matched '{}', ", parser.input().slice(0, expected.1)));
    }
    if expected.1 + 10 < parser.input().len() {
        message.push_str(&format!("could not match '{}...', ", parser.input().slice(expected.1, expected.1 + 10)));
    } else {
        message.push_str(&format!("could not match '{}', ", parser.input().slice(expected.1, parser.input().len())));
    };
    message.push_str(&format!("expected {:?}" , expected.0));
    message
}

use std::panic::catch_unwind;
use std::ffi::{CStr,CString};
use std::os::raw::c_char;

#[derive(Debug)]
#[repr(C)]
pub struct ParseResult {
   status: i32,  // 0: successfull parse, 1: parse error, 2: panic caught
   text: *mut c_char  // parsed, canonicized text, or error message
}

#[no_mangle]
pub extern fn canonify_music_code(raw_input: *const c_char) -> *mut ParseResult {
    let result: Result<ParseResult, _> = catch_unwind(|| {
        assert!(!raw_input.is_null());
        let c_str = unsafe { CStr::from_ptr(raw_input) };
        let input = c_str.to_str().unwrap();  // Python should have sent valid UTF-8, panic if not
        let mut parser = Rdp::new(StringInput::new(input));
        let (status, text) = if parser.music_code_line() {  // if parse succeeded
            (0, visit_parse_tree(&parser))                  // get canonical result
        } else {                                            // else
            (1, parse_get_error_message(&mut parser))       // get error message
        };
        ParseResult { status: status, text: CString::new(text).unwrap().into_raw() }
    });
    let pr: ParseResult;
    match result {
        Ok(r) => { pr = r; }
        Err(e) => {  // the closure panicked, so try to get an error message
            let s: &str;
            // why does catch_unwind() throw away the location information?
            //   -> libstd/panicking.rs:try()
            //   -> src/libpanic_unwind/lib.rs:__rust_maybe_catch_panic() discards the location
            //      (file and line) information (if it was ever valid), so the cause is the most
            //      we can retreive:
            if let Some(rs) = e.downcast_ref::<&'static str>() {
                s = *rs;
            } else if let Some(rs) = e.downcast_ref::<String>() {
                s = &rs[..];
            } else {
                s = "Panic!";
            }
            pr = ParseResult { status: 2, text: CString::new(s).unwrap().into_raw() };
        }
    }
    Box::into_raw(Box::new(pr))
}

#[no_mangle]
pub extern fn free_result(p: *mut ParseResult) {
    if !p.is_null() {
        unsafe {
            let b = Box::from_raw(p);
            CString::from_raw(b.text);
        }
    }
}

// tests for RString
    //~ let a = RString::from_slice(0, 1);
    //~ let b = RString::from_slice(1, 3);
    //~ println!("{:?} {:?}", a, b);
    //~ let c = a.add(b, parser.input().slice(0,7));
    //~ println!("{:?}", c);
    //~ let d = RString::from_str("hello!");
    //~ let e = c.add(d, parser.input().slice(0,7));
    //~ println!("{:?}", e);
    //~ let f = RString::from_str("goodbye!");
    //~ let g = e.add(f, parser.input().slice(0,7));
    //~ println!("{:?}", g);
    //~ let h = RString::from_slice(1, 2);
    //~ let i = h.add(g, parser.input().slice(0,7));
    //~ println!("{:?}", i);
    //~ let j = RString::from_slice(1, 2);
    //~ let k = i.add(j, parser.input().slice(0,7));
    //~ println!("{:?}", k);
