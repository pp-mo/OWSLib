# -*- coding: ISO-8859-15 -*-
from unittest import TestCase
from lxml import etree
import wcs_20_describe_coverage as wcs
import wcs_20_metocean as metOcean
import gml
import gmlcov


class TestCoverageMetadata(TestCase):
    def setUp(self):
        with open('describeCoverage_met_ocean_example.txt', 'r') as fh:
            root = etree.XML(fh.read())
        grid_cov = wcs.DescribeCoverage.from_xml(root[0])
        self.coverage_metadata = grid_cov.extension
        self.assertIsInstance(self.coverage_metadata, metOcean.CoverageMetadata)

    def test_repr(self):
        self.assertEqual(repr(self.coverage_metadata), "<CoverageMetadata (11 fields)>")

    def test_fields(self):
        fields = self.coverage_metadata.fields
        self.assertIsInstance(fields, dict)
        self.assertIsInstance(fields['5-wave-geopotential-height'], metOcean.MetOceanDataMask)
#        self.assertEqual(fields['5-wave-geopotential-height'], 'maskId_GFS_Latest_ISBL_1')
#        self.assertEqual(fields['ozone-mixing-ratio'], 'maskId_GFS_Latest_ISBL_5')

    def test_masks(self):
        masks = self.coverage_metadata.masks
        self.assertIsInstance(masks, dict)
        self.assertIsInstance(masks['maskId_GFS_Latest_ISBL_1'], metOcean.MetOceanDataMask)


class TestMetOceanDataMask(TestCase):
    def setUp(self):
        with open('describeCoverage_met_ocean_example.txt', 'r') as fh:
            root = etree.XML(fh.read())
        grid_cov = wcs.DescribeCoverage.from_xml(root[0])
        self.data_mask = grid_cov.extension.fields['relative-humidity']
        self.assertIsInstance(self.data_mask, metOcean.MetOceanDataMask)

    def test_attributes(self):
        self.assertEqual(self.data_mask.mask_id, 'maskId_GFS_Latest_ISBL_6')
        self.assertIsInstance(self.data_mask.grid_coverage, gmlcov.ReferenceableGridCoverage)

    def test_axes(self):
        axes = self.data_mask.axes
        self.assertIsInstance(axes, dict)
        self.assertEqual(sorted(axes.keys()), ['Lat', 'Long', 't', 'z'])

        # XXX What order do we want?
        self.assertEqual(axes['t'].ordinates.shape, (1, 1, 1, 35))
        self.assertEqual(axes['z'].ordinates.shape, (1, 1, 25, 1))
        self.assertEqual(axes['Lat'].ordinates.shape, (1, 360, 1, 1))
        self.assertEqual(axes['Long'].ordinates.shape, (719, 1, 1, 1))

        self.assertEqual([axes['Lat'].ordinates.min(), axes['Lat'].ordinates.max()], [-90.0, 90.0])
        self.assertEqual([axes['Long'].ordinates.min(), axes['Long'].ordinates.max()], [-180.0, 180.0])


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)
