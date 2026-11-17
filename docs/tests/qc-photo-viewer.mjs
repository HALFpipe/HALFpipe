// Synthetic DOM and a small Bootstrap API stand-in: no scans or participant data.
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import assert from 'node:assert/strict';
const script = readFileSync(new URL('../qc/photo-viewer.js', import.meta.url), 'utf8');
class Element {
  constructor(tag = 'div') {
    this.tagName = tag; this.children = []; this.attributes = {}; this.handlers = {};
    this.className = ''; this.textContent = ''; this.id = '';
    this.offsetWidth = 88; this.clientWidth = 200;
    this.classList = {
      contains: name => this.className.split(' ').includes(name),
      add: name => { if (!this.classList.contains(name)) this.className += ` ${name}`; },
      toggle: (name, enabled) => {
        const classes = this.className.split(' ').filter(x => x && x !== name);
        if (enabled) classes.push(name); this.className = classes.join(' ');
      }
    };
  }
  append(...items) {
    items.forEach(item => {
      if (item.parent) item.parent.children = item.parent.children.filter(x => x !== item);
      item.parent = this; this.children.push(item);
    });
  }
  prepend(item) { this.append(item); this.children = [item, ...this.children.filter(x => x !== item)]; }
  before(item) {
    const parent = this.parent; item.parent = parent;
    parent.children.splice(parent.children.indexOf(this), 0, item);
  }
  setAttribute(name, value) { this.attributes[name] = value; }
  addEventListener(name, handler) { (this.handlers[name] ||= []).push(handler); }
  emit(name, event = {}) { (this.handlers[name] || []).forEach(handler => handler(event)); }
  closest(selector) {
    for (let item = this; item; item = item.parent) {
      if (selector === item.tagName) return item;
      if (selector.includes('input') && ['input', 'textarea', 'select'].includes(item.tagName)) return item;
    }
    return null;
  }
  querySelector(selector) {
    const tags = selector.split(',').map(x => x.trim());
    for (const child of this.children) {
      if (tags.includes(child.tagName)) return child;
      const found = child.querySelector(selector); if (found) return found;
    }
    return null;
  }
  contains(item) { return this === item || this.children.some(child => child.contains(item)); }
  get offsetLeft() { return this.parent ? this.parent.children.indexOf(this) * 88 : 0; }
  scrollTo(options) { this.scrollPosition = options.left; }
  focus() { this.focused = true; }
}
function fixture(count) {
  const section = new Element('section'); const heading = new Element('h2');
  heading.textContent = 'Synthetic examples'; section.append(heading);
  const gallery = new Element(); gallery.className = 'qc-example-gallery'; section.append(gallery);
  for (let i = 0; i < count; i++) {
    const item = new Element(); item.className = 'quarto-figure';
    const image = new Element('img'); image.alt = `Fabricated image ${i + 1}`; image.src = `synthetic-${i}.svg`;
    const caption = new Element('figcaption'); caption.textContent = `Original synthetic caption ${i}`;
    item.append(image, caption); gallery.append(item);
  }
  return { section, gallery, originals: [...gallery.children] };
}
function run(counts, bootstrapAvailable = true) {
  const groups = counts.map(fixture); const instances = []; let ready;
  class Carousel {
    constructor(stage, options) {
      this.stage = stage; this.options = options; this.selected = 0; instances.push(this);
    }
    to(index) {
      const items = this.stage.children[0].children;
      if (index < 0 || index >= items.length) return;
      this.selected = index;
      items.forEach((item, i) => item.classList.toggle('active', i === index));
      this.stage.emit('slid.bs.carousel', { to: index });
    }
    prev() { this.to(this.selected - 1); }
    next() { this.to(this.selected + 1); }
  }
  runInNewContext(script, {
    window: bootstrapAvailable ? { bootstrap: { Carousel } } : {},
    document: {
      addEventListener(name, handler) { assert.equal(name, 'DOMContentLoaded'); ready = handler; },
      querySelectorAll() { return groups.map(x => x.gallery); },
      createElement(tag) { return new Element(tag); }
    }
  });
  ready(); return { groups, instances };
}
const { groups, instances } = run([3, 2, 1, 0]);
assert.equal(instances.length, 2);
const viewer = groups[0].gallery.parent.parent;
const [context, controls, stage, strip] = viewer.children;
assert.equal(context.textContent, "Synthetic examples");
const [previous, status, next] = controls.children;
const [first, second, third] = strip.children;
assert.equal(previous.disabled, true);
assert.equal(next.disabled, false);
assert.equal(status.textContent, 'Example 1 of 3');
assert.equal(first.attributes['aria-pressed'], 'true');
assert.equal(second.tabIndex, -1);
assert.deepEqual(groups[0].gallery.children, groups[0].originals);
assert.equal(groups[0].originals[0].querySelector('figcaption').textContent, 'Original synthetic caption 0');
next.emit('click'); assert.equal(status.textContent, 'Example 2 of 3');
assert.equal(second.attributes['aria-pressed'], 'true');
third.emit('click'); assert.equal(next.disabled, true); assert.equal(status.textContent, 'Example 3 of 3');
assert.equal(strip.scrollPosition, 120); // Scroll only the strip, not the page.
previous.emit('click'); assert.equal(status.textContent, 'Example 2 of 3');
function key(key, target = second, extra = {}) {
  let prevented = false;
  viewer.emit('keydown', { key, target, preventDefault() { prevented = true; }, ...extra });
  return prevented;
}
assert.equal(key('ArrowLeft'), true); assert.equal(status.textContent, 'Example 1 of 3');
assert.equal(first.focused, true);
key('ArrowLeft'); assert.equal(status.textContent, 'Example 1 of 3');
key('End'); assert.equal(status.textContent, 'Example 3 of 3');
key('Home'); assert.equal(status.textContent, 'Example 1 of 3');
assert.equal(key('ArrowRight', second, { ctrlKey: true }), false);
assert.equal(key('ArrowRight', new Element('input')), false);
assert.equal(key('Tab'), false);
assert.equal(instances[0].options.interval, false); assert.equal(instances[0].options.ride, false);
assert.equal(instances[0].options.wrap, false); assert.equal(instances[0].options.touch, true);
assert.equal(instances[1].selected, 0); // Each gallery has independent state.
const singleton = groups[2].gallery.parent.parent;
assert.equal(singleton.children.length, 2); // No redundant thumbnail strip or buttons.
assert.equal(groups[2].originals[0].classList.contains('active'), true);
assert.notEqual(groups[0].originals[0].id, groups[1].originals[0].id);
const fallback = run([3], false).groups[0];
assert.equal(fallback.gallery.parent, fallback.section);
assert.equal(fallback.originals.some(x => x.classList.contains('carousel-item')), false);
console.log('Photo-viewer checks passed: controls, thumbnails, keyboard selection, captions, boundaries, independent galleries, singleton and no-Bootstrap fallback.');
