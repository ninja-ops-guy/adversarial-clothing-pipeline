(function () {
  'use strict';
  if (typeof RACStudio === 'undefined') {
    throw new Error('RACStudio runtime was not initialized.');
  }
  window.RACStudio = RACStudio;

  if (!document.querySelector('script[data-rac-research-catalog]')) {
    const script = document.createElement('script');
    script.src = 'studio-research-catalog.js';
    script.async = false;
    script.dataset.racResearchCatalog = 'true';
    document.head.appendChild(script);
  }
})();
