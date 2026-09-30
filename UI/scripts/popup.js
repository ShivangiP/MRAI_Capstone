// Check if the user has agreed to the terms
function hasUserAgreed() {
  return document.cookie.includes('userAgreed=true');
}

// Show or hide the user agreement popup based on the user's agreement status
function toggleUserAgreementPopup() {
  var popupOverlay = document.getElementById('popup-overlay');
  popupOverlay.style.display = hasUserAgreed() ? 'none' : 'flex';
}

// Set the user agreement status to cookies
function setUserAgreed() {
  document.cookie = 'userAgreed=true; expires=Thu, 31 Dec 2099 23:59:59 UTC; path=/';
  toggleUserAgreementPopup();
}

// Add event listener to the agree button
document.addEventListener('DOMContentLoaded', function() {
var agreeButton = document.getElementById('agree-button');
agreeButton.addEventListener('click', setUserAgreed);
});

// Call the toggleUserAgreementPopup function on page load
window.addEventListener('load', toggleUserAgreementPopup);
