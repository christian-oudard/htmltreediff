from nose.tools import assert_equal

from htmltreediff.test_util import collapse
from htmltreediff.util import parse_minidom, minidom_tostring
from htmltreediff.changes import dom_diff

test_cases = [
    (
        'nested list items',
        collapse('''
        <ul>
          <li>Monday
            <ul>
              <li>2pm - 3pm</li>
            </ul>
          </li>
          <li>Wednesday
            <ul>
              <li>11am - Noon</li>
              <li>3pm - 5pm</li>
            </ul>
          </li>
          <li>Thursday
            <ul>
              <li>11am - Noon</li>
            </ul>
          </li>
          <li>Friday
            <ul>
              <li>Noon - 1pm</li>
            </ul>
          </li>
        </ul>
        '''),
        collapse('''
        <ul>
          <li>Tuesday
            <ul>
              <li>3pm - 5pm</li>
            </ul>
          </li>
          <li>Thursday
            <ul>
              <li>11am - Noon</li>
            </ul>
          </li>
        </ul>
        '''),
        collapse('''
        <ul>
          <del>
            <li>
              Monday
              <ul>
                <li>
                  2pm - 3pm
                </li>
              </ul>
            </li>
            <li>
              Wednesday
              <ul>
                <li>
                  11am - Noon
                </li>
                <li>
                  3pm - 5pm
                </li>
              </ul>
            </li>
          </del>
          <ins>
            <li>
              Tuesday
              <ul>
                <li>
                  3pm - 5pm
                </li>
              </ul>
            </li>
          </ins>
          <li>
            Thursday
            <ul>
              <li>
                11am - Noon
              </li>
            </ul>
          </li>
          <del>
            <li>
              Friday
              <ul>
                <li>
                  Noon - 1pm
                </li>
              </ul>
            </li>
          </del>
        </ul>
        '''),
    )
]

def test_xml_diff():
    for test_name, old_html, new_html, target in test_cases:
        old_dom = parse_minidom(old_html, strict_xml=True)
        new_dom = parse_minidom(new_html, strict_xml=True)
        changes_xml = minidom_tostring(dom_diff(old_dom, new_dom))
        assert_equal(changes_xml, target)
