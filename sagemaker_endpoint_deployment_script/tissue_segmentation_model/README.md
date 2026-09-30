### Please follow below steps in order to deploy model as endpoint  

- Instantiate jupyter notebook instance (ml.t3.medium would work fine!)  
- Place the entire deployment folder content in sagemaker jupyter instance  
- Run segmentation_model_deployment notebook script  
- Increase service quota of g4dn.xlarge instance count for inference in case if it g4dn.xlarge is unavailable during execution of notebook  
- check cloud trail log of endpoint to see if model is getting loaded and endpoint is in service
- create lambda function and replace content of lambda_function.py file  
- follow steps mentioned in lambda_function.py file  
- check cloud trail log to validate there is no error during lambda function invoke
