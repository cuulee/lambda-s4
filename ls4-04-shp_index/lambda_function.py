# --------------- IMPORTS ---------------
import os
import boto3
import geopandas as gpd
import rasterio
from shapely.geometry import box

# --------------- Main handler ------------------

def lambda_handler(event, context):
    print(event)
    print(context)
    # establish some variables
    source_bucket = event['sourceBucket']
    source_key = event['sourceKey']

    # verify input is a cog
    if 'cog/' not in source_key:
        print("source key is not cog! exiting...")
        print(source_key)
        return

    filename = source_key.split("/")[-1]
    key_path = source_key.replace(filename, '')
    print(key_path)
    # connect to s3
    client = boto3.client('s3')
    # gather a list of keys in the COG sub directory for the collection
    cog_keys = []
    def get_keys(token=''):
        if token == '':
            response = client.list_objects_v2(Bucket=source_bucket,
                                              Prefix=key_path)
        else:
            response = client.list_objects_v2(Bucket=source_bucket,
                                              Prefix=key_path,
                                              ContinuationToken=token)
        print(response)
        for cog in response['Contents']:
            prefix = 's3://' + source_bucket + '/'
            s3_path = prefix + cog['Key']
            cog_keys.append(s3_path)
        if 'NextContinuationToken' in response.keys():
            get_keys(response['NextContinuationToken'])
    get_keys()
    print(str(len(cog_keys)) + " COG keys found.")
    # setup container for shapefile data
    df = gpd.GeoDataFrame(columns=['location','src_srs','geometry'])
    src_srs = "EPSG:3857"
    # fille shapefile data container
    for key in cog_keys:
        with rasterio.open(key) as dataset:
            print(dataset.profile)
            location = key.replace('s3://', '/vsis3/')
            bounds = dataset.bounds
            df = df.append({'location':location, 'src_srs': src_srs, 'geometry': box(bounds[0], bounds[1], bounds[2], bounds[3])},ignore_index=True)
    # write shapefile
    df.to_file("tile_index.shp")
    # setup upload keys
    band = source_key.split("/")[0]
    band_pre = band + "/"
    index_name = key_path.replace(band_pre, '').replace('cog/', '').replace('/', '_')
    print(index_name)
    shp_key = key_path + "tile_index/" + index_name
    print(shp_key)
    # upload shapefile
    shp_suffixes = ['.cpg', '.dbf', '.shp', '.shx']
    for sfx in shp_suffixes:
        filename = 'tile_index' + sfx
        keyname = shp_key + sfx
        print('uploading: ' + keyname)
        client.upload_file(filename, source_bucket, keyname)
    print("upload success!")


if __name__ == '__main__':
    test = {'sourceBucket': 'tnris-ls4', 'sourceKey': 'bw/countyDelete/agencyDelete_YYYY/frames/cog/02-08-60_6-107.tif'}
    lambda_handler(test, context='context')