import os, re, cPickle, string, time
import cgi, shutil, datetime

import rst_html
import PyRSS2Gen as RSS2

# Filename for the pickled indexes
HOME_DIR = os.environ['HOME']
INDEX_FILENAME = os.path.join(HOME_DIR, 'files/books/index.pkl')

# Directory holding the review source files
SRC_DIR=os.path.join(HOME_DIR, 'files/books/s/')

# Directory for the HTML output 
BASE_DIR=os.path.join(HOME_DIR, 'files/www/sites/amk.ca/books/')
BASE_URL='/books'

# Names of generated files
TITLE = BASE_DIR + 'titles.ht'
SUBJECT = BASE_DIR + 'subjects.ht'
AUTHOR = BASE_DIR + 'authors.ht'
INDEX = BASE_DIR + 'index.ht'
RSS = BASE_DIR + 'index.rss'

# Still to do
CHRON = BASE_DIR + 'chron.ht'
SCHRON = BASE_DIR + 'full-chron.ht'
BEST = BASE_DIR + 'best.ht'
GOOD = BASE_DIR + 'good.ht'
REVIEW_DIR = BASE_DIR + 'h/'
SUBJECT_DIR = BASE_DIR + 's/'
AUTHOR_DIR = BASE_DIR + 'a/'
TITLE_DIR = BASE_DIR + 't/'

abbrevs = { 'A': 'Author',
            'C': 'City',
            'D': 'Date',
            'E': 'Editor',
            'F': 'Translator',
            'G': 'ISBN',
            'I': 'Publisher',
            'J': 'Journal',
            'K': 'Keywords',
            'L': 'Language',
            'M': 'Original Language',
            'N': 'Journal Number',
            'P': 'Number of Pages',
            'Q': 'Illustrator',
            'R': 'Real Name',
            'S': 'Subtitle',
            'T': 'Title',
            'U': 'URL',
            'V': 'Volume',
            'W': 'Location', # Author URL
            'Y': 'Categorization',
            '*': 'Score',    # * for good books, ** for really good books
            '@': 'Date of review',
}

preferred_order = ['@', 'T', 'S', 'A', 'R', 'J', 'V', 
                   'N', 'E', 'L', 'M', 'F', 'Q', 
                   'I', 'C', 'D', 'G', 'P', 
                   'U', 'K', 'Y', 'W', '*']

def make_dirs ():
    for dir in [BASE_DIR, SUBJECT_DIR, REVIEW_DIR, AUTHOR_DIR, TITLE_DIR]:
        if not os.path.exists(dir):
            os.mkdir(dir)

        output = open(os.path.join(dir, 'Makefile'), 'w')
        print >>output, "include ~/files/www/scripts/make.rules"
        output.close()

    f = open(os.path.join(BASE_DIR, '.treeinfo'), 'w')
    f.write('Book Reviews\n')
    f.close()
    
    for path, title in [(SUBJECT_DIR, 'Subject Index'),
                        (AUTHOR_DIR, 'Author Index'),
                        (TITLE_DIR, 'Title Index'),
                        (REVIEW_DIR, 'Reviews'),
                        ]:
        f = open(os.path.join(path, '.treeinfo'), 'w')
        f.write('skip\n')
        f.close()

    
class BibEntry:
    multiple = ['A', 'E', 'F', 'Q']
    
    def __init__ (self, filename):
        self.filename = make_filename(os.path.basename(filename))
        
        self.fields = {}
        self.field_text = None
        self.body = None

    def save (self):
        output = open(get_pickle_filename(self.filename), 'wb')
        cPickle.dump(self, output, 1)
        output.close()
	        
    def parse (self, input):
        self.body = ""
        while 1:
            L = input.readline()
            if L == "":
                raise RuntimeError, 'No bibliographic data: ' + self.filename
            if re.match('^-{2,}$', L):
                break
            self.body += L

        self.body = self.body.strip()
        self.body = rst_html.process_rst(self.filename, self.body)
        
        # Read metadata fields
        self.field_text = ""
        while 1:
            L = input.readline()
            if L == "":
                break
            self.field_text += L
            m = re.match('\s*%([A-Za-z@\*])\s*(.*)\s*', L)
            if m is None:
                continue
            field, value = m.group(1,2)
            field = field.upper()
            if field in self.multiple:
                fl = self.fields.setdefault(field, [])
                fl.append(value.strip())
            else:
                self.fields[field] = value

        self.field_text = self.field_text.strip()
        
        # Fix the fields
        L = self.fields.get('K', '').split(',')
        L = map(string.strip, L)
        L = map(string.lower, L)
        L = filter(None, L)
        self.fields['K'] = L

        self.review_date = self.fields.get('@')
        if self.review_date:
            self.review_date = self.review_date.strip()
        self.pub_date = None

    def link (self):
        url = self.get_url()
        title = cgi.escape(self.fields['T'])
        if self.fields.get('V'):
            title += ' (vol. %s)' % self.fields['V']
                           
        link = '<a href="%s">%s</a>' % (url, title)
        if self.fields.get('S'):
            link += ': ' + cgi.escape(self.fields['S'])
        return link
            
    def get_url (self):
        url = BASE_URL
        url += '/h/' + self.filename
        return url

    def get_isbn (self):
        g = self.fields.get('G')
        if g is None:
            return None
        m = re.search('ISBN\s*([-0-9Xx]+)', g)
        if m:
            isbn = m.group(1)
            isbn = isbn.replace('-', '')
            isbn = isbn.upper()
            return isbn
        else:
            return None

    def as_html (self):
        s = '<div class=diary-entry>'
        s += '<h2>Book: %s</h2>\n' % cgi.escape(self.get_full_title())
        s += ('<span class=diary-date>%s</span>\n' % self.review_date)
        s += ('<a class=diary-permalink href="%s">#</a>\n' % cgi.escape(self.get_url()))
        if not self.body.startswith('<p>'):
            s += '<p>'
        s += self.body 
        s += '\n</div>\n'
        return s

    def write_output (self):
        make_dirs()
        title = self.fields['T']
        filename = self.filename + '.ht'
        path = os.path.join(BASE_DIR, 'h/' + filename)
        isbn = self.get_isbn()
        output = file(path, 'wt')
        print >>output, 'Title: Book review: ' + title
        print >>output, '\n'

        print >>output, self.get_html_format()
        output.close()

        # Set the time of the file
        if False:
            y, m, d = self.get_review_date()
            ftime = time.mktime((y,m,d,0,0,0,0,0,0))
            if ftime is not None:
                os.utime(path, (ftime, ftime))


    def get_html_format (self):
        S = '<div class="hreview">'
        S += self.get_html_header() + '\n<p>\n'
        # Convert text to HTML
        S += ('<div class="description">' +
              re.sub('\n\s*\n', '\n<p>\n', self.body) +
              '</div>')

        S += '</div>'                   # Close 'hreview' class
        return S
        
    def index (self):
        "Add this entry to the indexes"

        review_i[self.filename] = self
        t = make_title(self.fields['T'])
        L = title_i.setdefault(t, [])
        L.append(self.filename)
        
        for s in self.fields['K']:
            L = subject_i.setdefault(s, [])
            L.append(self.filename)
        for a in self.fields.get('A', ''):
            L = author_i.setdefault(a, [])
            L.append(self.filename)
        for a in self.fields.get('E', ''):
            L = author_i.setdefault(a, [])
            L.append(self.filename)

    def get_full_title (self):
        title = self.fields['T']
        subtitle = self.fields.get('S')
        if subtitle:
            title += ': ' + subtitle
        return title

    def get_review_date (self):
        date = self.fields.get('@', None)
        if date is None:
            print self.fields['T']
            return None
        L = date.split('-')
        assert len(L) == 3
        y, m, d = map(int, L)
        return y, m, d
        
    def get_html_header (self):
        L = []
        e = cgi.escape
        g = self.fields.get

        # Title
        title = e(self.get_full_title())
        if g('U'):
            title = '<a href="%s" class="url">%s</a>' % (g('U'), title)
        if g('V') and not g('J'):
            title += ' (Vol. %s)' % g('V')
        title = '<big class="fn">' + title + '</big>'
        if g('*'):
            title += ' ' + g('*')
        L.append(title)
        
        for author in g('A', []):
            author = e(author)
            if g('W'):
                author = '<a href="%s">%s</a>' % (e(g('W')), author)
            if g('R'):
                author += ' (%s)' % e(g('R'))
            L.append(author)

        editors = g('E', [])
        if editors:
            L.append('Ed. ' + ('; '.join(editors)))

        if g('L'):
            translator = g('F', [])
            if translator:
                translator = '; '.join(translator)
            original = g('M')
            lang = g('L')
            msg = 'Translated from %s ' % e(original)
            if lang: msg += 'to ' + e(lang) + ' '
            if translator:
                lang += ' by ' + e(translator)
            L.append(lang)
            
        illus = g('Q', [])
        if illus:
            illus = e('; '.join(g('Q')))
            L.append('Illustrated by:  %s' % illus)

        # Journal information
        if g('J'):
            journal = e(g('J'))
            number = g('N')
            volume = g('V')
            journal = '<cite>%s</cite> %s, no. %s' % (journal, volume, number)
            L.append(journal)
            
        # Publishing info
        imprint = g('I', '') ; city = g('C')
        if imprint and city:
            imprint += ': ' + city 
        if g('D'):
            imprint += ' ' + g('D')
        if imprint:
            L.append(e(imprint))
            
        if g('G'):
            L.append(e(g('G')))

        if g('P'):
            L.append(e(g('P')))
            
        if g('@'):
            L.append('Date finished: <span class="dtreviewed">' + g('@') + '</span>')

        if g('G'):
            # Buy link
            isbn = self.get_isbn()
            if isbn:
                buy = '<a href="http://www.amazon.com/exec/obidos/ASIN/%s">[Buy this book]</a>'
                L.append(buy % isbn)

        # Add item description
        L.insert(0, '<div class="item">')
        L.append('</div>')
        
        s = '<br >\n'.join(L)
        s = "<p>" + s + "</p>\n"
        return s

    also_fiction = ['fantasy', 'erotica', 'novel', 'mystery']
    def is_fiction (self):
        "Returns true if this book is fiction."
        keywords = self.fields.get('K', [])
        if 'reference' in keywords:
            return False
        for subject in keywords:
            if (subject in self.also_fiction or
                re.search(r'\bfiction\b', subject) or
                re.search(r'\bmystery\b', subject)):
                return True
            
        return False
                            
#
# Define indexes
#
# review_i:   f_name -> (date, length, titles, subjects, authors)
# title_i:    title -> [f_name]
# subject_i:  subject -> [f_name]
# author_i:   author -> [f_name]

review_i = {}
subject_i = {}
title_i = {}
author_i = {}

def load ():
    "Load indexes for the book review databases"
    for d in review_i, subject_i, title_i, author_i:
        d.clear()
    for dirname, dirs, files in os.walk(SRC_DIR):
        for f in files:
	    if not (f.startswith('.') and f.endswith('.pkl')):
	        continue
            input = open(os.path.join(dirname, f), 'rb')
	    entry = cPickle.load(input)
	    entry.index()
	    input.close()


STOPWORDS = ['a', 'and', 'the', 'of']

def remove_stopwords (S):
    for sw in STOPWORDS:
        p = re.compile(r'\b%s\b' % sw, re.IGNORECASE)
        S = p.sub('', S)
    return ' '.join(S.split())

def make_title (title):
    title = title.replace("'", '')
    title = title.replace("&", ' ')
    title = title.replace('/', ' ')
    title = title.replace('(', ' ')
    title = title.replace(')', ' ')
    title = title.replace('!', ' ')
    title = title.replace('?', ' ')
    title = remove_stopwords(title)
    return title

def make_filename (title):
    title = make_title(title)
    if ':' in title:
        index = title.find(':')
        title = title[:index]

    fn = re.sub(r'\s+', '_', title)
    t = fn 
    count = 2
    while 1:
        if not review_i.has_key(t):
            return t
        t = fn + '_' + str(count) 
        count += 1
        
    
def sort_by_title (L):
    L = [review_i[i] for i in L]
    L = [(remove_stopwords(r.fields['T']).lower(), r.review_date, r)
         for r in L]
    L.sort()
    L = [rev for title, review_date, rev in L]
    return L

def _write_index_header (output, letters):
    print >>output, "\n<p align=center>"
    letters.sort()
    s = ""
    for a in letters:
        s += '<a href="%s">[%s]</a> | ' % (a, a.upper())
    print >>output, s[:-3]              # Chop off the last '|'
    
    
def _write_index (index, output_dir, output_complete, field_name,
                  include_keys=False):
    keys = index.keys() ; keys.sort()
    letters = {}
    for k in keys:
        first_let = k[0:1].lower()
        letters[first_let] = None
    letters = letters.keys()

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Write /{s,a,t}/index.ht
    out = open(os.path.join(output_dir, 'index.ht'), 'w')
    print >>out, "Title: %s" % (field_name)
    print >>out, 'Meta: <meta name="robots" content="noindex">'
    
    _write_index_header(out, letters)
    out.close()
    
    # Write single-file indexes
    cur_letter = 'a'
    out = open(os.path.join(output_dir, '%s.ht' % cur_letter), 'w')
    print >>out, "Title: %s: %s" % (field_name, cur_letter.upper())
    print >>out, 'Meta: <meta name="robots" content="noindex">'
    _write_index_header(out, letters)
    print >>out, "\n<ul>"
    for k in keys:
        first_letter = k[0].lower()
        if first_letter in string.lowercase and first_letter != cur_letter:
            print >>out, '</ul>'
            out.close()
            cur_letter = first_letter
            out = open(os.path.join(output_dir, '%s.ht' % cur_letter), 'w')
            print >>out, "Title: %s: %s" % (field_name, cur_letter)
            print >>out, 'Meta: <meta name="robots" content="noindex">'
            print >>out, "\n<ul>"
            _write_index_header(out, letters)

        if include_keys:
            print >>out, '<li>', k
            print >>out, '<ul>'
        for rev in sort_by_title(index[k]):
            print >>out, '<li>', rev.link()
        if include_keys:
            print >>out, '</ul>'
        
    print >>out, "\n</ul>"
    
    # Write complete index
    out = open(output_complete, 'wt')
    print >>out, 'Title: %s Index' % field_name
    print >>out, 'Meta: <meta name="robots" content="noindex">'
    print >>out, ''
    print >>out, "<ul>"
    for k in keys:
        reviews = sort_by_title(index[k])
        if include_keys:
            print >>out, '<li>', cgi.escape(k)
            print >>out, "<ul>"
        for rev in reviews:
            print >>out, "<li>", rev.link()
        if include_keys:
            print >>out, "</ul>"
    print >>out, "</ul>"

    
def update_subject_index ():
    _write_index(subject_i, SUBJECT_DIR, SUBJECT, 'Subjects',
                 include_keys=True)

def update_author_index ():
    _write_index(author_i, AUTHOR_DIR, AUTHOR, 'Authors', include_keys=True)

def update_title_index ():
    _write_index(title_i, TITLE_DIR, TITLE, 'Titles')

def sort_by_chron ():
    L = review_i.values()
    L = [(r.review_date, remove_stopwords(r.fields['T']).lower(), r)
         for r in L]
    L.sort() ; L.reverse()
    return L
    
def update_chron_index ():
    output = open(CHRON, 'w')
    print >>output, "Title: Chronological Index"
    print >>output, 'Meta: <meta name="robots" content="noindex">'
    print >>output, "\n"
    print >>output, '<ul>'
    L = sort_by_chron()
    for rev_date, title, rev in L:
        print >>output, '<li>',
        if rev.review_date:
            print >>output, rev.review_date + ':'
        print >>output, rev.link()
    print >>output, '</ul>'
    output.close()

def update_best_index ():
    best_fiction = []
    best_nonfiction = []
    for key, rev in review_i.items():
        if rev.fields.get('*'):
            if rev.is_fiction():
                best_fiction.append(key)
            else:
                best_nonfiction.append(key)

    best_fiction = sort_by_title(best_fiction)
    best_nonfiction = sort_by_title(best_nonfiction)
    
    output = open(BEST, 'w')
    print >>output, """Title: Favorite Books
Meta: <meta name="robots" content="noindex">

<p>This page lists books that I found especially enjoyable,
useful, or otherwise notable.  %i of the %i books in my diary are listed.

<h3>Non-fiction</h3>
<ul>""" % (len(best_fiction) + len(best_nonfiction), len(review_i))

    for rev in best_nonfiction:
        print >>output, '<li>', rev.link()
    print >>output, '</ul><h3>Fiction</h3><ul>'
    for rev in best_fiction:
        print >>output, '<li>', rev.link()
    output.close()


def update_indexes ():
    print 'Writing index HTML'
    update_author_index()
    update_title_index()
    update_subject_index()
    update_chron_index()
    update_best_index()
    
    # Generate list of 7 most recent items
    recent_titles = ""
    L = sort_by_chron()[:7]
    for rev_date, title, rev in L:
        recent_titles += "<li> "
        if rev_date:
            recent_titles += rev_date + ': '
        recent_titles += rev.link() + '\n'
        
    # Write the top-level index file
    output = open(INDEX, 'w')
    print >>output, (INDEX_HT.lstrip()) % vars()
    output.close()

    # Write RSS file
    rss = RSS2.RSS2(title='Book Diary',
                    link='http://www.amk.ca/books/',
                    description="A diary of books I've read.",
                    lastBuildDate = datetime.datetime.now(),
                    language='en',
                   )

    for rev_date, title, rev in L:
        url = 'http://www.amk.ca' + rev.get_url()
        item = RSS2.RSSItem(title=rev.get_full_title(),
                            link = url, guid=url,
                            author = 'akuchling',
                            description = rev.get_html_format())
        y, m, d = rev.get_review_date()
	item.pubDate = datetime.datetime(y,m,d)
        for cat in ['books'] + rev.fields.get('K', []):
            item.categories.append(cat)
            
        rss.items.append(item)
        
    output = open(RSS, 'w')
    rss.write_xml(output)
    output.close()

    # Write recent.html file
    output = open(os.path.join(BASE_DIR, 'recent.html'), 'w')
    for rev_date, title, rev in L:
        title = rev.get_full_title()
        print >>output, ('<p><a href="%s">%s</a></p>'
                         % (rev.get_url(), cgi.escape(title)))

    output.close()


INDEX_HT = """Title: Book Diary: Index Page
RSS-File: index.rss
Keywords: books, review, book, reviews, book review, book reviews, 
          reading, summaries, summary
Description: A.M. Kuchling's book diary.

<P>This is my diary of books I've read.  While it's only for my own
use (mostly to avoid buying books twice and to keep track of authors
I've read), it costs me little effort and no money to publish it on
the Web, and posting it is useful to encourage me to keep it up to
date.

<P>Usually the reviews will be positive or only somewhat negative.
This isn't because I'm easy to please, but because I'll
only write entries for books that I actually finish, or at least read
about 90%% of the pages.  Really bad books aren't noted
because I don't bother to finish them.

<p>You can browse the list by <a href="t/a">title</a> (<a
href="titles">full listing</a>), <a href="a/a">author</a>
(<a href="authors">full listing</a>), <a
href="s/a">subject</a>, or in <a href="chron">chronological
order</a>.  There's also an index of <a href="best">recommended
books</a>.

<h3>Most recent titles</h3>

<ul>
  %(recent_titles)s
</ul>

<p><a href="index.rss"><img src="/images/xml.gif" alt="[RSS feed
available]"></a>
"""

def get_pickle_filename (filename):
    dir = os.path.dirname(filename)
    filename = os.path.basename(filename)
    return os.path.join(dir, '.'+filename + '.pkl')
