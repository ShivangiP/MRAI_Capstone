"""
this script prepares data from SKM-TEA dataset for model training
this is ONE TIME PROCESSING STEP which needs to be executed only ONCE
"""
import utilities
import pandas as pd
from datetime import datetime
import constants

def create_master_annotation_files(readBucketName,annotationFilePath, writeFilePath):
    """
    this function creates master annotation file 
    @params:
    readBucketName : S3 bucket names where annotations file are present 
    annotationFilePath: S3 File path where annotation files are present
    writeFilePath : S3 file path along with prefix where we master annotation files will be created
    """
    try:
        files=list_all_objects_in_s3(readBucketName,annotationFilePath)
        fileList=[x.split('/')[-1] for x in files]
        print('Files in s3 ::',fileList)
        bbox = pd.DataFrame()

        for fileName in fileList:
            print('Reading file ...',fileName)
            outputFileName=fileName.split('.')[0]+'_annotations'
            print('Writing data to file :: ',outputFileName)
            metadata=read_json_file_from_s3('skm-dataset', 'skm-tea/qdess/v1-release/annotations/v1.0.0/', fileName)
            annotations= pd.DataFrame(metadata["annotations"])
            categories = pd.DataFrame(metadata["categories"])
            cat_dict = dict(zip(categories.id, categories.name))
            cat_id_to_supercat_id = dict(zip(categories.id, categories.supercategory_id))
            supercat_dict = dict(zip(categories.supercategory_id, categories.supercategory))
            annotations["category"] = annotations["category_id"].map(cat_dict)
            annotations["supercat_id"] = annotations["category_id"].map(cat_id_to_supercat_id) 
            annotations["supercategory"] = annotations["supercat_id"].map(supercat_dict) 

            for ind in annotations.index:
                dict_row = annotations.iloc[ind].to_dict()
                for i in range(int(dict_row["bbox"][2]), (int(dict_row["bbox"][2]) + int(dict_row["bbox"][5]))):
                    dict_row["sl"] = i
                    dict_row["2d_bbox"] = [(dict_row["bbox"][1], dict_row["bbox"][0]), dict_row["bbox"][4], dict_row["bbox"][3]]
                    bbox = pd.concat([bbox, pd.DataFrame([dict_row])], ignore_index=True)

            write_file_to_s3(writeFilePath, bbox, outputFileName, 'dataframe')
    
        print('Creation of annotation files is completed')
    
    except Exception as e:
        print('Issue with creating annotation file :: '+ str(e))

    return

def preprocessing_skmimages(bucketName=None, prefix=None):
    """
    this function is one time and extracts echo1 and echo2 slices and persist it for model pickup
    @params:
    bucketName : S3 bucket names where h5 is present
    prefix: S3 File path where h5 is present
    """
    imageFileNames=list_all_objects_in_s3(bucketName,prefix)
    image_stats=[]
    for imageFileName in imageFileNames:
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
                file_name='s3://skm-dataset-echo1/'+outputFileName+'_'+str(echo1_counter)+'.npy'
                to_s3_npy(np.array(clips), file_name)

            echo2_counter=0
            for clips in cliped_echo2:
                echo2_counter=echo2_counter+1
                file_name='s3://skm-dataset-echo2/'+outputFileName+'_'+str(echo2_counter)+'.npy'
                to_s3_npy(np.array(clips), file_name)

            f.close()
        write_file_to_s3('transactionLog',image_stats,'log_'+str(datetime.today().strftime('%Y-%m-%d-%H'))+'.txt',None,None)
        print('Writing completed for..',outputFileName,'No of slices in echo1 :',echo1_counter-1,' & in echo2 :',echo2_counter-1)
        return



if __name__ == '__main__':
    create_master_annotation_files('skm-dataset', 'skm-tea/qdess/v1-release/annotations/v1.0.0/', 'master-annotation-files')
    preprocessing_skmimages('skm-dataset', 'skm-tea/qdess/v1-release/image_files/')