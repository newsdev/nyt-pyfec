import datetime
import exceptions
import string

SCHEDULE_FIELDS = {'A': ['back_reference_sched_name', 'back_reference_tran_id_number', 'conduit_city', 'conduit_name', 'conduit_state', 'conduit_street1', 'conduit_street2', 'conduit_zip', 'contribution_aggregate', 'contribution_amount', 'contribution_date', 'contribution_date_formatted', 'contribution_purpose_code', 'contribution_purpose_descrip', 'contributor_city', 'contributor_employer', 'contributor_first_name', 'contributor_last_name', 'contributor_middle_name', 'contributor_name', 'contributor_occupation', 'contributor_organization_name', 'contributor_prefix', 'contributor_state', 'contributor_street_1', 'contributor_street_2', 'contributor_suffix', 'contributor_zip', 'donor_candidate_district', 'donor_candidate_fec_id', 'donor_candidate_first_name', 'donor_candidate_last_name', 'donor_candidate_middle_name', 'donor_candidate_name', 'donor_candidate_office', 'donor_candidate_prefix', 'donor_candidate_state', 'donor_candidate_suffix', 'donor_committee_fec_id', 'donor_committee_name', 'election_code', 'election_other_description', 'entity_type', 'filer_committee_id_number', 'filing_number', 'form_type', 'line_sequence', 'memo_code', 'memo_text_description', 'reference_code', 'superseded_by_amendment', 'transaction_id'], 'B': ['back_reference_sched_name', 'back_reference_tran_id_number', 'beneficiary_candidate_district', 'beneficiary_candidate_fec_id', 'beneficiary_candidate_first_name', 'beneficiary_candidate_last_name', 'beneficiary_candidate_middle_name', 'beneficiary_candidate_name', 'beneficiary_candidate_office', 'beneficiary_candidate_prefix', 'beneficiary_candidate_state', 'beneficiary_candidate_suffix', 'beneficiary_committee_fec_id', 'beneficiary_committee_name', 'category_code', 'communication_date', 'conduit_city', 'conduit_name', 'conduit_state', 'conduit_street_1', 'conduit_street_2', 'conduit_zip', 'election_code', 'election_other_description', 'entity_type', 'expenditure_amount', 'expenditure_date', 'expenditure_date_formatted', 'expenditure_purpose_code', 'expenditure_purpose_descrip', 'filer_committee_id_number', 'filing_number', 'form_type', 'line_sequence', 'memo_code', 'memo_text_description', 'payee_city', 'payee_first_name', 'payee_last_name', 'payee_middle_name', 'payee_name', 'payee_organization_name', 'payee_prefix', 'payee_state', 'payee_street_1', 'payee_street_2', 'payee_suffix', 'payee_zip', 'ref_to_sys_code_ids_acct', 'refund_or_disposal_of_excess', 'semi_annual_refunded_bundled_amt', 'superseded_by_amendment', 'transaction_id'], 'E': ['back_reference_sched_name', 'back_reference_tran_id_number', 'calendar_y_t_d_per_election_office', 'candidate_district', 'candidate_first_name', 'candidate_id_number', 'candidate_last_name', 'candidate_middle_name', 'candidate_name', 'candidate_office', 'candidate_prefix', 'candidate_state', 'candidate_suffix', 'category_code', 'completing_first_name', 'completing_last_name', 'completing_middle_name', 'completing_prefix', 'completing_suffix', 'date_signed', 'date_signed_formatted', 'effective_date', 'election_code', 'election_other_description', 'entity_type', 'expenditure_amount', 'expenditure_date', 'expenditure_date_formatted', 'dissemination_date','dissemination_date_formatted', 'expenditure_purpose_code', 'expenditure_purpose_descrip', 'filer_committee_id_number', 'filing_number', 'form_type', 'line_sequence', 'memo_code', 'memo_text_description', 'payee_city', 'payee_cmtte_fec_id_number', 'payee_first_name', 'payee_last_name', 'payee_middle_name', 'payee_name', 'payee_organization_name', 'payee_prefix', 'payee_state', 'payee_street_1', 'payee_street_2', 'payee_suffix', 'payee_zip', 'superseded_by_amendment', 'support_oppose_code', 'transaction_id'], 'O': ['filer_committee_id_number', 'filing_number', 'form_parser', 'form_type', 'line_sequence', 'line_dict', 'superseded_by_amendment', 'transaction_id']}


class PyFecException(exceptions.Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


class FilingHeaderDoesNotExist(PyFecException):
    pass


class FilingHeaderAlreadyProcessed(PyFecException):
    pass


# these candidates / committees have submitted what appear to be fictitious filings
# there's not really a procedure for FEC to deal with them, so the filings are received
# and eventually marked as F99's instead of F3's. But that's till farther down the line. 
BLACKLISTED_CANDIDATES = ['C00507947', 'C00428599']
BLACKLISTED_COMMITTEES = ['P20003851', 'P80003205']

# Removes some characters we've discovered, including some special Windows chars,
# the `|` delimiter that would confuse Postgres's `copy` command and all instances
# of `\` since it's not used for any good reason.
TRANSLATED_STRING = string.maketrans("\n\x85\x91\x92\x93\x94\x97|\\", " .''\"\"-, ")

# Remove a handful of other characters, including tabs.
TO_REMOVE = "\xA5\xA0\x22\x26\x3C\x3E\xA0\xA1\xA2\xA3\xA4\xA5\xA6\xA7\xA8\xA9\xAA\xAB\xAC\xAD\xAE\xAF\xB0\xB1\xB2\xB3\xB4\xB5\xB6\xB7\xB8\xB9\xBA\xBB\xBC\xBD\xBE\xBF\xD7\xF7\x95\x96\x98\x99\t"

def utf8_clean(raw_string):
    raw_string = raw_string.translate(None, TO_REMOVE)
    return raw_string.translate(TRANSLATED_STRING)
    
def recode_to_utf8(text):
    """
    FEC spec allows ascii 9,10,11,13,32-126,128-156,160-168,173.
    """
    return text.decode('cp1252').encode('utf8')

# *** NOTE THIS IS RUN ON EVERY SINGLE ENTRY ***
# Optimize whenever possible.
def clean_entry(entry):
    return entry.strip().replace("^"," ").replace('"', "").upper().strip()

##
## CYCLE UTILITIES
##

def get_cycle(year):
    """
    Takes a four-digit year string or integer and pads it to an even number.
    Returns a string for some reason. Returns None for unparsable years.
    """
    try:
        this_year = int(year)
        if this_year % 2 != 0:
            this_year = this_year + 1
        return str(this_year)

    except ValueError:
        return None

def is_valid_cycle(string_cycle):
    """
    >>> dates = [2001,2000,2006,2020,2086,2003,2014,2010,2015,2016]
    >>> [is_valid_four_digit_string_cycle(d) for d in dates]
    [False, True, True, True, False, False, True, True, False, True]
    """
    # Figure out this year; pad by 1 if it's an odd-numbered
    # year because election cycles are (helpfully) on even-
    # numbered years.
    this_year = int(get_cycle(datetime.date.today().year))

    # If you're not passing something that can be an integer,
    # I am not even interested in helping you.
    try:

        # The only hard-coded date is a six-year horizon in the future.
        # Assumption is that three cycles (two Presidential) is the
        # furthest in the future we care about.
        if int(string_cycle) in range(2000, this_year + 8, 2):
            return True
    except ValueError:
        pass

    return False

def get_four_digit_year(two_digit_string):
    """
    >>> dates = [99,98,75,62,18,14,16,20]
    >>> [get_four_digit_year(d) for d in dates]
    ['1999', '1998', '1975', '1962', '2018', '2014', '2016', '2020']
    """
    try:
        two_digit_year = int(two_digit_string)
        this_year = int(str(datetime.date.today().year)[2:4])

        if two_digit_year <= this_year + 10:
            four_digit_year = 2000 + two_digit_year
        else:
            four_digit_year = 1900 + two_digit_year

        return str(four_digit_year)

    except ValueError:
        return None
