import json
import os
import random
import hashlib
from urlparse import urlparse
from WikilinksIterator import *
from WikilinksStatistics import *
from DbWrapper import *
import utils.text
def _urlHash(url):
    '''
    # uses the domain name as hash - to be on the strict side we put all wikilinks from the same domain on
    # a single folder
    '''
    if len(urlparse(url).netloc) == 0:
        print "bad: ", url
    return urlparse(url).netloc

def _get_split(iter, validation_frac=0.2, test_frac=0.2):
    '''
    reads all urls of wikilinks and assignes each url to a folder.
    Returns a set of urls (by hash) for each folder
    '''

    # reads all urls of wikilinks and assignes each url to a folder

    test_hash = set()
    validation_hash = set()
    train_hash = set()
    for i, wlink in enumerate(iter.jsons()):
        if _urlHash(wlink['url']) not in test_hash and \
                _urlHash(wlink['url']) not in validation_hash and \
                _urlHash(wlink['url']) not in train_hash:
            r = random.random()
            if r < validation_frac:
                validation_hash.add(_urlHash(wlink['url']))
            elif r < validation_frac + test_frac:
                test_hash.add(_urlHash(wlink['url']))
            else:
                train_hash.add(_urlHash(wlink['url']))
        if i % 10000 == 0:
            print "calc split, done: ", i
    return (train_hash, validation_hash, test_hash)

class wlink_writer:
    def __init__(self, dir, json_per_file=400000):
        self._dir = dir
        self._n = 0
        self._json_per_file = json_per_file
        if not os.path.exists(dir):
            os.mkdir(dir)
        self._l = []

    def _next_file(self):
        f = open(os.path.join(self._dir, 'wikilinks_{}.json'.format(self._n)), mode='w')
        self._n += 1
        return f

    def _dump(self):
        if len(self._l) >= 1:
            f = self._next_file()
            for s in self._l:
                f.write(s + '\n')
            f.close()
            self._l = []

    def save(self, wlink):
        self._l.append(json.dumps(wlink))
        if len(self._l) >= self._json_per_file:
            self._dump()

    def finalize(self):
            self._dump()

def splitWikis(iter, dest_dir, json_per_file=400000, validation_frac=0.1, test_frac=0.1):
    train_hash, validation_hash, test_hash = _get_split(iter,
                                                        validation_frac=validation_frac,
                                                        test_frac=test_frac)
    print "got ", len(train_hash)+len(validation_hash)+len(test_hash), " unique urls"
    train_writer = wlink_writer(os.path.join(dest_dir, "train"))
    validation_writer = wlink_writer(os.path.join(dest_dir, "validation"))
    test_writer = wlink_writer(os.path.join(dest_dir, "test"))

    for i, wlink in enumerate(iter.jsons()):
        h = _urlHash(wlink['url'])
        if h in train_hash:
            train_writer.save(wlink)
        if h in validation_hash:
            validation_writer.save(wlink)
        if h in test_hash:
            test_writer.save(wlink)
        if i % 10000 == 0:
            print "do split, done: ", i

    train_writer.finalize()
    validation_writer.finalize()
    test_writer.finalize()

class ShuffleFiles:
    """
    This class takes a source directory which is assumed to contain some text file.
    It then writes the contents of these files into dest_dir, into a similar number
    of files but with the lines: roughly equally devided between the files and randomly
    shuffled both between the files and inside the files.

    the process is a two step process and one must call work1() and then work2() to do
    the job
    """
    def __init__(self, src_dir, dest_dir):
        self._src_dir = src_dir
        self._dest_dir = dest_dir

    def _open_for_write(self, dir, n):
        return open(os.path.join(dir, 'wikilinks_{}.json'.format(n)), mode='w')

    # step 1 of randomizing
    def work1(self):
        # open files for write
        dest_files = [self._open_for_write(self._dest_dir, n) for n in xrange(len(os.listdir(self._src_dir)))]
        print "first phase..."

        for fname in os.listdir(self._src_dir):
            in_f = open(os.path.join(self._src_dir, fname), 'r')
            dest_files_temp = [[] for n in xrange(len(dest_files))]
            for line in in_f:
                dest_files_temp[random.randrange(len(dest_files))].append(line)
            in_f.close()

            for f, l in zip(dest_files, dest_files_temp):
                    f.writelines(l)
            print "done ", fname

        for f in dest_files:
            f.close()

    # step 2 of randomizing
    def work2(self):
        print "second phase..."
        for fname in os.listdir(self._dest_dir):
            print "opening file: " + fname
            f = open(os.path.join(self._dest_dir, fname), 'r')
            l = f.readlines()
            f.close()

            random.shuffle(l)

            f = open(os.path.join(self._dest_dir, fname), 'w')
            f.writelines(l)
            f.close()

def copyWithFilter(src_path, dest_path, word_filter):
    train_iter = WikilinksNewIterator(path=src_path)
    writer = wlink_writer(dest_path)
    for wlink in train_iter.jsons():
        if utils.text.strip_wiki_title(wlink['word']) in word_filter:
            writer.save(wlink)
    writer.finalize()

if __name__ == "__main__":
    # Resolving ids
#    wikiDB = WikipediaDbWrapper(user='yotam', password='rockon123', database='wiki20151002')
#    iter = WikilinksNewIterator(path="../../data/wikilinks/unprocessed", resolveIds=True, db=wikiDB)
#    writer = wlink_writer('../../data/wikilinks/with-ids')
#    for i, wlink in enumerate(iter.wikilinks()):
#        writer.save(wlink)
#        if i % 10000 == 0:
#            print "resolve ids: ", i
#    writer.finalize()

    ## shuffle the dataset
#    random.seed()
#    shuffler = ShuffleFiles('../../data/wikilinks/with-ids', '../../data/wikilinks/randomized')
#    shuffler.work1()
#    shuffler.work2()

    ## split into train/validation/test (split by urls. All mentions from same url go to same folder)
#    iter = WikilinksNewIterator('../../data/wikilinks/randomized')
#    splitWikis(iter, '../../data/wikilinks/all-split')

    ## calculate statistics for ttrain
    #iter = WikilinksNewIterator('../data/intralinks/all')
    #stats = WikilinksStatistics(iter)
    #stats.calcStatistics()
    #stats.saveToFile('../data/intralinks/train-stats-new')
    #stats.printSomeStats()

    # filter sets
    stats = WikilinksStatistics(None, load_from_file_path='../data/wikilinks/all-stats')
    good = stats.getGoodMentionsToDisambiguate(p=0.9, t=10)
    good = {x for x in good if random.random() <= 0.1}
    copyWithFilter("../data/wikilinks/all-split/train", '../data/wikilinks/filtered_small/train', good)
    copyWithFilter("../data/wikilinks/all-split/test", '../data/wikilinks/filtered_small/test', good)
    copyWithFilter("../data/wikilinks/all-split/validation", '../data/wikilinks/filtered_small/validation', good)

    #fix
#    iter = WikilinksNewIterator(path="../data/intralinks/all")
#    writer = wlink_writer('../data/intralinks/fixed')
#    for i, wlink in enumerate(iter.wikilinks()):
#       writer.save(wlink)
#       if i % 10000 == 0:
#           print "resolve ids: ", i
#    writer.finalize()
