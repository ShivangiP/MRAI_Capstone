from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

import io
from io import BytesIO
import os
import boto3
import h5py
import base64
import uuid
import torch
import requests
from urllib.parse import urlparse

import cv2
import matplotlib.pyplot as plt
import numpy as np
import json
import datetime

import logging
import concurrent.futures
from skimage.color import label2rgb
from intensity_normalization.normalize.nyul import NyulNormalize

# from utilities.py
# import utilities

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your desired list of origins or ["*"] to allow all origins
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

home_dir = os.path.expanduser("~")
log_file = os.path.join(home_dir, "myapp.log")
logging.basicConfig(filename=log_file, level=logging.INFO)

static_info = {
'upload_image_bucketName' : 'user-input-ui',
'upload_image_prefixName' : 'uploadedScans',
'stats_bucketName': 'stats-ui',
'prefix_uploadedImageStats': 'uploadedScanStats',
'prefix_segmentationModelSliceStats': 'segmentation/sliceInfo' , 
'prefix_segmentationModelSummaryStats': 'segmentation/summary' , 
 'prefix_pathologyModelSliceStats' : 'pathology/sliceInfo' , 
 'prefix_pathologyModelSummaryStats' : 'pathology/summary',
 'png_image_bucketName' : 'w210-h5-images'    
}

aws_access_key_id = "Dummy"
aws_secret_access_key = "Dummy"

session = boto3.Session(
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name='us-east-1'
)

client = session.client("s3")
nyul_normalizer = NyulNormalize()

global_h5_np_data = None


@app.get("/")
def read_root():
    return {"Hello": "World"}


"""
    API FUNCTIONS
"""

# generate UUID
@app.get("/generate_uuid")
def generate_uuid():
    return str(uuid.uuid4())

# saves pngs of all slices to bucket w210-h5-images
@app.get("/save_raw_images")
def save_raw_images(uuid:str):

    # get numpy of raw images in echo1 dataset
    # data = h5_to_numpy(uuid)

    # set bucket name
    bucket_name = static_info['png_image_bucketName']

    create_folder(bucket_name, uuid + '/raw-images')

    for i in range(1,161):
        image = load_npy_from_s3(static_info['upload_image_bucketName'], 
            'extractedSlices/echo1/' + uuid + '/' + uuid + '_' + str(i) + '.npy')
        # image = data['image_data'][:, :, i-1]

        save_image_to_s3(bucket_name, image, uuid, 'raw-images', str(i))

    return {"uuid": uuid,
    "status": "raw images successfully uploaded"}

# saves pngs of all slices + segmentation prediction to bucket w210-h5-images
@app.get("/save_segmentation_images")
def save_segmentation_images(uuid:str):
    print("entered save segmentation")

    # set bucket name
    bucket_name = static_info['png_image_bucketName']

    create_folder(bucket_name, uuid + '/segmentation')
    print("new segmentation folder created")

    for i in range(1,161):

        raw_image = load_npy_from_s3(static_info['upload_image_bucketName'], 
            'extractedSlices/echo1/' + uuid + '/' + uuid + '_' + str(i) + '.npy')

        segmentation_slice = read_json_file_from_s3(static_info['stats_bucketName'],
            static_info['prefix_segmentationModelSliceStats'] + '/' + uuid,
            uuid + '_' + str(i) + '.json')

        seg_image = np.array(segmentation_slice['slice_info'][0]['pred_mask'])

        save_segmentation_to_s3(bucket_name, raw_image, seg_image, uuid, 'segmentation', str(i))

    return {"uuid": uuid,
    "status": "segmentation images successfully uploaded"}

# Saves all slices within the h5 file to an s3 bucket
@app.get("/save_image")
def save_image(uuid:str):

    # get numpy of raw images in echo1 dataset
    data = h5_to_numpy(uuid, "echo1")
    print("this is the return numpy" + data)

    # set bucket name
    bucket_name = 'w210-h5-images'

    # create folders for raw images and for segmentation images
    create_folder(bucket_name, uuid + '/raw-images')
    create_folder(bucket_name, uuid + '/segmentation')

    # get temporary segmentation json here
    segmentation_data = segmentation_result()
    segmentation = segmentation_data['slice_info'][0]['pred_mask']
    segmentation_np = np.array(segmentation)

    # for all 160 images, upload the raw image and the segmentation image to the respective folders
    for i in range(1,161):
        image = data['image_data'][:, :, i-1]
        save_image_to_s3(bucket_name, image, uuid, 'raw-images', str(i))
        save_segmentation_to_s3(bucket_name, image, segmentation_np, uuid, 'segmentation', str(i))

    return {"bucket_name": bucket_name,
    "uuid": uuid,
    "status": "successfully uploaded"}


# Uploads image stats to s3 bucket
@app.get("/upload_image_stats")
def upload_image_stats(uuid:str):
    """
    @params:
    uuid generated from client-side
    """
    try:
        stats={}
        
        #write_file_to_s3(static_info['upload_image_bucketName'], fileContent, fileName, fileType=None, prefixName=static_info['upload_image_prefixName'])
        image_id=uuid
        uploaded_on=str(datetime.datetime.now().strftime('%Y-%m-%d-%H'))
        file_type='h5'
        stats['image_id'] = image_id
        stats['uploaded_on'] = uploaded_on
        stats['file_type'] = file_type
        #uploads stats 
        write_file_to_s3(static_info['stats_bucketName'], stats, image_id , fileType='json', prefixName=static_info['prefix_uploadedImageStats'])
        return stats
        #return {"image_id": image_id}

    except Exception as e: # work on python 3.x
        print('Failed to write numpy to S3: '+ str(e))

# Gets image base64 url from s3 bucket (comes after save_image)
@app.get("/get_image")
def get_image(bucketName: str, filePath:str):
    try:
        # Get the image object from S3
        obj = client.get_object(Bucket=bucketName, Key=filePath)
        image_data = obj['Body'].read()
        base64_data = base64.b64encode(image_data).decode('utf-8')
        data_url = f"data:image/png;base64,{base64_data}"

        # 'image_data' now contains the binary image data
        return data_url
    except Exception as e:
        print('Error fetching image from S3:', str(e))
        return None


@app.get("/segmentation_summary")
def segmentation_summary(uuid):

    data = read_json_file_from_s3(static_info['stats_bucketName'], 
        static_info['prefix_segmentationModelSummaryStats'], 
        uuid + '_tissue_summary.json')

    return data

@app.get("/pathology_summary")
def pathology_summary():

    data = read_json_file_from_s3(static_info['stats_bucketName'], 
        static_info['prefix_pathologyModelSummaryStats'], 
        uuid + '_pathology_summary.json')

    return data

@app.get("/segmentation_slice_summary")
def segmentation_slice_summary(uuid, slice_num):

    data = read_json_file_from_s3(static_info['stats_bucketName'], 
        static_info['prefix_segmentationModelSliceStats'] + '/' + uuid, 
        uuid + '_' + slice_num + '.json')

    return { "patellar cartilage": data['slice_info'][0]['tissue']['patellar cartilage'],
    "femoral cartilage": data['slice_info'][0]['tissue']['femoral cartilage'],
    "medial/lateral tibial cartilage": data['slice_info'][0]['tissue']['medial/lateral tibial cartilage'],
    "medial/lateral meniscus": data['slice_info'][0]['tissue']['medial/lateral meniscus']
    }

@app.get("/read_json_from_s3")
def read_json_file_from_s3(bucketName, prefixName, fileName):
    """ returns json file content
        @param
        bucketName : s3 bucket
        prefixName : s3 prefix to bucket
        fileName   : input json file Name
        [example of S3 bucket with prefix f"s3://{bucketName}/{prefix}"]
    """

    key = prefixName + '/' + fileName
    data = client.get_object(Bucket=bucketName, Key=key)
    contents = data['Body'].read()

    return json.loads(contents.decode("utf-8"))

@app.get("/preprocess_h5")
def preprocessing_uploadedimages(uploadStats, ifEcho1=True):
    """
    this function processing uploaded h5 images
    @params:
    uploadStats : {'image_id' : 'xyz' , 'uploadedOn' : '2023-10-03-01' , 'echo1' : '1' , 'echo2' : '0', 'file_type': 'h5'} 
    reads h5 file from  and writes to user-input-ui/extractedSlices/echo1/ or user-input-ui/extractedSlices/echo2/
    """
    uploadStats = json.loads(uploadStats)
    print("starting preprocessing uploadedimages")
    bucketName=static_info['upload_image_bucketName']
    prefixName=static_info['upload_image_prefixName']
    imageFileName=uploadStats['image_id']
    imageFullPrefix="user-input-ui/uploadedScans/"+imageFileName+'.h5'
    print("imageFileName, ", imageFileName)
    imagesUploaded=list_all_objects_in_s3(bucketName,prefixName)

    image_stats=[]
    if imageFullPrefix in imagesUploaded:
        image_stats_dict=dict()
        outputFileName=imageFileName.split('/')[-1].split('.')[0]
        image_stats_dict['image_fileName']=outputFileName
        print('Reading now..',outputFileName)

        #memory efficient as everytime downloadImage.h5 will be overwritten
        client.download_file(bucketName, prefixName+'/'+outputFileName+'.h5','downloadImage.h5')
        with h5py.File('downloadImage.h5', "r") as f:

            # Information present in h5 collection::f.keys()
            infoList=f.keys()
            if ifEcho1 and 'echo1' in infoList:
                echo1_slices=f["echo1"].shape[-1]
            else:
                echo1_slices=0
            if not ifEcho1 and 'echo2' in infoList:
                echo2_slices=f["echo2"].shape[-1]
            else:
                echo2_slices=0

            # Collecting some stats about h5 ----->
            image_stats_dict['info_in_h5']=infoList
            image_stats_dict['echo1_image_shape']=f["echo1"].shape
            image_stats_dict['echo2_image_shape']=f["echo2"].shape
            image_stats_dict['echo1_no_of_slices']=echo1_slices
            image_stats_dict['echo2_no_of_slices']=echo2_slices
            image_stats_dict['segmentation_shape']=f["seg"].shape
            image_stats_dict['segmentation_noOfClasses']=f["seg"].shape
            image_stats.append(image_stats_dict)

            echo1_list=[]
            echo2_list=[]
            segmentation_list=[]
            
            if ifEcho1:
                for i in range(echo1_slices):
                    echo1_list.append(f["echo1"][:, :, i])
            else:    
                for i in range(echo2_slices):
                    echo2_list.append(f["echo2"][:, :, i])

            #print("echo1_list", echo1_list)

            for i in range(echo1_slices):
                segmentation = f["seg"][:, :, i, :]  # Shape: (x, y, z, #classes)
                segmentation = one_hot_to_categorical(segmentation, channel_dim=-1)
                segmentation_list.append(segmentation)

            if ifEcho1:
                normalized_echo1=image_intensity_normalization(echo1_list)
                cliped_echo1=[clip_image(image) for image in normalized_echo1]
                
                echo1_counter=0
                for clips in cliped_echo1:
                    echo1_counter=echo1_counter+1
                    file_name='s3://user-input-ui/extractedSlices/echo1/'+ outputFileName + '/' +outputFileName+'_'+str(echo1_counter)+'.npy'
                    to_s3_npy(np.array(clips), file_name)
                
            if not ifEcho1:
                normalized_echo2=image_intensity_normalization(echo2_list)
                cliped_echo2=[clip_image(image) for image in normalized_echo2]

                echo2_counter=0
                for clips in cliped_echo2:
                    echo2_counter=echo2_counter+1
                    file_name='s3://user-input-ui/extractedSlices/echo2/'+ outputFileName + '/' +outputFileName+'_'+str(echo2_counter)+'.npy'
                    to_s3_npy(np.array(clips), file_name)

            f.close()
        print('Writing completed for..',outputFileName)
        return {"status": "Writing completed for.." + outputFileName}

"""
    NON-API FUNCTIONS
"""
 

def write_file_to_s3(bucketName, fileContent, fileName, fileType=None, prefixName=None):
    """
        @param
        bucketName : s3 bucket
        fileContent : data to be written
        fileName   : output file Name
        fileType : optional; valid values : json (to write JSON file) 
                                            dataframe (to write df as csv file)
                                            None (any default file format)
        prefixName : optional; s3 prefix to bucket
    """
    try:
        if prefixName:
            fileName=prefixName+'/'+fileName

        if fileType=='json':
            response = client.put_object(Bucket=bucketName, #'testshi'
                                         Body=(bytes(json.dumps(fileContent).encode('UTF-8'))), #json.dumps(fileContent),  # '{"content": "bytes or seekable file-like object"}',
                                         Key=fileName)  #'test.json' # 'Object key for which the PUT operation was initiated'
        elif fileType=='dataframe':
            fileContent.to_csv('s3://'+bucketName+'/'+fileName+'.csv', index=False)
        else:
            response = client.put_object( Bucket=bucketName, #'testshi'
                                         Body=fileContent, # '{"content": "bytes or seekable file-like object"}',
                                         Key=fileName) #'test.json' # 'Object key for which the PUT operation was initiated'
        print('Writing to S3 completed for ',fileName)
    except Exception as e: # work on python 3.x
        print('Failed to write numpy to S3: '+ str(e))


def create_folder(bucketName, folderName):
    client.put_object(Bucket=bucketName, Key=f'{folderName}/')

def save_segmentation_to_s3(bucket_name, image_data, segmentation_data, uuid, folder, slice_num):
    object_key = uuid+'/'+folder+'/'+slice_num+'.png'
    scale_factor = 1.5

    seg_colorized = label2rgb(segmentation_data, bg_label=0, bg_color=None)

    fig = plt.figure(figsize=((image_data.shape[1]/100) * scale_factor, (image_data.shape[0]/100) * scale_factor))

    plt.imshow(image_data, cmap = plt.cm.bone)
    plt.imshow(seg_colorized, alpha = 0.4)
    plt.axis('off')

    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight', pad_inches=0)
    buffer.seek(0)

    image_bytes = buffer.getvalue()
    client.put_object(Body=image_bytes, Bucket=bucket_name, Key=object_key)

    plt.close('all')


def save_image_to_s3(bucket_name, image_data, uuid, folder, slice_num):
    object_key = uuid+'/'+folder+'/'+slice_num+'.png'
    scale_factor = 1.5

    fig = plt.figure(figsize=((image_data.shape[1]/100) * scale_factor, (image_data.shape[0]/100) * scale_factor))

    #image_data_scaled = cv2.normalize(image_data, None, 0, 255, cv2.NORM_MINMAX) / 255
    plt.imshow(image_data, cmap = plt.cm.bone)
    plt.axis('off')

    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight', pad_inches=0)
    buffer.seek(0)

    image_bytes = buffer.getvalue()
    client.put_object(Body=image_bytes, Bucket=bucket_name, Key=object_key)

    plt.close('all')

# get h5 from s3 bucket and convert to numpy
def h5_to_numpy(uuid:str):

    try:
        # Get the file from the S3 bucket
        response = client.get_object(Bucket=static_info['upload_image_bucketName'], 
            Key=static_info['upload_image_prefixName'] + '/' + uuid + '.h5')

        # Read the file data as bytes
        file_data = response["Body"].read()

        # Open the .h5 file using h5py
        with h5py.File(io.BytesIO(file_data), "r") as f:
            # Access the dataset you want to convert to a numpy array
            dataset = f['echo1']

            # Convert the dataset to a numpy array
            np_array = np.array(dataset)
            # full_dataset = np.array((512,512), int)
            # img=np_array[:,:,100]

        return {"image_shape": np_array.shape,
        "image_data": np_array}

    except Exception as e:
        return {"error": str(e)}


def list_all_objects_in_s3(bucketName, prefixName=None):
    """Get a list of objects in an S3 bucket path.
    @params:
    bucketName : s3 bucket 
    prefixName : s3 prefix to bucket
    returns : list of objects in s3 path
    [example of S3 bucket with prefix f"s3://{bucketName}/{prefix}"]
    """
    paginator = client.get_paginator('list_objects_v2')
    if prefixName:
        pages = paginator.paginate(Bucket=bucketName, StartAfter=prefixName)
    else:
        pages = paginator.paginate(Bucket=bucketName)
    list_of_files=[]
    for page in pages:
        for obj in page['Contents']:
            files = bucketName+'/'+obj['Key']
            if prefixName:
                if bucketName+'/'+prefixName in files:
                    if bucketName+'/'+prefixName+'/' !=files:
                        list_of_files.append(files)
            else:
                list_of_files.append(files)
    return list_of_files

def one_hot_to_categorical(x, channel_dim: int = 1, background=False):
    """Converts one-hot encoded predictions to categorical predictions.

    Args:
        x (torch.Tensor | np.ndarray): One-hot encoded predictions.
        channel_dim (int, optional): Channel dimension.
            Defaults to ``1`` (i.e. ``(B,C,...)``).
        background (bool, optional): If ``True``, assumes index 0 in the
            channel dimension is the background.

    Returns:
        torch.Tensor | np.ndarray: Categorical array or tensor. If ``background=False``,
        the output will be 1-indexed such that ``0`` corresponds to the background.
    """
    is_ndarray = isinstance(x, np.ndarray)
    if is_ndarray:
        x = torch.as_tensor(x)

    if background is not None and background is not False:
        out = torch.argmax(x, channel_dim)
    else:
        out = torch.argmax(x.type(torch.long), dim=channel_dim) + 1
        out = torch.where(x.sum(channel_dim) == 0, torch.tensor([0], device=x.device), out)

    if is_ndarray:
        out = out.numpy()
    return out

def image_intensity_normalization(image_list: np.array):
    """
    returns normalized image
    @params 
    image_list : list of images (numpy array list) 
    """
    try:
        nyul_normalizer.fit(image_list)
        normalized_echo = [nyul_normalizer(image) for image in image_list]
        return normalized_echo
    except Exception as e:
        print('Image Intensity normalization failed. '+ str(e))


def clip_image(image_list: np.array):
    """
    returns clipped image
    @params :
    image_list : list of images (numpy array list).
    """
    try:
        clipped_image = np.clip(image_list / 255.0, 0, 1)
    except Exception as e:
        print('clipping image failed. '+ str(e))
    return clipped_image

def to_s3_npy(data: np.array, s3_uri: str):
    # s3_uri looks like f"s3://{BUCKET_NAME}/{KEY}"
    """
    @params 
    data : file content 
    s3_uri : s3 file path along with name [example of S3 bucket with prefix f"s3://{bucketName}/{prefix}/{fileName.npy}"]
    """
    try:
        bytes_ = BytesIO()
        np.save(bytes_, data, allow_pickle=True)
        bytes_.seek(0)
        parsed_s3 = urlparse(s3_uri)
        client.upload_fileobj(
            Fileobj=bytes_, Bucket=parsed_s3.netloc, Key=parsed_s3.path[1:]
        )
    except Exception as e: # work on python 3.x
        print('Failed to read numpy array from S3: '+ str(e))
    return True

def load_npy_from_s3(bucket_name, object_key):
    response = client.get_object(Bucket=bucket_name, Key=object_key)
    data = response['Body'].read()
    np_array = np.load(io.BytesIO(data))
    return np_array

