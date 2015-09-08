import datetime
import os
import re
import sys

from colorama import Fore, Back, Style, init
import humanize

from pyfec import form
from pyfec import filing
from pyfec import settings

fp = form.parser()
fec_format_file = re.compile(r'\d+\.fec')

files = ['827978', '1019752', '1019943']
init(autoreset=True)

start = datetime.datetime.now()

payload = []

for this_file in files:
    filing_dict = {}
    f1 = filing.filing(this_file)

    filing_dict['formtype'] = f1.get_form_type()
    filing_dict['version'] = f1.version
    filing_dict['filer_id'] = f1.get_filer_id()
    filing_dict['transactions'] = []

    print Style.BRIGHT + Fore.CYAN + "~~DEMO APP~~"
    print Style.BRIGHT + Fore.GREEN + " Headers: " + Style.BRIGHT + Fore.YELLOW + "%s" % ", ".join(f1.headers.keys())
    print Style.BRIGHT + Fore.GREEN + " Version: " + Style.BRIGHT + Fore.YELLOW +  "%s" % (filing_dict['version'])

    if f1.is_amendment:
        print Style.BRIGHT + Fore.GREEN + " Amends filing: " + Style.BRIGHT + Fore.YELLOW + "%s" % (f1.headers['filing_amended'])

    if not fp.is_allowed_form(filing_dict['formtype']):
        print Style.BRIGHT + Fore.RED + " Not parseable: " + Style.BRIGHT + Fore.YELLOW +  "%s" % filing_dict['formtype']
        continue

    firstrow = fp.parse_form_line(f1.get_first_row(), filing_dict['version'])

    line_sequence = 0

    while True:
        line_sequence += 1
        row = f1.get_body_row()

        if not row:
            break

        try:
            linedict = fp.parse_form_line(row, filing_dict['version'])
            filing_dict['transactions'].append(linedict)

        except form.ParserMissingError:
            msg = 'process_filing_body: Unknown line type in filing %s line %s: type=%s Skipping.' % (filingnum, linenum, row[0])
            print msg
            continue

    payload.append(filing_dict)

    print Style.BRIGHT + Fore.CYAN + "~~DEMO APP~~"
    print Style.BRIGHT + Fore.MAGENTA + "Processed records: " + Style.BRIGHT + Fore.YELLOW +  "%s" % humanize.intcomma(len(filing_dict['transactions']))
    print Style.BRIGHT + Fore.YELLOW + filing_dict['formtype']
    print Style.BRIGHT + Fore.YELLOW + filing_dict['version']
    print Style.BRIGHT + Fore.YELLOW + filing_dict['filer_id']

end = datetime.datetime.now()
print Style.BRIGHT + Fore.MAGENTA + "Time to complete: " + Style.BRIGHT + Fore.YELLOW + "%s" % (end - start)
