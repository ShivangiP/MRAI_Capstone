/*
 * GLOBAL VARIABLES
 */

let globalEC2PublicIPv4 = "18.215.176.219";
let uuid;
let segmentation_slice_summary;
let segmentation_summary;
const images_bucket_name = 'w210-h5-images';


/*
* GENERAL FUNCTIONS 
*/

/* display single html element */
function displayElement(id, display){
    const element = document.getElementById(id);
    element.style.display = display;
};

/* hide single html element */
function hideElement(id){
    const element = document.getElementById(id);
    element.style.display = 'none';
};

/* does a hard refresh on page only when there hasn't been one since last update */
function refresh() {
    var refresh = localStorage.getItem('refresh');

    if (refresh === null || refresh.trim() === '') {
        localStorage.setItem('refresh', 'refresh');
        location.reload(true);
    }
};

function elementExists(id) {
    const element = document.getElementById(id);
    if(element){
        return true;
    } else {
        //console.log(id +'element does not exist yet');
        return false;
    }
};


/*
* API FUNCTIONS 
*/

async function getImage(bucketName, filePath, slice_num, retryCount = 3, retryDelay = 10000, segmentation="") {
  try {
    const url = 'http://' + globalEC2PublicIPv4 + ':8000/get_image?bucketName=' + bucketName + '&filePath=' + filePath;
    const response = await fetch(url);

    const data = await response.json();
    if (data['status'] == 404){
        console.log('hitting this 404');
    } else {
        const id = filePath.split("/").pop() + segmentation;
        const seg = segmentation !== "";
        await createImgElement(data, id, slice_num, seg);
    }

  } catch (error) {
    console.log("error: " + error);
    console.log('or does it hit this bigger catch and seg: ' + segmentation);
    console.log("file path its catching on : " + filePath);
    if (retryCount > 0) {
      console.log("Retrying in 10 seconds...");
      await new Promise((resolve) => setTimeout(resolve, retryDelay));
      return getImage(bucketName, filePath, slice_num, retryCount - 1, retryDelay, segmentation);
    } else {
      console.log('this is the catch of the getImage function on filePath: ' + filePath);
      throw new Error("Image not found after retries.");
    }
  }
}

async function getSegmentationSliceSummary(uuid, slice_num) {
    const url = 'http://' + globalEC2PublicIPv4 + ':8000/segmentation_slice_summary?uuid=' + uuid + '&slice_num=' + slice_num;
    try {
        const response = await fetch(url);
        const data = await response.json();
        segmentation_slice_summary = JSON.stringify(data);
        console.log("slice summary: " + JSON.stringify(data));
        return JSON.parse(JSON.stringify(data));
    } catch (error) {
        console.error(error);
        throw error;
    }
}

function getSegmentationSummary(uuid) {
const url = 'http://' + globalEC2PublicIPv4 + ':8000/segmentation_summary?uuid=' + uuid;
  return fetch(url)
    .then(response => response.json())
    .then(data => {
      segmentation_summary = data;
      console.log("segmentation slice summary: " + segmentation_summary['medial/lateral meniscus']);
      console.log("segmentation slice summary: " + segmentation_summary['femoral cartilage']);
      updateTissueTable(data);
    })
    .catch(error => console.error(error));
};


/*
 * UPDATE FILE SUMMARY
 */

function updateFileSummary() {
    // get file summary information from local storage
    const file_summary = JSON.parse(localStorage.getItem('fileSummary'));
    console.log(file_summary);

    // get text elements from ID
    const uniqueIdentifier = document.getElementById('uniqueIdentifier');
    const uploadDate = document.getElementById('uploadDate');

    // fill in text elements
    uniqueIdentifier.textContent = uuid;
    uploadDate.textContent = file_summary['uploaded_on'] + ':00';

};


/*
 * UPDATE SEGMENTATION SUMMARY TABLE
 */

function updateTissueTable(segmentation_summary) {
    // get segmentation summary information from local storage
    //const segmentation_summary = JSON.parse(localStorage.getItem('segmentationSummary'));
    //const segmentation_summary = segmentation_slice_summary;
    console.log(segmentation_summary);

    // mapping of tissue to table row id
    var tissue_mapping = {
        'patellar cartilage': 'segsum-pc',
        'femoral cartilage': 'segsum-fc',
        'medial/lateral tibial cartilage': 'segsum-mltc',
        'medial/lateral meniscus': 'segsum-mlm'
    };

    // gets tissue table
    const tissueTable = document.getElementById('segmentation-summary-table');

    // gets all tissues listed in tissue table
    const tissues = tissueTable.querySelectorAll('td');

    // for each tissue
    tissues.forEach(td => {

        // get the tissue name
        const value = td.textContent.trim();
        console.log('tissue:' + value);

        // get id of row that this tissue is on
        const id = tissue_mapping[value];

        // get row element that tissue is on
        const row = document.getElementById(id);

        // get start slice
        const start_slice = segmentation_summary[value][0]['start_sl'];

        // get end slice
        const end_slice = segmentation_summary[value][0]['end_sl'];

        // get number of slices 
        const slice_count = segmentation_summary[value][0]['slice_count'];

        // create new td elements for each metric
        const start_table_value = document.createElement('td');
        start_table_value.textContent = start_slice;

        const end_table_value = document.createElement('td');
        end_table_value.textContent = end_slice;

        const count_table_value = document.createElement('td');
        count_table_value.textContent = slice_count;

        // add all new metrics to correct tissue row
        row.appendChild(start_table_value);
        row.appendChild(end_table_value);
        row.appendChild(count_table_value);

    });

};


/*
 * UPDATE PATHOLOGY SUMMARY TABLE
 */

function updatePathologyTable() {

    // get pathology results from local storage
    const pathology_summary = JSON.parse(localStorage.getItem('pathologySummary'));
    console.log('pathology_summary: ' + pathology_summary);

    // get document elements by id for all pathology table related elements
    const pathology_text = document.getElementById('pathology-summary-text');
    const pathology_metrics = document.getElementById('pathology-metrics');

    // set pathology text to summary
    pathology_text.textContent = pathology_summary['summary'];

    // get start slice
    const start_slice = pathology_summary['abnormality'][0]['start_sl'];

    // get end slice
    const end_slice = pathology_summary['abnormality'][0]['end_sl'];

    // get number of slices 
    const slice_count = pathology_summary['abnormality'][0]['slice_count'];

    // create new td elements for each metric
    const start_table_value = document.createElement('td');
    start_table_value.textContent = start_slice;

    const end_table_value = document.createElement('td');
    end_table_value.textContent = end_slice;

    const count_table_value = document.createElement('td');
    count_table_value.textContent = slice_count;

    // add all new metrics to correct tissue row
    pathology_metrics.appendChild(start_table_value);
    pathology_metrics.appendChild(end_table_value);
    pathology_metrics.appendChild(count_table_value);

};


/*
 * UPDATE VISUALIZATION
 */

/* For each image, grabs image from s3 and adds to container */
async function updateVisualization(fileName) {
  console.log("updating visualization now");

  for (let i = 1; i <= 160; i++) {
    const rawFilePath = fileName + "/raw-images/" + i.toString() + ".png";

    const segFilePath = fileName + "/segmentation/" + i.toString() + ".png";

    try {
      await getImage(images_bucket_name, rawFilePath, i, 3, 10000);
      await getImage(images_bucket_name, segFilePath, i, 3, 10000, "seg");
    } catch (error) {
      console.log('this is the catch of the for loop on id: ' + i);
    }
  }

};


/* create html div elements to add each element */
async function createImgElement(imageDataUrl, id, slice_num, seg=false) {

    const segmentation = document.getElementById('segmentation-images');
    segmentation_slice_summary = await getSegmentationSliceSummary(uuid, slice_num);
    console.log('segslicesummary here: ' + segmentation_slice_summary);

    // create new div that will hold image and slice information
    if (elementExists('div-' + id.split('.')[0])) {
        var newDiv = document.getElementById('div-' + id.split('.')[0]);
    } else {
        var newDiv = document.createElement('div');
        newDiv.id = 'div-' + id.split('.')[0];
        newDiv.classList.add('indiv-img-div');

        const segText = document.createElement('p')
        segText.innerHTML = 'Slice: ' + id.split('.')[0] + 
        '<br>patellar cartilage: ' + segmentation_slice_summary['patellar cartilage'] + 
        '<br>femoral cartilage: ' + segmentation_slice_summary['femoral cartilage'] + 
        '<br>medial/lateral tibial cartilage: ' + segmentation_slice_summary['medial/lateral tibial cartilage'] +
        '<br>medial/lateral meniscus: ' + segmentation_slice_summary['medial/lateral meniscus'];
        segText.classList.add('seg-overlay-text');

        newDiv.appendChild(segText);
        newDiv.style.display = 'none';
        newDiv.style.color = 'white';
    }

    // create image element & add image properties
    const imgElement = document.createElement('img');
    imgElement.src = imageDataUrl;
    imgElement.id = id;
    if (seg) {
        imgElement.style.display = 'none';
    };

    // add each div to segmentation div
    segmentation.appendChild(newDiv);

    // add image element to new div
    newDiv.appendChild(imgElement);
};


function addVisualizationScroll() {
    const parentDiv = document.getElementById('segmentation-images');

    parentDiv.addEventListener('scroll', function() {
        const parentDiv = document.getElementById('segmentation-images');
        const scrollPosition = parentDiv.scrollLeft;
        console.log('sp: ' + scrollPosition);
        const childDivs = parentDiv.getElementsByClassName('indiv-img-div');
        const childDivCount = parentDiv.childElementCount;
        console.log('childDivs: ' + childDivCount);

        // Calculate the index of the visible child div based on the scroll position and child div width
        const visibleChildIndex = Math.floor(scrollPosition / childDivs[0].offsetWidth);
        console.log('vis child: ' + visibleChildIndex);

        // Hide all child divs except the one at the visible index
        for (let i = 0; i < childDivs.length; i++) {
            if (i === visibleChildIndex) {
                childDivs[i].style.display = 'inline-block';
            } else {
                childDivs[i].style.display = 'none';
            }
        }
    });
};


/*
* UPDATE IMAGE RANGE
*/

/* Event listener for range filter on UI */
window.addEventListener("DOMContentLoaded", (event) => {

    // get form element that holds the range inputs
    var form = document.getElementById('update-image-range');

    form.addEventListener('submit', function(event) {
        // Prevent the form from being submitted
        event.preventDefault(); 

        // get min, max
        var range_min = document.getElementById("range-min").value;
        var range_max = document.getElementById("range-max").value;

        // convert min and max to integers
        range_min = parseInt(range_min);
        range_max = parseInt(range_max);

        // if min or max is empty, set to 0 or 160 respectively
        if (isNaN(range_min)) { range_min = 0 };
        if (isNaN(range_max)) { range_max = 160 };

        // if min is greater than max, display value error
        if (range_max < range_min) {

            displayElement("value-error", "block");

        } else {

            hideElement("value-error");

            // get full range from min to max
            const range = [];
            for (let i = range_min; i <= range_max; i++){
                range.push(i.toString());
            }

            // pass range to update images
            updateImageRange(range);

        };

        //addVisualizationScroll();
        console.log('min: ' + range_min.toString());
        console.log('max: ' + range_max.toString());        
    });
});


/* Updates the range of images shown on the UI */
function updateImageRange(rangeInput) {
    displayElement("toggle", "flex");
    displayElement("segmentation-images", "block");


    var maxInput = Math.max(...rangeInput);

    if (elementExists('div-'+maxInput.toString())) {

        const imageContainer = document.getElementById('segmentation-images');
        const imgElements = imageContainer.querySelectorAll('div');

        imgElements.forEach((div) => {
            const imgID = div.id.split('-')[1];

            if (!rangeInput.includes(imgID)) {
                div.style.display = "none";
            } else {
                div.style.display = "inline";
            }

        });
    } else {
        setTimeout(() => updateImageRange(rangeInput), 10000);
    }
};


/*
* SEGMENTATION TOGGLE
*/


/* Event listener for segmentation toggle on UI */
window.addEventListener("DOMContentLoaded", (event) => {

    // Get a reference to the checkbox element
    const toggleSwitch = document.getElementById('switch');

    // Add an event listener to the checkbox for the 'change' event
    toggleSwitch.addEventListener('change', function() {

        const imageContainer = document.getElementById('segmentation-images');
        const imgElements = imageContainer.querySelectorAll('img');

        // Check if the checkbox is checked (toggled on)
        if (toggleSwitch.checked) {

            // Perform actions when the toggle is on
            console.log('Toggle is on. Do something here...');
            console.log(imgElements);

            imgElements.forEach(image => {
                //console.log('imgID' + image.id);
                if (image.id.includes("seg")){
                    image.style.display="inline";
                } else {
                    image.style.display="none";
                }
            });
            
        } else {
            // Perform actions when the toggle is off
            console.log('Toggle is off.');

            imgElements.forEach(image => {
                if (!image.id.includes("seg")){
                    image.style.display="inline";
                } else {
                    image.style.display="none";
                }
            });
        }
    });

});

/*
 * MAIN
 */


window.addEventListener("DOMContentLoaded", (event) => {
    refresh();

    // update global variable uuid
    uuid = localStorage.getItem('uuid');

    // update file summary on page
    updateFileSummary();

    // get segmentation summary and update tissue table
    getSegmentationSummary(uuid);
    //getSegmentationSliceSummary(uuid);

    // update segmentation tissue table on page
    //updateTissueTable();

    // update pathology table on page
    updatePathologyTable();

    // update visualization
    updateVisualization(uuid);

});
