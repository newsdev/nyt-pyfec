import csv
import os
import re

from colorama import Fore, Back, Style, init
import requests

from pyfec import header
from pyfec.utils.parsing_utils import utf8_clean, clean_entry


# Current FCC files are delimited by ascii 28.
# Electronic versions below 6 -- through 5.3 -- use a comma.
new_delimiter = chr(28)
old_delimiter = ','

old_headers = ['record_type', 'ef_type', 'fec_version', 'soft_name', 'soft_ver', 'name_delim', 'report_id', 'report_number']
new_headers = ['record_type', 'ef_type', 'fec_version', 'soft_name', 'soft_ver', 'report_id', 'report_number']
paper_headers_v1 = ['record_type', 'fec_version', 'vendor', 'batch_number']
paper_headers_v2_2 = ['record_type', 'fec_version', 'vendor', 'batch_number']
paper_headers_v1 = ['record_type', 'fec_version', 'vendor', 'batch_number', 'report_id']


class filing(object):
    """
    Represents a single filing.
    """

    def __init__(self, filing_number, is_paper=False):
        init(autoreset=True)
        print Style.BRIGHT + Fore.CYAN + "~~FILING CLASS~~"
        print Style.BRIGHT + Fore.MAGENTA + "Getting filing " + Style.BRIGHT + Fore.YELLOW +  "%s" % filing_number
        self.version = None
        self.filing_lines = []

        self.is_amendment = None
        self.filing_amended = None

        self.page_read = None
        self.headers = {}
        self.headers_list = []

        self.use_new_delimiter = True
        self.csv_reader = None

        self.filing_number = filing_number
        self.is_paper = is_paper
        self.headers['filing_number'] = filing_number
        self.local_file_location = "/tmp/%s.fec" % self.filing_number

        self.get_filing()

        self.fh = open(self.local_file_location, 'r')

        # The header row indicates what type of file this is.
        self.header_row = self.fh.readline()    

        # Check for a delimiter. 
        if self.header_row.find(new_delimiter) > -1:
            self.use_new_delimiter = True
            self.headers_list = new_headers
            self.fh.seek(0)
            
        else:
            self.use_new_delimiter = False
            self.headers_list = old_headers
            self.fh.seek(0)
            self.csv_reader = csv.reader(self.fh)
        
        self.is_error = not self.parse_headers()

    def get_filing(self):
        init(autoreset=True)
        if not os.path.isfile(self.local_file_location):
            print Style.BRIGHT + Fore.GREEN + " Downloading from the FEC."
            r = requests.get('http://docquery.fec.gov/comma/%s' % self.local_file_location.split('/')[-1].split('.fec')[0])
            with open('/tmp/%s' % filename, 'w') as writefile:
                writefile.write(r.content)
        else:
            print Style.BRIGHT + Fore.GREEN + " Found local copy."

    def get_next_fields(self):
        if self.use_new_delimiter:
            nextline = self.fh.readline()

            if nextline:
                return [utf8_clean(i) for i in nextline.split(new_delimiter)]

            else:
                return None
        else:
            try:
                return [utf8_clean(i) for i in self.csv_reader.next()]

            except StopIteration:
                return None

    def parse_headers(self):

        header_arr = self.get_next_fields()
        summary_line = self.get_next_fields()
        self.form_row = summary_line

        self.headers = header.parse(header_arr, self.is_paper)
        self.headers['filing_amended'] = None
        self.headers['report_num'] = None
        self.version = self.headers['fec_version']

        try:
            self.headers['form'] = clean_entry(summary_line[0])
            self.headers['fec_id'] = clean_entry(summary_line[1])

        except IndexError:
            return False

        # Amendment discovery.
        # Identify if this is an amemndment to a filing.
        # If so, identify which filing it amends.        
        form_last_char = self.headers['form'][-1].upper()

        if form_last_char == 'A':
            self.is_amendment = True
            self.headers['is_amendment'] = self.is_amendment
            
            if self.is_paper:
                self.headers['filing_amended'] = None

            else:
                # Listing the original only works for electonic filings, of course!
                print "Found amendment %s : %s " % (self.filing_number, self.headers['report_id'])
                amendment_match = re.search('^FEC\s*-\s*(\d+)', self.headers['report_id'])
    
                if amendment_match:
                    original = amendment_match.group(1)
                    self.headers['filing_amended'] = original

                else:
                    raise Exception("Can't find original filing in amended report %s" % (self.filing_number))
        else:
            self.is_amendment = False
            self.headers['is_amendment'] = self.is_amendment

        return True

    def get_headers(self):
        """ Get a dictionary of file data. """
        return self.headers

    def get_error(self):
        """ Was there an error? """
        return self.is_error

    def get_first_row(self):
        return(self.form_row)

    def get_raw_first_row(self):
        """ Deprecated. """
        return(self.form_row)
    
    def get_filer_id(self):
        return self.headers['fec_id']

    def get_body_row(self):
        """ Get the next body row. """
        next_line = ''

        while True:
            next_line = self.get_next_fields()

            if next_line:

                if "".join(next_line).isspace():
                    continue

                else:
                    return next_line

            else:
                break

    def get_form_type(self):
        """
        Get the base form.
        Removes the A, N or T (amended, new, termination) designations.
        """
        try:
            raw_form_type = self.headers['form']
            a = re.search('(.*?)[A|N|T]', raw_form_type)

            if (a):
                return a.group(1)
            else:
                return raw_form_type

        except KeyError:
            return None

    def get_version(self):
        try:
            return self.version

        except KeyError:
            return None

    def dump_details(self):
        print "filing_number: %s ; self.headers: %s" % (self.filing_number, self.headers)
