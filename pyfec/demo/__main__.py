import os
import re
import sys

from pyfec import form
from pyfec import filing
from pyfec import settings
from pyfec.utils.filing_body_processor import process_body_row

fp = form.parser()
fec_format_file = re.compile(r'\d+\.fec')

payload = []

for d, _, files in os.walk(settings.FILECACHE_DIRECTORY):
    for this_file in files:
        
        if not fec_format_file.match(this_file):
            continue
        
        filingnum = this_file.replace(".fec", "")
        f1 = filing.filing(filingnum)
    
        formtype = f1.get_form_type()
        version = f1.version
        filer_id = f1.get_filer_id()

        print "Processing form number %s - type=%s version=%s is_amended: %s" % (f1.filing_number, formtype, version, f1.is_amendment)
        print "Headers are: %s" % f1.headers
    
        if f1.is_amendment:
            print "Original filing is: %s" % (f1.headers['filing_amended'])
    
    
        if not fp.is_allowed_form(formtype):
            print "skipping form %s - %s isn't parseable" % (f1.filing_number, formtype)
            continue

        firstrow = fp.parse_form_line(f1.get_first_row(), version)    

        print "Version is: %s" % (version)
        print "First row is: %s" % (firstrow)
    
        line_sequence = 0

        while True:
            line_sequence += 1
            row = f1.get_body_row()

            if not row:
                break

            try:
                linedict = fp.parse_form_line(row, version)
                payload.append(linedict)

            except form.ParserMissingError:
                msg = 'process_filing_body: Unknown line type in filing %s line %s: type=%s Skipping.' % (filingnum, linenum, row[0])
                print msg
                continue

print len(payload)
