// Keep the model point under the cursor or pinch centre stationary as the view scales.
const limit = scale => Math.max(0.1, Math.min(2.5, scale));

export function installCanvasZoom(canvas, graph) {
  const {view} = graph;
  const touches = new Map();
  let pinch, gesture, lastPointer;
  const listeners = new AbortController();
  const listen = (name, handler) => canvas.addEventListener(name, handler, {
    capture: true, passive: false, signal: listeners.signal,
  });

  function localPoint(event) {
    const rect = canvas.getBoundingClientRect();
    return {x: event.clientX - rect.left - canvas.clientLeft, y: event.clientY - rect.top - canvas.clientTop};
  }
  function anchor(point) {
    return {
      x: (point.x + canvas.scrollLeft) / view.scale - view.translate.x,
      y: (point.y + canvas.scrollTop) / view.scale - view.translate.y,
    };
  }
  function zoomTo(scale, point, world = anchor(point)) {
    if (!Number.isFinite(scale) || scale <= 0) return;
    const target = limit(scale);
    const left = canvas.scrollLeft, top = canvas.scrollTop;
    view.scaleAndTranslate(target, (point.x + left) / target - world.x, (point.y + top) / target - world.y);
    // Shrinking the SVG can clamp a scrollbar during layout. Fold its offset into the translation.
    if (canvas.scrollLeft !== left || canvas.scrollTop !== top) {
      canvas.scrollLeft = canvas.scrollTop = 0;
      view.scaleAndTranslate(target, point.x / target - world.x, point.y / target - world.y);
    }
  }

  listen('wheel', event => {
    if (!event.deltaY || event.shiftKey || event.target.closest?.('textarea,input,[contenteditable=true]')) return;
    event.preventDefault();
    if (gesture || pinch) return;
    const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? canvas.clientHeight : 1;
    const rate = event.ctrlKey ? 0.01 : 0.002;
    const exponent = Math.max(-1, Math.min(1, -event.deltaY * unit * rate));
    zoomTo(view.scale * Math.exp(exponent), localPoint(event));
  });

  // Safari trackpads report an absolute gesture scale. Chromium and Firefox use Ctrl+wheel.
  function gesturePoint(event) {
    const point = localPoint(event);
    if (point.x >= 0 && point.x <= canvas.clientWidth && point.y >= 0 && point.y <= canvas.clientHeight) return point;
    return lastPointer || {x: canvas.clientWidth / 2, y: canvas.clientHeight / 2};
  }
  listen('gesturestart', event => {
    event.preventDefault();
    if (!touches.size) gesture = {scale: view.scale, world: anchor(gesturePoint(event))};
  });
  listen('gesturechange', event => {
    event.preventDefault();
    if (gesture && !pinch) zoomTo(gesture.scale * event.scale, gesturePoint(event), gesture.world);
  });
  listen('gestureend', event => { event.preventDefault(); gesture = null; });

  function touchPair() {
    const [a, b] = touches.values();
    return {centre: {x: (a.x + b.x) / 2, y: (a.y + b.y) / 2}, distance: Math.hypot(b.x - a.x, b.y - a.y)};
  }
  function consumeTouch(event) {
    event.preventDefault();
    event.stopImmediatePropagation();
  }
  listen('pointerdown', event => {
    if (event.pointerType !== 'touch') return;
    touches.set(event.pointerId, localPoint(event));
    if (touches.size === 2) {
      const {centre, distance} = touchPair();
      pinch = {scale: view.scale, distance, world: anchor(centre)};
      gesture = null;
      graph.escape();
      graph.panningHandler.reset();
      for (const id of touches.keys()) canvas.setPointerCapture(id);
    }
    if (pinch) consumeTouch(event);
  });
  listen('pointermove', event => {
    if (event.pointerType === 'mouse') lastPointer = localPoint(event);
    if (!touches.has(event.pointerId)) return;
    touches.set(event.pointerId, localPoint(event));
    if (!pinch) return;
    consumeTouch(event);
    if (touches.size !== 2 || !pinch.distance) return;
    const {centre, distance} = touchPair();
    zoomTo(pinch.scale * distance / pinch.distance, centre, pinch.world);
  });
  function endTouch(event) {
    if (!touches.delete(event.pointerId) || !pinch) return;
    consumeTouch(event);
    if (touches.size === 0) pinch = null;
  }
  listen('pointerup', endTouch);
  listen('pointercancel', endTouch);
  listen('lostpointercapture', event => {
    if (event.target === canvas && !canvas.hasPointerCapture(event.pointerId)) endTouch(event);
  });
  return () => listeners.abort();
}
