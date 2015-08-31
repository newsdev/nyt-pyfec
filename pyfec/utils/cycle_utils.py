## Utils to handle common date / cycle manipulation.
## cycles are stored as 4-digit *strings*.
## this is for 2-year cycle...

from datetime import date

""" Are cycles consistent? """
cycle_calendar = {
    2008: {'start':date(2007,1,1), 'end':date(2008,12,31)},
    2010: {'start':date(2009,1,1), 'end':date(2010,12,31)},
    2012: {'start':date(2011,1,1), 'end':date(2012,12,31)},
    2014: {'start':date(2013,1,1), 'end':date(2014,12,31)},
    2016: {'start':date(2015,1,1), 'end':date(2016,12,31)},
}


def is_valid_four_digit_string_cycle(string_cycle):
    if string_cycle in ['2000', '2002','2004', '2006', '2008', '2010', '2012', '2014', '2016', '2018', '2020']:
        return True
    return False

def fix_year(year):
    if year%2 == 1:
        return str(year+1)
    else:
        return str(year)

def get_cycle_from_date(date):
    # Should work for a date or datetime
    if not date:
        return None
    else:
        year = date.year
        return fix_year(year)

def get_cycle_from_two_digit_string(twodigitstring):
    try:
        yearint = 2000 + int(twodigitstring)
    except ValueError:
        return None
        
    return fix_year(yearint)


def get_cycle_abbreviation(integer_cycle):
    cycle_base = integer_cycle-2000
    return ("%s-%s" % (cycle_base-1, cycle_base))

def get_cycle_endpoints(integer_cycle):
    try:
        return cycle_calendar[integer_cycle]
    except KeyError:
        return None


        