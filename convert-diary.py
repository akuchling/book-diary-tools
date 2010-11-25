#!/usr/bin/env python

# Script to convert my old diary files
# This code is pure evil.

import re, sys

# Pattern to match a date
date_pat = re.compile("""
(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat) \s+
(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+
(?P<day>\d+) \s+
(?P<year>\d+) \s*""", re.VERBOSE)

para_pat = re.compile("""<[pP]([^>]*)>
\s* <[Bb]> (""" + date_pat.pattern + """)(?:</[Bb]\s*>)?\s*:""", re.VERBOSE)

DAYS=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
MONTHS = {
    'jan':1, 'feb':2, 'mar':3, 'apr':4, 'may':5, 'jun':6,
    'jul':7, 'aug':8, 'sep':9, 'oct':10, 'nov':11, 'dec':12
    }
MONTHS_REV = {}
for key, value in MONTHS.items():
    MONTHS_REV[value] = key.capitalize()

def main ():
    # Skip the header until the first blank line
    for line in sys.stdin:
        if line.strip() == '':
            break

    # Now, parse the body
    entry = "" ; para_attr = "" ; date=""
    for line in sys.stdin:
        m = para_pat.match(line)
        if m:
            if entry:
                process_entry(para_attr, date, entry)
            entry = line[m.end():]
            para_attr = m.group(1)
            date = m.group(2)
        else:
            entry += line

    if entry:
        process_entry(para_attr, date, entry)


href_pat = re.compile('<a[\n\s]+href=[\'"]?(.*?)[\'"]?>(.*?)</a>',
                      re.VERBOSE | re.DOTALL | re.S)

def process_entry(para_attr, date, entry):
    dayname, month, day, year = date.split()
    date = '%04s-%02i-%02i' % (year, MONTHS[month.lower()], int(day))
    # Determine the class
    category = ""
    m = re.search('class=\s*[\'"]?(.*)[\'"\s]*', para_attr)
    if m:
        category = 'Category: ' + m.group(1)

    # Turn my HTMLish text into RST
    entry = entry.replace('<p>', '\n\n')
    entry = entry.replace('</p>', '')
    entry = entry.replace('<cite>', ':cite:`')
    entry = entry.replace('</cite>', '`')
    entry = entry.replace('<code>', '``')
    entry = entry.replace('</code>', '``')
    entry = entry.replace('<em>', '*')
    entry = entry.replace('</em>', '*')
    entry = entry.replace('<ul>', '')
    entry = entry.replace('</ul>', '')
    entry = entry.replace('<li>', '* ')

    def f(match):
        import string
        s = match.group(1)
        lines = entry.split('\n')
        lines = map(string.strip, lines)
        lines = map(string.lstrip, lines)
        entry ='\t' + '\n\t'.join(lines)
        entry = entry.rstrip() + '\n'
        return '\n::\n\n' + entry
    
    entry = re.sub('<blockquote>(.*?)</blockquote>', f, entry)

    def f(match):
        import string
        s = match.group(1)
        lines = entry.split('\n')
        lines = map(string.strip, lines)
        lines = map(string.lstrip, lines)
        entry ='\t' + '\n\t'.join(lines)
        entry = entry.rstrip() + '\n'
        return '\n' + entry
    
    entry = href_pat.sub('`\g<2> <\g<1>>`_', entry)

    entry = entry.strip() + '\n'
    entry = re.sub(r'\n{3,}', '\n\n', entry)
    entry = re.sub(r'\n[ \t]+\n', '\n\n', entry)
    
    # Write output
    output = open('/tmp/' + date, 'wt')
    print >>output, 'Date:', date
    if category:
        print >>output, category
    print >>output
    print >>output, entry
    output.close()

    
if __name__ == '__main__':
    #m = para_pat.match('<p><b>Wed Mar 12 2003</b>: Coming soon: <a href="/d2/">Diary 2.0</a>,')
#    print m and m.group()
    main()
