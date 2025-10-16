// headder scroll down style

// Script to hide header on scroll down
let lastScrollTop = 0;
const header = document.querySelector('header');
window.addEventListener('scroll', function() {
    let scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    if (scrollTop > lastScrollTop && scrollTop > 200) { // Disappears after scrolling 200px down
        header.classList.add('header-scrolled');
    } else {
        header.classList.remove('header-scrolled');
    }
    lastScrollTop = scrollTop;
});

// This JavaScript will handle the image gallery and quantity selector functionality.

document.addEventListener('DOMContentLoaded', function() {
    const thumbnails = document.querySelectorAll('.thumbnail');
    const mainImage = document.getElementById('mainProductImage');
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    let currentIndex = 0;

    // Function to update the main image and active thumbnail
    function updateGallery(index) {
        // Update main image
        mainImage.src = thumbnails[index].src;
        // Update active state on thumbnails
        thumbnails.forEach(thumb => thumb.classList.remove('active'));
        thumbnails[index].classList.add('active');
        currentIndex = index;
    }

    // Event listener for thumbnail clicks
    window.changeImage = function(element) {
        const index = Array.from(thumbnails).indexOf(element);
        updateGallery(index);
    };

    // Event listeners for prev/next buttons
    prevBtn.addEventListener('click', () => {
        let newIndex = (currentIndex - 1 + thumbnails.length) % thumbnails.length;
        updateGallery(newIndex);
    });

    nextBtn.addEventListener('click', () => {
        let newIndex = (currentIndex + 1) % thumbnails.length;
        updateGallery(newIndex);
    });

    // Quantity Selector Logic
    const minusBtn = document.getElementById('minus-btn');
    const plusBtn = document.getElementById('plus-btn');
    const quantityInput = document.getElementById('quantity-input');

    minusBtn.addEventListener('click', () => {
        let currentValue = parseInt(quantityInput.value);
        if (currentValue > 1) {
            quantityInput.value = currentValue - 1;
        }
    });

    plusBtn.addEventListener('click', () => {
        let currentValue = parseInt(quantityInput.value);
        quantityInput.value = currentValue + 1;
    });

    // Ruling Type Buttons Logic
    const rulingButtons = document.querySelectorAll('.btn-ruling');
    const rulingTypeText = document.getElementById('ruling-type-text');
    rulingButtons.forEach(button => {
        button.addEventListener('click', () => {
            rulingButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            rulingTypeText.textContent = button.textContent;
        });
    });
});

// zoom effect product detail view

// === Existing function to change images when a thumbnail is clicked ===
function changeImage(thumbnailElement) {
    const mainImage = document.getElementById('mainProductImage');
    mainImage.src = thumbnailElement.src;

    // Update the active state for thumbnails
    document.querySelectorAll('.product-thumbnails .thumbnail').forEach(thumb => {
        thumb.classList.remove('active');
    });
    thumbnailElement.classList.add('active');
}


// === In-Place Image Zoom on Hover ===

document.addEventListener('DOMContentLoaded', function() {
    const container = document.querySelector('.main-image-container');
    const img = document.getElementById('mainProductImage');
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');

    if (container && img) {
        // Event listener for mouse movement over the container
        container.addEventListener('mousemove', function(e) {
            // Prevent zoom effect if the cursor is over the navigation buttons
            if (e.target === prevBtn || e.target === nextBtn || prevBtn.contains(e.target) || nextBtn.contains(e.target)) {
                img.style.transform = 'scale(1)';
                img.style.transformOrigin = 'center center';
                return; // Stop the function here
            }

            // Calculate cursor position relative to the image
            const rect = img.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width) * 100;
            const y = ((e.clientY - rect.top) / rect.height) * 100;

            // Apply the zoom and set the origin for the transformation
            img.style.transformOrigin = `${x}% ${y}%`;
            img.style.transform = 'scale(2)'; // Adjust the scale factor (e.g., 2 for 200% zoom)
        });

        // Event listener for when the mouse leaves the container
        container.addEventListener('mouseleave', function() {
            // Reset the image to its original state
            img.style.transform = 'scale(1)';
            img.style.transformOrigin = 'center center';
        });
    }
});

// === Keep your existing function to change images ===
// This function is separate and should work as before.
function changeImage(thumbnailElement) {
    const mainImage = document.getElementById('mainProductImage');
    mainImage.src = thumbnailElement.src;

    // Update the active state for thumbnails
    document.querySelectorAll('.product-thumbnails .thumbnail').forEach(thumb => {
        thumb.classList.remove('active');
    });
    thumbnailElement.classList.add('active');
}