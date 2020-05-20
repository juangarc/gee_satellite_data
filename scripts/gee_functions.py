import ee
import json
import geopandas as gpd
import numpy as np
from datetime import timedelta
from scripts import gis_functions
ee.Initialize()


def calculate_displacement(eeimage, eeimageref, maxoffset=200, patchwidth=400):
    refimageproj = eeimageref.reproject(crs=eeimage.projection())

    displacement = eeimage.displacement(referenceImage=refimageproj,
                                        maxOffset=maxoffset,
                                        patchWidth=patchwidth)
    return displacement

def dates_maxcover(df, limit = 80, numdays = 20):
    datasummary = df.loc[df.cover_percentage >= limit].reset_index()
    datemin = datemax = None
    if(datasummary.shape[0]>0):

        datemaxcover = datasummary.dates.iloc[datasummary.cover_percentage.idxmax()]

        datemin = (datemaxcover - timedelta(days=numdays)).strftime("%Y-%m-%d")
        datemax = (datemaxcover + timedelta(days=numdays)).strftime("%Y-%m-%d")

    return [datemin,
            datemax]


### ee geometry
def geometry_as_ee(filename):
    '''transform shapefile format to ee geometry'''
    ### read csv file
    if(type(filename) == str):
        sp_geometry = gpd.read_file(filename)
        ## reproject spatial data
        if sp_geometry.crs[[*sp_geometry.crs][0]] != 'epsg:4326':
            sp_geometry = sp_geometry.to_crs('epsg:4326')

    if type(filename) == gpd.geodataframe.GeoDataFrame:
        sp_geometry = filename

    ## get geometry points in json format
    jsonFormat = json.loads(sp_geometry.to_json())['features'][0]['geometry']

    return ee.Geometry.Polygon(jsonFormat['coordinates'])


def getfeature_fromeedict(eecollection, attribute, featname):
    '''get image collection properties'''
    aux = []
    for feature in range(len(eecollection['features'])):

        ## get data from the dictionary
        datadict = eecollection['features'][feature][attribute][featname]
        ## check if it has info
        aux.append(datadict)
    return (aux)


def get_eeimagecover_percentage(eeimage, eegeometry):
    imagewithdata = eeimage.clip(eegeometry).select(0).gt(ee.Number(-100))
    imagewithdatamasked = eeimage.clip(eegeometry).select(0).updateMask(imagewithdata)
    area = imagewithdatamasked.pixelArea()

    pixelareavalue = imagewithdata.multiply(area).reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=eegeometry,
        scale=30
    )

    ### calculate percentage using the geometry
    polarea = eegeometry.area()

    ## calculate image cover area
    areavaluelocal = ee.Number(pixelareavalue.get(ee.Image(eeimage).bandNames().get(0)))

    return areavaluelocal.divide(polarea).multiply(ee.Number(100))


def get_eeurl(imagecollection, geometry, scale=10):
    imagesurls = []

    listimages = imagecollection.toList(imagecollection.size());

    for i in range(imagecollection.size().getInfo()):
        try:
            imagesurls.append(ee.Image(listimages.get(ee.Number(i))).getDownloadUrl({
                'scale': scale,  # for resolution of image
                'crs': 'EPSG:4326',  # which crs-transformation should apply
                'region': geometry  # polygon region
            }))
        except:
            imagesurls.append(ee.Image(listimages.get(ee.Number(i))).getDownloadUrl({
                'scale': scale,  # for resolution of image
                'crs': 'EPSG:4326',  # which crs-transformation should apply
                'region': geometry  # polygon region
            }))
    return imagesurls


def query_image_collection(initdate, enddate, satellite_mission, ee_sp):
    '''mission data query'''

    ## mission data query
    return ee.ImageCollection(satellite_mission).filterDate(initdate, enddate).filterBounds(ee_sp)


def LatLonImg(img, geometry, scale):
    img = img.addBands(ee.Image.pixelLonLat())

    img = img.reduceRegion(reducer=ee.Reducer.toList(), geometry=geometry, maxPixels=1e13, scale=scale)

    data = np.array((ee.Array(img.get("result")).getInfo()))
    lats = np.array((ee.Array(img.get("latitude")).getInfo()))
    lons = np.array((ee.Array(img.get("longitude")).getInfo()))
    return lats, lons, data