import os
import re
import sys

from pyfec import form
from pyfec import filing
from pyfec import settings
from pyfec.utils.filing_body_processor import process_body_row

# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# sys.path.append(BASE_DIR)

fp = form.parser()
fec_format_file = re.compile(r'\d+\.fec')

# connection = get_connection()
# cursor = connection.cursor()

# logger=fec_logger()


# Process all .fec files in the FILECACHE_DIRECTORY
for d, _, files in os.walk(settings.FILECACHE_DIRECTORY):
    for this_file in files:
        
        # Ignore it if it isn't a numeric fec file, e.g. \d+\.fec
        if not fec_format_file.match(this_file):
            continue
        
        filingnum = this_file.replace(".fec", "")
        # cd = CSV_dumper(connection)
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
        
        print "Version is: %s" % (version)
        firstrow = fp.parse_form_line(f1.get_first_row(), version)    
        print "First row is: %s" % (firstrow)
    
        line_sequence = 0
        while True:
            line_sequence += 1
            row = f1.get_body_row()
            if not row:
                break
        
            try:
                linedict = fp.parse_form_line(row, version)
                
                
                # process_body_row(linedict, filingnum, line_sequence, f1.is_amendment, cd, filer_id)
                
                
                print linedict
            except form.ParserMissingError:
                msg = 'process_filing_body: Unknown line type in filing %s line %s: type=%s Skipping.' % (filingnum, linenum, row[0])
                continue
        
        # # commit all the leftovers
        # cd.commit_all()
        # cd.close()
        # counter = cd.get_counter()
        # total_rows = 0
        # for i in counter:
        #     total_rows += counter[i]

        # msg = "read_and_transform_FEC_dem: Filing # %s Total rows: %s Tally is: %s" % (filingnum, total_rows, counter)
        # # print msg
        # # logger.info(msg)
        # print msg
        