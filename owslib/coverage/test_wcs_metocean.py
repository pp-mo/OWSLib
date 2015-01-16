'''
Created on Jan 14, 2015

@author: itpp
'''
import unittest as tests
from lxml import etree

import mock

from owslib.coverage.wcs_metocean import _GetCoverage_etree as get_etree, \
    GetCoverage_xml as get_xml


def _check_el(test, el, tag, attributes=None, text=None, n_children=0):
    """Check an etree element has the expected properties."""
    if attributes is None:
        attributes = {}
    test.assertEqual(el.tag, tag)
    test.assertEqual(el.attrib, attributes)
    test.assertEqual(el.text, text)
    test.assertEqual(len(el), n_children)


class Test__GetCoverage_etree(tests.TestCase):
    def test__etree_for_GetCoverage__simple(self):
        # Get a maximally-simple request.
        tree = get_etree('Dummy_Coverage_Name', fields='Dummy_Field_Name')

        # Check the basic structure.
        def tree_structure(el):
            # Make a simple summary of an etree, showing names and text content
            # but omitting attributes and namespaces.
            tag = el.tag
            # Skip the namespace + just show a tagname.
            tag_namestart = tag.find('}') + 1
            tag = tag[tag_namestart:]
            # Show '' rather than None for empty text.
            text = el.text or ''
            children = [tree_structure(esub) for esub in el]
            return (tag, text, children)

        test_struct = (
            'GetCoverage', '', [
                ('Extension', '', [
                    ('rangeSubset', '', [
                        ('rangeComponent', 'Dummy_Field_Name', [])
                    ]),
                    ('GetCoverageCrs', '', [
                        ('subsettingCrs', '', [])
                    ])
                ]),
                ('CoverageId', 'Dummy_Coverage_Name', []),
                ('format', 'NetCDF3', [])
            ])
        got_struct = tree_structure(tree)
        self.assertEqual(got_struct, test_struct)

        # Also check exact details of the root component.
        _check_el(self, tree,
                  tag='{http://www.opengis.net/wcs/2.0}GetCoverage',
                  attributes={'version': '2.0.0', 'service': 'WCS'},
                  n_children=3)

    def test__etree_for_GetCoverage__multiple_fields(self):
        # Get a request asking for two fields.
        # TODO: in integration, check these as variables in the file.
        tree = get_etree('Dummy_Coverage_Name',
                         fields=['Dummy_Field_1', 'Dummy_Field_2'])
        self.assertEqual(len(tree[0][0]), 2)
        self.assertEqual(tree[0][0][0].text, 'Dummy_Field_1')
        self.assertEqual(tree[0][0][1].text, 'Dummy_Field_2')

#    def test__etree_for_GetCoverage__selected_regions(self):
#        pass


class Test_GetCoverage_xml(tests.TestCase):
    def test__xml_for_GetCoverage(self):
        # Test a minimal case, just to check the conversion to xml.
        xml = get_xml('Dummy_Coverage_Name', fields='Dummy_Field_Name')
        test_string = ( \
            '''<?xml version='1.0' encoding='UTF-8'?>\n'''
            '<wcs20:GetCoverage'
            ' xmlns:rsub="http://www.opengis.net/wcs/range-subsetting/1.0"'
            ' xmlns:srvx="http://www.opengis.net/wcs_service-extension_crs/1.0"'
            ' xmlns:wcs20="http://www.opengis.net/wcs/2.0"'
            ' service="WCS" version="2.0.0">'
            '<wcs20:Extension>'
            '<rsub:rangeSubset>'
            '<rsub:rangeComponent>Dummy_Field_Name</rsub:rangeComponent>'
            '</rsub:rangeSubset>'
            '<srvx:GetCoverageCrs>'
            '<srvx:subsettingCrs/>'
            '</srvx:GetCoverageCrs>'
            '</wcs20:Extension>'
            '<wcs20:CoverageId>Dummy_Coverage_Name</wcs20:CoverageId>'
            '<wcs20:format>NetCDF3</wcs20:format>'
            '</wcs20:GetCoverage>')
        self.assertEqual(xml, test_string)


if __name__ == '__main__':
    tests.main()
