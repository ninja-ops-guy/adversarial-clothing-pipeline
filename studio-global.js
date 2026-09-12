(function () {
  'use strict';
  if (typeof RACStudio === 'undefined') {
    throw new Error('RACStudio runtime was not initialized.');
  }
  window.RACStudio = RACStudio;
})();
