'''
Perform an actual GetCoverage operation.

'''
import netCDF4
import os
import os.path
import shutil
import tempfile
import unittest as tests
from lxml import etree


from owslib.coverage import wcs200, wcs_metocean

class TestGetCoverage(tests.TestCase):
    def test_basic(self):
        # Use the known-working internal service.
        wcs_url = 'http://exxvmviswxaftsing02:8008/GlobalWCSService'

        # Create a service object from the url.
        wcs = wcs200.WebCoverageService_2_0_0(wcs_url)

        # Get XML for a coverage request.
        test_xml = wcs_metocean.build_GetCoverage_xml(
            'UKMO_Global_2015-01-15T12.00.00Z_Ground',
            'UKMO_Global_Orography')

        # Fetch the coverage.
        data = wcs.getCoverage_from_xml(test_xml)
        # Crude check that it looks like a netCDF file (and not an XML error).
        self.assertEqual(data[:3], 'CDF')

        # Write it out to a temporary netCDF file.
        dir_path = tempfile.mkdtemp()
        try:
            ncfile_name = 'temp.nc'
            ncfile_path = os.path.join(dir_path, ncfile_name)
            with open(ncfile_path, 'wb') as out_file:
                out_file.write(data)

            # Read the file back in + check a few things.
            with netCDF4.Dataset(ncfile_path) as ds:
                latlon_shapes = (ds.variables['longitude'].shape,
                                 ds.variables['latitude'].shape)
        except:
            pass

        shutil.rmtree(dir_path)

        # Finally, a simple check that result is as expected.
        self.assertEqual(latlon_shapes, ((640,), (481,)))


if __name__ == '__main__':
    tests.main()
