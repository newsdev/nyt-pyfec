import csv
import os
import re

from colorama import Fore, Back, Style, init
import requests
from collections import defaultdict
from datetime import datetime

from pyfec import header
from pyfec import form
from pyfec.utils import utf8_clean, clean_entry
from pyfec import utils


# Current FCC files are delimited by ascii 28.
# Electronic versions below 6 -- through 5.3 -- use a comma.
new_delimiter = chr(28)
old_delimiter = ','

old_headers = ['record_type', 'ef_type', 'fec_version', 'soft_name', 'soft_ver', 'name_delim', 'report_id', 'report_number']
new_headers = ['record_type', 'ef_type', 'fec_version', 'soft_name', 'soft_ver', 'report_id', 'report_number']
paper_headers_v1 = ['record_type', 'fec_version', 'vendor', 'batch_number']
paper_headers_v2_2 = ['record_type', 'fec_version', 'vendor', 'batch_number']
paper_headers_v1 = ['record_type', 'fec_version', 'vendor', 'batch_number', 'report_id']


class Filing(object):
    """
    Represents a single filing.
    """
    def __init__(self, filing_number, is_paper=False):
        init(autoreset=True)
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
        self.flat_filing = self.flatten_filing()

    def get_filing(self):
        init(autoreset=True)
        if not os.path.isfile(self.local_file_location):
            print Style.BRIGHT + Fore.GREEN + " Downloading from the FEC."

            constructed_url = 'http://docquery.fec.gov/dcdev/posted/%s' % self.local_file_location.split('/')[-1]

            r = requests.get(constructed_url)

            if r.status_code == 200:
                with open(self.local_file_location, 'w') as writefile:
                    writefile.write(r.content)
            else:
                raise utils.PyFecException(Style.BRIGHT + Fore.RED + " %s error: Can't download %s. " % (r.status_code, constructed_url))

        else:
            print Style.BRIGHT + Fore.GREEN + " Using local copy."

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

    def flatten_filing(self):
        """Create a one-level dict with info needed to create a campfin filing obj"""
        fp = form.Form()

        if not fp.is_allowed_form(self.get_form_type()):
            return {}

        summary = fp.parse_form_line(self.form_row, self.version)
        
        if self.get_form_type().upper() in ['F3A', 'F3N', 'F3T', 'F3']:
            parsed_data = process_f3_header(summary)
        
        elif self.get_form_type().upper() in ['F3PA', 'F3PN', 'F3PT', 'F3P']:
            parsed_data = process_f3p_header(summary)
            
        elif self.get_form_type().upper() in ['F3X', 'F3XA', 'F3XN', 'F3XT']:
            parsed_data = process_f3x_header(summary)
        
        elif self.get_form_type().upper() in ['F5', 'F5A', 'F5N']:
            parsed_data = process_f5_header(summary)
                    
            try:
                self.is_f5_quarterly = summary['report_code'] in ['Q1', 'Q2', 'Q3', 'Q4', 'YE']
            except KeyError:
                # this is probably a problem. 
                pass

        elif self.get_form_type().upper() in ['F7', 'F7A', 'F7N']:
            parsed_data = process_f7_header(summary)        

        elif self.get_form_type().upper() in ['F9', 'F9A', 'F9N']:
            parsed_data = process_f9_header(summary)        
        
        elif self.get_form_type().upper() in ['F13', 'F13A', 'F13N']:
            parsed_data = process_f13_header(summary)
                    
        else:
            raise NotImplementedError("Form %s processing not implemented" % self.get_form_type().upper())
        parsed_data.update(self.headers)
        parsed_data['filing_id'] = int(self.filing_number)
        parsed_data['filing_number'] = self.filing_number
        return(parsed_data)

def dateparse_notnull(datestring):
    """ dateparse returns today if given an empty string. Don't do that. """
    if datestring:
        datestring = datetime.strptime(datestring, '%Y%m%d')
    else:
        return None

def process_f3x_header(header_data):
    return_dict = defaultdict(lambda:0)
    return_dict['coh_end'] = header_data.get('col_a_cash_on_hand_close_of_period')
    return_dict['tot_raised'] = header_data.get('col_a_total_receipts')
    return_dict['tot_spent'] = header_data.get('col_a_total_disbursements')
    return_dict['new_loans'] = header_data.get('col_a_total_loans')
    return_dict['tot_ies'] = header_data.get('col_a_independent_expenditures')
    return_dict['tot_coordinated'] = header_data.get('col_a_coordinated_expenditures_by_party_committees')
    
    return_dict['outstanding_loans'] = header_data.get('col_a_debts_by')
    return_dict['tot_contribs'] = header_data.get('col_a_total_contributions')
    return_dict['tot_ite_contribs_indivs'] = header_data.get('col_a_individuals_itemized')
    return_dict['tot_non_ite_contribs_indivs'] = header_data.get('col_a_individuals_unitemized')
    
    return return_dict

def process_f3p_header(header_data):
    return_dict = defaultdict(lambda:0)
    return_dict['coh_end'] = header_data.get('col_a_cash_on_hand_close_of_period')
    return_dict['tot_raised'] = header_data.get('col_a_total_receipts')
    return_dict['tot_spent'] = header_data.get('col_a_total_disbursements')
    return_dict['new_loans'] = header_data.get('col_a_total_loans')
    return_dict['tot_ies'] = header_data.get('col_a_independent_expenditures')
    return_dict['tot_coordinated'] = header_data.get('col_a_coordinated_expenditures_by_party_committees')

    return_dict['outstanding_loans'] = header_data.get('col_a_debts_by')
    return_dict['tot_contribs'] = header_data.get('col_a_total_contributions')
    return_dict['tot_ite_contribs_indivs'] = header_data.get('col_a_individuals_itemized')
    return_dict['tot_non_ite_contribs_indivs'] = header_data.get('col_a_individuals_unitemized')
    
    return return_dict
 
def process_f3_header(header_data):
    return_dict = defaultdict(lambda:0)
    return_dict['coh_end'] = header_data.get('col_a_cash_on_hand_close_of_period')
    return_dict['tot_raised'] = header_data.get('col_a_total_receipts')
    return_dict['tot_spent'] = header_data.get('col_a_total_disbursements')
    return_dict['new_loans'] = header_data.get('col_a_total_loans')
    
    return_dict['outstanding_loans'] = header_data.get('col_a_debts_by')
    return_dict['tot_contribs'] = header_data.get('col_a_total_contributions')
    return_dict['tot_ite_contribs_indivs'] = header_data.get('col_a_individual_contributions_itemized')
    return_dict['tot_non_ite_contribs_indivs'] = header_data.get('col_a_individual_contributions_unitemized')
    
    return return_dict
    
def process_f5_header(header_data):
    # non-committee report of IE's
    return_dict= defaultdict(lambda:0)
    return_dict['tot_raised'] = header_data.get('total_contribution')
    return_dict['tot_spent'] = header_data.get('total_independent_expenditure')  

    # This usually isn't reported, but... 
    return_dict['tot_contribs'] = header_data.get('total_contribution')
    
    # sometimes the dates are missing--in this case make sure it's set to None--this will otherwise default to today.
    return_dict['coverage_from_date'] = dateparse_notnull(header_data.get('coverage_from_date'))
    return_dict['coverage_to_date'] =dateparse_notnull(header_data.get('coverage_through_date'))   
        
    return return_dict
    
def process_f7_header(header_data):
    # communication cost    
    return_dict= defaultdict(lambda:0)
    return_dict['tot_spent'] = header_data.get('total_costs')    
    return_dict['coverage_from_date'] = dateparse_notnull(header_data.get('coverage_from_date'))
    return_dict['coverage_to_date'] =dateparse_notnull(header_data.get('coverage_through_date'))
    
    return return_dict

def process_f9_header(header_data):
    # electioneering 
    return_dict= defaultdict(lambda:0)
    return_dict['tot_raised'] = header_data.get('total_donations')
    return_dict['tot_spent'] = header_data.get('total_disbursements')    
    return_dict['coverage_from_date'] = dateparse_notnull(header_data.get('coverage_from_date'))
    return_dict['coverage_to_date'] =dateparse_notnull(header_data.get('coverage_through_date'))
    
    # typically not reported... 
    return_dict['tot_contribs'] = header_data.get('total_donations')
    
    return return_dict

def process_f13_header(header_data):
    # donations to inaugural committee
    return_dict= defaultdict(lambda:0)
    return_dict['tot_raised'] = header_data.get('net_donations')
    return_dict['coverage_from_date'] = dateparse_notnull(header_data.get('coverage_from_date'))
    return_dict['coverage_to_date'] =dateparse_notnull(header_data.get('coverage_through_date'))
    
    # This is greater than tot_raised because it's before the donations refunded... 
    return_dict['tot_contribs'] = header_data.get('total_donations_accepted')
    return return_dict