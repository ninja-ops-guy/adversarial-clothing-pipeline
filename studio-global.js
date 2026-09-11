(function () {
  'use strict';
  if (typeof RACStudio === 'undefined') {
    throw new Error('RACStudio runtime was not initialized.');
  }
  window.RACStudio = RACStudio;

  // Remove non-functional mode chrome so every visible control maps to a real
  // Product Studio capability. Batch ranking/export remain in Production Mapper.
  const modeTabs = document.querySelector('.mode-tabs');
  if (modeTabs) modeTabs.remove();

  for (const row of document.querySelectorAll('.output-file span')) {
    if (row.textContent.includes('production_map.zip')) {
      row.innerHTML = 'panel_pack.zip<small>via Production Mapper</small>';
    }
  }

  if (!document.querySelector('script[data-rac-research-catalog]')) {
    const script = document.createElement('script');
    script.src = 'studio-research-catalog.js';
    script.async = false;
    script.dataset.racResearchCatalog = 'true';
    document.head.appendChild(script);
  }
})();
