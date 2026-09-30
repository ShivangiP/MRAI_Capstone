"""

# This is lambda script to trigger sagemaker tissue segmentation endpoint                        #
# Note : increase memory and timeout in config. Add endpoint as env variable                     #
# grab environment variables                                                                     #
# ex : ENDPOINT_NAME	DEMO-segmentation-prediction-endpoint                                    #
# set lambda timeout ~12 mins in configuration                                                   #
# create function url endpoint with CORS enabled with Access-Control-Allow-Headers: content-type #
# use monitor section to check cloud trail log                                                   #

"""
import os
import io
import boto3
import json
import csv

#Note : increase memory and timeout in config. Add endpoint as env variable
print("Loading Lambda Function")
# grab environment variables
# ex : ENDPOINT_NAME	DEMO-seg-prediction-endpoint
ENDPOINT_NAME = os.environ['ENDPOINT_NAME']

runtime = boto3.client("runtime.sagemaker")
def lambda_handler(event, context):
    # we simulate the data of a new call
    input_data = event#["image_id"]
    print("The input data is ",input_data)
    print("The input data is ",input_data['body'])
    # # Serialize the input data to JSON format
    midSliceRange=int(input_data['body']['slice_end_range']/2)
    
    #begining of first payload 
    
    payload = input_data['body']#json.dumps(input_data)
    payload['slice_start_range']=0
    payload['slice_end_range']=midSliceRange-1
    
    print("extracted first payload is ", payload)

    # invoking the endpoint ''
    response = runtime.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        ContentType="application/json",
        Body=payload,
    )
    
    #begining of first payload 
    
    payload = input_data['body']#json.dumps(input_data)
    payload['slice_start_range']=midSliceRange-1
    
    print("extracted second payload is ", payload)

    # invoking the endpoint ''
    response = runtime.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        ContentType="application/json",
        Body=payload,
    )
    
    print(response)
    result = json.loads(response["Body"].read().decode())
    print(result)
    return result