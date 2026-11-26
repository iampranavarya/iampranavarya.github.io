/* PAFP blog: nav, menu, reading progress, topic filter, reveal on scroll. */
(function () {
  'use strict';
  var doc = document.documentElement, body = document.body;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // nav background + hide on scroll down
  var nav = document.getElementById('nav'), last = 0, ticking = false;
  var bar = document.getElementById('progress');
  var prose = document.querySelector('.prose');
  function onScroll() {
    var y = window.scrollY;
    if (nav) {
      nav.classList.toggle('scrolled', y > 20);
      nav.classList.toggle('hide', y > 300 && y > last && !body.classList.contains('menu-open'));
    }
    last = y;
    if (bar && prose) {
      var r = prose.getBoundingClientRect();
      var total = r.height - window.innerHeight * 0.6;
      var p = Math.min(1, Math.max(0, (-r.top + window.innerHeight * 0.2) / Math.max(1, total)));
      bar.style.transform = 'scaleX(' + p + ')';
    }
    ticking = false;
  }
  window.addEventListener('scroll', function () {
    if (!ticking) { ticking = true; requestAnimationFrame(onScroll); }
  }, { passive: true });
  onScroll();

  // mobile menu
  var burger = document.getElementById('burger'), menu = document.getElementById('menu');
  function setMenu(open) {
    body.classList.toggle('menu-open', open);
    if (burger) { burger.setAttribute('aria-expanded', open); burger.setAttribute('aria-label', open ? 'Close menu' : 'Open menu'); }
    if (menu) menu.setAttribute('aria-hidden', !open);
  }
  if (burger) burger.addEventListener('click', function () { setMenu(!body.classList.contains('menu-open')); });
  if (menu) menu.addEventListener('click', function (e) { if (e.target.closest('a')) setMenu(false); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setMenu(false); });

  // copy link
  document.querySelectorAll('.copy').forEach(function (b) {
    b.addEventListener('click', function () {
      var url = b.getAttribute('data-url');
      (navigator.clipboard ? navigator.clipboard.writeText(url) : Promise.reject()).then(function () {
        b.textContent = 'Copied';
        setTimeout(function () { b.textContent = 'Copy link'; }, 1800);
      }).catch(function () { window.prompt('Copy this link', url); });
    });
  });

  // topic filter on the blog index
  var list = document.querySelector('.post-list');
  var chips = document.querySelectorAll('.chip');
  function applyFilter(f, push) {
    chips.forEach(function (c) { c.classList.toggle('on', c.getAttribute('data-f') === f); });
    list.querySelectorAll('.post-card').forEach(function (card) {
      card.hidden = !(f === 'all' || card.getAttribute('data-cat') === f);
      card.classList.add('in');
    });
    list.classList.toggle('filtered', f !== 'all');
    if (push && history.replaceState) history.replaceState(null, '', f === 'all' ? location.pathname : '#' + f);
  }
  if (list && chips.length) {
    chips.forEach(function (c) {
      c.addEventListener('click', function () { applyFilter(c.getAttribute('data-f'), true); });
    });
    var h = location.hash.slice(1);
    if (h && document.querySelector('.chip[data-f="' + h.replace(/[^a-z0-9-]/g, '') + '"]')) applyFilter(h, false);
  }

  // reveal cards and sections that start below the fold
  if (!reduce && 'IntersectionObserver' in window) {
    var targets = document.querySelectorAll('.post-card, .author-card, .cta-inner, .rel-head');
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
      });
    }, { rootMargin: '0px 0px -8% 0px' });
    var vh = window.innerHeight;
    doc.classList.add('js');
    targets.forEach(function (el) {
      if (el.getBoundingClientRect().top > vh) { el.setAttribute('data-reveal', ''); io.observe(el); }
    });
  }
})();
