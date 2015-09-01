import string
import urllib2

from pyfec import USER_AGENT


# Removes some characters we've discovered, including some special Windows chars,
# the `|` delimiter that would confuse Postgres's `copy` command and all instances
# of `\` since it's not used for any good reason.
pretrans = "\n\x85\x91\x92\x93\x94\x97|\\"
posttrans = " .''\"\"-, "
trans = string.maketrans(pretrans, posttrans)

# Remove a handful of other characters, including tabs.
toremove = "\xA5\xA0\x22\x26\x3C\x3E\xA0\xA1\xA2\xA3\xA4\xA5\xA6\xA7\xA8\xA9\xAA\xAB\xAC\xAD\xAE\xAF\xB0\xB1\xB2\xB3\xB4\xB5\xB6\xB7\xB8\xB9\xBA\xBB\xBC\xBD\xBE\xBF\xD7\xF7\x95\x96\x98\x99\t"

def utf8_clean(raw_string):
    raw_string = raw_string.translate(None, toremove)
    return raw_string.translate(trans)
    
def recode_to_utf8(self, text):
    """ FEC spec allows ascii 9,10,11,13,32-126,128-156,160-168,173. """
    text_uncoded = text.decode('cp1252')
    text_fixed = text_uncoded.encode('utf8')
    return text_fixed
    
def download_with_headers(url):
    """ Sign our requests with a user agent set in the FEC_local_settings file. """
    headers = { 'User-Agent' : USER_AGENT }    
    req = urllib2.Request(url, None, headers)
    return urllib2.urlopen(req).read()

# *** NOTE THIS IS RUN ON EVERY SINGLE ENTRY ***
# Optimize whenever possible.
def clean_entry(entry):
    entry = entry.strip()
    entry = entry.replace("^"," ")

    # Filing software called "Trail Blazer" adds quotes.; see 704636.fec.
    entry = entry.replace('"', "")
    entry = entry.upper()

    return entry
