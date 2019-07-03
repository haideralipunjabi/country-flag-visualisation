import json
import os
from PIL import Image
import geopandas as gpd
from geopandas.tools import geocode
import matplotlib.pyplot as plt
from fiona.crs import from_epsg
import pandas as pd
from shapely.geometry import Point, Polygon
from matplotlib import font_manager as fm, rcParams
from geopandas.plotting import plot_polygon_collection
import functools
from functools import reduce
import textwrap
from xml.dom import minidom
import math

# SOURCE: https://github.com/hjnilsson/country-flags
FLAGS_DIR = "flags/"
COUNTRY_DATA= json.load(open("countries.json","r"))

# SOURCE: http://www.naturalearthdata.com/
SHP_FILE="map/ne_50m_admin_0_countries.shp"
DIS_FILE="map/ne_10m_admin_0_disputed_areas.shp"

gismap = gpd.read_file(SHP_FILE)
dismap = gpd.read_file(DIS_FILE)

def get_country(flag):
    return COUNTRY_DATA[os.path.splitext(flag)[0].upper()]

# SOURCE: http://kuanbutts.com/2018/08/30/geodataframe-to-svg/
def process_to_svg_group(row,dis=False):
    orig_svg = row.geometry.svg()
    doc = minidom.parseString(orig_svg)
    paths = doc.getElementsByTagName('path')
    pathssvg = []
    for path in paths:
        path.setAttribute('fill', 'url(#%s)'%(row['ISO_A2'].lower()))
        path.setAttribute('stroke-width','0.1')
        path.setAttribute('stroke','#000000')
        path.setAttribute('opacity','1')
        path.setAttribute('transform','scale(10,-10)')
        pathssvg.append(path.toxml())
    return ''.join(pathssvg)


processed_rows = []
def_rows = []


res_symdiff = gpd.overlay(gismap, dismap, how='difference')

for index,row in res_symdiff.iterrows():
    country_data=[]
    dominant_pixels = []
    stops = []    
    country_code = row['ISO_A2'].lower()
    try:
        flag_image = Image.open(FLAGS_DIR+country_code+".png")
    except FileNotFoundError:
        continue
    
    flag_image = flag_image.convert("RGB")
    # SOURCE: https://stackoverflow.com/a/52879133/4698800
    pixels = flag_image.getcolors(flag_image.width * flag_image.height)
    sorted_pixels = sorted(pixels, key=lambda t: t[0])
    
    for pixel in pixels:
        if pixel[0]*100/(flag_image.width * flag_image.height) > 5:
            dominant_pixels.append(pixel)
    
    for pixel in dominant_pixels:
        percentage = pixel[0]*100/(flag_image.width * flag_image.height)
        color = "#%02x%02x%02x" % pixel[1]
        perc = reduce(lambda x,y: math.floor(x+y), {x['percentage'] for x in country_data}) if len(country_data) > 0 else 0
        stops.append('<stop offset="%s%%" stop-color="%s" stop-opacity="1"/><stop offset="%s%%" stop-color="%s" stop-opacity="1"/>'%(perc,color,perc+percentage,color))
        country_data.append({"color":color,"percentage":percentage})
    grad = '''<defs>
            <linearGradient x1="0" x2="0" y1="1" y2="0" id="%s">
                %s           
            </linearGradient>
            </defs>
            '''%(country_code,''.join(stops))
    def_rows.append(grad)

    p = process_to_svg_group(row)
    processed_rows.append(p)


props = {
    'version': '1.1',
    'baseProfile': 'full',
    'width': '100%',
    'height': '100%',
    'viewBox': '{}'.format(','.join(map(str, gismap.total_bounds))),
    'xmlns': 'http://www.w3.org/2000/svg',
    'xmlns:ev': 'http://www.w3.org/2001/xml-events',
    'xmlns:xlink': 'http://www.w3.org/1999/xlink'
}
template = '{key:s}="{val:s}"'
attrs = ' '.join([template.format(key=key, val=props[key]) for key in props])

raw_svg_str = textwrap.dedent(r'''
    <?xml version="1.0" encoding="utf-8" ?>
    <svg {attrs:s}>
    <g>{data:s}</g>
    {grads:s}
    </svg>
''').format(attrs=attrs, data=''.join(processed_rows),grads=''.join(def_rows)).strip()
with open('out/map.svg', 'w') as f:
    f.write(raw_svg_str)