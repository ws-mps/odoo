# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import pyPdf
from lxml import etree
import zipfile

from StringIO import StringIO

from odoo import api, models

_logger = logging.getLogger(__name__)
FTYPES = ['docx', 'pptx', 'xlsx', 'opendoc', 'pdf']

# Keep function in case it is necessary to do toUnicode(buf.encode('ascii', 'replace'))
def toUnicode(s):
    try:
        return s.decode('utf-8')
    except UnicodeError:
        try:
            return s.decode('latin')
        except UnicodeError:
            try:
                return s.encode('ascii')
            except UnicodeError:
                return s


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _index_docx(self, bin_data):
        '''Index Microsoft .docx documents'''
        buf = u""
        f = StringIO(bin_data)
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        if zipfile.is_zipfile(f):
            try:
                zf = zipfile.ZipFile(f)
                content = etree.fromstring(zf.read('word/document.xml'))
                buf = u'\n'.join(u''.join(element.itertext())
                                 for val in ['.//w:p', './/w:h']
                                 for element in content.iterfind(val, namespaces=ns))
            except Exception:
                pass
        return buf

    def _index_pptx(self, bin_data):
        '''Index Microsoft .pptx documents'''

        buf = u""
        f = StringIO(bin_data)
        ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
        if zipfile.is_zipfile(f):
            try:
                zf = zipfile.ZipFile(f)
                zf_filelist = [x for x in zf.namelist() if x.startswith('ppt/slides/slide')]
                for i in range(1, len(zf_filelist) + 1):
                    content = etree.fromstring(zf.read('ppt/slides/slide%s.xml' % i))
                    buf = u'\n'.join(u''.join(element.itertext())
                                     for val in ['.//a:t']
                                     for element in content.iterfind(val, namespaces=ns))
            except Exception:
                pass
        return buf

    def _index_xlsx(self, bin_data):
        '''Index Microsoft .xlsx documents'''

        buf = u""
        f = StringIO(bin_data)
        ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        if zipfile.is_zipfile(f):
            try:
                zf = zipfile.ZipFile(f)
                content = etree.fromstring(zf.read('xl/sharedStrings.xml'))
                buf = u'\n'.join(u''.join(element.itertext())
                                 for val in ['.//s:t']
                                 for element in content.iterfind(val, namespaces=ns))
            except Exception:
                pass
        return buf

    def _index_opendoc(self, bin_data):
        '''Index OpenDocument documents (.odt, .ods...)'''

        buf = u""
        f = StringIO(bin_data)
        ns = {'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'}
        if zipfile.is_zipfile(f):
            try:
                zf = zipfile.ZipFile(f)
                content = etree.fromstring(zf.read('content.xml'))
                buf = u'\n'.join(u''.join(element.itertext())
                                 for val in ['.//text:p', './/text:h', './/text:list']
                                 for element in content.iterfind(val, namespaces=ns))
            except Exception:
                pass
        return buf

    def _index_pdf(self, bin_data):
        '''Index PDF documents'''

        buf = u""
        if bin_data.startswith('%PDF-'):
            f = StringIO(bin_data)
            try:
                pdf = pyPdf.PdfFileReader(f)
                for page in pdf.pages:
                    buf += page.extractText()
            except Exception:
                pass
        return buf

    @api.model
    def _index(self, bin_data, datas_fname, mimetype):
        for ftype in FTYPES:
            buf = getattr(self, '_index_%s' % ftype)(bin_data)
            if buf:
                return buf

        return super(IrAttachment, self)._index(bin_data, datas_fname, mimetype)
