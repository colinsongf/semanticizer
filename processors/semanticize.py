# Copyright 2012-2013, University of Amsterdam. This program is free software:
# you can redistribute it and/or modify it under the terms of the GNU Lesser 
# General Public License as published by the Free Software Foundation, either 
# version 3 of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or 
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License 
# for more details.
# 
# You should have received a copy of the GNU Lesser General Public License 
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import wpm.wpmutil as wpmutil
from nltk import regexp_tokenize
from nltk.util import ngrams as nltk_ngrams
import urllib
import unicodedata


def tokenize(text):
    return regexp_tokenize(text, r'\w+([.,\']\w+)*|[^\w\s]+')


class Semanticizer:

    def __init__(self, language_code, sense_probability_threshold):
        """"""
        self.language_code = language_code
        self.sense_probability_threshold = sense_probability_threshold
        self.wikipedia_url_template = 'http://%s.wikipedia.org/wiki/%s'
        self.wpm = wpmutil.wpm_dumps[language_code]
        self.title_page = {} # This needs to be removed

    def semanticize(self, sentence, normalize_dash=True,
                    normalize_accents=True, normalize_lower=False,
                    translations=True, counts=False,
                    sense_probability_threshold=None):
        if sense_probability_threshold == None:
            sense_probability_threshold = self.sense_probability_threshold
        result = {"links": []}
        ngrams = set()
        tokens = [tokenize(sentence),
                  tokenize(sentence.replace('-', ' ')),
                  tokenize(sentence.replace('.', ' ')),
                  tokenize(sentence.replace('.', ''))]

        # get all ngrams for this sentence
        for words in tokens:
            for n in range(1, len(words) + 1):
                for ngram in nltk_ngrams(words, n):
                    ngrams.add(' '.join(ngram))

        for ngram in ngrams:
            normal_ngram = self.normalize(ngram)
            if self.wpm.normalized_entity_exists(normal_ngram):
                normalized_ngram = self.normalize(ngram, normalize_dash,
                                                  normalize_accents,
                                                  normalize_lower)
                anchors = self.wpm.get_all_entities(normal_ngram)
                for anchor in anchors:
                    normalized_anchor = self.normalize(anchor, normalize_dash,
                                                       normalize_accents,
                                                       normalize_lower)
                    if normalized_ngram == normalized_anchor:
                        if not self.wpm.entity_exists(anchor):
                            raise LookupError("Data corrupted, cannot "
                                              + "find %s in the database" \
                                              % anchor)
                        entity = self.wpm.get_entity_data(anchor)
                        for sense in entity['senses']:
                            sense_str = str(sense)
                            sense_data = self.wpm.get_sense_data(anchor,
                                                                 sense_str)
                            if entity['cnttextocc'] == 0:
                                link_probability = 0
                                sense_probability = 0
                            else:
                                link_probability = float(entity['cntlinkdoc']) / entity['cnttextdoc']
                                sense_probability = float(sense_data['cntlinkdoc']) / entity['cnttextdoc']
                            if sense_probability > sense_probability_threshold:
                                title = unicode(self.wpm.get_sense_title(sense_str))
                                url = self.wikipedia_url_template \
                                      % (self.language_code,
                                         urllib.quote(title.encode('utf-8')))
                                if entity['cntlinkocc'] == 0:
                                    prior_probability = 0
                                else:
                                    prior_probability = float(sense_data['cntlinkocc']) / entity['cntlinkocc']
                                link = {
                                    "label": anchor,
                                    "text": ngram,
                                    "title": title,
                                    "id": sense,
                                    "url": url,
                                    "linkProbability": link_probability,
                                    "senseProbability": sense_probability,
                                    "priorProbability": prior_probability
                                }
                                if translations:
                                    link["translations"] = {self.language_code:
                                                            {"title": title,
                                                             "url": url}}
                                    if self.wpm.sense_has_trnsl(sense_str):
                                        for lang in self.wpm.get_trnsl_langs(sense_str):
                                            trnsl = self.wpm.get_sense_trnsl(sense_str, lang)
                                            link["translations"][lang] = {
                                                'title': unicode(trnsl),
                                                'url': self.wikipedia_url_template % (lang, urllib.quote(unicode(trnsl).encode('utf-8')))
                                            }
                                if counts:
                                    link["occCount"] = entity['cnttextocc']
                                    link["docCount"] = entity['cnttextdoc']
                                    link["linkOccCount"] = entity['cntlinkocc']
                                    link["linkDocCount"] = entity['cntlinkdoc']
                                    link["senseOccCount"] = int(sense_data['cntlinkocc'])
                                    link["senseDocCount"] = int(sense_data['cntlinkdoc'])
                                    link['fromTitle'] = sense_data['from_title']
                                    link['fromRedirect'] = sense_data['from_redir']
                                result["links"].append(link)

        return result

    def normalize(self, raw, dash=True, accents=True, lower=True):
        text = raw
        if dash:
            text = text.replace('-', ' ')
        if accents:
            text = self.remove_accents(text)
        if lower:
            text = text.lower()
        text = text.strip()
        return text if len(text) else raw

    def remove_accents(self, input_str):
        if type(input_str) is str:
            input_unicode = unicode(input_str, errors="ignore")
        else:
            input_unicode = input_str
        nkfd_form = unicodedata.normalize('NFKD', input_unicode)
        return u"".join([c for c in nkfd_form if not unicodedata.combining(c)])
