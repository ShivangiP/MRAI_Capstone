import os
import random
import shutil
import time
import warnings
import pandas as pd
import numpy as np
import h5py
import matplotlib.pyplot as plt
import torch
from tqdm.notebook import tqdm
from sklearn.model_selection import GroupKFold, KFold
import torch.nn as nn
import copy
import boto3
import json
from io import BytesIO
from io import StringIO
from urllib.parse import urlparse
import math
import skm_tea as st
from meddlr.data.data_utils import collect_mask
import timeit
from utilities import write_file_to_s3, is_json_file_exist_in_s3, from_s3_read_h5_echo,read_json_from_s3
import constants
import re
import tarfile
import yaml
import gdown
# import botocore
import zipfile
import logging
from datetime import datetime


logger = logging.getLogger("sagemaker.config")
logger.setLevel(logging.DEBUG)

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
    

def model_fn(model_dir):
    logger.info('Loading the model.')
    try:
        model = st.get_model_from_zoo(
                  cfg_or_file="download://https://drive.google.com/file/d/1z-fN626jAfc3-iRL5EvHvSD4vjvNJ84S/view?usp=drive_link",
                  weights_path="download://https://drive.google.com/file/d/1pM2RJLjwsMudV67xkWaUd1p_-Rm5Rj8Q/view?usp=drive_link",
                )

        logger.info('Done loading model')
        return model
    except Exception as e: # work on python 3.x
        logger.info('error in loading model: '+ str(e))


def input_fn(request_body, content_type='application/json'):
    try:
        logger.info('Deserializing the input data.')
        if content_type == 'application/json':
            input_data = json.loads(request_body)
            logger.info(f'Input recieved Image id: {input_data}')
            return input_data
    except Exception as e: # work on python 3.x
        logger.info('error in input: '+ str(e))

    
def predict_fn(input_data, model):
    try:
        logger.info(f'running prediction : {input_data}')
        bucketName = constants.static_info['upload_image_bucketName'] # place where h5 is uploaded #"skm-dataset"
        prefixName = constants.static_info['upload_image_prefixName'] # h5 file prefix #"skm-tea/qdess/v1-release/image_files"
        scan_id = input_data['image_id'] #"MTR_173" or "uuid" if image is saved as uuid
        slice_start_range=input_data['slice_start_range']
        slice_end_range=input_data['slice_end_range']

        s3_url = "s3://" + bucketName + "/" + prefixName + "/" + scan_id + ".h5" 
        echo1 = from_s3_read_h5_echo(s3_url)
        echo1 = torch.as_tensor(echo1).unsqueeze(0).unsqueeze(0).float()
        echo1 = (echo1 - echo1.mean()) / echo1.std()

        metadata_summary = {}
        metadata_summary = {
            "image_id" : scan_id,
            "patellar cartilage": [],
            "femoral cartilage": [],
            "medial/lateral tibial cartilage": [],
            "medial/lateral meniscus": [],
            "summary": ""
        }

        t1_start, t1_count = -1, 0
        t2_start, t2_count = -1, 0
        t3_start, t3_count = -1, 0
        t4_start, t4_count = -1, 0

        for sl in range(slice_start_range,slice_end_range): 

            tissue = [False, False, False, False]

            slice_no = sl+1

            metadata_sl = {}
            metadata_sl = {
                "image_id": scan_id,
                "slice_no": slice_no,
                "slice_info": []
            }

            echo1_sl = echo1[..., sl]

            with torch.no_grad():
                logits = model({"image": echo1_sl})["sem_seg_logits"]

            prediction = pred_to_categorical(logits, activation="sigmoid").squeeze(0)
            pred = prediction.detach().cpu().numpy()

            if 1 in np.unique(pred):
                tissue[0] = True
                if t1_start == 0:
                    t1_start = sl+1
                    t1_count = 1
                else:
                    t1_count += 1

            if 2 in np.unique(pred):
                tissue[1] = True
                if t2_start == 0:
                    t2_start = sl+1
                    t2_count = 1
                else:
                    t2_count += 1

            if 3 in np.unique(pred):
                tissue[2] = True
                if t3_start == 0:
                    t3_start = sl+1
                    t3_count = 1
                else:
                    t3_count += 1

            if 4 in np.unique(pred):
                tissue[3] = True
                if t4_start == 0:
                    t4_start = sl+1
                    t4_count = 1
                else:
                    t4_count += 1

            metadata_sl["slice_info"].append(
                {"pred_mask": pred.tolist(),
                 "tissue": {"patellar cartilage":tissue[0], "femoral cartilage":tissue[1], "medial/lateral meniscus":tissue[2], "medial/lateral tibial cartilage":tissue[3]}
                }
            )

            metadata_sl_json = json.dumps(metadata_sl)

            outFileName_md_sl = scan_id + "_" + str(slice_no) + ".json"
            write_file_to_s3(constants.static_info['stats_bucketName'], metadata_sl_json, outFileName_md_sl, "json", constants.static_info['prefix_segmentationModelSliceStats']+"/"+scan_id)


        outSummaryFileName = scan_id + "_tissue_summary.json"
        if outSummaryFileName in [f.split("/")[-1] for f in list_all_objects_in_s3(constants.static_info['stats_bucketName'], constants.static_info['prefix_segmentationModelSummaryStats'])]:
            metadata_summary = read_json_file_from_s3(constants.static_info['stats_bucketName'], constants.static_info['prefix_segmentationModelSummaryStats']+"/" + outSummaryFileName, outSummaryFileName)
            t1_start_p1 = metadata_summary["patellar cartilage"][0].get("start_sl")
            t1_end_p1 = metadata_summary["patellar cartilage"][0].get("end_sl")
            t1_count_p1 = metadata_summary["patellar cartilage"][0].get("slice_count")

            t2_start_p1 = metadata_summary["femoral cartilage"][0].get("start_sl")
            t2_end_p1 = metadata_summary["femoral cartilage"][0].get("end_sl")
            t2_count_p1 = metadata_summary["femoral cartilage"][0].get("slice_count")

            t3_start_p1 = metadata_summary["medial/lateral meniscus"][0].get("start_sl")
            t3_end_p1 = metadata_summary["medial/lateral meniscus"][0].get("end_sl")
            t3_count_p1 = metadata_summary["medial/lateral meniscus"][0].get("slice_count")

            t4_start_p1 = metadata_summary["medial/lateral tibial cartilage"][0].get("start_sl")
            t4_end_p1 = metadata_summary["medial/lateral tibial cartilage"][0].get("end_sl")
            t4_count_p1 = metadata_summary["medial/lateral tibial cartilage"][0].get("slice_count")

            metadata_summary["patellar cartilage"] = [{"start_sl": t1_start_p1, "end_sl": t1_end_p1 + t1_count, "slice_count": t1_count_p1 + t1_count}]
            metadata_summary["femoral cartilage"] = [{"start_sl": t2_start_p1, "end_sl": t2_end_p1 + t2_count, "slice_count": t2_count_p1 + t2_count}]
            metadata_summary["medial/lateral meniscus"] = [{"start_sl": t3_start_p1, "end_sl": t3_end_p1 + t3_count, "slice_count": t3_count_p1 + t3_count}]
            metadata_summary["medial/lateral tibial cartilage"] = [{"start_sl": t4_start_p1, "end_sl": t4_end_p1 + t4_count, "slice_count": t4_count_p1 + t4_count}]
        else:
            metadata_summary["patellar cartilage"].append(
            {"start_sl": t1_start, "end_sl": t1_start + t1_count - 1, "slice_count": t1_count}
            )
            metadata_summary["femoral cartilage"].append(
                {"start_sl": t2_start, "end_sl": t2_start + t2_count - 1, "slice_count": t2_count}
            )
            metadata_summary["medial/lateral meniscus"].append(
                {"start_sl": t3_start, "end_sl": t3_start + t3_count - 1, "slice_count": t3_count}
            )
            metadata_summary["medial/lateral tibial cartilage"].append(
                {"start_sl": t4_start, "end_sl": t4_start + t4_count - 1, "slice_count": t4_count}
            )

        metadata_summary_json = json.dumps(metadata_summary)

        write_file_to_s3(constants.static_info['stats_bucketName'], metadata_summary_json, outSummaryFileName, "json", constants.static_info['prefix_segmentationModelSummaryStats'])

        logger.info(f'prediction summary : {metadata_summary}')
        logger.info(f'prediction completed : {input_data}')
        return metadata_summary
    except Exception as e: # work on python 3.x
        logger.info('error in prediction: '+ str(e))

def output_fn(prediction, content_type):
    if content_type == "application/json":
        response = str(json.dumps(prediction))
    else:
        response = str(json.dumps(prediction))
    return response
