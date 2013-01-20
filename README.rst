
Book Diary
----------

A set of scripts for managing a collection of book notes.

The format for the notes is similar to that of the refer(1)
bibliographic tool that's part of groff.  One entry is stored per
file, consisting of:

* the text of a review formatted in reST.
* a line containing only two or more '-' characters, indicating the start of
  the metadata fields.
* any number of metadata fields, one per line.  Fields are denoted as '%<letter>';
  a list of the legal values for <letter> is below.

To do anything, run the 'books' command and specify a subcommand.

* 'books update' examines the current working directory for files and writes a
  pickled version of each file as .<filename>.pkl.
* 'books stats' prints statistics about how many books you read each year.
* 'books best' prints HTML for lists of the books you marked as especially good.

Legal values for the fields are close to those supported by refer(1).
Fields that can be supplied multiple times have 'multiple' in their
description.

* A: Author name (multiple)
* C: City of the publisher
* D: Date of publication, as YYYY
* E: Editor
* F: Translator
* G: ISBN number.
* I: Publisher
* J: Journal
* K: Keywords, separated by commas
* L: Language
* M: Original Language
* N: Journal Number
* P: Number of Pages
* Q: Illustrator (multiple)
* R: Real Name of author
* S: Subtitle of book
* T: Title of book
* U: URL for book.
* V: Volume
* W: URL for author
* \*: Score.  If present, must have the value '*' to indicate an especially good book.
* @: Date of review, as YYYY-MM-DD

The license is MIT.  Two scripts (books and books.d/help) come from
the subcommander project (https://github.com/datagrok/subcommander),
and are under the AGPLv3.
