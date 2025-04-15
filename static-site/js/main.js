// Simple JavaScript for the static site
document.addEventListener('DOMContentLoaded', function() {
  // Mobile menu toggle functionality could be added here
  
  // Get the current page path
  const currentPath = window.location.pathname;
  
  // Highlight the current page in the navigation
  const navLinks = document.querySelectorAll('.nav-links a');
  navLinks.forEach(link => {
    const linkPath = link.getAttribute('href');
    if (currentPath === linkPath) {
      link.style.textDecoration = 'underline';
    }
  });
  
  // Add smooth scrolling to anchor links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      e.preventDefault();
      
      document.querySelector(this.getAttribute('href')).scrollIntoView({
        behavior: 'smooth'
      });
    });
  });
});