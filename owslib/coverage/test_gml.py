from unittest import TestCase
from lxml import etree
import gml


XML_template = """
<?xml version="1.0" encoding="UTF-8"?>
<root xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:gmlrgrid="http://www.opengis.net/gml/3.3/rgrid">
{content}
</root>
""".strip()

DOMAINSET_EXAMPLE = """
<?xml version="1.0" encoding="UTF-8"?>
<root xmlns:gml="http://www.opengis.net/gml/3.2">
<gml:domainSet>
  <gml:RectifiedGrid dimension="2" gml:id="GFS_Latest_ISBL_grid">
    <gml:limits>
      <gml:GridEnvelope>
        <gml:low>0 0</gml:low>
        <gml:high>719 360</gml:high>
      </gml:GridEnvelope>
    </gml:limits>
    <gml:axisName>x</gml:axisName>
    <gml:axisName>y</gml:axisName>
    <gml:origin>
      <gml:Point srsName="EPSG:4326" gml:id="GFS_Latest_ISBL_grid_origin">
        <gml:coordinates>0 -90</gml:coordinates>
      </gml:Point>
    </gml:origin>
    <gml:offsetVector srsName="EPSG:4326">0.5 7.0467596052536985</gml:offsetVector>
    <gml:offsetVector srsName="EPSG:4326">0 14.573944878270581</gml:offsetVector>
  </gml:RectifiedGrid>
</gml:domainSet>
</root>""".strip()


class TestGMLDomainSet(TestCase):
    def setUp(self):
        root = etree.XML(DOMAINSET_EXAMPLE)
        self.ds = gml.GMLdomainSet.from_xml(root[0])

    def test_limits(self):
        envelope = self.ds.limits
        self.assertIsInstance(envelope, gml.GMLGridEnvelope)

    def test_axes(self):
        axes = self.ds.axes
        self.assertEqual(axes, ['x', 'y'])

    def test_origin(self):
        origin = self.ds.origin
        self.assertIsInstance(origin, gml.GMLPoint)

    def test_offset_vectors(self):
        offset_vectors = self.ds.offset_vectors
        for vector in offset_vectors:
            self.assertIsInstance(vector, gml.GMLVector)


class TestGMLRectifiedGrid(TestCase):
    def setUp(self):
        root = etree.XML(DOMAINSET_EXAMPLE)
        self.grid = gml.GMLdomainSet.from_xml(root[0])
        self.assertIsInstance(self.grid, gml.GMLRectifiedGrid)

    def test_repr(self):
        self.assertEqual(repr(self.grid), '<GMLRectifiedGrid instance>')

    def test_attributes(self):
        self.assertIsInstance(self.grid.limits, gml.GMLGridEnvelope)
        self.assertEqual(self.grid.axes, ['x', 'y'])
        self.assertEqual(self.grid.dims, 2)
        self.assertIsInstance(self.grid.origin, gml.GMLPoint)
        self.assertIsInstance(self.grid.offset_vectors[0], gml.GMLVector)


class TestGMLReferenceableGridByArray(TestCase):
    def setUp(self):
        root = etree.XML(XML_template.format(content="""
        <gmlrgrid:ReferenceableGridByArray gml:id="ex" dimension="2"
            srsName="http://www.opengis.net/def/crs/EPSG/0/4326">
            <gml:limits>
                <gml:GridEnvelope>
                    <gml:low>0 0</gml:low>
                    <gml:high>4 5</gml:high>
                </gml:GridEnvelope>
            </gml:limits>
            <gml:axisLabels>x y</gml:axisLabels>
            <gml:posList>
            2 8 3 10 6 12 8 14 10 18
            4 6 6 8 8 12 10 14 12 16
            6 2 7 4 9 6 10 8 13 12
            8 2 8 3 10 5 11 8 13 10
            </gml:posList>
            <gml:sequenceRule axisOrder="+1 +2">Linear</gml:sequenceRule>
        </gmlrgrid:ReferenceableGridByArray>"""))
        self.grid = gml.GMLReferenceableGridByArray.from_xml(root[0])

        root2 = etree.XML(XML_template.format(content="""
          <gml:ReferenceableGridByArray gml:id="6d-SO_t" dimension="3" uomLabels="DMSH DMSH metre" srsDimension="3"
           srsName="EPSG/0/4327">
            <gml:limits>
              <gml:GridEnvelope>
                <gml:low>0 0 0</gml:low>
                <gml:high>3 4 2</gml:high>
              </gml:GridEnvelope>
            </gml:limits>
            <gml:axisLabels>two 1 3</gml:axisLabels>
            <gml:posList>
              40   9.2 200   40.1 9.3 200   40.3 9.5 210
              40.1 9.3 205   40.3 9.5 220   40.4 9.7 225
              40.4 9.4 215   40.7 9.7 225   40.8 9.8 235
              40.6 9.5 220   40.8 9.7 230   40.9 9.9 240
        
              40.0 9.1 205   40.1 9.2 210   40.4 9.6 230
              40.2 9.5 220   40.2 9.4 240   40.7 9.7 240
              40.5 9.7 225   40.5 9.6 245   40.8 9.8 285
              40.7 9.8 230   40.6 9.8 290   41   10  295
            </gml:posList>
            <gml:sequenceRule axisOrder="+2 +1 +3">Linear</gml:sequenceRule>
          </gml:ReferenceableGridByArray>""".strip()))

        self.grid2 = gml.GMLReferenceableGridByArray.from_xml(root2[0])

    def test_repr(self):
        self.assertEqual(repr(self.grid), '<GMLReferenceableGridByArray instance>')

    def test_attributes(self):
        self.assertIsInstance(self.grid.limits, gml.GMLGridEnvelope)
        self.assertEqual(self.grid.axes, ['x', 'y'])
        self.assertEqual(self.grid.dims, 2)
        self.assertEqual(self.grid.pos_list[:12], [2.0, 8.0, 3.0, 10.0, 6.0, 12.0, 8.0, 14.0, 10.0, 18.0, 4.0, 6.0])
        self.assertEqual(self.grid.sequence_rule, ('+1 +2', 'Linear'))

    def test_ndarray(self):
        arrays1 = self.grid.np_arrays()
        self.assertIsInstance(arrays1, dict)
        self.assertEqual(sorted(arrays1.keys()), sorted(self.grid.axes))
        self.assertEqual(arrays1['y'].shape, (4, 1))
        self.assertEqual(arrays1['x'].shape, (1, 5))

    def test_ndarray_3d(self):
        arrays1 = self.grid2.np_arrays()
        self.assertEqual(arrays1['1'].shape, (1, 4, 1))
        self.assertEqual(list(arrays1['1'].flat), [9.2, 9.3, 9.4, 9.5])

        self.assertEqual(arrays1['two'].shape, (1, 1, 2))
        self.assertEqual(arrays1['3'].shape, (3, 1, 1))


class TestGMLVector(TestCase):
    def setUp(self):
        root = etree.XML(DOMAINSET_EXAMPLE)
        geom = gml.GMLdomainSet.from_xml(root[0])
        self.vector = geom.offset_vectors[0]

    def test_repr(self):
        self.assertEqual(repr(self.vector), "GMLVector({}, [0.5, 7.0467596052536985])")

    def test_attributes(self):
        self.assertEqual(self.vector.components, [0.5, 7.0467596052536985])


class TestGMLEnvelope(TestCase):
    def setUp(self):
        root = etree.XML(XML_template.format(content="""
          <gml:Envelope axisLabels="Long Lat" srsDimension="2" srsName="CRS:84" uomLabels="deg deg">
            <gml:lowerCorner>-180 -90</gml:lowerCorner>
            <gml:upperCorner>180 90</gml:upperCorner>
          </gml:Envelope>
        """))
        self.envelope = gml.GMLEnvelope.from_xml(root[0])

    def test_repr(self):
        self.assertEqual(repr(self.envelope),
                         "GMLEnvelope({'srsName': 'CRS:84', 'axisLabels': 'Long Lat', "
                                      "'uomLabels': 'deg deg', 'srsDimension': '2'}, "
                                     "lows=[-180.0, -90.0], highs=[180.0, 90.0])")

    def test_attributes(self):
        self.assertIsInstance(self.envelope.lows[0], float)
        self.assertEqual(self.envelope.lows, [-180.0, -90.0])
        self.assertEqual(self.envelope.highs, [180.0, 90.0])


class TestGMLTimePeriod(TestCase):
    def setUp(self):
        root = etree.XML(XML_template.format(content="""
          <gml:TimePeriod gml:id="tp_ForecastTimeRange_GFS_Latest_ISBL">
                <gml:beginPosition>2015-01-12T00:00:00Z</gml:beginPosition>
                <gml:endPosition>2015-01-20T00:00:00Z</gml:endPosition>
          </gml:TimePeriod>
        """))
        self.time_period = gml.GMLTimePeriod.from_xml(root[0])

    def test_repr(self):
        self.assertEqual(repr(self.time_period),
                         "TimePeriod({'gml:id': 'tp_ForecastTimeRange_GFS_Latest_ISBL'}, datetime.datetime(2015, 1, 12, 0, 0), datetime.datetime(2015, 1, 20, 0, 0))")

    def test_attributes(self):
        from datetime import datetime
        self.assertEqual(self.time_period.attrs, {'gml:id': 'tp_ForecastTimeRange_GFS_Latest_ISBL'})
        self.assertEqual(self.time_period.start, datetime.strptime('2015-01-12T00:00:00Z', gml.GMLTimeFormat))
        self.assertEqual(self.time_period.end, datetime.strptime('2015-01-20T00:00:00Z', gml.GMLTimeFormat))


class TestGMLGridEnvelope(TestCase):
    def setUp(self):
        root = etree.XML(DOMAINSET_EXAMPLE)
        ds = gml.GMLdomainSet.from_xml(root[0])
        self.envelope = ds.limits

    def test_repr(self):
        self.assertEqual(repr(self.envelope),
                         'GMLGridEnvelope({}, lows=[0, 0], highs=[719, 360])')

    def test_attributes(self):
        self.assertIsInstance(self.envelope.lows[0], int)
        self.assertEqual(self.envelope.lows, [0, 0])
        self.assertEqual(self.envelope.highs, [719, 360])


class TestGMLPoint(TestCase):
    def setUp(self):
        root = etree.XML(DOMAINSET_EXAMPLE)
        ds = gml.GMLdomainSet.from_xml(root[0])
        self.point = ds.origin

    def test_repr(self):
        self.assertEqual(repr(self.point),
                         "GMLPoint({'gml:id': 'GFS_Latest_ISBL_grid_origin'}, [0.0, -90.0])")

    def test_attributes(self):
        self.assertIsInstance(self.point.coords[0], float)
        self.assertEqual(self.point.coords, [0.0, -90.0])


# Chapter 14

class TestGMLTimePosition(TestCase):
    def setUp(self):
        root = etree.XML(XML_template.format(content="""
          <gml:timePosition gml:id="wibble">2015-01-11T15:31:52Z</gml:timePosition>
        """))
        self.time = gml.GMLTimePosition.from_xml(root[0])

    def test_repr(self):
        self.assertEqual(repr(self.time),
                         "GMLTimePosition({'gml:id': 'wibble'}, datetime.datetime(2015, 1, 11, 15, 31, 52))")

    def test_attributes(self):
        import datetime
        self.assertIsInstance(self.time.datetime, datetime.datetime)
        self.assertEqual(self.time.datetime, datetime.datetime(2015, 1, 11, 15, 31, 52))


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)