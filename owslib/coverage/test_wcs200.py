'''
Created on Jan 14, 2015

@author: itpp
'''
import unittest as tests
from lxml import etree

import mock

# TODO:
#  wcs2
#  ServiceIdentification
#  ServiceProvider
#  ContactMetadata

import owslib.coverage.wcs200 as wcs

class TestCoverageSummary(tests.TestCase):
    def setUp(self):
        self.xml = '''<?xml version="1.0" encoding="UTF-8"?>
            <root xmlns:wcs20="http://www.opengis.net/wcs/2.0">
            <wcs20:CoverageSummary>
              <wcs20:CoverageId>Dummy Coverage Id</wcs20:CoverageId>
              <wcs20:CoverageSubtype>Dummy Subtype</wcs20:CoverageSubtype>
            </wcs20:CoverageSummary>
            </root>'''
        self.el = etree.XML(self.xml)[0]

        self.dummy_service = mock.Mock(spec=wcs.WebCoverageService_2_0_0,
                                       version='2.0', cookies=None)
        self.obj = wcs.CoverageSummary.from_xml(self.el, self.dummy_service)

    def test_from_xml(self):
        testobj = self.obj
        self.assertEqual(testobj.service, self.dummy_service)
        self.assertEqual(testobj.coverage_id, 'Dummy Coverage Id')
        self.assertEqual(testobj.subtype, 'Dummy Subtype')

#    def test_describe(self):
#        print self.obj.describe()
#
# TODO: this is too hard, because it calls openURL directly.
#

class TestOperation(tests.TestCase):
    def setUp(self):
        self.xml = '''<?xml version="1.0" encoding="UTF-8"?>
            <root xmlns:ows200="http://www.opengis.net/ows/2.0"
            xmlns:xlink="http://www.w3.org/1999/xlink">
            <ows200:Operation name="DummyName">
              <ows200:DCP>
                <ows200:HTTP>
                  <ows200:Get xlink:href="dummy_get_url" />
                  <ows200:Post xlink:href="dummy_post_url">
                    <ows200:Constraint name="PostEncoding">
                      <ows200:AllowedValues>
                        <ows200:Value>XML</ows200:Value>
                      </ows200:AllowedValues>
                    </ows200:Constraint>
                  </ows200:Post>
                </ows200:HTTP>
              </ows200:DCP>
            </ows200:Operation>
            </root>'''
        self.el = etree.XML(self.xml)[0]
        self.obj = wcs.Operation(self.el)

    def test__init__(self):
        testobj = self.obj
        self.assertEqual(testobj.name, 'DummyName')
        self.assertEqual(testobj.formatOptions, [])
        self.assertEqual(
            testobj.methods,
            {'{http://www.opengis.net/ows/2.0}Post': {'url': 'dummy_post_url'},
             '{http://www.opengis.net/ows/2.0}Get': {'url': 'dummy_get_url'}})

    def test_href_via(self):
        testobj = self.obj
        self.assertEqual(testobj.href_via('HTTP', 'Get'), 'dummy_get_url')
        self.assertEqual(testobj.href_via('HTTP', 'Post'), 'dummy_post_url')
        with self.assertRaisesRegexp(ValueError, 'Unexpected method or protocol'):
            testobj.href_via('-x-proto-', 'Get')
        with self.assertRaisesRegexp(ValueError, 'Unexpected method or protocol'):
            testobj.href_via('HTTP', '-x-method-')


class TestServiceIdentification(tests.TestCase):
    def setUp(self):
        self.xml = '''<?xml version="1.0" encoding="UTF-8"?>
            <root xmlns:ows200="http://www.opengis.net/ows/2.0"
            xmlns:xlink="http://www.w3.org/1999/xlink">
            <ows200:ServiceIdentification>
              <ows200:Title>IBL WCS</ows200:Title>
              <ows200:Abstract>WCS Server developed by IBL Software Engineering</ows200:Abstract>
              <ows200:ServiceType>OGC WCS</ows200:ServiceType>
              <ows200:ServiceTypeVersion>2.0.0</ows200:ServiceTypeVersion>
              <ows200:Profile>eg-profile-url-1</ows200:Profile>
              <ows200:Profile>eg-profile-url-2</ows200:Profile>
            </ows200:ServiceIdentification>
            </root>'''
        self.el = etree.XML(self.xml)[0]
        self.obj = wcs.ServiceIdentification(self.el)

    def test__init__(self):
        testobj = self.obj
        self.assertEqual(testobj.service, 'WCS')
        self.assertEqual(testobj.version, wcs.VERSION)
        
        #
        # NOTE: had to hack code to get this
        #  - more namespace problems...
        #
        self.assertEqual(testobj.title, 'IBL WCS')
        


if __name__ == '__main__':
    tests.main()
