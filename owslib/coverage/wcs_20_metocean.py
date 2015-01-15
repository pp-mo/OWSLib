import gmlcov
import gml


namespaces = {'metOcean': 'http://def.wmo.int/metce/2013/metocean'}


class ExtensionProperty(gmlcov.ExtensionProperty):
    TAGS = ['metOcean:extensionProperty']
    EXTRA_NAMESPACES = namespaces

    @classmethod
    def from_xml(cls, element):
        return CoverageMetadata.from_xml(element[0])


class CoverageMetadata(object):
    TAGS = ['metOcean:MetOceanCoverageMetadata']
    def __init__(self, fields, masks):
        self.fields = fields
        self.masks = masks

    @classmethod
    def from_xml(cls, element):
        reference = element.find('metOcean:dataMaskReferenceProperty', namespaces=namespaces)
        fields = {field.get('fieldName'): field.text.strip()
                  for field in reference[0]}

        dm = element.find('metOcean:dataMaskProperty', namespaces=namespaces)
        masks = DataMaskProperty.from_xml(dm)

        fields = {field: masks[mask_id] for field, mask_id in fields.items()}

        # TODO: sourceObservationProperty

        return cls(fields, masks)

    def __repr__(self):
        return '<CoverageMetadata ({} fields)>'.format(len(self.fields))


@gml.non_instantiable
class DataMaskProperty(object):
    """A container of a DataMaskMemberList."""
    @classmethod
    def from_xml(cls, element):
        # Should only contain a single DataMaskMemberList
        masks = {}
        for mask in element[0]:
            mask_obj = MetOceanDataMask.from_xml(mask)
            masks[mask_obj.mask_id] = mask_obj
        return masks


class MetOceanDataMask(object):
    # XXX Should this be a subclass of GMLElement. Or ReferenceableGridCoverage?
    def __init__(self, mask_id, grid_coverage):
        self.mask_id = mask_id
        self.grid_coverage = grid_coverage

    @property
    def coords(self):
        """
        A dictionary showing the mapping of axes name to ...?
        """
        import numpy as np
        axes = {}

        return self.grid_coverage.domain_set.np_arrays()
#        for ax in self.grid_coverage.domain_set.axes:
#            axes[ax] = None

#        for ax in self.grid_coverage.range_set.axes:
#            axes[ax] = None
        return axes

    @classmethod
    def from_xml(cls, element):
        datamask_id = element.get(gml.apply_namespace('gml:id', gml.namespaces))
        actual_mask = gmlcov.ReferenceableGridCoverage.from_xml(element[0])
        return cls(datamask_id, actual_mask)



