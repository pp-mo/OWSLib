# -*- coding: ISO-8859-15 -*-
from unittest import TestCase
from lxml import etree
import wcs_20_describe_coverage as wcs
import wcs_20_metocean as metOcean
import gml


class TestReferenceableGridCoverage(TestCase):
    def setUp(self):
        with open('describeCoverage_met_ocean_example.txt', 'r') as fh:
            root = etree.XML(fh.read())
        self.grid_cov = wcs.DescribeCoverage.from_xml(root[0])

    def test_repr(self):
        self.assertEqual(repr(self.grid_cov), "<DescribeCoverage instance>")

    def test_attributes(self):
        self.assertIsInstance(self.grid_cov.domain_set, gml.GMLRectifiedGrid)
        self.assertIsInstance(self.grid_cov.extension, metOcean.CoverageMetadata)

        # Check that _coverage_description is available to the extension.
        self.assertIs(self.grid_cov.extension._coverage_description, self.grid_cov)

#        self.assertIsNone(self.grid_cov.range_type)
#        self.assertIsInstance(self.grid_cov.range_set, gml.GMLRangeSet)
#        self.assertEqual(self.grid_cov.gml_id, 'rgc_maskId_GFS_Latest_ISBL_1')


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)
