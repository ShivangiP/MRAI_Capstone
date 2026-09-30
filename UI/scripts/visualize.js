/*
* For testing visualization functionality
*/

function saveImage(uuid){
    const url = 'http://DUMMY:8000/save_image?uuid=' + uuid;
    fetch(url)
        .then(response => response.json())
        .then(data => {
            console.log(data); // Log the received data
        })
        .catch(error => console.error(error));

};

function getImage(bucketName, uuid, slice) {
  const params = {
    Bucket: bucketName,
    Key: `${uuid}/${slice}.png`
  };

  s3.getSignedUrl('getObject', params, (err, url) => {
    if (err) {
      console.error('Error getting signed URL:', err);
      return;
    }

    const imageElement = document.getElementById('imageCanvas');
    imageElement.src = url;
  });
}




/*
* Main
*/

const s3 = new AWS.S3({
    accessKeyId: "DUMMY",
    secretAccessKey: "DUMMY",
    region: 'us-east-1',
});

/*saveImage("4643191688938172522");*/
getImage("w210-h5-images", "4643191688938172522", "100");