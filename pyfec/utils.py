import datetime
import exceptions
import string

from dateutil import parser

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

def utf8_clean(raw_string):
    # Remove a handful of other characters, including tabs.
    TO_REMOVE = "\xA5\xA0\x22\x26\x3C\x3E\xA0\xA1\xA2\xA3\xA4\xA5\xA6\xA7\xA8\xA9\xAA\xAB\xAC\xAD\xAE\xAF\xB0\xB1\xB2\xB3\xB4\xB5\xB6\xB7\xB8\xB9\xBA\xBB\xBC\xBD\xBE\xBF\xD7\xF7\x95\x96\x98\x99\t"

    # Removes some characters we've discovered, including some special Windows chars,
    # the `|` delimiter that would confuse Postgres's `copy` command and all instances
    # of `\` since it's not used for any good reason.
    TRANSLATED_STRING = string.maketrans("\n\x85\x91\x92\x93\x94\x97|\\", " .''\"\"-, ")

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

##
## SCHEDULE PARSERS
##

def skeda_from_skedadict(line_dict, filing_number, line_sequence, is_amended):
    """
    We can either pass the header row in or not; if not, look it up.
    """
    line_dict['transaction_id'] = line_dict['transaction_id'][:20]
    line_dict['line_sequence'] = line_sequence
    line_dict['superseded_by_amendment'] = is_amended
    line_dict['filing_number'] = filing_number
    if line_dict['contribution_date']:
        try:
            line_dict['contribution_date_formatted'] = parser.parse(line_dict['contribution_date'])
        except ValueError:
            pass
    return line_dict

def skeda_from_f65(line_dict, filing_number, line_sequence, is_amended):
    """
    Enter 48-hour contributions to candidate as if it were a sked A.
    Will later be superseded by periodic F3 report.
    This is almost to skeda_from_skedadict?
    """
    line_dict['transaction_id'] = line_dict['transaction_id'][:20]
    line_dict['superseded_by_amendment'] = is_amended
    line_dict['line_sequence'] = line_sequence
    line_dict['filing_number'] = filing_number
    if line_dict['contribution_date']:
        try:
            line_dict['contribution_date_formatted'] = parser.parse(line_dict['contribution_date'])
        except ValueError:
            pass
    return line_dict

def skeda_from_f56(line_dict, filing_number, line_sequence, is_amended):
    """
    Example: See filing ID 847857.
    """
    line_dict['transaction_id'] = line_dict['transaction_id'][:20]
    line_dict['superseded_by_amendment'] = is_amended
    line_dict['line_sequence'] = line_sequence
    line_dict['filing_number'] = filing_number
    if line_dict['contribution_date']:
        try:
            line_dict['contribution_date_formatted'] = parser.parse(line_dict['contribution_date'])
        except ValueError:
            pass
    line_dict['contribution_amount'] = line_dict['contribution_amount']
    return line_dict

def skeda_from_f92(line_dict, filing_number, line_sequence, is_amended):
    """
    Electioneering communication contributions.
    """
    line_dict['transaction_id'] = line_dict['transaction_id'][:20]
    line_dict['superseded_by_amendment'] = is_amended
    line_dict['line_sequence'] = line_sequence
    line_dict['filing_number'] = filing_number
    if line_dict['contribution_date']:
        try:
            line_dict['contribution_date_formatted'] = parser.parse(line_dict['contribution_date'])
        except ValueError:
            pass
    return line_dict


def skeda_from_f132(line_dict, filing_number, line_sequence, is_amended):
    """
    Inaugural donations.
    """
    line_dict['transaction_id'] = line_dict['transaction_id'][:20]
    line_dict['superseded_by_amendment'] = is_amended
    line_dict['line_sequence'] = line_sequence
    line_dict['filing_number'] = filing_number

    if line_dict['contribution_date']:
        try:
            line_dict['contribution_date_formatted'] = parser.parse(line_dict['contribution_date'])
        except ValueError:
            pass
    return line_dict

def skeda_from_f133(line_dict, filing_number, line_sequence, is_amended):
    """
    Inaugural donor REFUNDS.
    """
    line_dict['transaction_id'] = line_dict['transaction_id'][:20]
    line_dict['line_sequence'] = line_sequence
    line_dict['superseded_by_amendment'] = is_amended
    line_dict['filing_number'] = filing_number
    # Map refund to contributions.
    line_dict['contribution_amount'] = line_dict['refund_amount']
    line_dict['contribution_date'] = line_dict['refund_date']
    del line_dict['refund_date']
    del line_dict['refund_amount']
    line_dict['contribution_amount'] = line_dict['contribution_amount']
    if line_dict['contribution_amount']  > 0:
        # Flip signs if this number is positive. 
        line_dict['contribution_amount'] = 0-line_dict['contribution_amount']

    if line_dict['contribution_date']:
        try:
            line_dict['contribution_date_formatted'] = parser.parse(line_dict['contribution_date'])
        except ValueError:
            pass
    return line_dict

def skedb_from_skedbdict(line_dict, filing_number, line_sequence, is_amended):
    line_dict['transaction_id'] = line_dict['transaction_id'][:20]
    line_dict['beneficiary_candidate_first_name'] = line_dict['beneficiary_candidate_first_name'][:20]
    line_dict['line_sequence'] = line_sequence
    line_dict['superseded_by_amendment'] = is_amended
    line_dict['filing_number'] = filing_number
    if not line_dict['expenditure_amount']:
        line_dict['expenditure_amount'] = None
    if not line_dict['semi_annual_refunded_bundled_amt']:
        line_dict['semi_annual_refunded_bundled_amt'] = None
    line_dict['ref_to_sys_code_ids_acct'] = line_dict['reference_to_si_or_sl_system_code_that_identifies_the_account']
    del line_dict['reference_to_si_or_sl_system_code_that_identifies_the_account'] # LOL FEC WAT

    if line_dict['expenditure_date']:
        try:
            line_dict['expenditure_date_formatted'] = parser.parse(line_dict['expenditure_date'])
        except ValueError:
            pass
    return line_dict

def skede_from_skededict(line_dict, filing_number, line_sequence, is_amended):
    line_dict['transaction_id'] = line_dict['transaction_id'][:20]
    line_dict['line_sequence'] = line_sequence
    line_dict['superseded_by_amendment'] = is_amended
    line_dict['filing_number'] = filing_number
    line_dict['completing_prefix'] = line_dict['completing_prefix'][:10]
    line_dict['completing_suffix'] = line_dict['completing_suffix'][:10]
    # The switch from v.8 to v.8.1 added a 'dissemination date' though it kept the expenditure date.
    # We now prefer the dissemination date, but fall back to the expenditure date if it's not available.
    # The spec says that not having either is an error. 
    try:
        line_dict['expenditure_date_formatted'] = parser.parse(line_dict['expenditure_date'])
        line_dict['effective_date'] = line_dict['expenditure_date_formatted']
    except:
        pass
    try: 
        line_dict['dissemination_date_formatted'] = parser.parse(line_dict['dissemination_date'])
        line_dict['effective_date'] = line_dict['dissemination_date_formatted']
    except:
        pass
    return line_dict

def skede_from_f57(line_dict, filing_number, line_sequence, is_amended):
    line_dict['transaction_id'] = line_dict['transaction_id'][:20]
    line_dict['superseded_by_amendment'] = is_amended
    line_dict['line_sequence'] = line_sequence
    line_dict['filing_number'] = filing_number
    if line_dict.get('expenditure_date', None):
        try:
            line_dict['expenditure_date_formatted'] = parser.parse(line_dict['expenditure_date'])
        except ValueError:
            pass
    return line_dict

def otherline_from_line(line_dict, filing_number, line_sequence, is_amended, filer_id):
    """
    http://initd.org/psycopg/docs/extras.html#hstore-data-type
    """
    try:
        # Some lines have illegal transaction ids -- longer than 20 characters. Truncate those.
        line_dict['transaction_id'] = line_dict['transaction_id'][:20]
    except KeyError:
        # Some lines are actually summary lines (F3S) and have no transaction ids, so don't freak out about this. 
        pass
    line_dict['superseded_by_amendment'] = is_amended 
    line_dict['line_sequence'] = line_sequence
    line_dict['filing_number'] = filing_number
    line_dict['filer_committee_id_number'] = filer_id
    try:
        # Text records use rec_type instead of form.
        line_dict['form_type'] = line_dict['rec_type']
    except KeyError:
        pass
    return line_dict

def transform_line(line_dict, flat_filing):
    """
    Returns a tuple: ('skedletter', datadict)
    """

    filing_id = flat_filing['filing_id']
    line_sequence = line_dict['line_sequence']
    is_amended = line_dict.get('is_amended', False)
    filer_id = flat_filing['fec_id']

    if line_dict['form_parser'] == 'SchA':
        return ('A', skeda_from_skedadict(line_dict, filing_id, line_sequence, is_amended))

    elif line_dict['form_parser'] == 'SchB':
        return ('B', skedb_from_skedbdict(line_dict, filing_id, line_sequence, is_amended))

    elif line_dict['form_parser'] == 'SchE':
        return ('E', skede_from_skededict(line_dict, filing_id, line_sequence, is_amended))

    # Treat 48-hour contribution notices like sked A.
    # Requires special handling for amendment, since these are superceded by regular F3 forms. 
    elif line_dict['form_parser'] == 'F65':
        return ('A', skeda_from_f65(line_dict, filing_id, line_sequence, is_amended))

    # Disclosed donor to non-commmittee. Rare. 
    elif line_dict['form_parser'] == 'F56':
        return ('A', skeda_from_f56(line_dict, filing_id, line_sequence, is_amended))

    # Disclosed electioneering donor.
    elif line_dict['form_parser'] == 'F92':
        return ('A', skeda_from_f92(line_dict, filing_id, line_sequence, is_amended))

    # Inaugural donors.
    elif line_dict['form_parser'] == 'F132':
        return ('A', skeda_from_f132(line_dict, filing_id, line_sequence, is_amended))

    # Inaugural refunds.
    elif line_dict['form_parser'] == 'F133':
        return ('A', skeda_from_f133(line_dict, filing_id, line_sequence, is_amended))

    # IE's disclosed by non-committees. Note that they use this for * both * quarterly and 24-hour notices.
    # There's not much consistency with this -- be careful with superceding stuff. 
    elif line_dict['form_parser'] == 'F57':
        return ('E', skede_from_f57(line_dict, filing_id, line_sequence, is_amended))

    # If this is some other kind of line, just dump it in `other lines.`
    else:
        return ('O', otherline_from_line(line_dict, filing_id, line_sequence, is_amended, filer_id))
