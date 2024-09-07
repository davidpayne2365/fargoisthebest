self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open('v1').then((cache) => {
      return cache.addAll([
        '/index.html',
        '/styles.css',
        '/app.js',
        '/NCLE ASTIGMATISM MADE EASY #1 [ ezmp3.cc ].mp3',
        '/NCLE ASTIGMATISM MADE EASY #2 [ ezmp3.cc ].mp3',
        '/NCLE ASTIGMATISM MADE EASY #3 [ ezmp3.cc ].mp3',
        '/NCLE BASE CURVE, DIAMETER, & SAGITTAL DEPTH RELATIONSHIP [ ezmp3.cc ].mp3',
        '/NCLE BEYOND TRANSPOSITION [ ezmp3.cc ].mp3',
        '/NCLE CONTACT LENS FITTING TIPS [ ezmp3.cc ].mp3',
        '/NCLE FRONT TORIC RGP [ ezmp3.cc ].mp3',
        '/NCLE GP FITTING (SAMFAP #2) [ ezmp3.cc ].mp3',
        '/NCLE GP FLUORESCEIN PATTERNS [ ezmp3.cc ].mp3',
        '/NCLE LENS ROTATION [ ezmp3.cc ].mp3',
        '/NCLE OVER REFRACTION [ ezmp3.cc ].mp3',
        '/NCLE RGP SPHERICAL, FRONT, BACK, AND BI-TORIC SELECTION [ ezmp3.cc ].mp3',
        '/NCLE SAM FAP [ ezmp3.cc ].mp3',
        '/NCLE SLIT LAMP [ ezmp3.cc ].mp3',
        '/NCLE SOFT LENSES AND SPHERICAL EQUIVALENT [ ezmp3.cc ].mp3',
        '/NCLE TEST QUESTION REVIEW [ ezmp3.cc ].mp3',
        '/NCLE UNDERSTANDING _K_ READINGS [ ezmp3.cc ].mp3',
        '/NCLE VERTEX DISTANCE - CYLINDRICAL LENSES [ ezmp3.cc ].mp3',
        '/NCLE VERTEX DISTANCE [ ezmp3.cc ] (1).mp3'
      ]);
    })
  );
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});
