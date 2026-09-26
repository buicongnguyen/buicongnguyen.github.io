import * as C from './core.mjs';

const root = document.querySelector('#petal'), q = sel => root.querySelector(sel);
const table = q('.worktop'), layer = q('[data-ingredients]'), effects = q('.effects'), buttons = new Map();
const sprite = name => `assets/sprites/${name}.webp`;
const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const LANTERNS = C.CHAPTERS.length;

let storageOK = true, migrated = false;
const parse = raw => { try { return raw ? JSON.parse(raw) : null; } catch { return null; } };
function load() {
  let read;
  try { read = key => localStorage.getItem(key); read(C.STORAGE); } catch { storageOK = false; return null; }
  const current = parse(read(C.STORAGE));
  if (current) return C.validate(current);
  for (const key of [C.LEGACY_V4, C.LEGACY_V3]) {
    const s = C.migrate(parse(read(key)));
    if (s) { migrated = true; return s; }
  }
  return null;
}
let state = load() || C.freshState();
let busy = false, active = null, drag = null, selected = null, hint = null, focus = 0, suppress = 0, audio;
let staffTimer, finishTimer, toastTimer;
const moments = [], toasts = [];
const seenLetters = () => { try { return Number(localStorage.getItem(C.STORAGE + ':letters')) || 0; } catch { return 0; } };
const welcome = C.offline(state);

function save() {
  const amount = C.offline(state);
  try { localStorage.setItem(C.STORAGE, JSON.stringify(state)); } catch { storageOK = false; }
  return amount;
}
function say(main, detail = '') {
  q('[data-feedback]').textContent = main;
  q('[data-feedback-detail]').textContent = detail;
}

// ------------------------------------------------------------------ sound ---
function sound(kind) {
  if (!state.sound) return;
  try {
    audio ??= new (window.AudioContext || window.webkitAudioContext)();
    audio.resume();
    const now = audio.currentTime;
    const notes = {reward: [523.25, 659.25, 783.99], new: [659.25, 783.99, 1046.5], pick: [440], pour: [196, 261.6],
      heart: [783.99, 987.77], golden: [523.25, 659.25, 783.99, 1046.5, 1318.5], lantern: [392, 523.25, 659.25, 783.99, 1046.5]}[kind] || [440];
    notes.forEach((f, i) => {
      const o = audio.createOscillator(), g = audio.createGain(), t = now + i * .08;
      o.type = kind === 'pour' ? 'sine' : 'triangle';
      o.frequency.setValueAtTime(f, t);
      g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(.035, t + .015);
      g.gain.exponentialRampToValueAtTime(.0001, t + .3);
      o.connect(g); g.connect(audio.destination);
      o.start(t); o.stop(t + .32);
    });
  } catch { state.sound = false; }
}

// ----------------------------------------------------------------- geometry ---
const dims = () => ({w: table.clientWidth, h: table.clientHeight});
function bounded(x, y) {
  const {w, h} = dims(), b = buttons.get(0), hx = b.offsetWidth / 2 + 3, hy = b.offsetHeight / 2 + 3;
  const top = Math.min(.45, (q('[data-baskets]').offsetHeight + 4 + hy) / h);
  return {x: clamp(x, hx / w, 1 - hx / w), y: clamp(y, Math.max(hy / h, top), 1 - hy / h)};
}
function position(button, pos) { button.style.left = pos.x * 100 + '%'; button.style.top = pos.y * 100 + '%'; }
function nearest(id, pos) {
  const {w, h} = dims(), radius = Math.min(80, w * .21, h * .32);
  return state.tokens.filter(t => t.id !== id).map(t => {
    const v = bounded(t.x, t.y);
    return {t, d: Math.hypot((v.x - pos.x) * w, (v.y - pos.y) * h)};
  }).filter(o => o.d <= radius).sort((a, b) => a.d - b.d || a.t.id - b.t.id)[0]?.t || null;
}
function appPoint(el) {
  const a = root.getBoundingClientRect(), r = el.getBoundingClientRect();
  return {x: r.x + r.width / 2 - a.x, y: r.y + r.height / 2 - a.y};
}

// ---------------------------------------------------------------- helpers ---
const guestKnown = g => g.person === 'rosa' ? true : C.knows(state, g);
const lineNow = () => busy && active ? active.line : state.queue;
function heartsHTML(person) {
  if (!C.REGULARS[person]) return '';
  const h = C.hearts(state, person);
  return '♥'.repeat(h) + '<span class="empty">' + '♥'.repeat(C.MAX_HEARTS - h) + '</span>';
}
function partsChips(r) {
  const box = document.createElement('span');
  box.className = 'chips';
  r.parts.forEach((p, i) => {
    if (i) box.append(' + ');
    const chip = document.createElement('span');
    chip.className = 'chip';
    chip.append(Object.assign(document.createElement('img'), {src: sprite(p), alt: ''}), C.LABELS[p]);
    box.append(chip);
  });
  return box;
}

// ----------------------------------------------------------------- render ---
function render() {
  const s = state;
  root.dataset.busy = String(busy);
  root.dataset.golden = String(s.golden > 0);
  root.dataset.festival = String(s.festival);
  root.dataset.ready = 'true';
  q('[data-coins]').textContent = s.coins;
  const pips = q('[data-glow-pips]').children;
  for (let i = 0; i < pips.length; i++) pips[i].dataset.on = String(s.golden > 0 || i < s.glow);
  q('[data-glow]').hidden = !C.picturesOnly(s);
  q('[data-glow]').setAttribute('aria-label', s.golden > 0 ? `Golden hour: ${s.golden} doubled cups left` : `Golden hour meter: ${s.glow} of ${C.GLOW_MAX} favorites`);
  q('[data-golden-badge]').hidden = !(s.golden > 0);
  q('[data-golden-left]').textContent = s.golden;
  q('[data-sound]').setAttribute('aria-pressed', String(s.sound));
  q('[data-sound]').setAttribute('aria-label', s.sound ? 'Turn sound off' : 'Turn sound on');
  q('.sound-slash').hidden = s.sound;
  q('[data-room]').src = sprite(s.festival ? 'cafe-festival' : 'cafe-' + s.level);
  const minaInLine = lineNow().some(g => g.person === 'mina');
  q('[data-staff]').hidden = s.level < 3 || minaInLine;
  q('[data-rosa-home]').hidden = !s.festival;
  renderGarland();
  renderLine();
  renderOrder();
  renderTable();
  renderChapter();
  q('[data-book-count]').textContent = `${Object.keys(s.discovered).length}/${C.RECIPES.length}`;
  const letters = letterEntries().length, unread = letters - seenLetters();
  q('[data-letter-count]').textContent = letters;
  q('[data-letters]').dataset.new = String(unread > 0);
  q('[data-staff-label]').textContent = s.level >= 3 ? (minaInLine ? 'Mina is on her break' : 'Mina · +10 every 20s') : s.festival ? 'All lanterns lit' : 'Made with love';
  q('[data-staff-track]').hidden = s.level < 3;
  staffProgress();
}

function renderGarland() {
  const g = q('[data-garland]');
  let lamps = g.querySelectorAll('.lamp');
  if (lamps.length !== LANTERNS) {
    for (let i = 0; i < LANTERNS; i++) {
      const lamp = document.createElement('span');
      lamp.className = 'lamp';
      const t = i / (LANTERNS - 1);
      lamp.style.left = (3 + t * 94) + '%';
      lamp.style.top = (Math.sin(t * Math.PI * 2) * 6 + 10 + Math.sin(t * Math.PI) * 10) + '%';
      lamp.append(Object.assign(document.createElement('img'), {alt: ''}));
      g.append(lamp);
    }
    lamps = g.querySelectorAll('.lamp');
  }
  lamps.forEach((lamp, i) => {
    const lit = i < state.chapter;
    lamp.dataset.lit = String(lit);
    lamp.querySelector('img').src = sprite(lit ? 'icon-lantern' : 'icon-lantern-dark');
  });
}

function renderLine() {
  const line = lineNow(), box = q('[data-line]');
  focus = clamp(focus, 0, Math.max(0, state.queue.length - 1));
  while (box.children.length < 3) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'guest';
    b.dataset.guest = box.children.length;
    b.innerHTML = '<span class="bubble"><img class="bubble-cup" alt=""><span class="mystery">?</span></span><img class="person" alt=""><span class="guest-hearts"></span>';
    b.addEventListener('click', () => {
      if (busy) return;
      focus = Number(b.dataset.guest);
      hint = null;
      render();
      const g = state.queue[focus];
      if (g) say(`${C.personName(g.person)} would love ${guestKnown(g) ? 'a ' + C.recipeByKey(g.key).name.toLowerCase() : 'this mystery cup'}.`,
        guestKnown(g) ? 'Bring the two ingredients together.' : 'Read the cup: its colors hint at the ingredients.');
    });
    box.append(b);
  }
  [...box.children].forEach((b, i) => {
    const g = line[i];
    b.hidden = !g;
    if (!g) return;
    const r = C.recipeByKey(g.key), known = guestKnown(g);
    b.dataset.person = g.person;
    b.dataset.focus = String(!busy && i === focus);
    b.dataset.known = String(known);
    b.disabled = busy;
    b.querySelector('.person').src = sprite(g.person);
    b.querySelector('.bubble-cup').src = sprite(r.art);
    b.querySelector('.mystery').hidden = known;
    b.querySelector('.guest-hearts').innerHTML = heartsHTML(g.person);
    b.setAttribute('aria-label', `${C.personName(g.person)} wants ${known ? r.name : 'a mystery cup'}. ${i === 0 ? 'First in line.' : ''}`);
  });
}

function renderOrder() {
  const g = busy && active ? active.line[active.result.index] : state.queue[focus];
  if (!g) return;
  const r = C.recipeByKey(g.key), known = guestKnown(g), rosa = g.person === 'rosa';
  q('[data-portrait]').src = sprite(g.person + '-portrait');
  q('[data-guest-name]').textContent = C.personName(g.person) + (rosa ? ' · home for the festival' : '');
  q('[data-guest-hearts]').innerHTML = heartsHTML(g.person);
  q('[data-order-name]').textContent = known ? r.name : 'Mystery cup';
  q('[data-order-cup]').src = sprite(r.art);
  q('[data-mystery]').hidden = known;
  const detail = q('[data-order-detail]');
  detail.replaceChildren(known ? partsChips(r) : Object.assign(document.createElement('span'), {className: 'clue', textContent: r.clue}));
  const peek = q('[data-peek]');
  peek.disabled = busy;
  peek.querySelector('[data-peek-label]').textContent = known ? 'Show pair' : 'Peek';
  peek.dataset.kind = known ? 'show' : 'peek';
  peek.setAttribute('aria-pressed', String(!!hint && C.pairKey(...hint) === g.key));
  peek.setAttribute('aria-label', known ? `Highlight the ingredients for ${r.name}` : 'Peek at the ingredients (no guessing bonus)');
}

function renderTable() {
  const tabs = q('[data-baskets]');
  const open = C.unlockedBaskets(state);
  tabs.hidden = open.length < 2;
  tabs.replaceChildren(...open.map(b => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'basket';
    btn.dataset.basket = b;
    btn.setAttribute('aria-pressed', String(state.basket === b));
    btn.setAttribute('aria-label', C.BASKETS[b].name);
    btn.disabled = busy;
    btn.append(Object.assign(document.createElement('img'), {src: sprite(C.BASKETS[b].items[0]), alt: ''}),
      Object.assign(document.createElement('span'), {textContent: C.BASKETS[b].short}));
    btn.addEventListener('click', () => pickBasket(b));
    return btn;
  }));
  for (const t of state.tokens) {
    const b = buttons.get(t.id);
    if (!drag || drag.id !== t.id) position(b, bounded(t.x, t.y));
    b.querySelector('img').src = sprite(t.type);
    b.querySelector('span').textContent = C.LABELS[t.type];
    const lit = !busy && !!hint?.includes(t.type);
    b.dataset.hint = String(lit);
    b.setAttribute('aria-label', `${C.LABELS[t.type]}${lit ? ', highlighted' : ''}. Drag onto another ingredient, or tap to select.`);
    b.setAttribute('aria-pressed', String(selected === t.id));
    b.setAttribute('aria-disabled', String(busy));
  }
  q('[data-tidy]').disabled = busy;
}

function renderChapter() {
  const p = C.chapterProgress(state), card = q('[data-chapter-card]'), buy = q('[data-buy]');
  const fill = q('[data-chapter-fill]'), bar = q('[data-chapter-progress]');
  if (!p) {
    const found = Object.keys(state.discovered).length, best = C.PEOPLE.filter(x => C.hearts(state, x) >= C.MAX_HEARTS).length;
    q('[data-chapter-number]').textContent = '★';
    q('[data-chapter-eyebrow]').textContent = `All ${LANTERNS} lanterns lit`;
    q('[data-chapter-title]').textContent = 'Every night is lantern night';
    q('[data-chapter-task]').textContent = `Recipes ${found}/${C.RECIPES.length} · Best friends ${best}/6 · Cards ${state.cards.length}/${C.CARDS.length}`;
    q('[data-chapter-count]').textContent = '';
    fill.style.width = (found / C.RECIPES.length * 100) + '%';
    bar.setAttribute('aria-valuemax', String(C.RECIPES.length));
    bar.setAttribute('aria-valuenow', String(found));
    buy.hidden = true;
    card.dataset.kind = 'done';
    q('[data-chapter-open]').hidden = false;
    return;
  }
  card.dataset.kind = p.kind;
  q('[data-chapter-open]').hidden = !['cards', 'recipes', 'friends'].includes(p.kind);
  q('[data-chapter-number]').textContent = p.index + 1;
  q('[data-chapter-eyebrow]').textContent = `Lantern ${p.index + 1} of ${LANTERNS}`;
  q('[data-chapter-title]').textContent = p.title;
  q('[data-chapter-task]').textContent = p.task;
  if (p.kind === 'buy') {
    const affordable = state.coins >= p.cost;
    q('[data-chapter-count]').textContent = affordable ? 'Ready!' : `${p.cost - state.coins} to go`;
    fill.style.width = Math.min(100, state.coins / p.cost * 100) + '%';
    bar.setAttribute('aria-valuemax', String(p.cost));
    bar.setAttribute('aria-valuenow', String(Math.min(state.coins, p.cost)));
    buy.hidden = false;
    buy.disabled = busy || !affordable;
    q('[data-buy-label]').textContent = p.action;
    q('[data-buy-cost]').textContent = p.cost;
    buy.setAttribute('aria-label', `${p.action} for ${p.cost} coins`);
  } else {
    q('[data-chapter-count]').textContent = `${p.value} / ${p.target}`;
    fill.style.width = (p.value / p.target * 100) + '%';
    bar.setAttribute('aria-valuemax', String(p.target));
    bar.setAttribute('aria-valuenow', String(p.value));
    buy.hidden = true;
  }
}

// ------------------------------------------------------------ interaction ---
function pickBasket(b) {
  if (busy || drag || !C.chooseBasket(state, b)) return;
  selected = null;
  hint = hint && hint.every(p => C.BASKETS[b].items.includes(p)) ? hint : null;
  save();
  render();
  say(C.BASKETS[b].name + '.', 'Four ingredients, six pairings. Your guests keep their places in line.');
}

function showPair() {
  if (busy || drag) return;
  const g = state.queue[focus];
  if (!g) return;
  const known = guestKnown(g);
  const r = known ? C.recipeByKey(g.key) : C.peek(state, focus);
  const basket = C.basketFor(state, r);
  if (basket && !C.onTable(state, r)) C.chooseBasket(state, basket);
  hint = r.parts;
  selected = null;
  save();
  render();
  say(`${C.personName(g.person)}: ${r.name}.`, `Drag the ${C.LABELS[r.parts[0]].toLowerCase()} onto the ${C.LABELS[r.parts[1]].toLowerCase()}.`);
}

function targetPreview(id, target) {
  clearTarget();
  if (!target) return;
  buttons.get(target.id).dataset.target = 'true';
  const a = state.tokens.find(t => t.id === id), drink = C.recipe(a.type, target.type), preview = q('[data-pair-preview]');
  if (state.discovered[drink.key]) {
    const to = C.receiver(state, drink), who = to && state.queue[to.index];
    preview.textContent = drink.name + (to?.favorite ? ` → ${C.personName(who.person)} ♥` : '');
  } else preview.textContent = '✨ Something new…';
  preview.hidden = false;
}
function clearTarget() {
  for (const b of buttons.values()) b.dataset.target = 'false';
  q('[data-pair-preview]').hidden = true;
}

function commit(idA, idB) {
  if (busy || idA === idB) return;
  const a = state.tokens[idA], b = state.tokens[idB];
  if (!a || !b) return;
  const startA = appPoint(buttons.get(idA)), startB = appPoint(buttons.get(idB)), line = JSON.parse(JSON.stringify(state.queue));
  const result = C.serve(state, idA, idB);
  if (!result) {
    selected = null;
    clearTarget();
    render();
    say('Auntie Rosa is waiting for her Lantern latte.', 'Only that cup will do. Read her recipe card in the book.');
    return;
  }
  busy = true;
  active = {result, line};
  hint = null;
  selected = null;
  clearTarget();
  for (const id of [idA, idB]) buttons.get(id).dataset.consumed = 'true';
  save();
  render();
  clearTimeout(finishTimer);
  finishTimer = setTimeout(() => finish(result), reduced() ? 380 : 1500);
  sound('pour');
  try { mixing(a.type, b.type, startA, startB, result); } catch { effects.replaceChildren(); }
  const who = C.personName(result.person);
  if (result.favorite) say(`${who}'s favorite! +${result.earned}${result.golden ? ' · golden ×2' : ''}${result.sharp ? ' · sharp eye!' : ''}`,
    result.isNew ? `New recipe: ${result.name}` : result.thanks || '');
  else say(`${result.name} for ${who}. +${result.earned}`, result.isNew ? `New recipe: ${result.name}. Not quite their order, but they are happy.` : 'Not their favorite, but every cup counts.');
}

function finish(result) {
  busy = false;
  active = null;
  effects.replaceChildren();
  for (const b of buttons.values()) b.dataset.consumed = 'false';
  focus = 0;
  render();
  const arrived = q(`[data-guest="${Math.min(result.index, state.queue.length - 1)}"]`);
  if (arrived && !reduced()) arrived.animate([{transform: 'translateX(calc(-50% + 40px))', opacity: 0}, {transform: 'translateX(-50%)', opacity: 1}], {duration: 450, easing: 'ease-out'});
  sound(result.isNew ? 'new' : 'reward');
  if (result.isNew) pulse(q('[data-book]'));
  queueMoments(result.chapters);
  if (result.heart?.gained) toast(result.person, result.heart.beat ? `♥${result.heart.hearts} · “${result.heart.beat}”` :
    result.heart.gift ? `Best friends! A gift of ${result.heart.gift} coins.` : `Friendship grew to ♥${result.heart.hearts}.`);
  if (result.card) toast('rosa', `Recipe card solved: “${result.card.title}”. +${result.card.reward} coins`);
  if (result.goldenStart) {
    sound('golden');
    toast('rosa', 'Golden hour! The next 5 cups pay double.');
  }
}

function mixing(a, b, startA, startB, result) {
  effects.replaceChildren();
  const p = appPoint(table), guest = q(`[data-guest="${result.index}"]`) || q('[data-order]'), dest = appPoint(guest);
  const img = (name, pt, cls) => {
    const el = Object.assign(document.createElement('img'), {src: sprite(name), className: cls, alt: ''});
    el.style.left = pt.x + 'px';
    el.style.top = pt.y + 'px';
    effects.append(el);
    return el;
  };
  if (reduced()) return;
  const one = img(a, startA, 'fly-prop'), two = img(b, startB, 'fly-prop');
  one.animate([{transform: 'scale(1)'}, {transform: `translate(${p.x - startA.x - 24}px,${p.y - startA.y - 14}px) rotate(-24deg) scale(.75)`, offset: .72},
    {transform: `translate(${p.x - startA.x}px,${p.y - startA.y}px) scale(.05)`, opacity: 0}], {duration: 520, fill: 'forwards', easing: 'cubic-bezier(.2,.6,.3,1)'});
  two.animate([{transform: 'scale(1)'}, {transform: `translate(${p.x - startB.x + 24}px,${p.y - startB.y - 34}px) rotate(48deg) scale(.75)`, offset: .7},
    {transform: `translate(${p.x - startB.x}px,${p.y - startB.y}px) scale(.05)`, opacity: 0}], {duration: 560, fill: 'forwards', easing: 'ease-in-out'});
  const drink = img(result.art, p, 'fly-drink');
  drink.style.opacity = '0';
  drink.animate([{opacity: 0, transform: 'scale(.15) rotate(-12deg)'}, {opacity: 1, transform: 'scale(1.12) rotate(4deg)', offset: .22},
    {opacity: 1, transform: 'scale(1)', offset: .5}, {opacity: 1, transform: `translate(${dest.x - p.x}px,${dest.y - p.y}px) scale(.4)`, offset: .9},
    {opacity: 0, transform: `translate(${dest.x - p.x}px,${dest.y - p.y}px) scale(.35)`}], {duration: 1150, delay: 300, fill: 'forwards', easing: 'ease-in-out'});
  const colors = result.golden ? ['#ffd23a', '#ffb21e', '#fff3b0'] : ['#ff5a48', '#ffd23a', '#0fa596', '#ff8ab0'];
  for (let i = 0; i < 14; i++) {
    const spark = document.createElement('i');
    spark.className = 'spark';
    spark.style.left = p.x + 'px';
    spark.style.top = p.y + 'px';
    spark.style.background = colors[i % colors.length];
    effects.append(spark);
    const ang = i * Math.PI / 7;
    spark.animate([{opacity: 0, transform: 'scale(0)'}, {opacity: 1, offset: .1}, {opacity: 0, transform: `translate(${Math.cos(ang) * 90}px,${Math.sin(ang) * 60}px) scale(.3)`}],
      {duration: 720, delay: 430, fill: 'forwards', easing: 'ease-out'});
  }
  const coins = Object.assign(document.createElement('span'), {className: 'coin-float', textContent: '+' + result.earned});
  coins.style.left = dest.x + 'px';
  coins.style.top = dest.y - 30 + 'px';
  coins.style.opacity = '0';
  effects.append(coins);
  coins.animate([{opacity: 0, transform: 'translate(-50%,0)'}, {opacity: 1, offset: .2}, {opacity: 0, transform: 'translate(-50%,-44px)'}],
    {duration: 700, delay: 980, fill: 'forwards'});
  if (result.favorite) {
    const heart = Object.assign(document.createElement('img'), {src: sprite('icon-heart'), className: 'heart-pop', alt: ''});
    heart.style.left = dest.x + 'px';
    heart.style.top = dest.y - 40 + 'px';
    heart.style.opacity = '0';
    effects.append(heart);
    heart.animate([{opacity: 0, transform: 'translate(-50%,0) scale(.3)'}, {opacity: 1, transform: 'translate(-50%,-10px) scale(1.2)', offset: .3},
      {opacity: 0, transform: 'translate(-50%,-50px) scale(.9)'}], {duration: 900, delay: 1000, fill: 'forwards'});
  }
}

function pulse(el) {
  el.classList.remove('pulse');
  void el.offsetWidth;
  el.classList.add('pulse');
}

// ---------------------------------------------------------- story moments ---
function toast(person, text) {
  toasts.push({person, text});
  if (q('[data-toast]').hidden) nextToast();
}
function nextToast() {
  const el = q('[data-toast]');
  clearTimeout(toastTimer);
  if (q('[data-moment]').open) { el.hidden = true; return; }
  const t = toasts.shift();
  if (!t) { el.hidden = true; return; }
  q('[data-toast-portrait]').src = sprite(t.person + '-portrait');
  q('[data-toast-name]').textContent = C.personName(t.person) + ' ';
  q('[data-toast-text]').textContent = t.text;
  el.hidden = false;
  if (t.person !== 'rosa' && t.text.startsWith('♥')) sound('heart');
  toastTimer = setTimeout(nextToast, Math.max(3200, t.text.length * 55));
}

const TIP_FOR = {
  cards: 'The riddles are in the recipe book.', friends: 'Hearts are shown in Letters.', recipes: 'Try new pairs in every basket.',
  golden: 'Every five favorites fill the sun.', favorites: 'Read the cups in the line.',
};
const PERSON_OF = {'Auntie Rosa': 'rosa', Jun: 'jun', Mina: 'mina', Sora: 'sora', Hana: 'hana', Leo: 'leo', Noor: 'noor'};
function queueMoments(chapters) {
  moments.push(...chapters);
  if (!q('[data-moment]').open) nextMoment();
}
function nextMoment() {
  const ch = moments.shift(), dlg = q('[data-moment]');
  if (!ch) { if (dlg.open) dlg.close(); else nextToast(); return; }
  const last = ch.id === 'festival';
  q('[data-moment-eyebrow]').textContent = last ? 'All lanterns lit' : `Lantern ${ch.index + 1} of ${LANTERNS} lit`;
  q('[data-moment-title]').textContent = ch.title;
  q('[data-moment-portrait]').src = sprite((PERSON_OF[ch.from] || 'rosa') + '-portrait');
  q('[data-moment-text]').textContent = '“' + ch.letter + '”';
  q('[data-moment-from]').textContent = '— ' + ch.from;
  q('[data-moment-reward]').textContent = ch.reward ? `A gift of ${ch.reward} coins.` : '';
  const next = C.CHAPTERS[ch.index + 1];
  q('[data-moment-next]').textContent = next ? `Next lantern: ${next.task}.${TIP_FOR[next.kind] ? ' ' + TIP_FOR[next.kind] : ''}` :
    'Petal Café is yours. Keep pouring, every night is lantern night.';
  dlg.dataset.finale = String(last);
  if (!dlg.open) dlg.showModal();
  sound('lantern');
  const lamp = q(`[data-garland] .lamp:nth-of-type(${ch.index + 1})`);
  if (lamp) pulse(lamp);
}
q('[data-moment-close]').addEventListener('click', () => { nextMoment(); if (!moments.length) render(); });

function letterEntries() {
  const out = [];
  for (let i = 0; i < state.chapter; i++) out.push({kind: 'chapter', ch: C.CHAPTERS[i], index: i});
  for (const b of state.beats) {
    const [person, h] = b.split(':');
    out.push({kind: 'beat', person, hearts: Number(h), text: C.REGULARS[person].beats[h]});
  }
  return out;
}

// ---------------------------------------------------------------- dialogs ---
function openBook() {
  if (busy || drag) return;
  const grid = q('[data-recipes]');
  grid.replaceChildren();
  for (const r of C.RECIPES) {
    const known = !!state.discovered[r.key], basket = C.basketFor(state, r);
    const card = document.createElement('button');
    card.type = 'button';
    card.className = 'sticker';
    card.dataset.state = known ? 'known' : basket ? 'unknown' : 'locked';
    card.dataset.recipe = r.key;
    const pic = Object.assign(document.createElement('img'), {src: sprite(r.art), alt: ''});
    const title = Object.assign(document.createElement('strong'), {textContent: known ? r.name : basket ? 'Undiscovered' : 'Locked'});
    const info = known ? partsChips(r) : Object.assign(document.createElement('small'), {textContent: basket ? r.clue :
      `Unlocks with the ${C.BASKETS[C.BASKET_ORDER.find(b => r.parts.every(p => C.BASKETS[b].items.includes(p)))].name.toLowerCase()}`});
    card.append(pic, title, info);
    card.disabled = !known;
    card.setAttribute('aria-label', known ? `${r.name}: ${r.parts.map(p => C.LABELS[p]).join(' and ')}. Highlight on the table.` : title.textContent + '. ' + info.textContent);
    card.addEventListener('click', () => {
      const b = C.basketFor(state, r);
      if (b && !C.onTable(state, r)) C.chooseBasket(state, b);
      hint = r.parts;
      save();
      render();
      q('[data-book-dialog]').close();
      say(`${r.name}: ${r.parts.map(p => C.LABELS[p].toLowerCase()).join(' + ')}.`, 'Serve it to anyone, or to the guest who ordered it for a tip.');
    });
    grid.append(card);
  }
  const open = C.cardsOpen(state), box = q('[data-card-box]'), list = q('[data-riddles]');
  box.hidden = !open.length;
  list.replaceChildren(...open.map(c => {
    const solved = state.cards.includes(c.id), el = document.createElement('article');
    el.className = 'riddle';
    el.dataset.solved = String(solved);
    el.innerHTML = '<img alt=""><div><strong></strong><p></p></div>';
    el.querySelector('img').src = sprite(solved ? C.recipeByKey(c.key).art : 'icon-card');
    el.querySelector('strong').textContent = c.title + (solved ? ' ✓' : '');
    el.querySelector('p').textContent = solved ? C.recipeByKey(c.key).name : '“' + c.riddle + '”';
    return el;
  }));
  q('[data-book-dialog]').showModal();
}

function openLetters() {
  if (busy || drag) return;
  const friends = q('[data-friends]');
  friends.replaceChildren(...C.PEOPLE.map(p => {
    const here = C.regularsHere(state).includes(p), el = document.createElement('div');
    el.className = 'friend';
    el.dataset.here = String(here);
    el.innerHTML = '<img alt=""><strong></strong><span class="hearts"></span>';
    el.querySelector('img').src = sprite(p + '-portrait');
    el.querySelector('strong').textContent = C.REGULARS[p].name;
    el.querySelector('.hearts').innerHTML = here ? heartsHTML(p) : '<span class="empty">not yet</span>';
    el.title = C.REGULARS[p].role;
    return el;
  }));
  const list = q('[data-letter-list]'), entries = letterEntries().reverse();
  list.replaceChildren(...entries.map(e => {
    const el = document.createElement('article');
    el.className = 'letter';
    const who = e.kind === 'chapter' ? (PERSON_OF[e.ch.from] || 'rosa') : e.person;
    el.innerHTML = '<img alt=""><div><small></small><h3></h3><p></p><span class="signature"></span></div>';
    el.querySelector('img').src = sprite(who + '-portrait');
    el.querySelector('small').textContent = e.kind === 'chapter' ? `Lantern ${e.index + 1}` : `♥${e.hearts} with ${C.REGULARS[e.person].name}`;
    el.querySelector('h3').textContent = e.kind === 'chapter' ? e.ch.title : C.REGULARS[e.person].role.replace('the ', '').replace(/^./, c => c.toUpperCase());
    el.querySelector('p').textContent = '“' + (e.kind === 'chapter' ? e.ch.letter : e.text) + '”';
    el.querySelector('.signature').textContent = '— ' + (e.kind === 'chapter' ? e.ch.from : C.REGULARS[e.person].name);
    return el;
  }));
  if (!entries.length) list.textContent = 'Letters arrive as you light lanterns and make friends.';
  try { localStorage.setItem(C.STORAGE + ':letters', String(letterEntries().length)); } catch { /* storage optional */ }
  render();
  q('[data-letters-dialog]').showModal();
}

// ------------------------------------------------------------- ingredients ---
for (let i = 0; i < 4; i++) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'ingredient';
  button.dataset.item = i;
  button.append(Object.assign(document.createElement('img'), {alt: '', draggable: false}), Object.assign(document.createElement('span'), {className: 'label'}));
  buttons.set(i, button);
  layer.append(button);
  button.addEventListener('pointerdown', e => {
    if (busy || drag || e.button !== 0) return;
    const pos = bounded(state.tokens[i].x, state.tokens[i].y);
    drag = {id: i, pointer: e.pointerId, start: {x: e.clientX, y: e.clientY}, origin: pos, pos, moved: false};
    button.setPointerCapture(e.pointerId);
    sound('pick');
  });
  button.addEventListener('pointermove', e => {
    if (!drag || drag.id !== i || drag.pointer !== e.pointerId) return;
    const dx = e.clientX - drag.start.x, dy = e.clientY - drag.start.y, {w, h} = dims();
    if (Math.hypot(dx, dy) > 6) drag.moved = true;
    if (!drag.moved) return;
    drag.pos = bounded(drag.origin.x + dx / w, drag.origin.y + dy / h);
    button.dataset.lifted = 'true';
    position(button, drag.pos);
    targetPreview(i, nearest(i, drag.pos));
  });
  button.addEventListener('pointerup', e => {
    if (!drag || drag.id !== i || drag.pointer !== e.pointerId) return;
    const old = drag;
    drag = null;
    button.dataset.lifted = 'false';
    if (!old.moved) return;
    suppress = performance.now() + 180;
    const target = nearest(i, old.pos);
    clearTarget();
    if (target) commit(i, target.id);
    else {
      Object.assign(state.tokens[i], old.pos);
      selected = null;
      save();
      render();
      say('Your table, just the way you like it.', 'Drop an ingredient onto another to make a drink.');
    }
  });
  const cancel = () => {
    if (!drag || drag.id !== i) return;
    drag = null;
    button.dataset.lifted = 'false';
    position(button, bounded(state.tokens[i].x, state.tokens[i].y));
    clearTarget();
    suppress = performance.now() + 180;
  };
  button.addEventListener('pointercancel', cancel);
  button.addEventListener('lostpointercapture', cancel);
  button.addEventListener('click', e => {
    if (busy || (e.detail && performance.now() < suppress)) return;
    if (selected !== null && selected !== i) { commit(selected, i); return; }
    selected = selected === i ? null : i;
    render();
    say(selected === null ? 'Pick any two ingredients.' : `${C.LABELS[state.tokens[i].type]} selected. Tap another ingredient.`);
  });
  button.addEventListener('keydown', e => {
    if (e.key === 'Escape') { selected = null; render(); return; }
    if (busy || !['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(e.key)) return;
    e.preventDefault();
    const t = state.tokens[i], {w, h} = dims();
    Object.assign(t, bounded(t.x + ({ArrowLeft: -12, ArrowRight: 12}[e.key] || 0) / w, t.y + ({ArrowUp: -12, ArrowDown: 12}[e.key] || 0) / h));
    save();
    render();
  });
}

// ------------------------------------------------------------------ staff ---
function staffProgress() {
  const fill = q('[data-staff-fill]');
  for (const a of fill.getAnimations()) a.cancel();
  const elapsed = state.staffMillis + Math.max(0, Date.now() - state.lastSeen), pct = clamp(elapsed / C.STAFF_MS * 100, 0, 100);
  fill.style.width = pct + '%';
  if (state.level >= 3 && !document.hidden && !reduced()) fill.animate([{width: pct + '%'}, {width: '100%'}], {duration: Math.max(1, C.STAFF_MS - elapsed), fill: 'forwards'});
}
function scheduleStaff() {
  clearTimeout(staffTimer);
  if (state.level < 3 || document.hidden) return;
  const remaining = Math.max(1, C.STAFF_MS - state.staffMillis - Math.max(0, Date.now() - state.lastSeen));
  staffTimer = setTimeout(() => {
    const amount = save();
    if (!busy) render();
    else q('[data-coins]').textContent = state.coins;
    if (amount) pulse(q('[data-staff]'));
    scheduleStaff();
  }, remaining);
}

// ------------------------------------------------------------------ wiring ---
q('[data-peek]').addEventListener('click', showPair);
q('[data-tidy]').addEventListener('click', () => {
  if (busy || drag) return;
  state.tokens.forEach((t, i) => Object.assign(t, {x: C.home[i][0], y: C.home[i][1]}));
  selected = null;
  save();
  render();
  say('A fresh little table.');
});
q('[data-buy]').addEventListener('click', () => {
  if (busy || drag) return;
  save();
  const res = C.buy(state);
  if (!res) return;
  hint = null;
  save();
  render();
  scheduleStaff();
  sound('new');
  say(`${res.action}: done!`, res.level === 2 ? 'The bakery basket is open. Sora and Leo are coming by.' : res.level === 4 ? 'The garden basket is open. Noor is on her way.' :
    res.level === 5 ? 'The lantern basket is open. Someone special is coming.' : res.level === 1 ? 'Three guests can wait in line now. Serve anyone!' : 'Mina is making coffees on her own.');
  queueMoments(res.chapters);
});
q('[data-book]').addEventListener('click', openBook);
q('[data-chapter-open]').addEventListener('click', () => (C.chapterProgress(state)?.kind === 'friends' ? openLetters : openBook)());
q('[data-letters]').addEventListener('click', openLetters);
q('[data-sound]').addEventListener('click', () => { state.sound = !state.sound; sound('pick'); save(); render(); });
for (const d of root.querySelectorAll('dialog.sheet')) {
  d.querySelector('[data-close]').addEventListener('click', () => d.close());
  d.addEventListener('click', e => {
    if (e.target !== d) return;
    const r = d.getBoundingClientRect();
    if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) d.close();
  });
}
q('[data-moment]').addEventListener('close', () => { if (moments.length) nextMoment(); else { nextToast(); render(); } });
q('[data-toast]').addEventListener('click', nextToast);
document.addEventListener('visibilitychange', () => {
  if (document.hidden) { clearTimeout(staffTimer); save(); return; }
  const amount = C.offline(state);
  if (amount) say(`Mina kept the café going: +${amount} coins.`, 'Up to five minutes of earnings while you were away.');
  save();
  render();
  scheduleStaff();
});
window.addEventListener('pagehide', () => { clearTimeout(staffTimer); save(); });
new ResizeObserver(() => { if (!drag) render(); }).observe(table);

render();
save();
scheduleStaff();
if (!storageOK) say('Your café is open. Saving is unavailable in this browser.');
else if (migrated) say('Welcome back! Your café moved to Lantern Street.', 'Coins, renovations, recipes and friendships came with you.');
else if (state.served === 0) {
  hint = C.recipeByKey(state.queue[0].key).parts;
  render();
  say('Mina would love a strawberry milk.', 'Drag the glowing strawberry onto the milk.');
  if (state.chapter === 0 && !letterEntries().length) {
    q('[data-moment-eyebrow]').textContent = 'A letter from the seaside';
    q('[data-moment-title]').textContent = 'The key is under the flowerpot';
    q('[data-moment-portrait]').src = sprite('rosa-portrait');
    q('[data-moment-text]').textContent = '“' + C.CHAPTERS[0].letter + '”';
    q('[data-moment-from]').textContent = '— Auntie Rosa';
    q('[data-moment-reward]').textContent = '';
    q('[data-moment-next]').textContent = 'Light all twelve lanterns before the Lantern Festival.';
    q('[data-moment]').dataset.finale = 'false';
    q('[data-moment]').showModal();
  }
} else say(`Welcome back to Lantern Street.`, welcome ? `Mina earned ${welcome} coins while you were away.` : 'Your guests are waiting.');
// Preload sprites so drinks never pop in mid-animation.
for (const name of [...Object.keys(C.LABELS), ...C.RECIPES.map(r => r.art), ...C.PEOPLE, 'rosa', ...C.PEOPLE.map(p => p + '-portrait'), 'rosa-portrait',
  'cafe-1', 'cafe-2', 'cafe-3', 'cafe-4', 'cafe-5', 'cafe-festival', 'icon-heart', 'icon-lantern', 'icon-lantern-dark', 'icon-card']) new Image().src = sprite(name);
