(function () {
  'use strict';

  const originalGetContext = HTMLCanvasElement.prototype.getContext;

  HTMLCanvasElement.prototype.getContext = function patchedGetContext(type, options) {
    const ctx = originalGetContext.call(this, type, options);
    if (!ctx || type !== '2d' || this.id !== 'mockupCanvas' || ctx.__racTextClean) {
      return ctx;
    }

    const originalFillText = ctx.fillText.bind(ctx);
    const originalStrokeText = ctx.strokeText.bind(ctx);

    // Product mockups are visual design outputs. Suppress all editorial copy,
    // slogans, view captions and garment label text while preserving shapes,
    // seams, pattern art and all non-text rendering.
    ctx.fillText = function () {};
    ctx.strokeText = function () {};
    Object.defineProperty(ctx, '__racTextClean', { value: true });
    Object.defineProperty(ctx, '__racOriginalFillText', { value: originalFillText });
    Object.defineProperty(ctx, '__racOriginalStrokeText', { value: originalStrokeText });
    return ctx;
  };
})();
