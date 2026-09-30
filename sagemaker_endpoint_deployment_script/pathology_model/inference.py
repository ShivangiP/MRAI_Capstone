import albumentations as A
import albumentations.augmentations.functional as F

import copy
import cv2
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import pickle
import timm
import torch
import torchvision as tv
import torch.nn as nn
import json
import boto3
from io import BytesIO
from io import StringIO
from urllib.parse import urlparse
from albumentations.pytorch import ToTensorV2
from sklearn.model_selection import GroupKFold, KFold
import gc
from sklearn.metrics import (
    accuracy_score, 
    confusion_matrix,
    f1_score, 
    precision_score, 
    recall_score,
    roc_auc_score,
    balanced_accuracy_score,
    average_precision_score
)
from torch.cuda.amp import GradScaler
from torch.cuda.amp import autocast
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm
import time
import seaborn as sns
import constants
from  utilities import list_all_objects_in_s3, from_s3_npy, read_file_from_s3, write_file_to_s3
# import gdown
# import zipfile
import logging
from datetime import datetime


logger = logging.getLogger("sagemaker.config")
logger.setLevel(logging.DEBUG)

# Global variables
BACKBONE = "efficientnet_b1"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
if DEVICE == "cuda":
    BATCH_SIZE = 8
else:
    BATCH_SIZE = 2

# Custom model class
class LesionModel(nn.Module):
    def __init__(self, backbone):
        super().__init__()
        self.model = timm.create_model(backbone, pretrained=True, in_chans=1, num_classes=2)

    def forward(self, x):
        x = self.model(x)
        return x

    
def predict_lesion(x, model, device, verbose=False):
    """Predicts the lesion class for a given image.

    Args:
        x: An image to predict lesions for.
        model: A model to use to make predictions.
        device: A device to evaluate on.
        verbose: A boolean flag indicating whether or not to display additional information.
    """
    x = x.to(device, dtype=torch.float)[None, :]
    model = model.to(device)
    model.eval()
    with torch.no_grad():
        logits = model(x)
        y_pred = torch.nn.functional.softmax(logits, dim=-1)[0]
    if verbose:
        fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(4, 4))
        ax.imshow(np.transpose(x[0].cpu().numpy(), (1, 2, 0)))
        print(f"y_pred = {np.around(y_pred.cpu().numpy(), 3)}")

    return y_pred.detach().cpu().numpy()


def model_fn(model_dir):
    logger.info('Loading the model.')
    """Loads a model from a specified location.
    Args:
        path: A path to load model weights from.
        device: A device to place the model onto.

    Returns:
        model: The model with the loaded weights.
    """

    try:
        print('model path:',os.path.join(model_dir,'abnorm_efficientnetb1-f0.tph'))
        model=LesionModel(BACKBONE)
        weights = torch.load(os.path.join(model_dir,'abnorm_efficientnetb1-f0.tph'))
        model.load_state_dict(weights)
        logger.info('Done loading model')
        return model
    except Exception as e: # work on python 3.x
        logger.info('error in loading model: '+ str(e))


def input_fn(request_body, content_type='application/json'):
    try:
        logger.info('Deserializing the input data.')
        if content_type == 'application/json':
            input_data = json.loads(request_body)
            # image_id = input_data['image_id'] #h5 file without h5 extension
            logger.info(f'Input recieved Image id: {input_data}')
            return input_data
    except Exception as e: # work on python 3.x
        logger.info('error in input: '+ str(e))

    
def predict_fn(input_data, model):
    try:
        logger.info(f'running prediction : {input_data}')
        bucketName = "s3://user-input-ui/extractedSlices/echo1/" #skm-dataset"
        #prefixName = "skm-tea/qdess/v1-release/image_files"
        scan_id = input_data['image_id']#"MTR_173"

        # bucketName = "s3://skm-dataset-echo1/"
        # scan_id = "MTR_173"

        metadata_summary = {}
        metadata_summary = {
            "image_id" : scan_id,
            "abnormality": [],
            "summary": ""
        }
    
        threshold = 0.8
        abnorm_start, abnorm_end, abnorm_count = -1, -1, 0

        for sl in range(1, 161):

            img = from_s3_npy(bucketName + scan_id + "_" + str(sl) + ".npy")
            img = torch.from_numpy(img).unsqueeze(0)
            y_pred = predict_lesion(img, model, DEVICE, False)
            if y_pred[0] >= threshold:
                if abnorm_start == -1:
                    abnorm_start = sl
                    abnorm_end = sl
                else:
                    abnorm_end = sl

        if abnorm_start == -1:
            metadata_summary["abnormality"].append({"start_sl": None, "end_sl": None, "slice_count": 0})
            metadata_summary["summary"] = f"no pathology found"
        else:
            metadata_summary["abnormality"].append({"start_sl": abnorm_start, "end_sl": abnorm_end, "slice_count": abnorm_end - abnorm_start + 1})
            metadata_summary["summary"] = f"abnormality found on slice {abnorm_start} to slice {abnorm_end}"

        metadata_summary_json = json.dumps(metadata_summary)
        outSummaryFileName = scan_id + "_pathology_summary.json"
        write_file_to_s3(constants.static_info['stats_bucketName'], metadata_summary_json, outSummaryFileName, "json", constants.static_info['prefix_pathologyModelSummaryStats'])        
        return metadata_summary
    except Exception as e: # work on python 3.x
        logger.info('error in prediction: '+ str(e))
        

def output_fn(prediction, content_type):
    if content_type == "application/json":
        response = str(json.dumps(prediction))
    else:
        response = str(json.dumps(prediction))
    return response
