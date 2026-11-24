document.addEventListener("DOMContentLoaded", () => {
  if (!window.bootstrap?.Carousel) return;
  document.querySelectorAll(".qc-example-gallery").forEach((gallery, galleryIndex) => {
    const items = [...gallery.children].filter((item) => item.classList.contains("quarto-figure"));
    if (!items.length) return;
    const heading = gallery.closest("section")?.querySelector("h2, h3") ||
      gallery.closest("main")?.querySelector("h1");
    const viewer = document.createElement("div");
    viewer.className = "qc-photo-viewer";
    viewer.setAttribute("role", "region");
    viewer.setAttribute("aria-label", heading?.textContent.trim() || "QC examples");
    const context = document.createElement("div");
    context.className = "qc-photo-context";
    const type = gallery.closest("main")?.querySelector("h1")?.textContent.trim();
    context.textContent = [type, heading?.textContent.trim()].filter(Boolean).join(" · ");
    viewer.append(context);
    const stage = document.createElement("div");
    stage.className = "qc-photo-stage carousel";
    gallery.before(viewer);
    viewer.append(stage);
    stage.append(gallery);
    gallery.classList.add("carousel-inner");
    items.forEach((item, index) => {
      item.classList.add("carousel-item");
      item.classList.toggle("active", index === 0);
      item.id ||= `qc-photo-${galleryIndex + 1}-item-${index + 1}`;
      item.setAttribute("role", "group");
      item.setAttribute("aria-roledescription", "slide");
      item.setAttribute("aria-label", `${index + 1} of ${items.length}`);
    });
    // A single example needs its full-size stage, but no navigation controls.
    if (items.length === 1) return;
    viewer.setAttribute("aria-roledescription", "carousel");
    const controls = document.createElement("div");
    controls.className = "qc-photo-controls";
    const button = (text) => {
      const element = document.createElement("button");
      element.type = "button";
      element.className = "btn btn-outline-secondary btn-sm";
      element.textContent = text;
      return element;
    };
    const previous = button("← Previous");
    previous.setAttribute("aria-label", "Previous example");
    const next = button("Next →");
    next.setAttribute("aria-label", "Next example");
    const status = document.createElement("span");
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    status.setAttribute("aria-atomic", "true");
    controls.append(previous, status, next);
    stage.before(controls);
    const strip = document.createElement("div");
    strip.className = "qc-photo-thumbnails";
    strip.setAttribute("role", "group");
    strip.setAttribute("aria-label", "Choose an example");
    viewer.append(strip);
    // Keep swipe handling on the image stage, so the thumbnail strip can scroll independently.
    const carousel = new window.bootstrap.Carousel(stage, {
      interval: false, ride: false, wrap: false, touch: true, keyboard: false
    });
    let selected = 0;
    const thumbnails = items.map((item, index) => {
      const image = item.querySelector("img");
      const thumbnail = button("");
      thumbnail.className = "qc-photo-thumbnail";
      thumbnail.setAttribute("aria-label", `Example ${index + 1}: ${image.alt}`);
      thumbnail.setAttribute("aria-controls", item.id);
      const preview = document.createElement("img");
      preview.src = image.src;
      preview.alt = "";
      preview.loading = "lazy";
      thumbnail.append(preview);
      thumbnail.addEventListener("click", () => carousel.to(index));
      strip.append(thumbnail);
      return thumbnail;
    });
    const update = (index, scroll = true) => {
      selected = index;
      previous.disabled = index === 0;
      next.disabled = index === items.length - 1;
      status.textContent = `Example ${index + 1} of ${items.length}`;
      thumbnails.forEach((thumbnail, position) => {
        thumbnail.setAttribute("aria-pressed", String(position === index));
        thumbnail.tabIndex = position === index ? 0 : -1;
      });
      if (scroll) {
        const thumbnail = thumbnails[index];
        strip.scrollTo({ left: thumbnail.offsetLeft + thumbnail.offsetWidth / 2 - strip.clientWidth / 2,
          behavior: "auto" });
      }
    };
    previous.addEventListener("click", () => carousel.prev());
    next.addEventListener("click", () => carousel.next());
    stage.addEventListener("slid.bs.carousel", (event) => update(event.to));
    viewer.addEventListener("keydown", (event) => {
      if (event.altKey || event.ctrlKey || event.metaKey ||
          event.target.closest("input, textarea, select, [contenteditable]")) return;
      const targets = { ArrowLeft: selected - 1, ArrowRight: selected + 1,
        Home: 0, End: items.length - 1 };
      if (!Object.hasOwn(targets, event.key)) return;
      event.preventDefault();
      const index = Math.max(0, Math.min(items.length - 1, targets[event.key]));
      carousel.to(index);
      if (strip.contains(event.target)) thumbnails[index].focus({ preventScroll: true });
    });
    update(0, false);
  });
});
