import csv
import os
import re
import sys

from colorama import Fore, Back, Style, init
import requests
from collections import defaultdict
from datetime import datetime

import pycurl

from pyfec import header
from pyfec import form
from pyfec.utils import utf8_clean, clean_entry
from pyfec import utils
from pyfec import output_headers


# Current FCC files are delimited by ascii 28.
# Electronic versions below 6 -- through 5.3 -- use a comma.
new_delimiter = chr(28)
old_delimiter = ','

class Filing(object):
    """
    Represents a single filing.
    """

    def __init__(self, filing_id, is_paper=False, base_url="http://docquery.fec.gov/dcdev/posted", local_copy=None):
        #local_copy is an absolute path to a local copy of the filing, useful for testing
        #or mucking around while offline.

        init(autoreset=True)
        print(Style.BRIGHT + Fore.MAGENTA + "Getting filing " + Style.BRIGHT + Fore.YELLOW +  "%s" % filing_id)
        self.document_base_url = base_url
        self.filing_lines = []

        #self.headers = {}

        self.use_new_delimiter = True
        self.csv_reader = None

        self.filing_id = filing_id
        self.is_paper = is_paper

        #self.headers['filing_id'] = filing_id
        
        if local_copy is None:
            self.local_file_location = "/tmp/%s.fec" % self.filing_id
        else:
            self.local_file_location = local_copy

        #download the filing
        self.get_filing()
        self.fh = open(self.local_file_location, 'r')

        # The header row indicates what type of file this is.
        self.header_row = self.fh.readline()

        #make sure it's not so old we don't know what to do with it
        if self.header_row.startswith('/*'):
            raise NotImplementedError("Form is very old and header type is depricated.")

        # Check for a delimiter.
        if self.header_row.find(new_delimiter) > -1:
            self.use_new_delimiter = True
            #self.headers_list = new_headers
            self.fh.seek(0)
            
        else:
            self.use_new_delimiter = False
            #self.headers_list = old_headers
            self.fh.seek(0)
            self.csv_reader = csv.reader(self.fh)
        
        self.is_error = not self.parse_headers()
        self.fields = self.get_form_fields()


    def get_filing(self):
        init(autoreset=True)
        if not os.path.isfile(self.local_file_location):
            print(Style.BRIGHT + Fore.GREEN + " Downloading from the FEC.")

            constructed_url = '{base_url}/{file_location}'.format(base_url=self.document_base_url, file_location=self.local_file_location.split('/')[-1])
            
            with open(self.local_file_location, 'wb') as f:
                c = pycurl.Curl()
                c.setopt(c.URL, constructed_url)
                c.setopt(c.WRITEDATA, f)
                c.perform()
                c.close()

        else:
            print(Style.BRIGHT + Fore.GREEN + " Using local copy.")

    def get_next_fields(self):
        if self.use_new_delimiter:
            nextline = self.fh.readline()

            if nextline:
                return nextline.split(new_delimiter)

            else:
                return None
        else:
            try:
                return next(self.csv_reader)

            except StopIteration:
                return None

    def parse_headers(self):

        header_arr = self.get_next_fields()
        summary_line = self.get_next_fields()
        self.form_row = summary_line

        common_form_headers = header.parse(header_arr, self.is_paper)

        self.amends_filing = None
        self.version = common_form_headers.get('fec_version')

        try:
            self.form = clean_entry(summary_line[0])
            self.fec_id = clean_entry(summary_line[1])

        except IndexError:
            return False


        # Amendment discovery.
        # Identify if this is an amemndment to a filing.
        # If so, identify which filing it amends.        
        form_last_char = self.form[-1].upper()

        if form_last_char == 'A':
            self.is_amendment = True
            
            if self.is_paper:
                self.amends_filing = None

            else:
                amendment_match = re.search('^FEC\s*-\s*(\d+)', common_form_headers['report_id'])
    
                if amendment_match:
                    original = amendment_match.group(1)
                    self.amends_filing = original

                else:
                    raise Exception("Can't find original filing in amended report %s" % (self.filing_id))
        else:
            self.is_amendment = False

        self.soft_name = common_form_headers.get('soft_name')
        self.soft_ver = common_form_headers.get('soft_ver')
        self.report_number = common_form_headers.get('report_number')
        self.ef_type = common_form_headers.get('ef_type')
        self.record_type = common_form_headers.get('record_type')

        return True

    def get_headers(self):
        """ Get a dictionary of file data. """
        return self.fields.keys()

    def get_error(self):
        """ Was there an error? """
        return self.is_error

    def get_first_row(self):
        return(self.form_row)

    def get_raw_first_row(self):
        """ Deprecated. """
        return(self.form_row)
    
    def get_filer_id(self):
        return self.fec_id

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
            raw_form_type = self.form
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
        print("filing_id: %s ; self.headers: %s" % (self.filing_id, self.headers))

    def get_form_fields(self):
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

        elif form_type in ['F24', 'F24A', 'F24N', 'F6', 'F6A', 'F6N', 'F99', 'F3L']:
            parsed_data = defaultdict(lambda:0)
                    
        else:
            raise NotImplementedError("Form %s processing not implemented" % self.get_form_type().upper())

        #parsed_data.update(self.headers)
        parsed_data['filing_id'] = int(self.filing_id)
        parsed_data['fec_id'] = self.fec_id
        parsed_data['is_amendment'] = self.is_amendment
        parsed_data['amends_filing'] = self.amends_filing
        parsed_data['filed_date'] = summary.get('date_signed')
        parsed_data['form_type'] = form_type
        parsed_data['coverage_from_date'] = summary.get('coverage_from_date')
        parsed_data['coverage_to_date'] = summary.get('coverage_through_date')
        parsed_data['election_date'] = summary.get('election_date')
        parsed_data['committee_name'] = summary.get('committee_name')
        if not parsed_data['committee_name']:
            parsed_data['committee_name'] = summary.get('organization_name')

        return(parsed_data)

    def write_filing(self):
        #write the filing's summary info
        fieldnames = output_headers.filing_headers
        writer = csv.DictWriter(sys.stdout, fieldnames)
        writer.writeheader()
        writer.writerow(self.fields)


    def write_skeda(self):
        #write sked a's to a csv
        #note that superseded_by_amendment, covered_by_periodic and obsolete are always going to be false
        #these are fields the loader needs in the db and computes later based on other filings
        pass

    def write_skedb(self):
        #write sked a's to a csv
        #note that superseded_by_amendment, covered_by_periodic and obsolete are always going to be false
        #these are fields the loader needs in the db and computes later based on other filings
        pass

    def write_skede(self):
        #write sked a's to a csv
        #note that superseded_by_amendment, covered_by_periodic and obsolete are always going to be false
        #these are fields the loader needs in the db and computes later based on other filings
        pass

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
        current_val = header_data.get(fec_key)
        return_dict[new_key] = 0 if current_val == "" else current_val
    return return_dict

def f3_common_fields():
    field_names = {
        #fields that have no reasonable cycle value (these tend to be snapshots)
        'coh_end':'col_a_cash_on_hand_close_of_period',
        'outstanding_debts':'debts_by',
        'election_date':'election_date',
        'objects_to_be_liquidated':'col_a_items_on_hand_to_be_liquidated',

        #period values for fields
        'period_total_receipts':'col_a_total_receipts',
        'period_total_disbursements':'col_a_total_disbursements',
        'period_total_loans_received':'col_a_total_loans_received',
        'period_total_contributions_indiv':'col_a_individual_contribution_total',
        'period_total_contributions':'col_a_total_contributions',
        'period_total_unitemized_indiv':'col_a_individuals_unitemized',
        'period_total_itemized_indiv':'col_a_individuals_itemized',
        'period_operating_offsets':'col_a_operating',
        'period_fundraising_offsets':'col_a_fundraising',
        'period_legal_offsets':'col_a_legal_and_accounting',
        'period_total_offsets':'col_a_total_offset_to_operating_expenditures',
        'period_total_transfers_to_auth_comms':'col_a_transfers_to_other_authorized_committees',
        'period_total_fundraising_disbursements':'col_a_fundraising_disbursements',
        'period_total_exempt_legal_disbursements':'col_a_exempt_legal_accounting_disbursement',
        'period_total_loan_repayments':'col_a_total_loan_repayments_made',
        'period_total_transfers_from_auth_comms':'col_a_transfers_from_aff_other_party_cmttees',
        'period_other_disbursements':'col_a_other_disbursements',
        'period_total_parties':'col_a_political_party_contributions',
        
        #cycle values for fields (should have corresponding period value)
        'cycle_total_receipts':'col_b_total_receipts',
        'cycle_total_disbursements':'col_b_total_disbursements',
        'cycle_total_loans_received':'col_b_total_loans_received',
        'cycle_total_contributions_indiv':'col_b_individual_contribution_total',
        'cycle_total_contributions':'col_b_total_contributions',
        'cycle_total_unitemized_indiv':'col_b_individuals_unitemized',
        'cycle_total_itemized_indiv':'col_b_individuals_itemized',
        'cycle_operating_offsets':'col_b_operating',
        'cycle_fundraising_offsets':'col_b_fundraising',
        'cycle_legal_offsets':'col_b_legal_and_accounting',
        'cycle_total_offsets':'col_b_total_offset_to_operating_expenditures',
        'cycle_total_transfers_to_auth_comms':'col_b_transfers_to_other_authorized_committees',
        'cycle_total_fundraising_disbursements':'col_b_fundraising_disbursements',
        'cycle_total_exempt_legal_disbursements':'col_b_exempt_legal_accounting_disbursement',
        'cycle_total_loan_repayments':'col_b_total_loan_repayments_made',
        'cycle_total_transfers_from_auth_comms':'col_b_transfers_from_aff_other_party_cmttees',
        'cycle_other_disbursements':'col_b_other_disbursements',
        'cycle_total_parties':'col_b_political_party_contributions',
        }

    return field_names

def process_f3x_header(header_data):
    field_names = {
        #period totals
        'period_total_ies':'col_a_independent_expenditures',
        'period_total_coordinated':'col_a_coordinated_expenditures_by_party_committees',
        'period_total_nonparty_comms':'col_a_other_political_committees_pacs',
        'period_total_loan_repayments_received':'col_a_total_loan_repayments_received',
        'period_other_federal_receipts':'col_a_other_federal_receipts',
        'period_transfers_from_nonfederal_h3':'col_a_transfers_from_nonfederal_h3',
        'period_levin_funds':'col_a_levin_funds',
        'period_total_nonfederal_transfers':'col_a_total_nonfederal_transfers',
        'period_total_federal_receipts':'col_a_total_federal_receipts',
        'period_shared_operating_expenditures_federal':'col_a_shared_operating_expenditures_federal',
        'period_shared_operating_expenditures_nonfederal':'col_a_shared_operating_expenditures_nonfederal',
        'period_other_federal_operating_expenditures':'col_a_other_federal_operating_expenditures',
        'period_total_operating_expenditures':'col_a_total_operating_expenditures',
        'period_transfers_to_affiliated':'col_a_transfers_to_affiliated',
        'period_contributions_to_candidates':'col_a_contributions_to_candidates',
        'period_independent_expenditures':'col_a_independent_expenditures',
        'period_coordinated_expenditures_by_party_committees':'col_a_coordinated_expenditures_by_party_committees',
        'period_loans_made':'col_a_loans_made',
        'period_refunds_to_individuals':'col_a_refunds_to_individuals',
        'period_refunds_to_parties':'col_a_refunds_to_party_committees',
        'period_refunds_to_nonparty_comms':'col_a_refunds_to_other_committees',
        'period_total_refunds':'col_a_total_refunds',
        'period_federal_refunds':'col_a_total_contributions_refunds',
        'period_federal_election_activity_federal_share':'col_a_federal_election_activity_federal_share',
        'period_federal_election_activity_levin_share':'col_a_federal_election_activity_levin_share',
        'period_federal_election_activity_all_federal':'col_a_federal_election_activity_all_federal',
        'period_federal_election_activity_total':'col_a_federal_election_activity_total',
        'period_total_federal_disbursements':'col_a_total_federal_disbursements',
        'period_total_federal_operating_expenditures':'col_a_total_federal_operating_expenditures',

        #cycle totals
        'cycle_total_ies':'col_b_independent_expenditures',
        'cycle_total_coordinated':'col_b_coordinated_expenditures_by_party_committees',
        'cycle_total_nonparty_comms':'col_b_other_political_committees_pacs',
        'cycle_total_loan_repayments_received':'col_b_total_loan_repayments_received',
        'cycle_other_federal_receipts':'col_b_other_federal_receipts',
        'cycle_transfers_from_nonfederal_h3':'col_b_transfers_from_nonfederal_h3',
        'cycle_levin_funds':'col_b_levin_funds',
        'cycle_total_nonfederal_transfers':'col_b_total_nonfederal_transfers',
        'cycle_total_federal_receipts':'col_b_total_federal_receipts',
        'cycle_shared_operating_expenditures_federal':'col_b_shared_operating_expenditures_federal',
        'cycle_shared_operating_expenditures_nonfederal':'col_b_shared_operating_expenditures_nonfederal',
        'cycle_other_federal_operating_expenditures':'col_b_other_federal_operating_expenditures',
        'cycle_total_operating_expenditures':'col_b_total_operating_expenditures',
        'cycle_transfers_to_affiliated':'col_b_transfers_to_affiliated',
        'cycle_contributions_to_candidates':'col_b_contributions_to_candidates',
        'cycle_independent_expenditures':'col_b_independent_expenditures',
        'cycle_coordinated_expenditures_by_party_committees':'col_b_coordinated_expenditures_by_party_committees',
        'cycle_loans_made':'col_b_loans_made',
        'cycle_refunds_to_individuals':'col_b_refunds_to_individuals',
        'cycle_refunds_to_parties':'col_b_refunds_to_party_committees',
        'cycle_refunds_to_nonparty_comms':'col_b_refunds_to_other_committees',
        'cycle_total_refunds':'col_b_total_refunds',
        'cycle_federal_refunds':'col_b_total_contributions_refunds',
        'cycle_federal_election_activity_federal_share':'col_b_federal_election_activity_federal_share',
        'cycle_federal_election_activity_levin_share':'col_b_federal_election_activity_levin_share',
        'cycle_federal_election_activity_all_federal':'col_b_federal_election_activity_all_federal',
        'cycle_federal_election_activity_total':'col_b_federal_election_activity_total',
        'cycle_total_federal_disbursements':'col_b_total_federal_disbursements',
        'cycle_total_federal_operating_expenditures':'col_b_total_federal_operating_expenditures',

        }

    field_names.update(f3_common_fields())
    
    return process_header(header_data, field_names)


def process_f3p_header(header_data):
    field_names = {
        #period totals
        'period_total_ies':'col_a_independent_expenditures',
        'period_total_coordinated':'col_a_coordinated_expenditures_by_party_committees',
        'period_total_parties':'col_a_political_party_committees',
        'period_total_nonparty_comms':'col_a_other_political_committees_pacs',
        'period_total_candidate':'col_a_the_candidate',
        'period_loans_from_candidate':'col_a_received_from_or_guaranteed_by_cand',
        'period_noncandidate_loans':'col_a_other_loans',
        'period_loan_repayments_by_candidate':'col_a_made_or_guaranteed_by_candidate',
        'period_noncandidate_loan_repayments':'col_a_other_repayments',
        'period_refunds_to_parties':'col_a_political_party_committees_refunds',
        'period_refunds_to_nonparty_comms':'col_a_other_political_committees',
        'period_refunds_to_individuals':'col_a_individuals',
        'period_total_operating_expenditures':'col_a_operating_expenditures',
        'period_total_refunds':'col_a_total_contributions_refunds',

        #cycle totals
        'cycle_total_ies':'col_b_independent_expenditures',
        'cycle_total_coordinated':'col_b_coordinated_expenditures_by_party_committees',
        'cycle_total_parties':'col_b_political_party_committees',
        'cycle_total_nonparty_comms':'col_b_other_political_committees_pacs',
        'cycle_total_candidate':'col_b_the_candidate',
        'cycle_loans_from_candidate':'col_b_received_from_or_guaranteed_by_cand',
        'cycle_noncandidate_loans':'col_b_other_loans',
        'cycle_loan_repayments_by_candidate':'col_b_made_or_guaranteed_by_candidate',
        'cycle_noncandidate_loan_repayments':'col_b_other_repayments',
        'cycle_refunds_to_parties':'col_b_political_party_committees_refunds',
        'cycle_refunds_to_nonparty_comms':'col_b_other_political_committees',
        'cycle_refunds_to_individuals':'col_b_individuals',
        'cycle_total_operating_expenditures':'col_b_operating_expenditures',
        'cycle_total_refunds':'col_b_total_contributions_refunds',
        }

    field_names.update(f3_common_fields())

    return process_header(header_data, field_names)
 
def process_f3_header(header_data):

    field_names = f3_common_fields()

    return process_header(header_data, field_names)

    
def process_f5_header(header_data):
    # non-committee report of IE's
    return_dict= defaultdict(lambda:0)
    return_dict['period_total_receipts'] = header_data.get('total_contribution')
    return_dict['total_disbursements'] = header_data.get('total_independent_expenditure')  

    # This usually isn't reported, but... 
    return_dict['period_total_contributions'] = header_data.get('total_contribution')
    
    # sometimes the dates are missing--in this case make sure it's set to None--this will otherwise default to today.
    return_dict['coverage_from_date'] = dateparse_notnull(header_data.get('coverage_from_date'))
    return_dict['coverage_to_date'] =dateparse_notnull(header_data.get('coverage_through_date'))   
    
    if return_dict['total_receipts'] == "":
        return_dict['period_total_receipts'] = None
    if return_dict['total_contributions'] == "":
        return_dict['period_total_contributions'] = None
    if return_dict['total_disbursements'] == "":
        return_dict['period_total_disbursements'] = None

    return return_dict
    
def process_f7_header(header_data):
    # communication cost    
    return_dict= defaultdict(lambda:0)
    return_dict['period_total_disbursements'] = header_data.get('total_costs')    
    return_dict['coverage_from_date'] = dateparse_notnull(header_data.get('coverage_from_date'))
    return_dict['coverage_to_date'] =dateparse_notnull(header_data.get('coverage_through_date'))
    
    return return_dict

def process_f9_header(header_data):
    # electioneering 
    return_dict= defaultdict(lambda:0)
    return_dict['period_total_receipts'] = header_data.get('total_donations')
    return_dict['period_total_disbursements'] = header_data.get('total_disbursements')    
    return_dict['coverage_from_date'] = dateparse_notnull(header_data.get('coverage_from_date'))
    return_dict['coverage_to_date'] =dateparse_notnull(header_data.get('coverage_through_date'))
    
    # typically not reported... 
    return_dict['period_total_contributions'] = header_data.get('total_donations')
    
    return return_dict

def process_f13_header(header_data):
    # donations to inaugural committee
    return_dict= defaultdict(lambda:0)
    return_dict['period_total_receipts'] = header_data.get('net_donations')
    return_dict['coverage_from_date'] = dateparse_notnull(header_data.get('coverage_from_date'))
    return_dict['coverage_to_date'] =dateparse_notnull(header_data.get('coverage_through_date'))
    
    # This is greater than tot_raised because it's before the donations refunded... 
    return_dict['period_total_contributions'] = header_data.get('total_donations_accepted')
    return return_dict