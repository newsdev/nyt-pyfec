from cStringIO import StringIO
import csv
import datetime

# this must match formdata.db_worker_settings : FIELDDIR_LOCATION
# the variable is set by the formdata/management/commands/generate_field_name_list.py
# the assumption here is that this is being executed from this directory
from pyfec import utils

# need  a settings place

TRANSACTION_MAX_ROWS = 1000

class CSV_dumper(object):
    """ Helper class to aggregate electronic filing data rows, which can then be loaded w/ raw postgres 'copy...' in a single transaction block. Because we're using cStringIO we can't both read and write--once we get the value from the StringIO we're done. """
    
    def _get_writer(self, stringio, fields):
        writer = csv.DictWriter(stringio, fields, restval="", extrasaction='ignore', lineterminator='\n', delimiter="|", quoting=csv.QUOTE_NONE, quotechar='', escapechar='')
        return writer
    
    def __init__(self, connection):
        # do we want to use the filing number to leave breadcrumbs ? Probably not, but...
        
        now = datetime.datetime.now()
        formatted_time = now.strftime("%Y%m%d_%H%M")
        connection.set_isolation_level(0)
        self.cursor = connection.cursor()
        self.fields = utils.fields
        self.writers = {}
        self.counter = {}
        for sked in ['A', 'B', 'E', 'O']:
            self.writers[sked] = {}
            self.writers[sked]['stringio'] = StringIO()
            # hack to make csv use pipes as delimiters and not escape quote chars. We need to use quote chars to create the hstores for postgres, so... 
            self.writers[sked]['writer'] = self._get_writer(self.writers[sked]['stringio'], self.fields[sked])
            self.counter[sked] = 0
        
    def _get_db_name(self, sked):
        # just for testing -- don't actually use this in normal operation # 

        db_name = "efilings_otherline"
        if sked in (['A', 'B', 'E']):
            db_name = "efilings_sked%s" % (sked.lower())
        return db_name
    
    def _commit_rows(self, sked):
        print "\nCommitting sked %s with length %s" % (sked, self.counter[sked]) 

        # mark the end of the data
        self.writers[sked]['stringio'].write("\\.\n")
        
        ## commit here
        
        length = self.writers[sked]['stringio'].tell()
        self.writers[sked]['stringio'].seek(0)
        dbname = self._get_db_name(sked)
        self.cursor.copy_from(self.writers[sked]['stringio'], dbname, sep='|', size=length, columns=self.fields[sked], null="")
        

        
        print "Commit completed."
        ## We're done, now clear the var
        self.writers[sked]['stringio'].close()
        self.writers[sked]['stringio'] = StringIO()
        self.writers[sked]['writer'] = self._get_writer(self.writers[sked]['stringio'], self.fields[sked])
    
    def writerow(self, sked, dictrow):
        self.counter[sked] = self.counter[sked] + 1
        #print "Writing row %s with counter set to %s" % (sked, self.counter[sked])
        #print "Row is %s" % dictrow
        thiswriter = self.writers[sked]['writer']
        thiswriter.writerow(dictrow)
        
        if self.counter[sked] % TRANSACTION_MAX_ROWS == 0:
            self._commit_rows(sked)
        
        return 1
    
    def get_counter(self):
        return self.counter
    
        

    def _get_sql_data(self, sked):
        return self.writers[sked]['stringio'].getvalue()
        

    def commit_all(self):
        for sked in ['A', 'B', 'E', 'O']:
            if self.counter[sked] > 0:
                self._commit_rows(sked)
    
    def close(self):
        for sked in ['A', 'B', 'E', 'O']:
            self.writers[sked]['stringio'].close()
            



"""
from formdata.utils.write_csv_to_db import CSV_dumper
d = CSV_dumper()

data = {'filing_number':23}
d.writerow('E', datadict)
d.get_rowdata('E')
"""
