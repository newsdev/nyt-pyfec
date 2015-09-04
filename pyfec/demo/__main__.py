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

payload = []

files = ['827978', '1019752', '1019943']
init(autoreset=True)

start = datetime.datetime.now()

for this_file in files:

    f1 = filing.filing(this_file)

    formtype = f1.get_form_type()
    version = f1.version
    filer_id = f1.get_filer_id()

    print Style.BRIGHT + Fore.CYAN + "~~DEMO APP~~"
    print Style.BRIGHT + Fore.GREEN + " Headers: " + Style.BRIGHT + Fore.YELLOW + "%s" % ", ".join(f1.headers.keys())
    print Style.BRIGHT + Fore.GREEN + " Version: " + Style.BRIGHT + Fore.YELLOW +  "%s" % (version)

    if f1.is_amendment:
        print Style.BRIGHT + Fore.GREEN + " Amends filing: " + Style.BRIGHT + Fore.YELLOW + "%s" % (f1.headers['filing_amended'])

    if not fp.is_allowed_form(formtype):
        print Style.BRIGHT + Fore.RED + " Not parseable: " + Style.BRIGHT + Fore.YELLOW +  "%s" % formtype
        continue

    firstrow = fp.parse_form_line(f1.get_first_row(), version)    

    line_sequence = 0

    while True:
        line_sequence += 1
        row = f1.get_body_row()

        if not row:
            break

        try:
            linedict = fp.parse_form_line(row, version)
            payload.append(linedict)

        except form.ParserMissingError:
            msg = 'process_filing_body: Unknown line type in filing %s line %s: type=%s Skipping.' % (filingnum, linenum, row[0])
            print msg
            continue

print Style.BRIGHT + Fore.CYAN + "~~DEMO APP~~"
print Style.BRIGHT + Fore.MAGENTA + "Processed records: " + Style.BRIGHT + Fore.YELLOW +  "%s" % humanize.intcomma(len(payload))

end = datetime.datetime.now()

print Style.BRIGHT + Fore.MAGENTA + "Time to complete: " + Style.BRIGHT + Fore.YELLOW + "%s" % (end - start)
