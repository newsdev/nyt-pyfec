"""
 This is a django-independent process to enter filing itemzations.
 The intent is for this to be run from a queue outside of django. 
 Because there's no database abstraction, there are a few db queries hardcoded
 The db connection uses the django settings, (see db_utils) it just shouldn't
 import all the django libraries.

"""

import time
import sys

from pyfec import filing
from pyfec.utils.form_mappers import *

# from write_csv_to_db import CSV_dumper

# from parsing.utils.fec_import_logging import fec_logger

# from db_utils import get_connection
verbose = True

## THIS SHOULD LIVE SOMEWHERE ELSE
CURRENT_CYCLE = '2016'

class FilingHeaderDoesNotExist(Exception):
    pass
    
class FilingHeaderAlreadyProcessed(Exception):
    pass


def process_body_row(linedict, filingnum, line_sequence, is_amended, cd, filer_id):
    form = linedict['form_parser']
    
    # this will be the arg passed to csv dumper: ('skedletter', datadict)
    result = None
    
    if form=='SchA':
        result = ['A', skeda_from_skedadict(linedict, filingnum, line_sequence, is_amended)]

    elif form=='SchB':
        result = ['B', skedb_from_skedbdict(linedict, filingnum, line_sequence, is_amended)]

    elif form=='SchE':
        result = ['E', skede_from_skededict(linedict, filingnum, line_sequence, is_amended)]

    # Treat 48-hour contribution notices like sked A.
    # Requires special handling for amendment, since these are superceded
    # by regular F3 forms. 
    elif form=='F65':
        result = ['A', skeda_from_f65(linedict, filingnum, line_sequence, is_amended)]

    # disclosed donor to non-commmittee. Sorta rare, but.. 
    elif form=='F56':
        result = ['A', skeda_from_f56(linedict, filingnum, line_sequence, is_amended)]

    # disclosed electioneering donor
    elif form=='F92':
        result = ['A', skeda_from_f92(linedict, filingnum, line_sequence, is_amended)]   

    # inaugural donors
    elif form=='F132':
        result = ['A', skeda_from_f132(linedict, filingnum, line_sequence, is_amended)]

    #inaugural refunds
    elif form=='F133':
        result = ['A', skeda_from_f133(linedict, filingnum, line_sequence, is_amended)]

    # IE's disclosed by non-committees. Note that they use this for * both * quarterly and 24- hour notices. There's not much consistency with this--be careful with superceding stuff. 
    elif form=='F57':
        result = ['E', skede_from_f57(linedict, filingnum, line_sequence, is_amended)]

    # Its another kind of line. Just dump it in Other lines.
    else:
        result = ['O', otherline_from_line(linedict, filingnum, line_sequence, is_amended, filer_id)]
    
    # write it to the db using csv to db (which will only actually write every 1,000 rows)    
    cd.writerow(result[0], result[1])

def process_filing_body(filingnum, fp=None, logger=None):
    
    
    #It's useful to pass the form parser in when running in bulk so we don't have to keep creating new ones. 
    if not fp:
      fp = form.parser()
      
    # if not logger:
    #     logger=fec_logger()
    msg = "process_filing_body: Starting # %s" % (filingnum)
    print msg
    # logger.info(msg)
      
    connection = get_connection()
    cursor = connection.cursor()
    cmd = "select fec_id, superseded_by_amendment, data_is_processed from efilings_filing where filing_number=%s" % (filingnum)
    cursor.execute(cmd)
    
    cd = CSV_dumper(connection)
    
    result = cursor.fetchone()
    if not result:
        msg = 'process_filing_body: Couldn\'t find a new_filing for filing %s' % (filingnum)
        print msg
        # logger.error(msg)
        raise FilingHeaderDoesNotExist(msg)
        
    # will throw a TypeError if it's missing.
    line_sequence = 1
    is_amended = result[1]
    is_already_processed = result[2]
    if is_already_processed == "1":
        msg = 'process_filing_body: This filing has already been entered.'
        print msg
        # logger.error(msg)
        raise FilingHeaderAlreadyProcessed(msg)
    
    #print "Processing filing %s" % (filingnum)
    f1 = filing.filing(filingnum)
    form = f1.get_form_type()
    version = f1.get_version()
    filer_id = f1.get_filer_id()
    
    # only parse forms that we're set up to read
    
    if not fp.is_allowed_form(form):
        if verbose:
            msg = "process_filing_body: Not a parseable form: %s - %s" % (form, filingnum)
            print msg
            # logger.info(msg)
        return None
        
    linenum = 0
    while True:
        linenum += 1
        row = f1.get_body_row()
        if not row:
            break
        
        #print "row is %s" % (row)
        #print "\n\n\nForm is %s" % form
        try:
            linedict = fp.parse_form_line(row, version)
            #print "\n\n\nform is %s" % form
            process_body_row(linedict, filingnum, line_sequence, is_amended, cd, filer_id)
        except form.ParserMissingError:
            msg = 'process_filing_body: Unknown line type in filing %s line %s: type=%s Skipping.' % (filingnum, linenum, row[0])
            print msg
            # logger.warn(msg)
            continue
        
    # commit all the leftovers
    cd.commit_all()
    cd.close()
    counter = cd.get_counter()
    total_rows = 0
    for i in counter:
        total_rows += counter[i]
        
    msg = "process_filing_body: Filing # %s Total rows: %s Tally is: %s" % (filingnum, total_rows, counter)
    print msg
    # logger.info(msg)
    
    # ######## DIRECT DB UPDATES. PROBABLY A BETTER APPROACH, BUT... 
    
    # header_data = dict_to_hstore(counter)
    # cmd = "update efilings_filing set lines_present='%s'::hstore where filing_number=%s" % (header_data, filingnum)
    # cursor.execute(cmd)
    
    # # mark file as having been entered. 
    # cmd = "update efilings_filing set data_is_processed='1' where filing_number=%s" % (filingnum)
    # cursor.execute(cmd)
    
    # # flag this filer as one who has changed. 
    # cmd = "update efilings_committee set is_dirty=True where fec_id='%s' and cycle='%s'" % (filer_id, CURRENT_CYCLE)
    # cursor.execute(cmd)
    
    # # should also update the candidate is dirty flag too by joining w/ ccl table. 
    # # these tables aren't indexed, so do as two separate queries. 
    # cmd = "select cand_id from ftpdata_candcomlink where cmte_id = '%s' and cmte_dsgn in ('A', 'P')" % (filer_id)
    # cursor.execute(cmd)
    # result = cursor.fetchone()
    # if result:
    #     cand_id = result[0]
    #     cmd = "update efilings_candidate set is_dirty=True where fec_id = '%s' and cycle='%s'" % (cand_id, CURRENT_CYCLE)
    #     cursor.execute(cmd)

    # connection.close()
    

"""
from parsing.utils.filing_body_processor import process_filing_body
process_filing_body(1022512)


for fn in [838168, 824988, 840327, 821325, 798883, 804867, 827978, 754317]:
    t0 = time.time()
    process_filing_body(fn, fp)
    t1 = time.time()
    print "total time to process filing %s=%s" ( fn, (t1-t0))

### Large historic filings to test with:
# 838168 (510 mb) - act blue - 2012-10-18         | 2012-11-26
# 824988 (217.3mb) - act blue - 2012-10-01         | 2012-10-17 - 874K lines
# 840327 - 169MB  C00431445 - OFA   | 2012-10-18         | 2012-11-26
# 821325 - 144 mb Obama for america 2012-09-01         | 2012-09-30
# 798883 - 141 mb
# 804867 - 127 mb
# 827978 - 119 mb
# 754317 - 118 mb

"""


