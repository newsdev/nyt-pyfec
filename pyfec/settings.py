import os

# FEC daily bulk ZIP files URL. Requires the date in YYYYMMDD format to be interpolated.
FEC_FILE_LOCATION = "ftp://ftp.fec.gov/FEC/electronic/%s.zip"

# FEC raw .fec files URL. Requires the filing ID to be interpolated.
FEC_DOWNLOAD = "http://docquery.fec.gov/dcdev/posted/%s.fec"

# FEC location of html pages of a filing. Requires the committee id and filing ID to be interpolated.
FEC_HTML_LOCATION = "http://docquery.fec.gov/cgi-bin/dcdev/forms/%s/%s/"

# Requires the candidate ID to be interpolated. For reference only.
FEC_CANDIDATE_SUMMARY = "http://www.fec.gov/fecviewer/CommitteeDetailCurrentSummary.do?tabIndex=1&candidateCommitteeId=%s&electionYr=2014"

# How should our requests be signed? 
USER_AGENT = "FEC READER 0.1; [ YOUR CONTACT INFO HERE ]"

# The FEC is known to block scrapers that do not have a delay.
# 2s is sufficient to avoid this.
DELAY_TIME=2

LOG_NAME = 'fecparsing.log'

# For the scraper.
USER_AGENT = "paper FEC (0.0.1)"
DELAY_TIME = 1

# The project root directory.
ARCHIVE_DIR_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# For local temp files.
FILECACHE_DIRECTORY = ARCHIVE_DIR_ROOT + '/data/fec_filings'
PAPER_FILECACHE_DIRECTORY = ARCHIVE_DIR_ROOT + '/paper_data/fec_filings'

# For downloading / unzipping FEC bundles.
ZIP_DIRECTORY = ARCHIVE_DIR_ROOT + '/data/zipped_fec_filings'
PAPER_ZIP_DIRECTORY = ARCHIVE_DIR_ROOT + '/paper_data/zipped_fec_filings'

# For JSON output.
JSON_DIRECTORY = ARCHIVE_DIR_ROOT + '/data/json'
PAPER_JSON_DIRECTORY = ARCHIVE_DIR_ROOT + '/paper_data/json'


LOG_DIRECTORY = ARCHIVE_DIR_ROOT + "/log"

# Updated CSVs from Fech.
CSV_FILE_DIRECTORY = ARCHIVE_DIR_ROOT + '/pyfec/fec-csv-sources'
PAPER_CSV_FILE_DIRECTORY = ARCHIVE_DIR_ROOT + '/pyfec/fec-csv-sources/paper_sources'

# Create directories that do not exist.
for directory in [ARCHIVE_DIR_ROOT,FILECACHE_DIRECTORY,PAPER_FILECACHE_DIRECTORY,ZIP_DIRECTORY,PAPER_ZIP_DIRECTORY,JSON_DIRECTORY,PAPER_JSON_DIRECTORY,LOG_DIRECTORY,CSV_FILE_DIRECTORY,PAPER_CSV_FILE_DIRECTORY]:
    if not os.path.isdir(directory):
        os.system('mkdir -p %s' % directory)



# Override any system-specific settings with FEC_local_settings.py.
try:
    from FEC_local_settings import *
except Exception, e:
    # nothing is required now, so just ignore.
    pass
