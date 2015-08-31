"""
Parse a header row, passed in as an array. This should happen after a delimiter has been 
detected and the line properly split, whether it's a delimited or csv style line. 
There are different methods for paper and electronic filings; because these come from 
different locations we're assuming we know what we're handling ahead of time. 
The logic here is analogous to what's used in line parser with the HDR.csv file, but for 
architectural reasons we don't want the overhead of attaching line parsers to filings. 
We still maintain the HDR.csv file, but don't actually read from it. 
"""

import re

from pyfec.utils.parsing_utils import clean_entry


old_eheaders = ['record_type', 'ef_type', 'fec_version', 'soft_name', 'soft_ver', 'name_delim', 'report_id', 'report_number']
old_eheaders_re = re.compile(r'^[3|4|5]')

new_eheaders = ['record_type', 'ef_type', 'fec_version', 'soft_name', 'soft_ver', 'report_id', 'report_number']
new_eheaders_re = re.compile(r'^[6|7|8]')

paper_headers_v1 = ['record_type', 'fec_version', 'vendor', 'batch_number']
paper_headers_v1_re = re.compile(r'^P1\.0')

paper_headers_v2_2 = ['record_type', 'fec_version', 'vendor', 'batch_number']
paper_headers_v2_2_re = re.compile(r'^P2\.2|^P2\.3|^P2\.4')

paper_headers_v2_6 = ['record_type', 'fec_version', 'vendor', 'batch_number', 'report_id']
paper_headers_v2_6_re = re.compile(r'^P2\.6|^P3\.0|^P3\.1')


class UnknownHeaderError(Exception):
    """ This should probably do something else? """
    pass
 
def parse(header_array, is_paper=False):
    """ Decides which version of the headers to use."""
    
    if not is_paper:
        version = clean_entry(header_array[2])
        
        if old_eheaders_re.match(version):
            headers_list = old_eheaders

        elif new_eheaders_re.match(version):
            headers_list = new_eheaders

        else:
            raise UnknownHeaderError ("Couldn't find parser for electronic version %s" % (version))
        
    else:
        version = clean_entry(header_array[1])
        
        if paper_headers_v1_re.match(version):
            headers_list = paper_headers_v1

        elif paper_headers_v2_2_re.match(version):
            headers_list = paper_headers_v2_2

        elif paper_headers_v2_6_re.match(version):
            headers_list = paper_headers_v2_6

        else:
            raise UnknownHeaderError ("Couldn't find parser for paper version %s" % (version))
        
    
    headers = {}   

    for i in range(0, len(headers_list)):
        this_arg = "" # It's acceptable for header rows to leave off delimiters, so enter missing trailing args as blanks.
        try:
            this_arg = clean_entry(header_array[i])

        except IndexError:
            # [JACOB WHAT DOES THIS INDICATE?]
            pass

        headers[headers_list[i]] = this_arg
    
    return headers
