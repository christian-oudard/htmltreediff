# coding: utf8

from textwrap import dedent
from nose.tools import assert_equal
from htmltreediff.html import diff
from htmltreediff.text import WordMatcher

def test_text_split():
    cases = [
        ('word',
         ['word']),
        ('two words',
         ['two', ' ', 'words']),
        ('abcdef12',
         ['abcdef', '12']),
        ('entity&quot;s',
         ['entity', '&quot;', 's']),
        ("we're excited",
         ["we're", " ", "excited"]),
        ('dial 1-800-555-1234',
         ['dial', ' ', '1-800-555-1234']),
        ('Effective 1/2/2003',
         ['Effective', ' ', '1/2/2003']),
        (u'über français',
         [u'über', u' ', u'français']),
    ]
    for text, target in cases:
        def test():
            assert_equal(WordMatcher()._split_text(text), target)
        yield test

def test_text_diff():
    cases = [
        (
            'sub-word changes',
            'The quick brown fox jumps over the lazy dog.',
            'The very quick brown foxes jump over the dog.',
            'The <ins>very </ins>quick brown <del>fox jumps</del><ins>foxes jump</ins> over the<del> lazy</del> dog.',
        ),
        (
            'contractions',
            "we were excited",
            "we're excited",
            "<del>we were</del><ins>we're</ins> excited",
        ),
        (
            'dates',
            'Effective 1/2/2003',
            'Effective 3/4/2005',
            'Effective <del>1/2/2003</del><ins>3/4/2005</ins>',
        ),
        (
            'text diff with <',
            'x',
            '&lt;',
            '<del>x</del><ins>&lt;</ins>',
        ),
        (
            'text diff with >',
            'x',
            '&gt;',
            '<del>x</del><ins>&gt;</ins>',
        ),
        (
            'text diff with &',
            'x',
            '&amp;',
            '<del>x</del><ins>&amp;</ins>',
        ),
        (
            'text normalization',
            'first <h1>middle</h1> last',
            'first last',
            'first <del><h1>middle</h1> </del>last',
        ),
#        (
#            'long text diff',
#            dedent('''
#                Release Announcement: Protected Policies and Bulk Override
#                Last night we successfully updated with a shiny new version. Some of the high notes in this release include:
#
#                Managers can now restrict the visibility of certain policies that only certain users can view policies. I'll be writing up a bit more about this feature a little later, but the gist is that you can now do things like restricting certain sensitive HR policies from being viewable by general staff members. Another nice usage would be for partitioning off one segment of policies, say your Lab policies, so that only users from the lab saw them, which can reduce search clutter for the majority of your staff that doesn't care about that set of policies.
#                Site administrators now have access to Bulk Admin Override, which makes performing sweeping changes a painless endeavor.
#                We optimized the auto-save functionality to allow for better editor performance on long, complicated documents.
#
#                 All three of these features were prioritized based on direct customer feedback and I'm excited we were able to make it happen. Once again, I think our customers were right on the money on where we could add some very useful functionality. Thanks for the feedback and as always, if you have any other questions/concerns/comments or if you are just wondering how the weather is in Indianapolis, drop us a line.
#             '''),
#             dedent('''
#                Release Announcement: Protected Policies and Bulk Override
#                Last night we successfully updated with a shiny new version. Some of the high notes in this release include:
#
#                Managers can now restrict the visibility of policies so that only certain users can view them. I'll be writing more about this feature a little later, but the gist is that you can now do things like restrict sensitive HR policies from being viewable by general staff members. Another nice usage would be to partition off one segment of policies, say your Lab policies, so that only users from the lab see them. This reduces search clutter for the rest of your staff members, who don't care about the lab policies.
#                Site administrators now have access to Bulk Admin Override, which makes performing sweeping changes a painless endeavor.
#                We optimized the auto-save functionality to eliminate occasional pauses when your changes get saved. These pauses were too long when working on large documents.
#
#                 All three of these features were prioritized based on direct customer feedback, and we're excited to be able to make them happen. Once again, I think our customers were right on the money with their suggestions on where things could be improved. Thanks for the feedback as always. If you have any questions/concerns/comments, or if you are just wondering how the weather is in Indianapolis, drop us a line.
#             '''),
#             '''
#             ''',
#            ),
    ]
    for description, old, new, changes in cases:
        def test():
            assert_equal(diff(old, new, html=False), changes)
        test.description = 'test_text_diff - %s' % description
        yield test
