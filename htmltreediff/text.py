import re, string
from difflib import SequenceMatcher, _calculate_ratio

def full_split(text, regex):
    """
    Split the text by the regex, keeping all parts.
    The parts should re-join back into the original text.

    >>> list(full_split('word', re.compile('&.*?')))
    ['word']
    """
    while text:
        m = regex.search(text)
        if not m:
            yield text
            break
        left = text[:m.start()]
        middle = text[m.start():m.end()]
        right = text[m.end():]
        if left:
            yield left
        if middle:
            yield middle
        text = right

def multi_split(text, regexes):
    """
    Split the text by the given regexes, in priority order.

    Make sure that the regex is parenthesized so that matches are returned in
    re.split().

    Splitting on a single regex works like normal split.
    >>> '|'.join(multi_split('one two three', [r'\w+']))
    'one| |two| |three'

    Splitting on digits first separates the digits from their word
    >>> '|'.join(multi_split('one234five 678', [r'\d+', r'\w+']))
    'one|234|five| |678'

    Splitting on words first keeps the word with digits intact.
    >>> '|'.join(multi_split('one234five 678', [r'\w+', r'\d+']))
    'one234five| |678'
    """
    def make_regex(s):
        return re.compile(s) if isinstance(s, basestring) else s
    regexes = [make_regex(r) for r in regexes]

    # Run the list of pieces through the regex split, splitting it into more
    # pieces. Once a piece has been matched, add it to finished_pieces and
    # don't split it again. The pieces should always join back together to form
    # the original text.
    piece_list = [text]
    finished_pieces = set()
    def apply_re(regex, piece_list):
        for piece in piece_list:
            if piece in finished_pieces:
                yield piece
                continue
            for s in full_split(piece, regex):
                if regex.match(s):
                    finished_pieces.add(s)
                if s:
                    yield s

    for regex in regexes:
        piece_list = list(apply_re(regex, piece_list))
        assert ''.join(piece_list) == text
    return piece_list


# A special case list of contractions and other words that should be grouped.
# Case insensitive.
_word_list = [
    "i'm", "i'll", "i'd", "i've", "you're", "you'll", "you'd", "you've",
    "he's", "he'll", "he'd", "she's", "she'll", "she'd", "it's", "it'll",
    "it'd", "we're", "we'll", "we'd", "we've", "they're", "they'll", "they'd",
    "they've", "there's", "there'll", "there'd", "that's", "that'll", "that'd",
    "ain't", "aren't", "can't", "couldn't", "didn't", "doesn't", "don't",
    "hadn't", "hasn't", "isn't", "mustn't", "needn't", "shouldn't", "wasn't",
    "weren't", "won't", "wouldn't",
]

_word_split_regexes = [
    # HTML Entities
    re.compile(r'&.*?;', re.IGNORECASE),
    # Special cases.
    re.compile('%s' % '|'.join(re.escape(c) for c in _word_list), re.IGNORECASE),
    # Simplified phone number pattern. Any dash-separated list of digits.
    re.compile(r'\d+(-\d+)+'),
    # Simplified date pattern. Any slash-separated list of digits.
    re.compile(r'\d+(/\d+)+'),
    # Numbers
    re.compile(r'\d+'),
    # Punctuation
    re.compile(r'[%s]' % re.escape(string.punctuation)),
    # Words
    re.compile(r'\w+', re.UNICODE),
]

def split_text(text):
    return multi_split(text, _word_split_regexes)

_stopwords = 'a an and as at by for if in it of or so the to'
_stopwords = set(_stopwords.strip().lower().split())
def _is_junk(word):
    """Treat whitespace and stopwords as junk for text matching."""
    return word.isspace() or word.lower() in _stopwords

class WordMatcher(SequenceMatcher):
    """
    WordMatcher is a SequenceMatcher that treats a string of text as a sequence
    of words, and matches accordingly. This produces more intuitive diffs of
    text, because it won't split a word.

    When the matcher is constructed, or the sequences are set, the string is
    split into a list of words. This uses a regular expression which groups
    word characters, numbers, punctuation, and html entities.
    """
    def __init__(self, isjunk=_is_junk, a=None, b=None):
        if a is None:
            a = []
        if b is None:
            b = []
        SequenceMatcher.__init__(self, isjunk, a, b)

    @staticmethod
    def _split_text(text):
        return multi_split(text, _word_split_regexes)

    def set_seq1(self, a):
        if not a:
            a = ''
        SequenceMatcher.set_seq1(self, self._split_text(a))

    def set_seq2(self, b):
        if not b:
            b = ''
        SequenceMatcher.set_seq2(self, self._split_text(b))

    def text_ratio(self):
        """Return a measure of the sequences' word similarity (float in [0,1]).

        Each word has weight equal to its length for this measure

        >>> m = WordMatcher(a='abcdef12', b='abcdef34') # 3/4 of the text is the same
        >>> '%.3f' % m.ratio() # normal ratio fails
        '0.500'
        >>> '%.3f' % m.text_ratio() # text ratio is accurate
        '0.750'
        """
        return _calculate_ratio(
            self.match_length(),
            self._text_length(self.a) + self._text_length(self.b),
        )

    def match_length(self):
        """ Find the total length of all words that match between the two sequences."""
        length = 0
        for match in self.get_matching_blocks():
            a, b, size = match
            length += self._text_length(self.a[a:a+size])
        return length

    def _text_length(self, word_sequence):
        # Find the length of non-junk text in the sequence.
        return sum(self._word_length(word) for word in word_sequence)

    def _word_length(self, word):
        if self.isjunk and self.isjunk(word):
            return 0
        return len(word)
