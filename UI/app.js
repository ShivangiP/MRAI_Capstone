const express = require('express');
const app = express();
const fs = require('fs');
const requestIp = require('request-ip');

// API endpoint to retrieve access keys
app.get('/api/accesskeys', (req, res) => {
  // Read the contents of the secure config file
  const configFile = fs.readFileSync('secure-config.json');
  // Parse the JSON content of the file
  const config = JSON.parse(configFile);
  // Retrieve the access keys from the config object
  const accessKeyID = config.accessKeyId;
  const secretAccessKey = config.secretAccessKey;
  
  // Return the access keys to the client
  res.json({ accessKeyID, secretAccessKey });
});

// app.get('/api/publicip', (req, res) => {
//   fetch('http://169.254.169.254/latest/meta-data/public-ipv4')
//       .then(response => response.text())
//       .then(publicIPv4Address => {
//         res.json({ publicIPv4Address });
//       })
//       .catch(error => {
//         console.error('Error retrieving EC2 Public IPv4 address:', error);
//   });
// });


// Start the server
app.listen(3000, () => {
  console.log('Server started on port 3000');
});