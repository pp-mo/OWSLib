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


class Test_GetCoverage_xml(tests.TestCase):
    def test__etree_for_GetCoverage__simple(self):
        tree = get_etree('Dummy_Coverage_Name', fields='Dummy_Field_Name')
        _check_el(self, tree,
                  tag='{http://www.opengis.net/wcs/2.0}GetCoverage',
                  attributes={'version': '2.0.0', 'service': 'WCS'},
                  n_children=3)
        el1, el2, el3 = tree
#        _check_el(self, el1,
#                  tag='{http://www.opengis.net/wcs/2.0}CoverageId',
#                  text='Dummy_Coverage_Name',
#                  n_children=0)
        _check_el(self, el2,
                  tag='{http://www.opengis.net/wcs/2.0}CoverageId',
                  text='Dummy_Coverage_Name',
                  n_children=0)

        print etree.tostring(tree, pretty_print=True)


#    def test__xml_for_GetCoverage(self):
#        wcs = self.wcs
#        xml = wcs._xml_for_GetCoverage('Dummy_Coverage_Name',
#                                          fields='Dummy_Field_Name')
#        test_string = ('<?xml version="1.0" encoding="UTF-8"?>'
#                       '<wcs20:GetCoverage xmlns:wcs20="http://www.opengis.net/wcs/2.0">'
#                       '<wcs20:CoverageId>Dummy_Coverage_Name</wcs20:CoverageId>'
#                       '</wcs20:GetCoverage>')
#        self.assertEqual(xml, test_string)


#    def test__etree_for_GetCoverage__selected_fields(self):
#        pass
#
#    def test__etree_for_GetCoverage__selected_regions(self):
#        pass


if __name__ == '__main__':
    tests.main()
