// ABCdb abcparser_peg.rs – ABC text string character encoding table generator
//
// This file is run at build time, to generate static hash maps of the character
// replacements.
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

extern crate phf_codegen;

use std::env;
use std::fs::File;
use std::io::{BufWriter, Write};
use std::path::Path;

const ABC_CHARACTER_MNEMONICS: &'static [(&str, &str)] = &[
    // from the ABC v2.1 standard
    ("\"A", "'Ä'"), ("'A", "'Á'"),  ("AA", "'Å'"),  ("^A", "'Â'"),  ("`A", "'À'"),
    ("uA", "'Ă'"),  ("~A", "'Ã'"),  ("cC", "'Ç'"),  ("\"E", "'Ë'"), ("'E", "'É'"),
    ("AE", "'Æ'"),  ("OE", "'Œ'"),  ("^E", "'Ê'"),  ("`E", "'È'"),  ("uE", "'Ĕ'"),
    ("DH", "'Ð'"),  ("TH", "'Þ'"),  ("\"I", "'Ï'"), ("'I", "'Í'"),  ("^I", "'Î'"),
    ("`I", "'Ì'"),  ("~N", "'Ñ'"),  ("\"O", "'Ö'"), ("'O", "'Ó'"),  ("/O", "'Ø'"),
    ("HO", "'Ő'"),  ("^O", "'Ô'"),  ("`O", "'Ò'"),  ("~O", "'Õ'"),  ("vS", "'Š'"),
    ("\"U", "'Ü'"), ("'U", "'Ú'"),  ("HU", "'Ű'"),  ("^U", "'Û'"),  ("`U", "'Ù'"),
    ("\"Y", "'Ÿ'"), ("'Y", "'Ý'"),  ("^Y", "'Ŷ'"),  ("vZ", "'Ž'"),  ("\"a", "'ä'"),
    ("'a", "'á'"),  ("^a", "'â'"),  ("`a", "'à'"),  ("aa", "'å'"),  ("ua", "'ă'"),
    ("~a", "'ã'"),  ("cc", "'ç'"),  ("\"e", "'ë'"), ("'e", "'é'"),  ("^e", "'ê'"),
    ("`e", "'è'"),  ("ae", "'æ'"),  ("oe", "'œ'"),  ("ue", "'ĕ'"),  ("dh", "'ð'"),
    ("th", "'þ'"),  ("\"i", "'ï'"), ("'i", "'í'"),  ("^i", "'î'"),  ("`i", "'ì'"),
    ("~n", "'ñ'"),  ("\"o", "'ö'"), ("'o", "'ó'"),  ("/o", "'ø'"),  ("Ho", "'ő'"),
    ("^o", "'ô'"),  ("`o", "'ò'"),  ("~o", "'õ'"),  ("ss", "'ß'"),  ("vs", "'š'"),
    ("\"u", "'ü'"), ("'u", "'ú'"),  ("Hu", "'ű'"),  ("^u", "'û'"),  ("`u", "'ù'"),
    ("\"y", "'ÿ'"), ("'y", "'ý'"),  ("^y", "'ŷ'"),  ("vz", "'ž'"),
    // from abcm2ps front.c
    (";A", "'Ą'"), ("=A", "'Ā'"), ("oA", "'Å'"), ("'C", "'Ć'"), (",C", "'Ç'"),
    (".C", "'Ċ'"), ("^C", "'Ĉ'"), ("vC", "'Č'"), ("/D", "'Đ'"), ("=D", "'Đ'"),
    ("vD", "'Ď'"), (".E", "'Ė'"), (";E", "'Ę'"), ("=E", "'Ē'"), ("vE", "'Ě'"),
    (",G", "'Ģ'"), (".G", "'Ġ'"), ("^G", "'Ĝ'"), ("uG", "'Ğ'"), ("=H", "'Ħ'"),
    ("^H", "'Ĥ'"), (".I", "'İ'"), (";I", "'Į'"), ("=I", "'Ī'"), ("uI", "'Ĭ'"),
    ("~I", "'Ĩ'"), ("^J", "'Ĵ'"), (",K", "'Ķ'"), ("'L", "'Ĺ'"), (",L", "'Ļ'"),
    ("/L", "'Ł'"), ("vL", "'Ľ'"), ("'N", "'Ń'"), (",N", "'Ņ'"), ("vN", "'Ň'"),
    (":O", "'Ő'"), ("=O", "'Ō'"), ("uO", "'Ŏ'"), ("'R", "'Ŕ'"), (",R", "'Ŗ'"),
    ("vR", "'Ř'"), ("'S", "'Ś'"), (",S", "'Ş'"), ("^S", "'Ŝ'"), (",T", "'Ţ'"),
    ("=T", "'Ŧ'"), ("vT", "'Ť'"), (":U", "'Ű'"), (";U", "'Ų'"), ("=U", "'Ū'"),
    ("oU", "'Ů'"), ("uU", "'Ŭ'"), ("~U", "'Ũ'"), ("'Z", "'Ź'"), (".Z", "'Ż'"),
    (";a", "'ą'"), ("=a", "'ā'"), ("oa", "'å'"), ("'c", "'ć'"), (",c", "'ç'"),
    (".c", "'ċ'"), ("^c", "'ĉ'"), ("vc", "'č'"), ("/d", "'đ'"), ("=d", "'đ'"),
    ("vd", "'ď'"), (".e", "'ė'"), (";e", "'ę'"), ("=e", "'ē'"), ("ve", "'ě'"),
    (",g", "'ģ'"), (".g", "'ġ'"), ("^g", "'ĝ'"), ("ng", "'ŋ'"), ("ug", "'ğ'"),
    ("=h", "'ħ'"), ("^h", "'ĥ'"), (".i", "'ı'"), (";i", "'į'"), ("=i", "'ī'"),
    ("ui", "'ĭ'"), ("~i", "'ĩ'"), ("^j", "'ĵ'"), (",k", "'ķ'"), ("'l", "'ĺ'"),
    (",l", "'ļ'"), ("/l", "'ł'"), ("vl", "'ľ'"), ("'n", "'ń'"), (",n", "'ņ'"),
    ("vn", "'ň'"), (":o", "'ő'"), ("=o", "'ō'"), ("uo", "'ŏ'"), ("'r", "'ŕ'"),
    (",r", "'ŗ'"), ("vr", "'ř'"), ("'s", "'ś'"), (",s", "'ş'"), ("^s", "'ŝ'"),
    (",t", "'ţ'"), ("=t", "'ŧ'"), ("vt", "'ť'"), (":u", "'ű'"), (";u", "'ų'"),
    ("=u", "'ū'"), ("ou", "'ů'"), ("uu", "'ŭ'"), ("~u", "'ũ'"), ("'z", "'ź'"),
    (".z", "'ż'"),
    // from jcabc2ps ABCdiacrit.html
    ("-A", "'Ā'"), ("-D", "'Đ'"), ("-E", "'Ē'"), ("-H", "'Ħ'"), ("-I", "'Ī'"),
    ("IJ", "'Ĳ'"), (".L", "'Ŀ'"), ("-O", "'Ō'"), ("-T", "'Ŧ'"), ("-U", "'Ū'"),
    ("^W", "'Ŵ'"), ("^Z", "'Ẑ'"), ("-a", "'ā'"), ("-d", "'đ'"), ("-e", "'ē'"),
    ("Ae", "'æ'"), ("Oe", "'œ'"), ("-h", "'ħ'"), ("-i", "'ī'"), ("Ij", "'ĳ'"),
    ("ij", "'ĳ'"), (".l", "'ŀ'"), ("-u", "'ū'"), ("^w", "'ŵ'"), ("^z", "'ẑ'"),
];

const ABC_NAMED_ENTITIES: &'static [(&str, &str)] = &[
    // from the ABC v2.1 standard
    ("AElig",   "'Æ'"), ("Aacute",  "'Á'"), ("Abreve",  "'Ă'"), ("Acirc",   "'Â'"),
    ("Agrave",  "'À'"), ("Aring",   "'Å'"), ("Atilde",  "'Ã'"), ("Auml",    "'Ä'"),
    ("Ccedil",  "'Ç'"), ("ETH",     "'Ð'"), ("Eacute",  "'É'"), ("Ecirc",   "'Ê'"),
    ("Egrave",  "'È'"), ("Euml",    "'Ë'"), ("Iacute",  "'Í'"), ("Icirc",   "'Î'"),
    ("Igrave",  "'Ì'"), ("Iuml",    "'Ï'"), ("Ntilde",  "'Ñ'"), ("OElig",   "'Œ'"),
    ("Oacute",  "'Ó'"), ("Ocirc",   "'Ô'"), ("Ograve",  "'Ò'"), ("Oslash",  "'Ø'"),
    ("Otilde",  "'Õ'"), ("Ouml",    "'Ö'"), ("Scaron",  "'Š'"), ("THORN",   "'Þ'"),
    ("Uacute",  "'Ú'"), ("Ucirc",   "'Û'"), ("Ugrave",  "'Ù'"), ("Uuml",    "'Ü'"),
    ("Yacute",  "'Ý'"), ("Ycirc",   "'Ŷ'"), ("Yuml",    "'Ÿ'"), ("Zcaron",  "'Ž'"),
    ("aacute",  "'á'"), ("abreve",  "'ă'"), ("acirc",   "'â'"), ("aelig",   "'æ'"),
    ("agrave",  "'à'"), ("aring",   "'å'"), ("atilde",  "'ã'"), ("auml",    "'ä'"),
    ("ccedil",  "'ç'"), ("eacute",  "'é'"), ("ecirc",   "'ê'"), ("egrave",  "'è'"),
    ("eth",     "'ð'"), ("euml",    "'ë'"), ("iacute",  "'í'"), ("icirc",   "'î'"),
    ("igrave",  "'ì'"), ("iuml",    "'ï'"), ("ntilde",  "'ñ'"), ("oacute",  "'ó'"),
    ("ocirc",   "'ô'"), ("oelig",   "'œ'"), ("ograve",  "'ò'"), ("oslash",  "'ø'"),
    ("otilde",  "'õ'"), ("ouml",    "'ö'"), ("scaron",  "'š'"), ("szlig",   "'ß'"),
    ("thorn",   "'þ'"), ("uacute",  "'ú'"), ("ucirc",   "'û'"), ("ugrave",  "'ù'"),
    ("uuml",    "'ü'"), ("yacute",  "'ý'"), ("ycirc",   "'ŷ'"), ("yuml",    "'ÿ'"),
    ("zcaron",  "'ž'"),
    // from the HTML 4.0 standard
    ("Alpha",   "'Α'"), ("Beta",    "'Β'"), ("Chi",     "'Χ'"), ("Dagger",  "'‡'"),
    ("Delta",   "'Δ'"), ("Epsilon", "'Ε'"), ("Eta",     "'Η'"), ("Gamma",   "'Γ'"),
    ("Iota",    "'Ι'"), ("Kappa",   "'Κ'"), ("Lambda",  "'Λ'"), ("Mu",      "'Μ'"),
    ("Nu",      "'Ν'"), ("Omega",   "'Ω'"), ("Omicron", "'Ο'"), ("Phi",     "'Φ'"),
    ("Pi",      "'Π'"), ("Prime",   "'″'"), ("Psi",     "'Ψ'"), ("Rho",     "'Ρ'"),
    ("Sigma",   "'Σ'"), ("Tau",     "'Τ'"), ("Theta",   "'Θ'"), ("Upsilon", "'Υ'"),
    ("Xi",      "'Ξ'"), ("Zeta",    "'Ζ'"), ("acute",   "'´'"), ("alefsym", "'ℵ'"),
    ("alpha",   "'α'"), ("amp",     "'&'"), ("and",     "'⊥'"), ("ang",     "'∠'"),
    ("asymp",   "'≈'"), ("bdquo",   "'„'"), ("beta",    "'β'"), ("brvbar",  "'¦'"),
    ("bull",    "'•'"), ("cap",     "'∩'"), ("cedil",   "'¸'"), ("cent",    "'¢'"),
    ("chi",     "'χ'"), ("circ",    "'ˆ'"), ("clubs",   "'♣'"), ("cong",    "'≅'"),
    ("copy",    "'©'"), ("crarr",   "'↵'"), ("cup",     "'∪'"), ("curren",  "'¤'"),
    ("dArr",    "'⇓'"), ("dagger",  "'†'"), ("darr",    "'↓'"), ("deg",     "'°'"),
    ("delta",   "'δ'"), ("diams",   "'♦'"), ("divide",  "'÷'"), ("empty",   "'∅'"),
    ("emsp",    "' '"), ("ensp",    "' '"), ("epsilon", "'ε'"), ("equiv",   "'≡'"),
    ("eta",     "'η'"), ("exist",   "'∃'"), ("fnof",    "'ƒ'"), ("forall",  "'∀'"),
    ("frac12",  "'½'"), ("frac14",  "'¼'"), ("frac34",  "'¾'"), ("frasl",   "'⁄'"),
    ("gamma",   "'γ'"), ("ge",      "'≥'"), ("gt",      "'>'"), ("hArr",    "'⇔'"),
    ("harr",    "'↔'"), ("hearts",  "'♥'"), ("hellip",  "'…'"), ("iexcl",   "'¡'"),
    ("image",   "'ℑ'"), ("infin",   "'∞'"), ("int",     "'∫'"), ("iota",    "'ι'"),
    ("iquest",  "'¿'"), ("isin",    "'∈'"), ("kappa",   "'κ'"), ("lArr",    "'⇐'"),
    ("lambda",  "'λ'"), ("lang",    "'〈'"), ("laquo",   "'«'"), ("larr",    "'←'"),
    ("lceil",   "'⌈'"), ("ldquo",   "'“'"), ("le",      "'≤'"), ("lfloor",  "'⌊'"),
    ("lowast",  "'∗'"), ("loz",     "'◊'"), ("lsaquo",  "'‹'"), ("lsquo",   "'‘'"),
    ("lt",      "'<'"), ("macr",    "'¯'"), ("mdash",   "'—'"), ("micro",   "'µ'"),
    ("middot",  "'·'"), ("minus",   "'−'"), ("mu",      "'μ'"), ("nabla",   "'∇'"),
    ("nbsp",    "' '"), ("ndash",   "'–'"), ("ne",      "'≠'"), ("ni",      "'∋'"),
    ("not",     "'¬'"), ("notin",   "'∉'"), ("nsub",    "'⊄'"), ("nu",      "'ν'"),
    ("oline",   "'‾'"), ("omega",   "'ω'"), ("omicron", "'ο'"), ("oplus",   "'⊕'"),
    ("or",      "'⊦'"), ("ordf",    "'ª'"), ("ordm",    "'º'"), ("otimes",  "'⊗'"),
    ("para",    "'¶'"), ("part",    "'∂'"), ("permil",  "'‰'"), ("perp",    "'⊥'"),
    ("phi",     "'φ'"), ("pi",      "'π'"), ("piv",     "'ϖ'"), ("plusmn",  "'±'"),
    ("pound",   "'£'"), ("prime",   "'′'"), ("prod",    "'∏'"), ("prop",    "'∝'"),
    ("psi",     "'ψ'"), ("quot",    "'\"'"), ("rArr",    "'⇒'"), ("radic",   "'√'"),
    ("rang",    "'〉'"), ("raquo",   "'»'"), ("rarr",    "'→'"), ("rceil",   "'⌉'"),
    ("rdquo",   "'”'"), ("real",    "'ℜ'"), ("reg",     "'®'"), ("rfloor",  "'⌋'"),
    ("rho",     "'ρ'"), ("rsaquo",  "'›'"), ("rsquo",   "'’'"), ("sbquo",   "'‚'"),
    ("sdot",    "'⋅'"), ("sect",    "'§'"), ("sigma",   "'σ'"), ("sigmaf",  "'ς'"),
    ("sim",     "'∼'"), ("spades",  "'♠'"), ("sub",     "'⊂'"), ("sube",    "'⊆'"),
    ("sum",     "'∑'"), ("sup1",    "'¹'"), ("sup2",    "'²'"), ("sup3",    "'³'"),
    ("sup",     "'⊃'"), ("supe",    "'⊇'"), ("tau",     "'τ'"), ("there4",  "'∴'"),
    ("theta",   "'θ'"), ("thetasym", "'ϑ'"), ("thinsp",  "' '"), ("tilde",   "'˜'"),
    ("times",   "'×'"), ("trade",   "'™'"), ("uArr",    "'⇑'"), ("uarr",    "'↑'"),
    ("uml",     "'¨'"), ("upsih",   "'ϒ'"), ("upsilon", "'υ'"), ("weierp",  "'℘'"),
    ("xi",      "'ξ'"), ("yen",     "'¥'"), ("zeta",    "'ζ'"),
];

fn main() {
    let path = Path::new(&env::var("OUT_DIR").unwrap()).join("tables.rs");
    let mut file = BufWriter::new(File::create(&path).unwrap());

    write!(&mut file, "static ABC_CHARACTER_MNEMONICS: phf::Map<&'static str, char> = ").unwrap();
    let mut phfmap = phf_codegen::Map::new();
    for &(s, c) in ABC_CHARACTER_MNEMONICS.iter() {
        phfmap.entry(s, c);
    }
    phfmap.phf_path("phf")
          .build(&mut file)
          .unwrap();
    write!(&mut file, ";\n\n").unwrap();

    write!(&mut file, "static ABC_NAMED_ENTITIES: phf::Map<&'static str, char> = ").unwrap();
    let mut phfmap = phf_codegen::Map::new();
    for &(s, c) in ABC_NAMED_ENTITIES.iter() {
        phfmap.entry(s, c);
    }
    phfmap.phf_path("phf")
          .build(&mut file)
          .unwrap();
    write!(&mut file, ";\n").unwrap();
}
