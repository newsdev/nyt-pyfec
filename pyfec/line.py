import csv
import re

from pyfec import CSV_FILE_DIRECTORY,PAPER_CSV_FILE_DIRECTORY
from pyfec.utils import clean_entry


class Line(object):
    """
    Representation of a single line from a Filing.
    Contains functions for parsing a line.
    """
    def __init__(self, form, is_paper=False):
        self.form = form
        self.regex_dict = {}
        self.column_locations_dict = {}

        # Maps form type to the CSV containing headers.
        if is_paper:
            form_file = "%s/%s.csv" % (PAPER_CSV_FILE_DIRECTORY, form)
        else:
            form_file = "%s/%s.csv" % (CSV_FILE_DIRECTORY, form)

        form_reader = csv.reader(open(form_file, 'rU'))
        header = form_reader.next()

        for i, regex in enumerate(header):
            if (regex != '' and regex != 'canonical'):
                self.regex_dict[regex] = i
        body_rows = [r for r in form_reader]

        # Create the column locations dict for each version.
        for regex in self.regex_dict:
            this_column_locations = {}
            for row in body_rows:

                # The CSV files are sometimes missing trailing commas when values are absent.
                if (len(row) > self.regex_dict[regex]):
                    if (row[self.regex_dict[regex]] != ''):

                        # The CSV files use 1-indexed positions.
                        # Subtract 1 because we want them 0-indexed.
                        this_column_locations[row[0]] = int(row[self.regex_dict[regex]]) - 1

            self.column_locations_dict[regex] = this_column_locations

    def get_column_locations(self, version):
        return self.column_locations_dict

    def parse_line(self, line_array, version):
        """
        Parses a line to a Python dictionary.
        """
        found_version = False
        regex_key = None
        line_dict = {}

        for regex in self.regex_dict:
            if (re.match(regex, version)):
                regex_key = regex
                found_version = True
        if not found_version:
            raise Exception("Can't find data to parse line type=%s version=%s" % (self.form, version))

        for column in self.column_locations_dict[regex_key]:
            col_position = self.column_locations_dict[regex_key][column]

            # Sometimes trailing commas are omitted, so test that there actually is a value.
            if (col_position <= len(line_array) - 1):
                line_dict[column] = clean_entry(line_array[col_position])
            else:
                line_dict[column] = ''

        return line_dict