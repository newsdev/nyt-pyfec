![](https://cloud.githubusercontent.com/assets/109988/9589471/97a005a8-4ffc-11e5-9b8b-3da984d183b3.png)

##This is alpha
Really. On a given day, we make no promises that it works. We make no promises that it's not wrong. We make no promises that we won't push breaking hotfixes. If you're going to use it, we strongly recommend a fork.

## Getting started
```
pip install -e git+git@github.com:newsdev/nyt-pyfec.git#egg=nyt-pyfec
python -m pyfec.demo
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
