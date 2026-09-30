/*
 * GLOBAL VARIABLES & REQUIREMENTS
 */

let globalEC2PublicIPv4 = "TEST";
let s3;
let uuid;
let uploadedH5Bucket = 'user-input-ui';
let uploadedH5BucketPrefix = 'uploadedScans';
let uploadScanStats;
let completedFunctions = 0;
let totalFunctions = 190;

/*
 * GENERAL FUNCTIONS
 */

function displayElement(id, display){
    const element = document.getElementById(id);
    element.style.display = display;
};

function hideElement(id){
    const element = document.getElementById(id);
    element.style.display = 'none';
};

function wait(time) {
  return new Promise((resolve) => {
    setTimeout(() => {
      updateProcessingProgress();
      resolve();
    }, time);
  });
};


/*
* PYTHON FETCH
*/


function generateUUID() {
  const url = 'http://' + globalEC2PublicIPv4 + ':8000/generate_uuid';
  return fetch(url)
    .then(response => response.json())
    .then(data => {
      uuid = data;
    })
    .catch(error => console.error(error));
};

function upload_scan_stats(uuid){
    const url = 'http://' + globalEC2PublicIPv4 + ':8000/upload_image_stats?uuid='+uuid;
    fetch(url)
        .then(response => response.json())
        .then(data => {
            console.log(data);
            localStorage.setItem('fileSummary', JSON.stringify(data));
            uploadScanStats = JSON.stringify(data);
        })
        .catch(error => console.error(error));
};

function saveImage(uuid) {
  const url = 'http://' + globalEC2PublicIPv4 + ':8000/save_image?uuid=' + uuid;

  fetch(url)
    .then(response => response.json())
    .then(data => {
        console.log('Images have been saved to s3')
    })
    .catch(error => {
        console.error(error);
    });
};


function save_raw_images(uuid) {
    const url = 'http://' + globalEC2PublicIPv4 + ':8000/save_raw_images?uuid=' + uuid;
    return fetch(url)
        .then(response => response.json())
        .then(data => {
            console.log(data['status']);
            updateProcessingProgress();
        })
        .catch(error => console.error(error));
};

function save_segmentation_images(uuid) {
    const url = 'http://' + globalEC2PublicIPv4 + ':8000/save_segmentation_images?uuid=' + uuid;
    fetch(url)
        .then(response => response.json())
        .then(data => {
            console.log(data['status']);
            updateProcessingProgress();
        })
        .catch(error => console.error(error));
};


function segmentation_summary(uuid) {
    const url = 'http://' + globalEC2PublicIPv4 + ':8000/segmentation_summary?uuid=' + uuid
    fetch(url)
        .then(response => response.json())
        .then(data => {
            console.log(data);
            localStorage.setItem('segmentationSummary', JSON.stringify(data));
            console.log(localStorage.getItem('segmentationSummary'));
            updateProcessingProgress();
        })
        .catch(error => console.error(error));
};

function pathology_summary() {
    const url = 'http://' + globalEC2PublicIPv4 + ':8000/pathology_summary'
    fetch(url)
        .then(response => response.json())
        .then(data => {
            console.log('ps:' + data);
            localStorage.setItem('pathologySummary', JSON.stringify(data));
            console.log('pathology_summary:' + localStorage.getItem('pathologySummary'));
            updateProcessingProgress();
        })
        .catch(error => console.error(error));
};

function file_summary(bucket_name, prefix_name, uuid) {
    const url = 'http://' + globalEC2PublicIPv4 + ':8000/read_json_from_s3?bucketName=' + bucket_name + '&prefixName=' + prefix_name + '&fileName=' + uuid;
    fetch(url)
        .then(response => response.json())
        .then(data => {
            console.log(data);
            localStorage.setItem('fileSummary', JSON.stringify(data));
        })
        .catch(error => console.error(error));
};

function preprocess_h5(uploadStats) {
    updateProcessingProgress();
    const url = 'http://' + globalEC2PublicIPv4 + ':8000/preprocess_h5?uploadStats=' + encodeURIComponent(uploadStats);
    fetch(url)
        .then(response => response.json())
        .then(data => {
            console.log(data);
            console.log("Preprocessing Done, now off to model running and other things")
            runAllModels(uuid);
        })
        .catch(error => console.error(error));
};


/*
*  MODEL ENDPOINTS
*/

function segmentation_model(uuid) {
    const lambdaEndpoint = 'https://DUMMY.lambda-url.us-east-1.on.aws/';

    const payload = {
        "image_id": uuid,
        "slice_start_range": 0,
        "slice_end_range": 160
    };

    const requestOptions = {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    };

    console.log(requestOptions);


    return fetch(lambdaEndpoint, requestOptions)
        .then(response => response.json())
        .then(data => {
            console.log(data);
            localStorage.setItem('segmentationSummary', JSON.stringify(data));
            console.log(localStorage.getItem('segmentationSummary'));
        })
        .catch(error => {
            console.error('Error:', error);
        });
};

function pathology_model(uuid){
    const lambdaEndpoint = 'https://DUMMY.lambda-url.us-east-1.on.aws/';

    const payload = {
        "image_id": uuid
    };

    const requestOptions = {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    };

    console.log(requestOptions);

    return fetch(lambdaEndpoint, requestOptions)
        .then(response => response.json())
        .then(data => {
            console.log(data);
            localStorage.setItem('pathologySummary', JSON.stringify(data));
            console.log(localStorage.getItem('pathologySummary'));
        })
        .catch(error => {
            console.error('Error:', error);
            // Handle the error here if the request fails
    });

};

/*
 * IMAGE UPLOAD
 */

/* upload image to s3 */

async function uploadFileToS3(file){
    // define constants
    const uniqueId = uuid;
    const objectKey = uniqueId;

    // provide UUID to user on UI
    const send_user_id = document.getElementById("uniqueIdentifier");
    send_user_id.innerHTML = uniqueId;

    // upload summary stats of file
    upload_scan_stats(uniqueId);

    // define parameter dict to pass to function
    const params = {
        Bucket: uploadedH5Bucket,
        Key: uploadedH5BucketPrefix + '/' + objectKey+'.h5',
        Body: file,
    };

    // runs everything and shows loading bar while running
    showLoadingBarUpload(params);

};


/*
 * UPLOAD DROP & HOVER BEHAVIOR
 */

window.addEventListener("DOMContentLoaded", (event) => {

    const dropContainer = document.getElementById("dropcontainer")
    const fileInput = document.getElementById("image")

    dropContainer.addEventListener("dragover", (e) => {
        // prevent default to allow drop
        e.preventDefault()
    }, false)

    dropContainer.addEventListener("dragenter", () => {
        dropContainer.classList.add("drag-active")
    })

    dropContainer.addEventListener("dragleave", () => {
        dropContainer.classList.remove("drag-active")
    })

    dropContainer.addEventListener("drop", (e) => {
        e.preventDefault()
        dropContainer.classList.remove("drag-active")
        fileInput.files = e.dataTransfer.files
    })

});



/*
 * UPLOAD FILE LOADING BAR
 */

function updateProcessingLoadingBar(progress) {
  const progressBar = document.getElementById("processing-progress-bar");
  progressBar.style.width = progress + "%";
};

function updateProcessingProgress() {
  completedFunctions++;
  const progress = (completedFunctions / totalFunctions) * 100;

  updateProcessingLoadingBar(progress);

  if (completedFunctions < totalFunctions) {
    setTimeout(updateProcessingProgress, 500); // Adjust the delay (milliseconds) for more frequent updates
  } else {
    updatesAferModelRun();
  }
};

function showLoadingBarUpload(params) {

    // display loading bar
    displayElement('upload-loading-bar', 'block');

    // run upload function while uploading loading bar
    uploadFileWithProgress(params)
        .then(() => {
            // Hide the loading bar when the upload is complete
            hideElement('upload-loading-bar');
            displayElement('processing-loading-bar', 'block');
        })
        .catch(error => {
            console.error('Error:', error);
            hideElement('upload-loading-bar'); // Hide the loading bar in case of an error
        });
};


function uploadFileWithProgress(params) {

    // Wrap the s3.upload() task in a Promise to track progress
    return new Promise((resolve, reject) => {

        // create new s3 session
        const s3 = new AWS.S3({
            accessKeyId: "Test",
            secretAccessKey: "Test",
            region: 'us-east-1',
        });

        // create new request and update loading bar whie request is running
        const request = s3.upload(params);
        request.on('httpUploadProgress', progress => {
            const {
                loaded,
                total
            } = progress;
            const percentage = (loaded / total) * 100;

            // Update the loading bar progress
            const loadingBar = document.getElementById('upload-progress-bar');
            loadingBar.style.width = `${percentage}%`;
        });

        // resolve depending on error or success
        request.send((err, data) => {
            if (err) {
                console.error('Error uploading file:', err);
                reject(err);
            } else {
                console.log('File uploaded successfully:', data.Location);

                console.log("What is the uuid at this point? " + uuid);

                preprocess_h5(uploadScanStats);
                resolve(data);
            }
        });
    });
};


/*
* PROCESSING H5 FILE AND RUN MODEL
*/


async function process_h5(uuid) {
    await Promise.all([save_raw_images(uuid), segmentation_model(uuid)]);
    console.log("save_raw_images and segmentation_model completed");

    save_segmentation_images(uuid);
};

async function runAllModels(uuid) {

    process_h5(uuid);
    pathology_model(uuid);

};

async function updatesAferModelRun() {
    hideElement('processing-loading-bar');
    displayElement('successful-upload', 'block');
    displayElement('results-instructions', 'block');
};


/*
 * FORM SUBMISSIONS
 */


/* submit new upload */
window.addEventListener("DOMContentLoaded", (event) => {

    // pulls the contents of the upload image form - an h5 file
    var form = document.getElementById('upload_image');

    form.addEventListener('submit', function(event) {
        // Prevent the form from being submitted
        event.preventDefault(); 

        // Get the uploaded file
        var imageInput = document.getElementById('image');
        var file = imageInput.files[0]; 

        // hide successful upload by default
        hideElement('successful-upload');

        if (file) {
            // Call a function to process the file and apply it to the ML model
            generateUUID().then(() => {

                // Set uuid to localStorage for future use in other pages
                localStorage.setItem('uuid', uuid);
                localStorage.setItem('refresh', '');
                console.log('global uuid: ' + uuid);
                uploadFileToS3(file);
            });
        }
    })
});

/* retrieve old upload */
window.addEventListener("DOMContentLoaded", (event) => {

    var form = document.getElementById('retrieve_results');

    form.addEventListener('submit', function(event) {
        event.preventDefault(); // Prevent the form from being submitted

        const uuid = document.getElementById("image_retrieval").value;
        localStorage.setItem('uuid', uuid);
        localStorage.setItem('refresh', '');

        file_summary('stats-ui', 'uploadedScanStats', uuid);

        displayElement('results-instructions', 'block');
    });
});

/* View Results */
window.addEventListener("DOMContentLoaded", (event) => {

    document.getElementById("view-results").addEventListener("click", function() {

    const url = "http://" + globalEC2PublicIPv4 + "/results.html";
  
    // Open the URL in a new tab

    window.open(url, "_blank");
    });

});



/*
*  MAIN
*/

// window.addEventListener("DOMContentLoaded", (event) => {
//     // console.log("about to run segmentation_model");
//     // segmentation_model('028c53b5-3693-4498-b0f7-b977a6822474');
//     // testUploadedStats = {"image_id": "5f13b78b-5542-469e-a2dd-2bf96dc50b3b", "uploaded_on": "2023-07-31-20", "file_type": "h5"};
//     // preprocess_h5(JSON.stringify(testUploadedStats));
//     console.log("testing pathology model");
//     pathology_model('06ed89e5-4807-4359-b36e-62cadb82bf52');

// });




