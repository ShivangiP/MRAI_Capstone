# MRAI : Magnetic Resonance Image Analysis Pipeline

## TEAM :  Annie He, Beijing Wu, Cindy Xun, Shivangi Pandey


Mission Statement :
>> “empowering radiologists in delivering timely and precise interpretation of the MRI scans”

How we do it ?

- an end-to-end pipeline with automated segmentation analysis and pathology detection algorithms for radiologists efficient diagnosis

- an integrable and assistive solution enhancing diagnostic capabilities for MRI scanners

Why do we do it ?

Currently, radiologists manually segment and detect potential diseases by iterating through each individual slice of an MRI scan. A single MRI scan can contain anywhere from dozens to hundreds of slices. This process is extremely time-intensive and subject to inter- and intra-observer variations such as image artifacts (ex. from motion), low tissue contrast. etc. This limits the use of routine MRI use in clinical practice.

## PRODUCT DEMO ::  [![DEMO LINK](/images/YoutubeVideo.PNG)](https://youtu.be/SvKnbiXA7lw)


## Dataset


Stanford Knee MRI Multi-Task Evaluation (SKM-TEA) Dataset | Authors: Arjun Desai (arjundd at stanford dot edu), Andrew Schmidt, Elka Rubin, Akshay Chaudhari & collaborators  
[Dataset Download](https://stanfordaimi.azurewebsites.net/datasets/4aaeafb9-c6e6-4e3c-9188-3aaaf0e0a9e7) | [Paper](https://openreview.net/forum?id=YDMFgD_qJuA)


### Access and Setup


To download the dataset, follow the instructions below. Note the dataset is 900GB in a compressed format and 1.6TB in the expanded format. Please ensure there is sufficient disk space to download and uncompress the data. Currently, the download does not support downloading different directories for different tracks separately. We are actively working to resolve this issue.

1. Navigate to [this page](https://stanfordaimi.azurewebsites.net/datasets/4aaeafb9-c6e6-4e3c-9188-3aaaf0e0a9e7).
1. On the top left corner, click the login button. Create a new account or log into an existing account.
1. Navigate back to the link above
1. Follow instructions for downloading the dataset.

### Data Overview


This dataset consists of raw k-space and image data acquired using quantitative double-echo-steady-state (qDESS) MRI knee scans of patients at Stanford Healthcare. Images were manually segmented for 4 tissues: (1) Patellar Cartilage, (2) Femoral Cartilage, (3) Tibial Cartilage, and (4) Meniscus. Images were also manually annotated with bounding boxes for pathology documented in radiologist reports.


### Directories

All data and annotations are stored in the directory structure shown below. Details of how data in each folder should be used are provided in the Tracks below.

- `annotations/`: Versioned splits of train/val/test data. See "Versioning" for more info.
- `files_recon_calib-24/`: Data related to the `Raw Data` track in HDF5 format
- `image_files/`: Data related to the `DICOM` track in HDF5 format
- `dicoms/`: Scanner-generated DICOM files. This should be used for visualization purposes only.
- `segmentation_masks/raw-data-track`: Ground truth segmentations (in Nifti format) for `Raw Data` track
- `segmentation_masks/dicom-track`: Ground truth segmentations (in Nifti format) for `DICOM` track
- `all_metadata.csv`: De-identified DICOM metadata for each scan

For this project we are considering these folders : annotations, image_files

#### Segmentations


The `seg` key holds one-hot encoded segmentations of key soft tissues in the knee. The order of these segmentations is as follows:

1. Patellar Cartilage
2. Femoral Cartilage
3. Tibial Cartilage - Medial
4. Tibial Cartilage - Lateral
5. Meniscus - Medial
6. Meniscus - Lateral

#### Bounding Boxes


See [Annotations and Dataset Splits](#annotations-and-dataset-splits) for detailed information contained in annotation csv. We create master annotation file for preprocessing.

## Annotations and Dataset Splits


Information for all dataset splits can be found in the annotation files, which are json files stored
in a similar manner to the [COCO annotation format](https://www.immersivelimit.com/tutorials/create-coco-annotations-from-scratch).
These annotation files are also versioned manually (see Versioning section below). Files are named
`{train, val, test}.json`, corresponding to the respective splits.

We break down the different components of the dictionary below:

```
{
    "info": {...},
    "categories": [...], <-- Only detection categories (not segmentation)
    "images": [...],
    "annotations": [...], <-- Only detection annotations (not segmentation)
}
```

### Info


The “info” section contains high level information about the split.
```
  "info": {
    "contributor": "Arjun Desai, Elka Rubin, Andrew Schmidt, Akshay Chaudhari",
    "description": "2020 Stanford qDESS Dataset - test",
    "year": "2020",
    "date_created": "2020-10-16 22:51:12 PDT",
    "version": "v0.0.1"
  },
```

### Images


The "images" section contains the complete list of scans in this split. This is simply a list of the 
scans and useful scan metadata. Note that image ids (`id`) are unique. A description of the keys and structure are shown below:

- `id`: The numeric image id
- `file_name`: The file holding this scan's information
- `msp_id`: The MedSegPy id (only useful for those using MedSegPy)
- `scan_id`: The scan id. This is the universal string used to track this scan.
- `subject_id`: The subject id
- `timepoint`: The timepoint of the scan (zero-indexed). i.e. The first scan, second scan, etc.
- `voxel_spacing`: The spacing for each voxel in mm. In same orientation as `orientation`
- `matrix_shape`: The shape of the matrix
- `orientation`: The orientation of the scan. `SI`- superior to inferior, `AP` - anterior to posterior, `LR` - left to right.
- `num_echoes`: The number of echoes. Should be 2 for all qDESS data
- `inspected`: If `True`, at least one labeler has looked at the image for labeling detection annotations.


```
"images": [
    {
      "id": 1,
      "file_name": "MTR_005.h5",
      "msp_id": "0000099_V00",
      "msp_file_name": "0000099_V00.h5",
      "scan_id": "MTR_005",
      "subject_id": 99,
      "timepoint": 0,
      "voxel_spacing": [0.3125, 0.3125, 0.8],
      "matrix_shape": [512, 512, 160],
      "orientation": ["SI", "AP", "LR"],
      "num_echoes": 2,
      "inspected": true
    },
    {...},
    ...
]
```

### Categories
The "categories" object contains a list of categories and each of those belongs to a supercategory.
The category is a combination of the pathology type and pathology subtype (e.g. Meniscus Tear - Myxoid).
There may be plans in the future to make tissue type an additional stratification level. This would
primarily affect the "Cartilage Lesion" categories, which are currently only separated by grade, but not
by tissue. If you would like to do tissues as well, you will have to reindex your categories (and annotations).

```
    "categories": [
        {
          "supercategory": "Meniscal Tear",
          "supercategory_id": 1,
          "id": 1,
          "name": "Meniscal Tear (Myxoid)"
        },
        {...},
    ]
```

### Tissues


The "tissues" object contains a list of tissues that are referenced in each annotation label

```
"tissues": [
    {
      "id": 1,
      "name": "Meniscus"
    },
    {...},
]
```

### Annotations


The "annotations" section has several components, which makes it a bit trickier to understand. It contains
a list of every individual detection (object) annotation from every scan in the dataset. For example,
if there are 10 Grade 2A cartilage lesions in a single scan, there will be 10 annotations corresponding to
these individual lesions for that scan alone.

The image id corresponds to a specific scan in the dataset.

The bounding box (bbox) format is [top left X position, top left Y position, top left Z position, deltaX, deltaY, deltaZ]. NOTE: X corresponds to row (SI), Y to column (AP), and Z (RL/LR) to depth.

The category id corresponds to a single category specified in the categories section.

Each annotation also has an id (unique to all other annotations in the dataset).

The confidence is on a scale of 0-5, where 0 is not confident at all and 5 is extremely confident. Feel free to filter labels by this scale.

The tissue id corresponds to a single tissue specified in the tissues section.

```
"annotations": [
    {
      "id": 1,
      "image_id": 1,
      "category_id": 6,
      "tissue_id": 1,
      "bbox": [
        304.0,
        297.0,
        87.0,
        20.0,
        35.0,
        20.0
      ],
      "confidence": 2.0,
    },
    {...},
    ...
]
```


## AWS Architecture  
![AWS Architecture](/images/AWSArch.PNG)

## S3 Buckets Setup  
Set up these buckets :  
a) Data folder : 
> skm-dataset/skm-tea/qdess/v1-release/image_files/  

b) User Input folder : 
> user-input-ui/uploadedScans  

c) Intermediate Status JSON folder :   
>stats-ui/uploadedScanStats  
stats-ui/segmentation/sliceInfo  
stats-ui/segmentation/summary  
stats-ui/pathology/sliceInfo  
stats-ui/pathology/summary  

## Preprocessing Setup

Please follow below steps :  
a) Download data and save it in bucket 'skm-dataset'. We will use 'skm-tea/qdess/v1-release/image_files/' for preprocessing. 

b) Execute [intial setup](https://github.com/wubeijing/W210_MR_Pipeline/blob/main/common/oneTimeDataPrep.py) to create master annotation file and extract numpy echo images from H5 file. Execute this function in c5.xlarge EC2 instance. Follow steps mentioned [here](https://github.com/wubeijing/W210_MR_Pipeline/blob/main/EDA/data_download.md).

c) For this project we will focus only on echo1 sagittal plane images  

## Models  
Tissue Segmentation :  
> Model : [U-Net model notebook](https://github.com/wubeijing/W210_MR_Pipeline/blob/main/model_notebooks/experiments/segmentation_unet.ipynb).  
> Evaluation: [Notebook](https://github.com/wubeijing/W210_MR_Pipeline/blob/main/model_notebooks/evaluation/seg_metrics_eval.ipynb).  

Pathology Detection :  
> Model & Evaluation : [EfficientNet model notebook](https://github.com/wubeijing/W210_MR_Pipeline/blob/main/model_notebooks/experiments/pathology_EfficientNet_abnormal.ipynb).  

## Sagemaker Endpoints
Follow these steps to setup [sagemaker endpoints](https://github.com/wubeijing/W210_MR_Pipeline/blob/main/sagemaker_endpoint_deployment_script/pathology_model/README.md).  


## Web UI 
1) Spin Apache web server using steps mentioned here : 
#### Steps starting from new instance ###
```
1. Create instance w/ key
(need to create key on laptop)
2. Install apache2 to instance (for ubuntu)
sudo apt update
sudo apt install -y apache2
3. Grant access to folder /var/www/html
sudo chown ubuntu:ubuntu /var/www/html
sudo chmod -R +rw /var/www/html
4. Grant access to index.html and images folder
sudo chmod 777 index.html
sudo chmod -R 777 images
```
2. Upload content of [UI](https://github.com/wubeijing/W210_MR_Pipeline/tree/main/UI) folder HTML on EC2 instance   

3. Start Fast API 

#### To start & connect to ec2 instance ####
```
start instance in aws
ssh -i ~/.ssh/w210_mrai.pem ubuntu@[public-ip-address]
public ip address changes each time
sudo systemctl start apache2
sudo service apache2 restart
http://[public-ip-address]

### If site is not updating with changes, stop web server and delete cache
sudo service apache2 stop
sudo a2enmod cache
sudo systemctl start apache2
sudo service apache2 restart

#### Location of UI files ####
/var/www/html/

#### copy UI files from local to apache ####
scp -i ~/.ssh/w210_mrai.pem https://github.com/wubeijing/W210_MR_Pipeline/tree/main/UI/* ubuntu@[public-ip-address]:/var/www/html/

#### location of api files ####
/home/ubuntu

#### copy api files from local to ec2 instance ####
scp -i ~/.ssh/w210_mrai.pem -r https://github.com/wubeijing/W210_MR_Pipeline/tree/main/API/* ubuntu@[public-ip-address]:/home/ubuntu

#### to start up api ####
uvicorn main:app --reload
uvicorn main:app --host 0.0.0.0 --port 8000
```

## H5 for website testing
Please use below H5 files for testing
Drive Link : [H5 Files](https://drive.google.com/drive/folders/1ZxlSfuh40H7gBQ9zZ_BPzm_k45srl0r2?usp=sharing)
