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
    def __init__(self, filing_number, is_paper=False, base_url="http://docquery.fec.gov/dcdev/posted", local_copy=None):
        #local_copy is an absolute path to a local copy of the filing, useful for testing
        #or mucking around while offline.

        init(autoreset=True)
        print Style.BRIGHT + Fore.MAGENTA + "Getting filing " + Style.BRIGHT + Fore.YELLOW +  "%s" % filing_number
        self.document_base_url = base_url
        self.version = None
        self.filing_lines = []

        self.is_amendment = None
        self.amends_filing = None

        self.page_read = None
        self.headers = {}
        self.headers_list = []

        self.use_new_delimiter = True
        self.csv_reader = None

        self.filing_number = filing_number
        self.is_paper = is_paper
        self.headers['filing_number'] = filing_number
        if local_copy is None:
            self.local_file_location = "/tmp/%s.fec" % self.filing_number
        else:
            self.local_file_location = local_copy

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
        flat_filing = self.flatten_filing()
        if 'cycle_totals' in flat_filing:
            self.cycle_totals = flat_filing['cycle_totals']
            del flat_filing['cycle_totals']
        else:
            self.cycle_totals = {}
        self.flat_filing = flat_filing


    def get_filing(self):
        init(autoreset=True)
        if not os.path.isfile(self.local_file_location):
            print Style.BRIGHT + Fore.GREEN + " Downloading from the FEC."

            constructed_url = '{base_url}/{file_location}'.format(base_url=self.document_base_url, file_location=self.local_file_location.split('/')[-1])

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
        self.headers['amends_filing'] = None
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
                self.headers['amends_filing'] = None

            else:
                amendment_match = re.search('^FEC\s*-\s*(\d+)', self.headers['report_id'])
    
                if amendment_match:
                    original = amendment_match.group(1)
                    self.headers['amends_filing'] = original

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

        form_type = self.get_form_type().upper()
        
        if form_type in ['F3A', 'F3N', 'F3T', 'F3']:
            parsed_data = process_f3_header(summary)
        
        elif form_type in ['F3PA', 'F3PN', 'F3PT', 'F3P']:
            parsed_data = process_f3p_header(summary)
            
        elif form_type in ['F3X', 'F3XA', 'F3XN', 'F3XT']:
            parsed_data = process_f3x_header(summary)
        
        elif form_type in ['F5', 'F5A', 'F5N']:
            parsed_data = process_f5_header(summary)
                    
            try:
                self.is_f5_quarterly = summary['report_code'] in ['Q1', 'Q2', 'Q3', 'Q4', 'YE']
            except KeyError:
                # this is probably a problem. 
                pass

        elif form_type in ['F7', 'F7A', 'F7N']:
            parsed_data = process_f7_header(summary)        

        elif form_type in ['F9', 'F9A', 'F9N']:
            parsed_data = process_f9_header(summary)        
        
        elif form_type in ['F13', 'F13A', 'F13N']:
            parsed_data = process_f13_header(summary)

        elif form_type in ['F24', 'F99']:
            parsed_data = defaultdict(lambda:0)
                    
        else:
            raise NotImplementedError("Form %s processing not implemented" % self.get_form_type().upper())
        print summary
        parsed_data.update(self.headers)
        parsed_data['filing_id'] = int(self.filing_number)
        parsed_data['filing_number'] = self.filing_number
        parsed_data['filed_date'] = summary.get('date_signed')
        parsed_data['form_type'] = form_type
        parsed_data['coverage_from_date'] = summary.get('coverage_from_date')
        parsed_data['coverage_to_date'] = summary.get('coverage_through_date')
        parsed_data['committee_name'] = summary.get('committee_name')

        return(parsed_data)

def dateparse_notnull(datestring):
    """ dateparse returns today if given an empty string. Don't do that. """
    if datestring:
        datestring = datetime.strptime(datestring, '%Y%m%d')
    else:
        return None


def process_header(header_data, field_names):
    return_dict = defaultdict(lambda:0)
    totals_dict = defaultdict(lambda:0)

    for new_key, fec_key in field_names.items():
        current_val = header_data.get('col_a_'+fec_key)
        if current_val is not None:
            return_dict[new_key] = 0 if current_val == "" else current_val
        cycle_val = header_data.get('col_b_'+fec_key)
        if cycle_val is not None:
            totals_dict[new_key] = 0 if cycle_val == "" else cycle_val
    
    return_dict['cycle_totals'] = totals_dict

    return return_dict

def f3_common_fields():
    field_names = {
        'coh_end':'cash_on_hand_close_of_period',
        'total_receipts':'total_receipts',
        'total_disbursements':'total_disbursements',
        'new_loans':'total_loans',
        'total_contributions_indiv':'individual_contribution_total',

        'outstanding_debts':'debts_by',
        'total_contributions':'total_contributions',
        'total_unitemized_indiv':'individuals_unitemized',
        'total_itemized_indiv':'individuals_itemized',
        'operating_offsets':'operating',
        'fundraising_offsets':'fundraising',
        'legal_offsets':'legal_and_accounting',
        'total_offsets':'total_offset_to_operating_expenditures',
        
        'total_transfers_to_auth_comms':'transfers_to_other_authorized_committees',
        'total_fundraising_disbursements':'fundraising_disbursements',
        'total_exempt_legal_disbursements':'exempt_legal_accounting_disbursement',
        'total_loan_repayments':'total_loan_repayments_made',
        'total_transfers_from_auth_comms':'transfers_from_aff_other_party_cmttees',
        
        'other_disbursements':'other_disbursements',
        'objects_to_be_liquidated':'items_on_hand_to_be_liquidated',
        'total_parties':'political_party_committees'}

    return field_names

def process_f3x_header(header_data):
    field_names = {
        'total_ies':'independent_expenditures',
        'total_coordinated':'coordinated_expenditures_by_party_committees',
        'total_nonparty_comms':'other_political_committees_pacs',
        'total_loan_repayments_received':'total_loan_repayments_received',
        'other_federal_receipts':'other_federal_receipts',
        'transfers_from_nonfederal_h3':'transfers_from_nonfederal_h3',
        'levin_funds':'levin_funds',
        'total_nonfederal_transfers':'total_nonfederal_transfers',
        'total_federal_receipts':'total_federal_receipts',
        'shared_operating_expenditures_federal':'shared_operating_expenditures_federal',
        'shared_operating_expenditures_nonfederal':'shared_operating_expenditures_nonfederal',
        'other_federal_operating_expenditures':'other_federal_operating_expenditures',
        'total_operating_expenditures':'total_operating_expenditures',
        'transfers_to_affiliated':'transfers_to_affiliated',
        'contributions_to_candidates':'contributions_to_candidates',
        'independent_expenditures':'independent_expenditures',
        'coordinated_expenditures_by_party_committees':'coordinated_expenditures_by_party_committees',
        'loans_made':'loans_made',
        'refunds_to_individuals':'refunds_to_individuals',
        'refunds_to_parties':'refunds_to_party_committees',
        'refunds_to_nonparty_comms':'refunds_to_other_committees',
        'total_refunds':'total_refunds',
        'federal_refunds':'total_contributions_refunds',
        'federal_election_activity_federal_share':'federal_election_activity_federal_share',
        'federal_election_activity_levin_share':'federal_election_activity_levin_share',
        'federal_election_activity_all_federal':'federal_election_activity_all_federal',
        'federal_election_activity_total':'federal_election_activity_total',
        'total_federal_disbursements':'total_federal_disbursements',
        'total_federal_operating_expenditures':'total_federal_operating_expenditures'

        }

    field_names.update(f3_common_fields())
    
    return process_header(header_data, field_names)


def process_f3p_header(header_data):
    field_names = {
        'total_ies':'independent_expenditures',
        'total_coordinated':'coordinated_expenditures_by_party_committees',
        'total_parties':'political_party_committees',
        'total_nonparty_comms':'other_political_committees_pacs',
        'total_candidate':'the_candidate',
        'loans_from_candidate':'received_from_or_guaranteed_by_cand',
        'noncandidate_loans':'other_loans',
        'loan_repayments_by_candidate':'made_or_guaranteed_by_candidate',
        'noncandidate_loan_repayments':'other_repayments',
        'refunds_to_parties':'political_party_committees_refunds',
        'refunds_to_nonparty_comms':'other_political_committees',
        'refunds_to_individuals':'individuals',
        'total_operating_expenditures':'operating_expenditures',
        'total_refunds':'total_contributions_refunds',}

    field_names.update(f3_common_fields())

    return process_header(header_data, field_names)
 
def process_f3_header(header_data):

    field_names = f3_common_fields()

    return process_header(header_data, field_names)

    
def process_f5_header(header_data):
    # non-committee report of IE's
    return_dict= defaultdict(lambda:0)
    return_dict['total_receipts'] = header_data.get('total_contribution')
    return_dict['total_disbursements'] = header_data.get('total_independent_expenditure')  

    # This usually isn't reported, but... 
    return_dict['total_contributions'] = header_data.get('total_contribution')
    
    # sometimes the dates are missing--in this case make sure it's set to None--this will otherwise default to today.
    return_dict['coverage_from_date'] = dateparse_notnull(header_data.get('coverage_from_date'))
    return_dict['coverage_to_date'] =dateparse_notnull(header_data.get('coverage_through_date'))   
        
    return return_dict
    
def process_f7_header(header_data):
    # communication cost    
    return_dict= defaultdict(lambda:0)
    return_dict['total_disbursements'] = header_data.get('total_costs')    
    return_dict['coverage_from_date'] = dateparse_notnull(header_data.get('coverage_from_date'))
    return_dict['coverage_to_date'] =dateparse_notnull(header_data.get('coverage_through_date'))
    
    return return_dict

def process_f9_header(header_data):
    # electioneering 
    return_dict= defaultdict(lambda:0)
    return_dict['total_receipts'] = header_data.get('total_donations')
    return_dict['total_disbursements'] = header_data.get('total_disbursements')    
    return_dict['coverage_from_date'] = dateparse_notnull(header_data.get('coverage_from_date'))
    return_dict['coverage_to_date'] =dateparse_notnull(header_data.get('coverage_through_date'))
    
    # typically not reported... 
    return_dict['total_contributions'] = header_data.get('total_donations')
    
    return return_dict

def process_f13_header(header_data):
    # donations to inaugural committee
    return_dict= defaultdict(lambda:0)
    return_dict['total_receipts'] = header_data.get('net_donations')
    return_dict['coverage_from_date'] = dateparse_notnull(header_data.get('coverage_from_date'))
    return_dict['coverage_to_date'] =dateparse_notnull(header_data.get('coverage_through_date'))
    
    # This is greater than tot_raised because it's before the donations refunded... 
    return_dict['total_contributions'] = header_data.get('total_donations_accepted')
    return return_dict