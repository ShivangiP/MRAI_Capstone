"""
This script contains common functions that can be used across different task
"""
import boto3
import json
import pandas as pd
from io import BytesIO
import numpy as np
from urllib.parse import urlparse
from intensity_normalization.normalize.nyul import NyulNormalize
import h5py
import torch
import meddlr.ops as oF
import matplotlib.pylab as plt
import botocore

client = boto3.client('s3')
nyul_normalizer = NyulNormalize()

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

def read_json_file_from_s3(bucketName, prefixName):
    """ returns json file content
        @param
        bucketName : s3 bucket
        prefixName : s3 prefix to bucket with file name
        [example of S3 bucket with prefix f"s3://{bucketName}/{prefix}"]
    """
    result = client.list_objects(Bucket = bucketName, Prefix=prefixName)
    for o in result.get('Contents'):
        data = client.get_object(Bucket=bucketName, Key=o.get('Key'))
        contents = data['Body'].read()
    return json.loads(contents.decode("utf-8"))


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
        if fileType=='dataframe':
            fileContent.to_csv('s3://'+bucketName+'/'+fileName+'.csv', index=False)
        else:
            response = client.put_object( Bucket=bucketName, #'testshi'
                                         Body=fileContent, # '{"content": "bytes or seekable file-like object"}',
                                         Key=fileName) #'test.json' # 'Object key for which the PUT operation was initiated'
        print('Writing to S3 completed for ',fileName)
    except Exception as e: # work on python 3.x
        print('Failed to write numpy to S3: '+ str(e))
    return


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

def from_s3_npy(s3_uri: str):
    """
    @params 
    data : file content 
    s3_uri : s3 file path along with name [example of S3 bucket with prefix f"s3://{bucketName}/{prefix}/{fileName.npy}"]
    """
    try:
        bytes_ = BytesIO()
        parsed_s3 = urlparse(s3_uri)
        client.download_fileobj(
            Fileobj=bytes_, Bucket=parsed_s3.netloc, Key=parsed_s3.path[1:]
        )
        bytes_.seek(0)
        np_data=np.load(bytes_, allow_pickle=True)
    
    except Exception as e: # work on python 3.x
        print('Failed to read numpy array from S3: '+ str(e))
    return np_data

def image_intensity_normalization(image_list: np.array):
    """
    returns normalized image
    @params 
    image_list : list of images (numpy array list) 
    """
    try:
        nyul_normalizer.fit(image_list)
        normalized_echo = [nyul_normalizer(image) for image in image_list]
    except Exception as e:
        print('Image Intensity normalization failed. '+ str(e))
    return normalized_echo

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

def plot_intensity_hist(fileName: str, echo_list: np.array,normalized : np.array, numOfSlices: int, whichEcho='echo1'):
    """
    plots intensity histogram between echos and corresponding normalized images
    @params :
    fileName : h5 image file name. This is used for title
    echo_list : echo image numpy list
    normalized : normalized numpy array
    numOfSlices : number of slices for plot. Max 4 allowd
    whichEcho : string; optional; default=echo1 . This is used for title 
    """
    noOfImages=4 #max number of images allowed in this func
    if noOfImages>numOfSlices:
        noOfImages=numOfSlices

    fig, axes = plt.subplots(2, noOfImages, figsize = (4, 4))
    plt.subplots_adjust(wspace=.5, hspace=.5)
    for i in range(noOfImages):
        axes[0][i].hist(echo_list[i].ravel(), 256, [0, 256])
        axes[1][i].hist(normalized[i].ravel(), 256, [0, 256])
    axes[0][0].set_title(fileName+" "+whichEcho+" original")
    axes[1][0].set_title(fileName+" "+whichEcho+" normalized")
    plt.show()

def plot_normalized_images(fileName, numOfSlices,whichEcho, original_echo, normalized_image, clipped_image):
    """
    plots echos and corresponding normalized images along with clipped image
    @params :
    fileName : h5 image file name
    echo_list : echo image numpy list
    normalized : normalized numpy array
    numOfSlices : number of slices for plot. Max 4 allowd
    whichEcho : string; optional; default=echo1 . This is used for title 
    """
    noOfImages=4 #max number of images allowed in this func
    if noOfImages>numOfSlices:
        noOfImages=numOfSlices
    fig, axes = plt.subplots(3, noOfImages, figsize = (5, 5))
    for i in range(4):
        axes[0][i].imshow(original_echo[i], cmap = plt.cm.bone)
        axes[0][i].axis("off")
        axes[1][i].imshow(normalized_image[i], cmap = plt.cm.bone)
        axes[1][i].axis("off")
        axes[2][i].imshow(clipped_image[i], cmap = plt.cm.bone)
        axes[2][i].axis("off")
    axes[0][0].set_title(fileName+" "+whichEcho+" original")
    axes[1][0].set_title(fileName+" "+whichEcho+" normalized")
    axes[2][0].set_title(fileName+" "+whichEcho+" clipped")

    
def preprocessing_uploadedimages(uploadStats):
    """
    this function processing uploaded h5 images
    @params:
    uploadStats : {'image_id' : 'xyz' , 'uploadedOn' : '2023-10-03-01' , 'echo1' : '1' , 'echo2' : '0', 'file_type': 'h5'} 
    reads h5 file from  and writes to user-input-ui/extractedSlices/echo1/ or user-input-ui/extractedSlices/echo2/
    """
    bucketName=constants.static_info['upload_image_bucketName']
    prefixName=constants.static_info['upload_image_prefixName']
    imageFileName=uploadStats['image_id']
    imagesUploaded=list_all_objects_in_s3(bucketName,prefix)
    image_stats=[]
    if imageFileName in imagesUploaded:
        image_stats_dict=dict()
        outputFileName=imageFileName.split('/')[-1].split('.')[0]
        image_stats_dict['image_fileName']=outputFileName
        print('Reading now..',outputFileName)

        #memory efficient as everytime downloadImage.h5 will be overwritten
        client.download_file(bucketName, prefix+outputFileName+'.h5','downloadImage.h5')
        with h5py.File('downloadImage.h5', "r") as f:
            # Information present in h5 collection::f.keys()
            infoList=f.keys()
            if 'echo1' in infoList:
                echo1_slices=f["echo1"].shape[-1]
            else:
                echo1_slices=0
            if 'echo2' in infoList:
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

            for i in range(echo1_slices):
                echo1_list.append(f["echo1"][:, :, i])
                
            for i in range(echo2_slices):
                echo2_list.append(f["echo2"][:, :, i])

            for i in range(echo1_slices):
                segmentation = f["seg"][:, :, i, :]  # Shape: (x, y, z, #classes)
                segmentation = oF.one_hot_to_categorical(segmentation, channel_dim=-1)
                segmentation_list.append(segmentation)

            normalized_echo1=image_intensity_normalization(echo1_list)
            normalized_echo2=image_intensity_normalization(echo2_list)

            cliped_echo1=[clip_image(image) for image in normalized_echo1]
            cliped_echo2=[clip_image(image) for image in normalized_echo2]

            echo1_counter=0
            for clips in cliped_echo1:
                echo1_counter=echo1_counter+1
                file_name='s3://user-input-ui/extractedSlices/echo1/'+outputFileName+'_'+str(echo1_counter)+'.npy'
                to_s3_npy(np.array(clips), file_name)

            echo2_counter=0
            for clips in cliped_echo2:
                echo2_counter=echo2_counter+1
                file_name='s3://user-input-ui/extractedSlices/echo2/'+outputFileName+'_'+str(echo2_counter)+'.npy'
                to_s3_npy(np.array(clips), file_name)

            f.close()
        write_file_to_s3('transactionLog',image_stats,'log_'+imageFileName+str(datetime.today().strftime('%Y-%m-%d-%H'))+'.txt',None,'uploaded')
        print('Writing completed for..',outputFileName,'No of slices in echo1 :',echo1_counter-1,' & in echo2 :',echo2_counter-1)
        return
    
    
def read_json_from_s3_to_df(bucketName, prefixName):
    """
    @params 
    bucketName : S3 bucket where json resides ex: 'stats-ui'
    prefixName : S3 file path containing json file name and is without bucketname ex: 'uploadedScanStats/MTR_133.json'
    returns list of dict
    """

    s3 = boto3.resource('s3')
    my_bucket_source = s3.Bucket(bucketName)

    for obj in my_bucket_source.objects.filter(Prefix=prefixName):
            data_location = 's3://{}/{}'.format(obj.bucket_name, obj.key)
            data = pd.read_json(data_location, lines = True )
    return data.to_dict('records')

def read_file_from_s3(bucket, file):
    try:
        s3 = boto3.resource('s3')
        obj = s3.Object(bucket, file)
        data = obj.get()["Body"]
        
    except Exception as e: # work on python 3.x
        print("Failed to read file from S3: "+ str(e))
    return data.read().decode(encoding="utf-8")

def from_s3_read_h5_echo(s3_uri: str):
    """
    @params 
    data : file content 
    s3_uri : s3 file path along with name [example of S3 bucket with prefix f"s3://{bucketName}/{prefix}/{fileName.h5}"]
    """
    try:
        
        bytes_ = BytesIO()
        parsed_s3 = urlparse(s3_uri)
        client.download_fileobj(
            Fileobj=bytes_, Bucket=parsed_s3.netloc, Key=parsed_s3.path[1:]
        )
        bytes_.seek(0)
        with h5py.File(bytes_, "w") as f:
            echo1 = f["echo1"][()]

    except Exception as e:
        print("Failed to read numpy array from S3: "+ str(e))
    return echo1

def generate_segmentation_summary(sliceJSON):
    """
    this function will generate summary from sliceJson. Will be used after model generates output.
    """
    sliceJson=read_json_from_s3_to_df(bucketName=constants.static_info[stats_bucketName], prefixName='prefix_segmentationModelSliceStats')[0]
    pass

def generate_pathology_summary(sliceJSON):
    """
    this function will generate summary from sliceJson. Will be used after model generates output.
    """
    sliceJson=read_json_from_s3_to_df(bucketName=constants.static_info[stats_bucketName], prefixName='prefix_pathologyModelSliceStats')[0]
    pass

"""
Below functions are used by models
"""

def pred_to_categorical(pred_or_logits, activation, channel_dim: int = 1, threshold: float = 0.5):
    """Converts one-hot encoded predictions or logits to category.

    Args:
        pred_or_logits: One-hot encoded predictions or logits. Shape BxCx...
        activation (str): Activation to use.
            Either ``'sigmoid'`` or ``'softmax'`` if ``pred_or_logits`` are logits.
            If `None` or '', assumes that `pred` does not need to be passed through
            activation function. If 'softmax', should include a background class.
        include_background (bool): If `True`, the first slice of class dimension (``C``)
            will not be dropped.
    """
    if activation not in [None, "", "sigmoid", "softmax"]:
        raise ValueError(f"activation '{activation}' not supported'")

    pred = pred_or_logits
    is_ndarray = isinstance(pred, np.ndarray)
    if is_ndarray:
        pred = torch.from_numpy(pred)

    if activation == "sigmoid":
        # TODO: Validate this case.
        out = one_hot_to_categorical(torch.sigmoid(pred) > threshold, channel_dim=channel_dim)
    elif activation == "softmax":
        out = torch.argmax(pred, dim=channel_dim)
    elif activation in (None, ""):
        # if not activation specified, assume it is one-hot encoded.
        out = one_hot_to_categorical(pred, channel_dim=channel_dim)
    else:
        raise ValueError(f"activation '{activation}' not supported'")

    if is_ndarray:
        out = out.numpy()
    return out

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


def is_json_file_exist_in_s3(bucket_name, file_key):
    """
    Check if a JSON file exists in the specified AWS S3 bucket.

    Args:
        bucket_name (str): The name of the S3 bucket.
        file_key (str): The key (path) of the JSON file in the S3 bucket.

    Returns:
        bool: True if the JSON file exists, False otherwise.
    """
    try:
        client.head_object(Bucket=bucket_name, Key=file_key)
        return True
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            # Handle other errors if necessary
            raise
        
        
def read_json_from_s3(bucket_name, file_key):
    """
    Read a JSON file from the specified AWS S3 bucket.

    Args:
        bucket_name (str): The name of the S3 bucket.
        file_key (str): The key (path) of the JSON file in the S3 bucket.

    Returns:
        dict: The JSON data read from the file.

    Raises:
        botocore.exceptions.ClientError: If the file does not exist or if there's an error reading it.
    """
    response = client.get_object(Bucket=bucket_name, Key=file_key)
    data = response['Body'].read().decode('utf-8')
    return json.loads(data)

