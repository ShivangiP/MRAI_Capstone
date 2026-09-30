## Steps to download data to AWS S3 Bucket

### Step 1: Create S3 Bucket in us-west-1 with all default settings.


### Step 2: Spin up EC2 instance
1. Amazon Machine Image (AMI): Ubuntu
2. Instance type: M5.xlarge
3. No key pair (because this instance is only for downloading the data)
4. Create security group that allows SSH and HTTPS traffic from the internet
5. 1024 GB Root volume
6. Specify IAM role full access to EC2 and S3

### Step 3: Launch instance
1. update and install relevant packages
```bash
sudo apt-get update -y
sudo apt-get install awscli -y
sudo apt-get install s3fs -y
```
2. mount S3 bucket and EC2 instance
```bash
sudo s3fs \
[S3 Bucket Name] \
[path in VM to be mounted to S3] \
-o iam_role=s3-ec2, nonempty, rw, allow_other, mp_umask=002 \
-o url=http://s3.us-west-1.amazonaws.com
```
For example:
```bash
sudo s3fs \
skm-dataset \
/home/ubuntu/skm_data_mount/ \
-o iam_role=s3-ec2, nonempty, rw, allow_other, mp_umask=002 \
-o url=http://s3.us-west-1.amazonaws.com
```
3. check if mount is successful
```bash
mount|grep s3fs
```
### Step 4: Download dataset
1. download AzCopy
```bash
wget https://aka.ms/downloadazcopy-v10-linux
```
2. expand archive
```bash
tar -xvf downloadazcopy-v10-linux
```
3. remove existing AzCopy version
```bash
sudo rm -rf /usr/bin/azcopy
```
4. move AzCopy
```bash
sudo cp ./azcopy_linux_amd64_*/azcopy /usr/bin/
```
5. start downloading
```bash
azcopy cp "[link to dataset]" "/home/ubuntu/skm_data_mount/skm-tea/" --recursive=true
```