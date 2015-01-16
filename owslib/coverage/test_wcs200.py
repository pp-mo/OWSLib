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

def _check_el(test, el, tag, attributes=None, text=None, n_children=0):
    """Check an etree element has the expected properties."""
    if attributes is None:
        attributes = {}
    test.assertEqual(el.tag, tag)
    test.assertEqual(el.attrib, attributes)
    test.assertEqual(el.text, text)
    test.assertEqual(len(el), n_children)


class Test_WebCoverageService_2_0_0(tests.TestCase):
    def setUp(self):
        test_xml = """<?xml version='1.0' encoding='utf8'?>
            <wcs20:Capabilities xmlns:gml32="http://www.opengis.net/gml/3.2" xmlns:ns4="http://def.wmo.int/metce/2013/metocean" xmlns:ows200="http://www.opengis.net/ows/2.0" xmlns:wcs20="http://www.opengis.net/wcs/2.0" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.0.0" xsi:schemaLocation="http://schemas.opengis.net/wcs/2.0 http://schemas.opengis.net/wcs/2.0/wcsAll.xsd http://def.wmo.int/metce/2013/metocean http://exxvmviswxaftsing02:8008/schemas/wcs-2.0/wcsMetOceanGetCapabilities.xsd">
              <ows200:ServiceIdentification>
                <ows200:Title>IBL WCS</ows200:Title>
                <ows200:Abstract>WCS Server developed by IBL Software Engineering</ows200:Abstract>
                <ows200:ServiceType>OGC WCS</ows200:ServiceType>
                <ows200:ServiceTypeVersion>2.0.0</ows200:ServiceTypeVersion>
                <ows200:Profile>http://www.opengis.net/spec/WCS/2.0/conf/core</ows200:Profile>
              </ows200:ServiceIdentification>
              <ows200:OperationsMetadata>
                <ows200:Operation name="GetCapabilities">
                  <ows200:DCP>
                    <ows200:HTTP>
                      <ows200:Get xlink:href="http://exxvmviswxaftsing02:8008/GlobalWCSService" />
                      <ows200:Post xlink:href="http://exxvmviswxaftsing02:8008/GlobalWCSService">
                        <ows200:Constraint name="PostEncoding">
                          <ows200:AllowedValues>
                            <ows200:Value>XML</ows200:Value>
                          </ows200:AllowedValues>
                        </ows200:Constraint>
                      </ows200:Post>
                    </ows200:HTTP>
                  </ows200:DCP>
                </ows200:Operation>
                <ows200:Operation name="DescribeCoverageCollection">
                  <ows200:DCP>
                    <ows200:HTTP>
                      <ows200:Get xlink:href="http://exxvmviswxaftsing02:8008/GlobalWCSService" />
                      <ows200:Post xlink:href="http://exxvmviswxaftsing02:8008/GlobalWCSService">
                        <ows200:Constraint name="PostEncoding">
                          <ows200:AllowedValues>
                            <ows200:Value>XML</ows200:Value>
                          </ows200:AllowedValues>
                        </ows200:Constraint>
                      </ows200:Post>
                    </ows200:HTTP>
                  </ows200:DCP>
                </ows200:Operation>
                <ows200:Operation name="DescribeCoverage">
                  <ows200:DCP>
                    <ows200:HTTP>
                      <ows200:Get xlink:href="http://exxvmviswxaftsing02:8008/GlobalWCSService" />
                      <ows200:Post xlink:href="http://exxvmviswxaftsing02:8008/GlobalWCSService">
                        <ows200:Constraint name="PostEncoding">
                          <ows200:AllowedValues>
                            <ows200:Value>XML</ows200:Value>
                          </ows200:AllowedValues>
                        </ows200:Constraint>
                      </ows200:Post>
                    </ows200:HTTP>
                  </ows200:DCP>
                </ows200:Operation>
                <ows200:Operation name="GetCoverage">
                  <ows200:DCP>
                    <ows200:HTTP>
                      <ows200:Post xlink:href="http://exxvmviswxaftsing02:8008/GlobalWCSService">
                        <ows200:Constraint name="PostEncoding">
                          <ows200:AllowedValues>
                            <ows200:Value>XML</ows200:Value>
                          </ows200:AllowedValues>
                        </ows200:Constraint>
                      </ows200:Post>
                    </ows200:HTTP>
                  </ows200:DCP>
                </ows200:Operation>
              </ows200:OperationsMetadata>
              <wcs20:Contents>
                <wcs20:CoverageSummary>
                  <wcs20:CoverageId>UKMO_Global_2014-04-27T00.00.00Z_AGL</wcs20:CoverageId>
                  <wcs20:CoverageSubtype>VerticalDependency</wcs20:CoverageSubtype>
                </wcs20:CoverageSummary>
                <wcs20:CoverageSummary>
                  <wcs20:CoverageId>UKMO_Global_2014-04-27T00.00.00Z_Ground</wcs20:CoverageId>
                  <wcs20:CoverageSubtype>NoVerticalDependency</wcs20:CoverageSubtype>
                </wcs20:CoverageSummary>
                <wcs20:CoverageSummary>
                  <wcs20:CoverageId>UKMO_Global_2014-04-27T06.00.00Z_AGL</wcs20:CoverageId>
                  <wcs20:CoverageSubtype>VerticalDependency</wcs20:CoverageSubtype>
                </wcs20:CoverageSummary>
                <wcs20:CoverageSummary>
                  <wcs20:CoverageId>UKMO_Global_2014-04-27T06.00.00Z_Ground</wcs20:CoverageId>
                  <wcs20:CoverageSubtype>NoVerticalDependency</wcs20:CoverageSubtype>
                </wcs20:CoverageSummary>
                <wcs20:Extension>
                  <ns4:CoverageCollectionSummary>
                    <ns4:coverageCollectionId>UKMO_Global</ns4:coverageCollectionId>
                    <gml32:name>UKMO_Global</gml32:name>
                    <gml32:boundedBy>
                      <gml32:Envelope axisLabels="Long Lat" srsDimension="2" srsName="CRS:84" uomLabels="deg deg">
                        <gml32:lowerCorner>-180 -90</gml32:lowerCorner>
                        <gml32:upperCorner>180 90</gml32:upperCorner>
                      </gml32:Envelope>
                    </gml32:boundedBy>
                    <ns4:referenceTimeList>
                      <ns4:ReferenceTime>
                        <gml32:timePosition>2014-04-27T00:00:00Z</gml32:timePosition>
                        <gml32:timePosition>2014-04-27T06:00:00Z</gml32:timePosition>
                      </ns4:ReferenceTime>
                    </ns4:referenceTimeList>
                  </ns4:CoverageCollectionSummary>
                </wcs20:Extension>
              </wcs20:Contents>
            </wcs20:Capabilities>
            """
        self.dummy_url = "dummy_url"
        self.wcs = wcs.WebCoverageService_2_0_0(self.dummy_url, xml=test_xml)

    def test__etree_for_GetCoverage__simple(self):
        wcs = self.wcs
        tree = wcs._etree_for_GetCoverage('Dummy_Coverage_Name',
                                          fields='Dummy_Field_Name')
        _check_el(self, tree,
                  tag='{http://www.opengis.net/wcs/2.0}GetCoverage',
                  n_children=2)
        el1, el2 = tree
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
