#!/usr/bin/env python3
# -*-Python-*-
#
# Contains the process_rst() function, which turns ReST files into
# HTML output that can be included in a page.
#

import io
from docutils import core
from docutils.writers import html4css1

class WeblogWriter (html4css1.Writer):
    def __init__ (self):
        super().__init__()
        self.translator_class = WeblogHTMLTranslator

class WeblogHTMLTranslator (html4css1.HTMLTranslator):
    doctype = ""
    generator = "<!-- %s -->"
    content_type = "<!-- %s -->"

    def __init__(self, document):
        super().__init__(document)
        self.head_prefix = []
        self.body_prefix = []
        self.stylesheet = []
        self.body_suffix = []
        self.section_level = 1

    def visit_system_message(self, node):
        pass

    def visit_document (self, node):
        pass

    def depart_document (self, node):
        pass


def process_rst (filename, body):
    "Parse 'body' as RST and convert it to HTML"
    output_file = io.StringIO()
    body = core.publish_string(
        reader_name='standalone',
        parser_name='restructuredtext',
        writer=WeblogWriter(),
        writer_name='html',
        source_path=filename,
        source=body,
        destination_path=filename,
        settings=None,
	settings_overrides={'input_encoding':'utf-8',
                            'output_encoding':'unicode'})

    return body
