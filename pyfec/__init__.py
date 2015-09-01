import os

DELAY_TIME = int(os.environ.get("pyfec_delay_time", "1"))
USER_AGENT = os.environ.get("pyfec_user_agent", "nyt-pyfec (jeremy.bowers@nytimes.com)")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
CSV_FILE_DIRECTORY = PROJECT_ROOT + '/pyfec/fec-csv-sources'
PAPER_CSV_FILE_DIRECTORY = PROJECT_ROOT + '/pyfec/fec-csv-sources/paper_sources'