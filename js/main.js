/* Buildin™ Website — Main JS */

// Mobile Navigation Toggle
const navToggle = document.getElementById('navToggle');
const navLinks = document.getElementById('navLinks');

if (navToggle && navLinks) {
  navToggle.addEventListener('click', () => {
    navToggle.classList.toggle('active');
    navLinks.classList.toggle('open');
  });

  // Close menu when a link is clicked
  navLinks.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
      navToggle.classList.remove('active');
      navLinks.classList.remove('open');
    });
  });
}

// Scroll-based fade-in animations
const observerOptions = {
  threshold: 0.15,
  rootMargin: '0px 0px -40px 0px'
};

const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      observer.unobserve(entry.target);
    }
  });
}, observerOptions);

document.querySelectorAll('.fade-in').forEach(el => {
  observer.observe(el);
});

// ─── EmailJS Configuration ───
// TODO: Replace these with your actual EmailJS credentials
// 1. Sign up at https://www.emailjs.com (free)
// 2. Add an Email Service (connect info@daybio.co.kr)
// 3. Create an Email Template
// 4. Copy your Service ID, Template ID, and Public Key below
const EMAILJS_PUBLIC_KEY = 'YOUR_PUBLIC_KEY';
const EMAILJS_SERVICE_ID = 'YOUR_SERVICE_ID';
const EMAILJS_TEMPLATE_ID = 'YOUR_TEMPLATE_ID';

// Initialize EmailJS
emailjs.init(EMAILJS_PUBLIC_KEY);

// Contact form handler
const contactForm = document.getElementById('contactForm');
if (contactForm) {
  contactForm.addEventListener('submit', (e) => {
    e.preventDefault();

    const submitBtn = contactForm.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Sending...';
    submitBtn.disabled = true;

    const templateParams = {
      from_name: document.getElementById('name').value,
      from_email: document.getElementById('email').value,
      company: document.getElementById('company').value,
      inquiry_type: document.getElementById('inquiry').value,
      message: document.getElementById('message').value
    };

    emailjs.send(EMAILJS_SERVICE_ID, EMAILJS_TEMPLATE_ID, templateParams)
      .then(() => {
        showFormMessage('Thank you! Your inquiry has been sent successfully.', 'success');
        contactForm.reset();
      })
      .catch(() => {
        showFormMessage('Failed to send. Please email us directly at info@daybio.co.kr', 'error');
      })
      .finally(() => {
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
      });
  });
}

function showFormMessage(text, type) {
  let msgEl = document.getElementById('formMessage');
  if (!msgEl) {
    msgEl = document.createElement('div');
    msgEl.id = 'formMessage';
    contactForm.appendChild(msgEl);
  }
  msgEl.textContent = text;
  msgEl.style.cssText = 'padding:12px 16px;border-radius:8px;margin-top:16px;font-size:14px;text-align:center;';
  if (type === 'success') {
    msgEl.style.background = '#e8f5e9';
    msgEl.style.color = '#2e7d32';
  } else {
    msgEl.style.background = '#fce4ec';
    msgEl.style.color = '#c62828';
  }
  setTimeout(() => msgEl.remove(), 6000);
}
