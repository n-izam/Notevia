// // Get the modal
// var modal = document.getElementById("myModal");

// // Get the button that opens the modal
// var btn = document.getElementById("addCategoryOffer","editCategoryOffer");

// // Get the <span> element that closes the modal
// var span = document.getElementsByClassName("close")[0];

// // When the user clicks on the button, open the modal
// btn.onclick = function() {
//   modal.style.display = "block";
// }

// // When the user clicks on <span> (x), close the modal
// span.onclick = function() {
//   modal.style.display = "none";
// }

// // When the user clicks anywhere outside of the modal, close it
// window.onclick = function(event) {
//   if (event.target == modal) {
//     modal.style.display = "none";
//   }
// }

// var modal = document.getElementById("myModal");
//     var addBtn = document.getElementsByClassName("addCategoryOffer");
//     var editBtn = document.getElementsByClassName("editCategoryOffer");
//     var closeBtn = document.getElementsByClassName("close")[0];
//     var cancelBtn = document.getElementById("cancelBtn");

//     var modalTitle = document.getElementById("modalTitle");
//     var modalSubmitBtn = document.getElementById("modalSubmitBtn");

//     // Open modal for Add
//     addBtn.onclick = function () {
//         modal.style.display = "block";
//         modalTitle.innerText = "Add the product Offer";
//         modalSubmitBtn.innerText = "Add";
//     }

//     // Open modal for Edit
//     editBtn.onclick = function () {
//         modal.style.display = "block";
//         modalTitle.innerText = "Edit the product Offer";
//         modalSubmitBtn.innerText = "Update";
//     }

//     // Close modal
//     closeBtn.onclick = function () {
//         modal.style.display = "none";
//     }

//     cancelBtn.onclick = function () {
//         modal.style.display = "none";
//     }

//     // Close when clicking outside
//     window.onclick = function (event) {
//         if (event.target == modal) {
//             modal.style.display = "none";
//         }
//     }

// for add and edit offers

// Get modal
// var modal = document.getElementById("myModal");

// // Get title & submit button text
// var modalTitle = document.getElementById("modalTitle");
// var modalSubmitBtn = document.getElementById("modalSubmitBtn");

// // Get all buttons that open modal
// var openBtns = document.querySelectorAll(".openOfferModal");

// // Get close span and cancel button
// var closeBtn = document.getElementsByClassName("close")[0];
// var cancelBtn = document.querySelector(".closeModal");

// // When clicking Add/Edit buttons
// openBtns.forEach(function(btn) {
//   btn.onclick = function() {
//     var action = btn.getAttribute("data-action");

//     if (action === "add") {
//       modalTitle.textContent = "Add the product Offer";
//       modalSubmitBtn.textContent = "Add";
//     } else if (action === "edit") {
//       modalTitle.textContent = "Edit the product Offer";
//       modalSubmitBtn.textContent = "Update";
//     }

//     modal.style.display = "block";
//   };
// });

// // Close modal on X or Cancel
// closeBtn.onclick = cancelBtn.onclick = function() {
//   modal.style.display = "none";
// };

// var modal = document.getElementById("myModal");// Get title & submit button text
// var modalTitle = document.getElementById("modalTitle");
// var modalSubmitBtn = document.getElementById("modalSubmitBtn");
// var openBtns = document.querySelectorAll(".openOfferModal");// Get all buttons that open modal
// var closeBtn = document.getElementsByClassName("close")[0];// Get close span and cancel button
// var cancelBtn = document.querySelector(".closeModal");
// // url path
// var offerForm = document.getElementById("offerForm");

// // When clicking Add/Edit buttons
// openBtns.forEach(function(btn) {
//   btn.onclick = function() {
//     var action = btn.getAttribute("data-action");
//     var categoryId = btn.getAttribute("data-category-id");

//     if (action === "add") {
//       modalTitle.textContent = "Add the Product Offer";
//       modalSubmitBtn.textContent = "Add";
//       // dynamically set form action using Django URL pattern
//       offerForm.action = `/addcategoryoffer/${categoryId}/`;
//     } else if (action === "edit") {
//       modalTitle.textContent = "Edit the Product Offer";
//       modalSubmitBtn.textContent = "Update";
//       // set edit URL similarly if you have edit feature
//       offerForm.action = `/edit-offer/${categoryId}/`;
//     }

//     modal.style.display = "block";
//   };
// });

// // Close modal on X or Cancel
// closeBtn.onclick = cancelBtn.onclick = function() {
//   modal.style.display = "none";
// };

// // Close modal on outside click
// window.onclick = function(event) {
//   if (event.target == modal) {
//     modal.style.display = "none";
//   }
// };


// for menu toggle
var el = document.getElementById("wrapper");
var toggleButton = document.getElementById("menu-toggle");

toggleButton.onclick = function () {
  el.classList.toggle("toggled");

};

// for crop and image product

