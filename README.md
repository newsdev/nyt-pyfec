![](https://cloud.githubusercontent.com/assets/109988/9589471/97a005a8-4ffc-11e5-9b8b-3da984d183b3.png)

## NOTE: Refactor underway
I'm working on a significant refactor in the branch `flat-files`. The goals of this refactor are as follows:

1. be smarter about the python object that comes out of pyfec. Right now it's a little haphazard where fields are located, and it has that terrible flat_filing key. I'll try to give things better names and put them in more logical places. These changes will be breaking whenever merged back in
2. Create a way to dump the transactions from a filing into csvs for easy import to a database via file copying. This part should be irrelevant to current users.

I don't believe that pyfec has a mailing list. If you're a user who wants to be informed about potentially breaking changes, please contact rachel.shorey@nytimes.com. When I merge in the new branch, I'm going to upgrade to v1 and will be good about version tagging from there on out.

## This is alpha
Really. On a given day, we make no promises that it works. We make no promises that it's not wrong. We make no promises that we won't push breaking hotfixes. If you're going to use it, we strongly recommend a fork.

## Getting started
```
pip install -e git+git@github.com:newsdev/nyt-pyfec.git#egg=nyt-pyfec
python -m pyfec.demo
```


## Example usage

Install pyfec as above. You can then call it from a python app as follows:

```
from pyfec import form
from pyfec import filing

fp = form.Form()
this_file = '1165198' #this is JON OSSOFF FOR CONGRESS's pre-general filing
f1 = filing.Filing(this_file)
```

`f1` is a python object with the following fields:

```
version
form
fec_id
filing_id
is_paper
is_amendment
amends_filing
soft_name
soft_ver
report_number
ef_type
record_type
is_periodic
fields
```

And fields is a dictionary of the fields available in an filing's first row.

To get parsed transactions from a filing:

```
row = f1.get_body_row()
fp.parse_form_line(row, f1.version)
```

## how to update fec-csv-sources...

...if you, like me, are other than awesome at git.

* Make the updates in the fec-csv-sources repo, commit and push to github
* Go your local nyt-pyfec repo, cd into pyfec
* Make sure everything is backed up and committeed and stuff
* If you've done this before, ```git submodule update --remote fec-csv-sources```
* If you haven't done it before, ```rm -r fec-csv-sources &&  git submodule update --init --remote fec-csv-sources```
* Commit and push
* Voila?
