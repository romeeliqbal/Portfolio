// Main interactions: smooth scroll, animations, mobile menu, particles, form

document.addEventListener('DOMContentLoaded', () => {
  // Year
  const yearEl = document.getElementById('year');
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  // AOS
  if (typeof AOS !== 'undefined') { AOS.init({ once: true, duration: 700 }); }

  // Lenis smooth scrolling
  if (typeof Lenis !== 'undefined') {
    const lenis = new Lenis({ smoothWheel: true, duration: 1.2 });
    function raf(time) { lenis.raf(time); requestAnimationFrame(raf); }
    requestAnimationFrame(raf);
  }

  // GSAP entrance + ScrollTrigger pinning for header shadow
  if (typeof gsap !== 'undefined') {
    if (gsap && gsap.registerPlugin && window.ScrollTrigger) { gsap.registerPlugin(ScrollTrigger); }
    gsap.from('#profileCard', { y: 24, opacity: 0, duration: 0.8, ease: 'power3.out' });
    gsap.from('.highlight', { y: 12, opacity: 0, duration: 0.7, stagger: 0.08 });
    gsap.to('header', { boxShadow: '0 1px 12px rgba(0,0,0,0.22)', scrollTrigger: { start: 'top -10', end: 99999, toggleActions: 'play none none reverse' } });
    gsap.to('#ring', { scale: 1.04, opacity: 0.7, duration: 2.6, repeat: -1, yoyo: true, ease: 'sine.inOut' });
  }

  // Mobile menu toggle
  const mobileBtn = document.getElementById('mobileMenuBtn');
  const mobileMenu = document.getElementById('mobileMenu');
  if (mobileBtn) {
    mobileBtn.addEventListener('click', () => {
      const expanded = mobileBtn.getAttribute('aria-expanded') === 'true';
      mobileBtn.setAttribute('aria-expanded', String(!expanded));
      if (mobileMenu) mobileMenu.classList.toggle('hidden');
    });
  }

  // Scroll spy to highlight nav links
  const sections = document.querySelectorAll('main section[id]');
  const navLinks = document.querySelectorAll('header .nav-link');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      const id = entry.target.getAttribute('id');
      const link = document.querySelector(`header .nav-link[href="#${id}"]`);
      if (!link) return;
      if (entry.isIntersecting) {
        navLinks.forEach(l => l.classList.remove('nav-link-active'));
        link.classList.add('nav-link-active');
      }
    });
  }, { rootMargin: '-40% 0px -50% 0px', threshold: 0.1 });
  sections.forEach((s) => observer.observe(s));

  // Close mobile menu on link click
  document.querySelectorAll('#mobileMenu a').forEach(a => {
    a.addEventListener('click', () => {
      if (mobileMenu && !mobileMenu.classList.contains('hidden')) mobileMenu.classList.add('hidden');
      if (mobileBtn) mobileBtn.setAttribute('aria-expanded', 'false');
    });
  });

  // Profile 3D tilt
  const profileCard = document.getElementById('profileCard');
  const wrap = document.querySelector('.profile-wrap');
  if (profileCard && wrap) {
    wrap.addEventListener('mousemove', (e) => {
      const rect = profileCard.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = (e.clientX - cx);
      const dy = (e.clientY - cy);
      const rx = (-dy / rect.height) * 12;
      const ry = (dx / rect.width) * 12;
      profileCard.style.transform = `perspective(700px) rotateX(${rx}deg) rotateY(${ry}deg) scale(1.02)`;
    });
    wrap.addEventListener('mouseleave', () => { profileCard.style.transform = ''; });
  }

  // Simple canvas particles background
  (function initParticles() {
    const canvas = document.getElementById('bgParticles');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let w = canvas.width = innerWidth;
    let h = canvas.height = innerHeight;
    const particles = [];
    const COUNT = Math.min(90, Math.floor((w * h) / 90000));

    function rand(min, max) { return Math.random() * (max - min) + min; }

    for (let i = 0; i < COUNT; i++) {
      particles.push({ x: Math.random() * w, y: Math.random() * h, r: rand(0.6, 2.6), vx: rand(-0.25, 0.25), vy: rand(-0.05, 0.15), opacity: rand(0.06, 0.18) });
    }

    function resize() { w = canvas.width = innerWidth; h = canvas.height = innerHeight; }
    addEventListener('resize', resize);

    function draw() {
      ctx.clearRect(0, 0, w, h);
      const grad = ctx.createLinearGradient(0, 0, w, h);
      grad.addColorStop(0, 'rgba(3,6,10,0.25)');
      grad.addColorStop(1, 'rgba(3,6,10,0.06)');
      ctx.fillStyle = grad; ctx.fillRect(0,0,w,h);

      for (let p of particles) {
        p.x += p.vx; p.y += p.vy;
        if (p.x < -10) p.x = w + 10;
        if (p.x > w + 10) p.x = -10;
        if (p.y > h + 20) p.y = -20;
        ctx.beginPath(); ctx.fillStyle = `rgba(6,182,212,${p.opacity})`; ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fill();
      }
      requestAnimationFrame(draw);
    }
    draw();
  })();

  // Swiper for mobile projects carousel
  if (typeof Swiper !== 'undefined') {
    new Swiper('.project-swiper', { loop: true, spaceBetween: 16, slidesPerView: 1.1, centeredSlides: true, pagination: { el: '.swiper-pagination', clickable: true } });
  }

  // Form handling
  const form = document.getElementById('feedbackForm');
  const status = document.getElementById('formStatus');
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!status) return;
      const name = form.querySelector('#name').value.trim();
      const email = form.querySelector('#email').value.trim();
      const message = form.querySelector('#message').value.trim();
      if (!name || !email || !message) { status.classList.remove('sr-only'); status.textContent = 'Please complete all fields.'; status.style.color = 'salmon'; return; }
      status.classList.remove('sr-only'); status.textContent = 'Sending...'; status.style.color = '#9ca3af';
      try {
        const resp = await fetch(form.action || '/api/contact', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, email, message }) });
        const data = await resp.json();
        if (resp.ok && data.ok !== false) {
          status.textContent = data.message || 'Message sent. Thanks!'; status.style.color = '#34d399'; form.reset();
          if (typeof gsap !== 'undefined') { gsap.fromTo(status, { scale: 0.96, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.4, ease: 'back.out(1.2)' }); }
        } else { status.textContent = data.message || 'Something went wrong. Try again later.'; status.style.color = 'salmon'; }
      } catch (err) {
        status.textContent = 'Request failed. Check your connection or server.'; status.style.color = 'salmon'; console.error(err);
      }
    });
  }
});
