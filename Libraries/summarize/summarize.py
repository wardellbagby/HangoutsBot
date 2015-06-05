# Copyright (c) 2013, Jonathon Vogel
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright notice,
#       this list of conditions and the following disclaimer in the documentation
#       and/or other materials provided with the distribution.
#     * Neither the name of summarize.py nor the names of its contributors
#       may be used to endorse or promote products derived from this software
#       without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

#!/usr/bin/env python

from __future__ import print_function

import codecs
import nltk
from nltk.corpus import stopwords
import re
import string
import sys

_IS_PYTHON_3 = sys.version_info.major == 3

stop_words = stopwords.words('english')

# The low end of shared words to consider
LOWER_BOUND = .20

# The high end, since anything above this is probably SEO garbage or a
# duplicate sentence
UPPER_BOUND = .90


def u(s):
    """Ensure our string is unicode independent of Python version, since Python 3 versions < 3.3 do not support the u"..." prefix"""
    if _IS_PYTHON_3 or type(s) == unicode:
        return s
    else:
        # not well documented but seems to work
        return codecs.unicode_escape_decode(s)[0]


def is_unimportant(word):
    """Decides if a word is ok to toss out for the sentence comparisons"""
    return word in ['.', '!', ',', ] or '\'' in word or word in stop_words


def only_important(sent):
    """Just a little wrapper to filter on is_unimportant"""
    return filter(lambda w: not is_unimportant(w), sent)


def compare_sents(sent1, sent2):
    """Compare two word-tokenized sentences for shared words"""
    if not len(sent1) or not len(sent2):
        return 0
    return len(set(only_important(sent1)) & set(only_important(sent2))) / ((len(sent1) + len(sent2)) / 2.0)


def compare_sents_bounded(sent1, sent2):
    """If the result of compare_sents is not between LOWER_BOUND and
    UPPER_BOUND, it returns 0 instead, so outliers don't mess with the sum"""
    cmpd = compare_sents(sent1, sent2)
    if cmpd <= LOWER_BOUND or cmpd >= UPPER_BOUND:
        return 0
    return cmpd


def compute_score(sent, sents):
    """Computes the average score of sent vs the other sentences (the result of
    sent vs itself isn't counted because it's 1, and that's above
    UPPER_BOUND)"""
    if not len(sent):
        return 0
    return sum(compare_sents_bounded(sent, sent1) for sent1 in sents) / float(len(sents))


def summarize_block(block):
    """Return the sentence that best summarizes block"""
    if not block:
        return None
    sents = nltk.sent_tokenize(block)
    word_sents = list(map(nltk.word_tokenize, sents))
    d = dict((compute_score(word_sent, word_sents), sent)
             for sent, word_sent in zip(sents, word_sents))
    return d[max(d.keys())]


def find_likely_body(b):
    """Find the tag with the most directly-descended <p> tags"""
    return max(b.find_all(), key=lambda t: len(t.find_all('p', recursive=False)))


class Summary(object):
    def __init__(self, url, article_html, title, summaries):
        self.url = url
        self.article_html = article_html
        self.title = title
        self.summaries = summaries

    def __repr__(self):
        return u('Summary({}, {}, {}, {})').format(repr(self.url), repr(self.article_html), repr(self.title),
                                                   repr(self.summaries))

    def __unicode__(self):
        return u('{} - {}\n\n{}').format(self.title, self.url, '\n'.join(self.summaries))

    def __str__(self):
        if _IS_PYTHON_3:
            return self.__unicode__()
        else:
            return self.__unicode__().encode('utf8')


def summarize_blocks(blocks):
    summaries = [re.sub('\s+', ' ', summarize_block(block) or '').strip()
                 for block in blocks]
    # deduplicate and preserve order
    summaries = sorted(set(summaries), key=summaries.index)
    return [u(re.sub('\s+', ' ', summary.strip())) for summary in summaries if
            any(c.lower() in string.ascii_lowercase for c in summary)]


def summarize_page(url):
    import bs4
    import requests

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36',
    }
    html = bs4.BeautifulSoup(requests.get(url, headers=headers).text)
    b = find_likely_body(html)
    summaries = summarize_blocks(map(lambda p: p.text, b.find_all('p')))
    return Summary(url, b, html.title.text if html.title else None, summaries)


def summarize_text(text, block_sep='\n\n', url=None, title=None):
    return Summary(url, None, title, summarize_blocks(text.split(block_sep)))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        print(summarize_page(sys.argv[1]))
        sys.exit(0)

    print('Usage summarize.py <URL>')
    sys.exit(1)
