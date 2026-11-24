document.addEventListener("DOMContentLoaded", () => {
  const dialog = document.createElement("dialog");
  if (!dialog.showModal) return;
  dialog.className = "qc-image-dialog";
  dialog.setAttribute("aria-label", "QC image preview");
  dialog.setAttribute("aria-describedby", "qc-image-caption");
  const button = (text, label) => {
    const element = document.createElement("button");
    element.type = "button";
    element.textContent = text;
    element.setAttribute("aria-label", label);
    return element;
  };
  const context = document.createElement("div");
  context.className = "qc-image-context";
  context.id = "qc-image-context";
  dialog.setAttribute("aria-labelledby", context.id);
  const header = document.createElement("div");
  header.className = "qc-image-toolbar";
  const navigation = document.createElement("div");
  navigation.className = "qc-image-navigation";
  const previous = button("‹", "Previous example");
  const next = button("›", "Next example");
  const counter = document.createElement("span");
  counter.setAttribute("aria-live", "polite");
  navigation.append(previous, counter, next);
  const controls = document.createElement("div");
  controls.className = "qc-image-zoom";
  const out = button("−", "Zoom out");
  const into = button("+", "Zoom in");
  const fitButton = button("Fit", "Fit image to window");
  const status = document.createElement("span");
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  status.setAttribute("aria-atomic", "true");
  controls.append(out, status, into, fitButton);
  const close = button("Close ×", "Close preview");
  close.className = "qc-image-close";
  header.append(navigation, controls, close);
  const stage = document.createElement("div");
  stage.className = "qc-image-workspace";
  stage.tabIndex = 0;
  stage.setAttribute("aria-label", "Image: scroll to zoom, drag to pan; arrow keys pan when zoomed");
  const image = document.createElement("img");
  image.draggable = false;
  const message = document.createElement("span");
  message.className = "qc-image-message";
  message.setAttribute("role", "status");
  stage.append(image, message);
  const caption = document.createElement("div");
  caption.className = "qc-image-caption";
  caption.id = "qc-image-caption";
  caption.tabIndex = 0;
  caption.setAttribute("aria-label", "Image caption");
  dialog.append(context, header, stage, caption);
  document.body.append(dialog);
  let links = [], selected = 0, opener, ready = false;
  let baseWidth = 0, baseHeight = 0, scale = 1, x = 0, y = 0, drag;
  const stopDrag = () => {
    if (drag && stage.hasPointerCapture(drag.id)) stage.releasePointerCapture(drag.id);
    drag = undefined;
    stage.classList.remove("qc-is-dragging");
  };
  const bound = (position, size, available) => {
    const limit = Math.abs(size * scale - available) / 2;
    return Math.max(-limit, Math.min(limit, position));
  };
  const render = () => {
    x = scale === 1 ? 0 : bound(x, baseWidth, stage.clientWidth);
    y = scale === 1 ? 0 : bound(y, baseHeight, stage.clientHeight);
    image.style.transform = `translate(${x}px, ${y}px) scale(${scale})`;
    stage.classList.toggle("qc-is-zoomed", scale > 1);
    status.textContent = `${Math.round(scale * 100)}%`;
    out.disabled = !ready || scale <= 1;
    into.disabled = !ready || scale >= 8;
    fitButton.disabled = !ready;
  };
  const fit = () => {
    if (!ready || !dialog.open) return;
    stopDrag();
    const ratio = Math.min(stage.clientWidth / image.naturalWidth, stage.clientHeight / image.naturalHeight);
    baseWidth = image.naturalWidth * ratio;
    baseHeight = image.naturalHeight * ratio;
    image.style.width = `${baseWidth}px`;
    image.style.height = `${baseHeight}px`;
    scale = 1; x = y = 0; render();
  };
  const zoom = (factor, clientX, clientY) => {
    if (!ready) return;
    stopDrag();
    const rect = stage.getBoundingClientRect();
    const px = clientX === undefined ? 0 : clientX - rect.left - rect.width / 2;
    const py = clientY === undefined ? 0 : clientY - rect.top - rect.height / 2;
    const target = Math.max(1, Math.min(8, scale * factor));
    // The cursor's image coordinate stays fixed, except where an edge bound intervenes.
    x = px - (px - x) * target / scale;
    y = py - (py - y) * target / scale;
    scale = target; render();
  };
  const show = (index) => {
    stopDrag(); selected = index; ready = false;
    scale = 1; x = y = 0; image.hidden = true;
    const link = links[index];
    context.textContent = link.closest(".qc-photo-viewer")?.querySelector(".qc-photo-context")?.textContent ||
      link.closest("main")?.querySelector("h1")?.textContent || "QC image preview";
    const source = link.querySelector("img");
    const figure = link.closest("figure");
    caption.textContent = figure?.querySelector("figcaption")?.textContent ||
      link.getAttribute("title") || source?.alt || "";
    caption.hidden = !caption.textContent;
    counter.textContent = `${index + 1} / ${links.length}`;
    previous.disabled = index === 0;
    next.disabled = index === links.length - 1;
    message.textContent = "Loading image…"; message.hidden = false;
    image.alt = source?.alt || caption.textContent;
    image.src = link.href;
    render();
  };
  image.addEventListener("load", () => {
    if (!dialog.open) return;
    ready = true; image.hidden = false; message.hidden = true; fit();
  });
  image.addEventListener("error", () => {
    ready = false; message.textContent = "Image could not be loaded."; render();
  });
  image.addEventListener("dragstart", (event) => event.preventDefault());
  // Capture before Quarto's link handler so its fitted lightbox never opens underneath.
  document.addEventListener("click", (event) => {
    const link = event.target.closest("a.lightbox");
    if (!link?.closest(".qc-manual") || event.button !== 0 ||
        event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault(); event.stopImmediatePropagation();
    opener = link;
    const group = link.closest(".qc-example-gallery");
    links = group ? [...group.querySelectorAll("a.lightbox")] : [link];
    document.body.classList.add("qc-image-preview-open");
    dialog.showModal();
    show(links.indexOf(link));
    stage.focus({ preventScroll: true });
  }, true);
  previous.addEventListener("click", () => show(selected - 1));
  next.addEventListener("click", () => show(selected + 1));
  out.addEventListener("click", () => zoom(1 / 1.25));
  into.addEventListener("click", () => zoom(1.25));
  fitButton.addEventListener("click", fit);
  close.addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => {
    stopDrag(); document.body.classList.remove("qc-image-preview-open");
    const link = links[selected] || opener;
    const carouselStage = link?.closest(".qc-photo-stage");
    if (carouselStage) window.bootstrap?.Carousel.getInstance(carouselStage)?.to(selected);
    link?.focus({ preventScroll: true });
  });
  stage.addEventListener("wheel", (event) => {
    if (!event.deltaY || !ready) return;
    event.preventDefault();
    const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? stage.clientHeight : 1;
    const delta = Math.max(-300, Math.min(300, event.deltaY * unit));
    zoom(Math.exp(-delta / 600), event.clientX, event.clientY);
  }, { passive: false });
  stage.addEventListener("pointerdown", (event) => {
    if (event.pointerType !== "mouse" || event.button !== 0 || scale <= 1) return;
    event.preventDefault();
    drag = { id: event.pointerId, startX: event.clientX, startY: event.clientY, x, y };
    stage.setPointerCapture(event.pointerId); stage.classList.add("qc-is-dragging");
  });
  stage.addEventListener("pointermove", (event) => {
    if (!drag || event.pointerId !== drag.id) return;
    x = drag.x + event.clientX - drag.startX;
    y = drag.y + event.clientY - drag.startY; render();
  });
  for (const type of ["pointerup", "pointercancel", "lostpointercapture"])
    stage.addEventListener(type, stopDrag);
  stage.addEventListener("keydown", (event) => {
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    const pan = { ArrowLeft: [40, 0], ArrowRight: [-40, 0], ArrowUp: [0, 40], ArrowDown: [0, -40] };
    if (["+", "="].includes(event.key)) zoom(1.25);
    else if (["-", "_"].includes(event.key)) zoom(1 / 1.25);
    else if (event.key === "0") fit();
    else if (Object.hasOwn(pan, event.key)) {
      if (scale > 1) { x += pan[event.key][0]; y += pan[event.key][1]; render(); }
      else if (event.key === "ArrowLeft" && selected > 0) show(selected - 1);
      else if (event.key === "ArrowRight" && selected < links.length - 1) show(selected + 1);
    } else return;
    event.preventDefault();
  });
  new ResizeObserver(() => { if (dialog.open) fit(); }).observe(stage);
});
