import unittest
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from services.utils import remove_timestamps_from_html

class TestTimestampRemoval(unittest.TestCase):

    def test_remove_simple_timestamp(self):
        """Test removing a basic timestamp."""
        html = 'Hello <font color="#ADD8E6">[00:01:02.3]</font> world'
        expected = 'Hello world'
        self.assertEqual(remove_timestamps_from_html(html), expected)

    def test_remove_timestamp_with_extra_attributes(self):
        """Test removing a timestamp with other HTML attributes."""
        html = 'Hello <font style="font-size: 12px;" color="#ADD8E6" face="Arial">[00:01:02.3]</font> world'
        expected = 'Hello world'
        self.assertEqual(remove_timestamps_from_html(html), expected)

    def test_remove_multiple_timestamps(self):
        """Test removing multiple timestamps from the string."""
        html = '<p><font color="#ADD8E6">[00:00:00.0]</font> sentence one.</p><p><font color="#ADD8E6">[00:00:05.5]</font> sentence two.</p>'
        expected = '<p>sentence one.</p><p>sentence two.</p>'
        self.assertEqual(remove_timestamps_from_html(html), expected)

    def test_no_timestamps_present(self):
        """Test with HTML that does not contain any timestamps."""
        html = '<p>This is a paragraph without any timestamps.</p>'
        self.assertEqual(remove_timestamps_from_html(html), html)

    def test_empty_string(self):
        """Test with an empty string input."""
        html = ''
        self.assertEqual(remove_timestamps_from_html(html), '')

    def test_string_with_only_timestamp(self):
        """Test a string that only contains a timestamp."""
        html = '<font color="#ADD8E6">[12:34:56.7]</font>'
        expected = ''
        self.assertEqual(remove_timestamps_from_html(html), expected)

    def test_case_insensitivity(self):
        """Test that the removal is case-insensitive."""
        html = 'Hello <FONT COLOR="#add8e6">[00:01:02.3]</FONT> world'
        expected = 'Hello world'
        self.assertEqual(remove_timestamps_from_html(html), expected)

    def test_raw_timestamp_no_html(self):
        """Test removing a raw timestamp without any HTML tags."""
        html = 'Hello [00:10:20] world'
        expected = 'Hello world'
        self.assertEqual(remove_timestamps_from_html(html), expected)

    def test_raw_timestamp_mm_ss(self):
        """Test removing a raw timestamp in [MM:SS] format."""
        html = 'Another test [12:34] here.'
        expected = 'Another test here.'
        self.assertEqual(remove_timestamps_from_html(html), expected)

    def test_mixed_styled_and_raw_timestamps(self):
        """Test removing both styled and raw timestamps in the same string."""
        html = '<p><font color="#ADD8E6">[00:00:01]</font> Hello [00:00:02] world.</p>'
        expected = '<p>Hello world.</p>'
        self.assertEqual(remove_timestamps_from_html(html), expected)

if __name__ == '__main__':
    unittest.main()