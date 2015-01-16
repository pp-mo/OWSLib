'''
Created on Jan 14, 2015

@author: itpp
'''
from owslib.coverage.wcs200 import WebCoverageService_2_0_0
from owslib.coverage.wcs_metocean import MetOceanCoverageCollection, \
    register_wcs_extension_subtypes as metocean_register_extensions


def main():
    metocean_register_extensions()

#    wcs = WebCoverageService_2_0_0('https://ogcie.iblsoft.com/metocean/wcs')
    wcs = WebCoverageService_2_0_0('http://exxvmviswxaftsing02:8008/GlobalWCSService')
    print(wcs.contents.keys())
    print(wcs.contents_extensions)
    print([op.name for op in wcs.operations])

    coverage_collections = {ext.coverage_collection_id: ext
                            for ext in wcs.contents_extensions
                            if isinstance(ext, MetOceanCoverageCollection)}
    print(coverage_collections)


if __name__ == '__main__':
    main()
