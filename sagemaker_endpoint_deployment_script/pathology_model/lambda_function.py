"""

# This is lambda script to trigger sagemaker pathology endpoint                                  #
# Note : increase memory and timeout in config. Add endpoint as env variable                     #
# grab environment variables                                                                     #
# ex : ENDPOINT_NAME	DEMO-pathology-prediction-endpoint                                       #
# set lambda timeout ~12 mins in configuration                                                   #
# create function url endpoint with CORS enabled with Access-Control-Allow-Headers: content-type #
# use monitor section to check cloud trail log                                                   #

"""
import os
import io
import boto3
import json
import csv


print("Loading Lambda Function")

ENDPOINT_NAME = os.environ['ENDPOINT_NAME']

runtime = boto3.client("runtime.sagemaker")
def lambda_handler(event, context):
    # we simulate the data of a new call
    input_data = event#["image_id"]
    print("The input data is ",input_data)

    #begining of payload 
    payload = input_data['body']
	
    print("extracted payload is ", payload)

    # invoking the endpoint
    response = runtime.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        ContentType="application/json",
        Body=payload,
    )
    
    print(response)
    result = json.loads(response["Body"].read().decode())
    print(result)
    return result