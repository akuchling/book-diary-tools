import os, re, cPickle, string, time
import cgi
import xmlrpclib
import rst_html

# Filename for the pickled indexes
HOME_DIR = os.environ['HOME']
INDEX_FILENAME = os.path.join(HOME_DIR, 'files/books/index.pkl')

# Directory holding the review source files
SRC_DIR=os.path.join(HOME_DIR, 'files/books/s/')

# Configuration for the posting mechanism
XMLRPC_SERVER = 'http://books.amk.ca/xmlrpc.php'
WEBLOG_NAME = 'Books'
WEBLOG_USER = 'amk'


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

def sort_by_chron ():
    L = review_i.values()
    L = [(r.review_date, remove_stopwords(r.fields['T']).lower(), r)
         for r in L]
    L.sort() ; L.reverse()
    return L    

def get_pickle_filename (filename):
    dir = os.path.dirname(filename)
    filename = os.path.basename(filename)
    return os.path.join(dir, '.'+filename + '.pkl')

#
# Weblog API functions
#

def _get_xmlrpc_server():
    return xmlrpclib.ServerProxy(XMLRPC_SERVER)

def _get_wp_password():
    # XXX need to implement a prompt
    return 'XXX'

def delete_all_posts():
    """Lists all posts to the weblog and deletes them.
    """
    wp = _get_xmlrpc_server()
    chunk = 50
    password = _get_wp_password()
    while True:
        posts = wp.metaWeblog.getRecentPosts(WEBLOG_NAME, WEBLOG_USER,
                                             password, chunk)
        if len(posts) == 0:
            break
        for p in posts:
            deleted = wp.blogger.deletePost(WEBLOG_NAME, p['postid'],
                                            WEBLOG_USER, password, 
                                            False)

        
