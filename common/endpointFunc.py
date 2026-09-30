"""
This script contains function for endpoint reference
"""

import uuid
import constants
from datetime import datetime
import boto3
import utilities

#client = boto3.client('s3')

# endpoint : function to be called when image is uploaded from UI
def upload_image_stats(file,echo1,echo2=None):
    """
    @params:
    echo1,echo2 : number of slices in echo1 and echo2 input by user from UI
    """
    try:
        stats={}
        # write your S3 upload h5 image code here 
        #write_file_to_s3(static_info['upload_image_bucketName'], fileContent, fileName, fileType=None, prefixName=static_info['upload_image_prefixName'])
        image_id=file #str(uuid.uuid4())[:8] #generates uuid
        uploaded_on=str(datetime.today().strftime('%Y-%m-%d-%H'))
        file_type='h5'
        stats['image_id'] = image_id
        stats['uploaded_on'] = uploaded_on
        stats['file_type'] = file_type
        stats['echo1'] = str(echo1)
        stats['echo2'] = str(echo2)
        #uploads stats 
        write_file_to_s3(static_info['stats_bucketName'], json.dumps(stats), image_id+'.json' , fileType='json', prefixName=static_info['prefix_uploadedImageStats'])
        
    except Exception as e: # work on python 3.x
        print('Failure in upload image stats function to S3: '+ str(e))
        
    return stats #display this on UI



def preprocessing_uploadedimages(uploadStats):
    """
    this function processing uploaded h5 images
    @params:
    uploadStats : {'image_id' : 'xyz' , 'uploadedOn' : '2023-10-03-01' , 'echo1' : '1' , 'echo2' : '0', 'file_type': 'h5'} 
    reads h5 file from  and writes to user-input-ui/extractedSlices/echo1/ or user-input-ui/extractedSlices/echo2/
    """
    bucketName=constants.static_info['upload_image_bucketName']
    prefixName=constants.static_info['upload_image_prefixName']
    imageFileName=bucketName+'/'+prefixName+'/'+uploadStats['image_id']+'.h5'
    imagesUploaded=list_all_objects_in_s3(bucketName,prefixName)
    image_stats=[]
    if imageFileName in imagesUploaded:
        image_stats_dict=dict()
        outputFileName=imageFileName.split('/')[-1].split('.')[0]
        image_stats_dict['image_fileName']=outputFileName
        print('Reading now..',outputFileName)

        #memory efficient as everytime downloadImage.h5 will be overwritten
        client.download_file(bucketName, prefixName+'/'+outputFileName+'.h5','uploadedImage.h5')
        with h5py.File('uploadedImage.h5', "r") as f:
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
    else:
        print('File not found !')
    write_file_to_s3('transactionLog',image_stats,'log_'+imageFileName+str(datetime.today().strftime('%Y-%m-%d-%H'))+'.txt',None,'uploaded')
    print('Writing completed for..',outputFileName,'No of slices in echo1 :',echo1_counter-1,' & in echo2 :',echo2_counter-1)
    return

def segmentation_model_allSliceOutput(image_id):
    return read_json_from_s3_to_df(bucketName=constants.static_info['stats_bucketName'], prefixName=constants.static_info['prefix_segmentationModelSliceStats')[0]


def segmentation_model_summary(image_id):
    return read_json_from_s3_to_df(bucketName=constants.static_info['stats_bucketName'], prefixName=constants.static_info['prefix_segmentationModelSummaryStats'])[0]


def pathology_model_allSliceOutput(image_id):
    return read_json_from_s3_to_df(bucketName=constants.static_info['stats_bucketName'], prefixName=constants.static_info['prefix_pathologyModelSliceStats'])[0]


def pathology_model_summary(image_id):
    return read_json_from_s3_to_df(bucketName=constants.static_info['stats_bucketName'], prefixName=constants.static_info['prefix_pathologyModelSummaryStats'])[0]


def retrieve_image_id(image_id):
    """
    This function will return existing user input image stats 
    @params
    image_id : UI image id
    """
    uploadedObjJsonStats=list_all_objects_in_s3(constants.static_info['stats_bucketName'],constants.static_info['prefix_uploadedImageStats'])
    filePath=constants.static_info['stats_bucketName']+'/'+constants.static_info['prefix_uploadedImageStats']+'/'+image_id+'.json'                                                                                                                     
    if filePath in uploadedObjJsonStats:
        return read_json_from_s3_to_df(constants.static_info['stats_bucketName'], constants.static_info['prefix_uploadedImageStats']+'/'+image_id+'.json')[0]
    else:
        return FILE_NOT_FOUND

# calls made in below order 
# upload_image_stats('MTR_133',1,1)
# uploadStats=read_json_from_s3_to_df(bucketName='stats-ui', prefixName='uploadedScanStats/MTR_133.json')
# preprocessing_uploadedimages(uploadStats[0])
