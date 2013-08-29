
import os, re, pickle, string, time
import cgi, getpass
import rst_html

# Filename for the pickled indexes
HOME_DIR = os.environ['HOME']

# Directory holding the review source files
SRC_DIR = os.path.join(HOME_DIR, 'Dropbox', 'home', 'text', 'books')


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
            '*': 'Score',    # * for good books, ** for really good books
            '@': 'Date of review',
}

preferred_order = ['@', 'T', 'S', 'A', 'R', 'J', 'V',
                   'N', 'E', 'L', 'M', 'F', 'Q',
                   'I', 'C', 'D', 'G', 'P',
                   'U', 'K', 'W', '*']


class BibEntry:
    # List of fields that can be supplied multiple times in one entry.
    multiple = ['A', 'E', 'F', 'Q']

    def __init__ (self, path):
        self.filename = os.path.basename(path)
        self.full_path = path
        self.fields = {}
        self.field_text = None
        self.body = None
        self.review_date = None
        self.post_id = None
        self.updated = False

    def save (self):
        ##print 'writing', get_pickle_filename(self.full_path)
        output = open(get_pickle_filename(self.full_path), 'wb')
        pickle.dump(self, output, 1)
        output.close()

    def parse (self, input):
        self.body = ""
        while 1:
            L = input.readline()
            if L == "":
                raise RuntimeError('No bibliographic data: ' + self.filename)
            if re.match('^-{2,}$', L):
                break
            self.body += L

        self.body = self.body.strip()
        self.body = rst_html.process_rst(self.filename, self.body)

        # Read metadata fields
        self.field_text = ""
        self.fields.clear()
        while True:
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
        L = [x.strip().lower() for x in L]
        L = [x for x in L if x]
        self.fields['K'] = L

        self.review_date = self.fields.get('@')
        if self.review_date:
            self.review_date = self.review_date.strip()
        self.updated = True

    def get_url (self):
        return 'http://books.amk.ca' + self.get_url_path()

    def get_url_path (self):
        y, m, d = self.get_review_date()
        return '/%04i/%02i/%s.html' % (y, m, self.filename)

    def get_tags (self):
        return self.fields.get('K', [])

    def get_sorting_title(self):
        stopwords = set(('the', 'a'))
        t = self.fields.get('T', '')
        t = t.lower()
        volume = self.fields.get('V')
        words = [word for word in t.split()
                 if word not in stopwords]
        if volume:
            words.append(str(volume).lower())
        return ' '.join(words)

    def get_authors (self):
        L = []
        e = cgi.escape
        g = self.fields.get
        for author_name in sorted(self.fields.get('A', [])):
            author = author_name
            author_url = self.fields.get('W')
            if author_url:
                author = '<a href="%s">%s</a>' % (e(author_url), e(author))
            realname = self.fields.get('R')
            if realname:
                author += ' (%s)' % e(realname)
            L.append(author)

        authors = '; '.join(L)

        editors = self.fields.get('E', [])
        if editors:
            if authors:
                authors += '; '
            authors += ('Ed. ' + ('; '.join(sorted(editors))))

        illustrators = self.fields.get('Q', [])
        if illustrators:
            if authors:
                authors += '; '
            authors += ('Illustrated by: ' + ('; '.join(sorted(illustrators))))

        return authors


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
        s = self.body
        if not s.startswith('<p>'):
            s = '<p>' + s
        return s

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

    def get_full_title (self, include_subtitle=True):
        title = self.fields['T']
        if include_subtitle:
            subtitle = self.fields.get('S')
            if subtitle:
                title += ': ' + subtitle
        if self.fields.get('V'):
            title += ' (vol. %s)' % self.fields['V']
        return title

    def get_review_date (self):
        date = self.fields.get('@', None)
        if date is None:
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
        if g('U'):
            L.append('<a href="%s" class="url">Web site</a>' % (g('U')))
        if g('V') and not g('J'):
            L.append(' (Vol. %s)' % g('V'))

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
            if imprint:
                imprint += ', ' + g('D')
            else:
                imprint = g('D')

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

        if g('*'):
            L.append('Starred review')

        # Add item description
        L.insert(0, '<div class="item">')
        L.append('</div>')

        s = '<br >\n'.join(L)
        s = "<p>" + s + "</p>\n"
        return s

    also_fiction = ['fantasy', 'erotica', 'novel', 'mystery', 'horror', 'sf',
                    'comics']
    def is_fiction (self):
        "Returns true if this book is fiction."
        keywords = self.get_tags()
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
# review_i:   f_name -> BibEntry
# title_i:    title -> [f_name]
# subject_i:  subject -> [f_name]
# author_i:   author -> [f_name]

review_i = {}
subject_i = {}
title_i = {}
author_i = {}

def scan_pickles ():
    "Yield the filenames of the .pkl files."
    for dirname, dirs, files in os.walk(SRC_DIR):
        for f in files:
            if not (f.startswith('.') and f.endswith('.pkl')):
                continue
            yield os.path.join(dirname, f)

def load ():
    "Load indexes for the book review databases"
    for d in review_i, subject_i, title_i, author_i:
        d.clear()
    for f in scan_pickles():
        input = open(f, 'rb')
        entry = pickle.load(input)
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
        if t not in review_i:
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

def sort_by_chron ():
    L = list(review_i.values())
    L = [(r.review_date, remove_stopwords(r.fields['T']).lower(), r)
         for r in L]
    L.sort() ; L.reverse()
    return L

def get_pickle_filename (filename):
    dir = os.path.dirname(filename)
    filename = os.path.basename(filename)
    return os.path.join(dir, '.'+filename + '.pkl')
