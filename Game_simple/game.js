import * as C from './core.mjs';
import {t, getLanguage, setLanguage, localizePage, LANGUAGE_KEY} from './i18n.mjs';
import {createSaveSession} from './save-session.mjs';

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
let busy = false, active = null, drag = null, hint = null, focus = 0, suppress = 0, suppressItem = -1, audio;
let cupParts = [], timingElapsed = 0, timingValue = 0, timingFrame, timingLast = null, lastTaste = null;
let staffTimer, finishTimer, toastTimer, stockTimer;
const moments = [], toasts = [];
let lastFeedback = ['', ''], shownMoment = null, shownToast = null, initialized = false;
const session = createSaveSession(C.STORAGE, suspendSession);
const seenLetters = () => { try { return Number(localStorage.getItem(C.STORAGE + ':letters')) || 0; } catch { return 0; } };
// A pour saves its completed chapters before its letters appear. Keep them in the save until
// shown, so a tab handover or leaving mid-pour cannot lose a chapter letter.
function rememberLetters(chapters) {
  if (chapters?.length) state.letters = [...new Set([...(state.letters || []), ...chapters.map(c => c.index)])];
}
// Keyboard players get focus back after a pour; pointer players never see a focus ring from it.
let keyboardInput = false, sessionStatus = '';
document.addEventListener('keydown', () => { keyboardInput = true; }, true);
document.addEventListener('pointerdown', () => { keyboardInput = false; }, true);
let welcome = 0;

function save() {
  if (!session.active) return 0;
  const amount = C.offline(state);
  if (!session.persistent) { storageOK = false; return amount; }
  try { localStorage.setItem(C.STORAGE, JSON.stringify(state)); } catch { storageOK = false; }
  return amount;
}
function say(main, detail = '') {
  lastFeedback = [main, detail];
  refreshFeedback();
}
const messageText = value => typeof value === 'function' ? value() : t(value);
function refreshFeedback() {
  q('[data-feedback]').textContent = messageText(lastFeedback[0]);
  q('[data-feedback-detail]').textContent = messageText(lastFeedback[1]);
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
  const top = Math.min(.45, (34 + hy) / h);
  return {x: clamp(x, hx / w, 1 - hx / w), y: clamp(y, Math.max(hy / h, top), 1 - hy / h)};
}
function position(button, pos) { button.style.left = pos.x * 100 + '%'; button.style.top = pos.y * 100 + '%'; }
let boardPositions = [];
const gridPosition = id => boardPositions[id];
function layoutTable() {
  const {w, h} = dims(), count = state.tokens.length;
  const wide = matchMedia('(max-height: 460px) and (min-width: 480px)').matches;
  const top = wide ? 30 : 34, available = h - top - 4;
  const dense = count > 6;
  // A short, wide board (landscape, or a compact phone with the full table) uses three rows.
  const threeRows = dense && (wide || w / Math.max(1, available) > 1.75);
  let cells, cols, rows;
  if (threeRows) {
    cols = 6; rows = 3;
    cells = [[0,0],[5,0],[0,2],[5,2],[0,1],[5,1],[1,0],[4,0],[1,1],[4,1],[1,2],[4,2]];
  } else if (dense) {
    cols = 4; rows = 4;
    cells = [[0,0],[3,0],[0,3],[3,3],[0,1],[3,1],[0,2],[3,2],[1,0],[2,0],[1,3],[2,3]];
  } else {
    cols = 3; rows = count > 4 ? 3 : 2;
    cells = [[0,0],[2,0],[0,rows-1],[2,rows-1],[0,1],[2,1]];
  }
  const cellW = w / cols, cellH = available / rows, pieceW = Math.min(90, cellW - 8);
  // The cup fills the free centre: two columns in three-row boards, the 2x2 middle of a 4x4 ring.
  const cupW = Math.min(threeRows ? cellW * 1.86 : dense ? w * .38 : cellW * .93, 128);
  const cupH = Math.min(dense && !threeRows ? available / 2 - 8 : available - 8, 142);
  const artH = Math.max(36, Math.min(cupH - 28, cupW / .8));
  table.style.setProperty('--rack-top', top + 'px');
  table.style.setProperty('--piece-width', pieceW + 'px');
  table.style.setProperty('--piece-height', Math.min(94, cellH - 4) + 'px');
  table.style.setProperty('--cup-width', cupW + 'px');
  table.style.setProperty('--cup-height', cupH + 'px');
  table.style.setProperty('--art-height', artH + 'px');
  table.style.setProperty('--art-width', artH * .8 + 'px');
  table.dataset.dense = String(dense);
  table.dataset.cols = cols;
  table.dataset.rows = rows;
  table.dataset.narrow = String(pieceW < 56);
  boardPositions = cells.slice(0, count).map(([x,y]) => ({x:(x+.5)/cols, y:(top + cellH*(y+.5))/h}));
}

function overCup(x, y) {
  const r = q('[data-cup]').getBoundingClientRect();
  return x >= r.left - 6 && x <= r.right + 6 && y >= r.top - 6 && y <= r.bottom + 6;
}
function appPoint(el) {
  const a = root.getBoundingClientRect(), r = el.getBoundingClientRect();
  return {x: r.x + r.width / 2 - a.x, y: r.y + r.height / 2 - a.y};
}

// ---------------------------------------------------------------- helpers ---
const drinkName = r => r.custom ? t`House blend: ${r.parts.map(p => t(C.LABELS[p])).join(' + ')}` : t(r.name);
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
    chip.append(Object.assign(document.createElement('img'), {src: sprite(p), alt: ''}), t(C.LABELS[p]));
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
  root.dataset.shelfUnlocked = String(s.level >= 1);
  root.dataset.ready = String(initialized);
  root.dataset.ingredientCount = String(s.tokens.length);
  q('[data-coins]').textContent = s.coins;
  const pips = q('[data-glow-pips]').children;
  for (let i = 0; i < pips.length; i++) pips[i].dataset.on = String(s.golden > 0 || i < s.glow);
  q('[data-glow]').hidden = !C.picturesOnly(s);
  q('[data-glow]').setAttribute('aria-label', s.golden > 0 ? t`Golden hour: ${s.golden} doubled cups left` : t`Golden hour meter: ${s.glow} of ${C.GLOW_MAX} favorites`);
  q('[data-golden-badge]').hidden = !(s.golden > 0);
  q('[data-golden-left]').textContent = s.golden;
  q('[data-sound]').setAttribute('aria-pressed', String(s.sound));
  q('[data-sound]').setAttribute('aria-label', t(s.sound ? 'Turn sound off' : 'Turn sound on'));
  q('.sound-slash').hidden = s.sound;
  q('[data-room]').src = sprite(s.festival ? 'cafe-festival' : 'cafe-' + s.level);
  const minaInLine = lineNow().some(g => g.person === 'mina');
  q('[data-staff]').hidden = s.level < 3 || minaInLine;
  q('[data-rosa-home]').hidden = !s.festival;
  renderGarland();
  renderLine();
  renderOrder();
  renderTable();
  renderCup();
  renderShelf();
  renderChapter();
  q('[data-book-count]').textContent = `${Object.keys(s.discovered).length}/${C.RECIPES.length}`;
  const letters = letterEntries().length, unread = letters - seenLetters();
  q('[data-letter-count]').textContent = letters;
  q('[data-letters]').dataset.new = String(unread > 0);
  q('[data-staff-label]').textContent = t(s.level >= 3 ? (minaInLine ? 'Mina is on her break' : 'Mina · +10 every 20s') : s.festival ? 'All lanterns lit' : 'Made with love');
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
      if (g) say(() => t`${t(C.personName(g.person))} would love ${guestKnown(g) ? t(C.recipeByKey(g.key).name).toLowerCase() : t('this mystery cup')}.`,
        guestKnown(g) ? 'Add those two ingredients to the cup.' : 'Read the cup: its colors hint at the ingredients.');
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
    b.setAttribute('aria-label', t`${t(C.personName(g.person))} wants ${known ? t(r.name) : t('a mystery cup')}. ${i === 0 ? t('First in line.') : ''}`);
  });
}

function renderOrder() {
  const g = busy && active && !active.result.stored ? active.line[active.result.index] : state.queue[focus];
  if (!g) return;
  const r = C.recipeByKey(g.key), known = guestKnown(g), rosa = g.person === 'rosa';
  q('[data-portrait]').src = sprite(g.person + '-portrait');
  q('[data-guest-name]').textContent = t(C.personName(g.person)) + (rosa ? t(' · home for the festival') : '');
  q('[data-guest-hearts]').innerHTML = heartsHTML(g.person);
  q('[data-order-name]').textContent = t(known ? r.name : 'Mystery cup');
  q('[data-order-cup]').src = sprite(r.art);
  q('[data-mystery]').hidden = known;
  const detail = q('[data-order-detail]');
  detail.replaceChildren(known ? partsChips(r) : Object.assign(document.createElement('span'), {className: 'clue', textContent: t(r.clue)}));
  const peek = q('[data-peek]');
  peek.disabled = busy;
  peek.querySelector('[data-peek-label]').textContent = t(known ? 'Show pair' : 'Peek');
  peek.dataset.kind = known ? 'show' : 'peek';
  peek.setAttribute('aria-pressed', String(!!hint && C.pairKey(...hint) === g.key));
  peek.setAttribute('aria-label', known ? t`Highlight the ingredients for ${t(r.name)}` : t('Peek at the ingredients (no guessing bonus)'));
}

function renderTable() {
  layoutTable();
  q('[data-table-count]').textContent = t`Ingredients · ${state.tokens.length}/${C.INGREDIENT_ORDER.length}`;
  for (const [id, button] of buttons) {
    button.hidden = id >= state.tokens.length;
    q(`[data-cell="${id}"]`).hidden = button.hidden;
  }
  for (const token of state.tokens) {
    const b = buttons.get(token.id);
    const pos = gridPosition(token.id);
    position(q(`[data-cell="${token.id}"]`), pos);
    if (!drag || drag.id !== token.id) position(b, pos);
    b.querySelector('img').src = sprite(token.type);
    b.querySelector('span').textContent = t(C.LABELS[token.type]);
    b.title = t(C.LABELS[token.type]);
    const lit = !busy && !!hint?.includes(token.type);
    b.dataset.hint = String(lit);
    const added = cupParts.includes(token.id);
    b.setAttribute('aria-label', t`${t(C.LABELS[token.type])}${lit ? t(', highlighted') : ''}. Drag into the cup, or tap to add.`);
    b.setAttribute('aria-pressed', String(added));
    b.setAttribute('aria-disabled', String(busy || added || cupParts.length === 2));
    b.dataset.added = String(added);
  }
  q('[data-tidy]').disabled = busy;
}

function renderChapter() {
  const p = C.chapterProgress(state), card = q('[data-chapter-card]'), buy = q('[data-buy]');
  const fill = q('[data-chapter-fill]'), bar = q('[data-chapter-progress]');
  if (!p) {
    const found = Object.keys(state.discovered).length, best = C.PEOPLE.filter(x => C.hearts(state, x) >= C.MAX_HEARTS).length;
    q('[data-chapter-number]').textContent = '★';
    q('[data-chapter-eyebrow]').textContent = t`All ${LANTERNS} lanterns lit`;
    q('[data-chapter-title]').textContent = t('Every night is lantern night');
    q('[data-chapter-task]').textContent = t`Recipes ${found}/${C.RECIPES.length} · Best friends ${best}/6 · Cards ${state.cards.length}/${C.CARDS.length}`;
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
  q('[data-chapter-eyebrow]').textContent = t`Lantern ${p.index + 1} of ${LANTERNS}`;
  q('[data-chapter-title]').textContent = t(p.title);
  q('[data-chapter-task]').textContent = t(p.task);
  if (p.kind === 'buy') {
    const affordable = state.coins >= p.cost;
    q('[data-chapter-count]').textContent = affordable ? t('Ready!') : t`${p.cost - state.coins} to go`;
    fill.style.width = Math.min(100, state.coins / p.cost * 100) + '%';
    bar.setAttribute('aria-valuemax', String(p.cost));
    bar.setAttribute('aria-valuenow', String(Math.min(state.coins, p.cost)));
    buy.hidden = false;
    buy.disabled = busy || !affordable;
    q('[data-buy-label]').textContent = t(p.action);
    q('[data-buy-cost]').textContent = p.cost;
    buy.setAttribute('aria-label', t`${t(p.action)} for ${p.cost} coins`);
  } else {
    q('[data-chapter-count]').textContent = `${p.value} / ${p.target}`;
    fill.style.width = (p.value / p.target * 100) + '%';
    bar.setAttribute('aria-valuemax', String(p.target));
    bar.setAttribute('aria-valuenow', String(p.value));
    buy.hidden = true;
  }
}

function renderShelf() {
  q('[data-shelf]').hidden = state.level < 1;
  const prep = q('[data-prep]');
  prep.disabled = busy;
  prep.setAttribute('aria-pressed', String(state.prep));
  q('[data-prep-label]').textContent = t(state.prep ? 'Make ahead' : 'Serve now');
  q('[data-prep-detail]').textContent = t(state.prep ? 'Tap to serve now' : 'Tap to make ahead');
  for (const button of root.querySelectorAll('[data-stock]')) {
    const drink = C.recipeByKey(state.stock[Number(button.dataset.stock)]);
    button.disabled = busy || cupParts.length > 0 || !drink;
    button.dataset.filled = String(!!drink);
    button.dataset.perfect = String(state.stockPerfect?.[Number(button.dataset.stock)] === true);
    const img = button.querySelector('img');
    img.hidden = !drink;
    if (drink) img.src = sprite(drink.art);
    button.querySelector('span').hidden = !!drink;
    button.setAttribute('aria-label', drink ? t`${drinkName(drink)}. Tap to serve; matching orders serve automatically.` + (button.dataset.perfect === 'true' ? ' ' + t('Perfect taste: +5 when served.') : '') : t`Empty preparation space ${Number(button.dataset.stock) + 1}`);
    button.title = drink ? drinkName(drink) : t('Save a drink for later');
    let parts = button.querySelector('.saved-parts');
    if (!parts) { parts = document.createElement('span'); parts.className = 'saved-parts'; button.append(parts); }
    parts.replaceChildren(...(drink?.custom ? drink.parts.map(p => Object.assign(document.createElement('img'), {src:sprite(p), alt:''})) : []));
    parts.hidden = !drink?.custom;
  }
}

// ------------------------------------------------------------ interaction ---

function showPair() {
  if (busy || drag) return;
  const g = state.queue[focus];
  if (!g) return;
  const known = guestKnown(g);
  const r = known ? C.recipeByKey(g.key) : C.peek(state, focus);
  hint = r.parts;
  resetCup();
  save();
  render();
  say(() => `${t(C.personName(g.person))}: ${t(r.name)}.`, () => t`Add ${t(C.LABELS[r.parts[0]]).toLowerCase()} and ${t(C.LABELS[r.parts[1]]).toLowerCase()} to the cup.`);
}

function clearTarget() {
  q('[data-cup]').dataset.target = 'false';
  q('[data-pair-preview]').hidden = true;
}
function resetCup() {
  cupParts = []; timingElapsed = timingValue = 0; timingLast = null; lastTaste = null;
  cancelAnimationFrame(timingFrame); timingFrame = null;
  clearTarget();
}
function renderCup() {
  const cup = q('[data-cup]'), complete = cupParts.length === 2;
  const colors = {strawberry:'#ff597e', mango:'#ffbd28', milk:'#fff0ce', coffee:'#7c4738', banana:'#ffe375', cocoa:'#9a5c42', blueberry:'#9470d7', orange:'#ffa43b', tea:'#d6a952', peach:'#ffaf91', honey:'#f4b928', matcha:'#8bb858'};
  const ingredients = cupParts.map(id => state.tokens[id].type);
  cup.dataset.filled = String(cupParts.length);
  cup.dataset.mixing = String(busy && !!active);
  q('[data-cup-count]').textContent = cupParts.length + ' / 2';
  q('[data-cup-caption]').textContent = t(busy ? 'Pouring…' : complete ? 'Ready to mix' : cupParts.length ? 'One more' : 'Drop here');
  q('[data-cup-parts]').replaceChildren(...ingredients.map(type => Object.assign(document.createElement('img'), {src:sprite(type), alt:''})));
  const liquid = q('[data-cup-liquid]');
  liquid.style.setProperty('--fill', [0, .38, .74][cupParts.length]);
  liquid.style.background = ingredients.length ? 'linear-gradient(0deg, ' + ingredients.map(type => colors[type]).join(', ') + (ingredients.length === 1 ? ', '+colors[ingredients[0]] : '') + ')' : 'transparent';
  const drink = q('[data-cup-finished]');
  drink.hidden = !busy || !active;
  if (!drink.hidden) drink.src = sprite(active.result.art);
  cup.setAttribute('aria-label', t`Mixing cup: ${cupParts.length} of 2 ingredients. ${ingredients.map(type => t(C.LABELS[type])).join(' + ')}`);
  cup.disabled = busy;
  const stop = q('[data-mix-stop]');
  stop.disabled = !session.active || !complete || busy;
  q('[data-mix-label]').textContent = t(busy ? 'Pouring…' : state.prep ? 'Stop & save' : 'Stop & pour');
  q('[data-mix-detail]').textContent = t(complete ? '+5 taste bonus' : 'Add 2 ingredients');
  q('[data-timing-label]').textContent = lastTaste !== null ? t(lastTaste ? 'Perfect taste! ★' : 'A lovely cup!') : t(complete ? 'Tap when it is green' : 'Fill the cup first');
  q('[data-timing-track]').dataset.result = lastTaste === null ? '' : lastTaste ? 'perfect' : 'normal';
  q('[data-timing-track]').dataset.running = String(complete && !busy);
  q('[data-timing-marker]').style.left = (timingValue * 100) + '%';
  if (complete && !busy && !timingFrame && session.active) timingFrame = requestAnimationFrame(tickTiming);
}
function tickTiming(now) {
  timingFrame = null;
  if (cupParts.length !== 2 || busy || !session.active) return;
  if (document.hidden || root.querySelector('dialog[open]')) timingLast = null;
  else {
    if (timingLast !== null) timingElapsed += Math.min(80, now - timingLast);
    timingLast = now;
    timingValue = C.timingPosition(timingElapsed, reduced() ? 4200 : C.TIMING_PERIOD);
    q('[data-timing-marker]').style.left = (timingValue * 100) + '%';
  }
  timingFrame = requestAnimationFrame(tickTiming);
}
function addIngredient(id) {
  if (!session.active || !state.tokens[id] || busy || cupParts.length === 2 || cupParts.includes(id)) return;
  if (state.prep && state.stock.length >= C.STOCK_LIMIT) {
    say('Your shelf is full.', 'Tap a saved cup to serve it, or switch to Serve now.'); return;
  }
  if (!cupParts.length) { lastTaste = null; timingElapsed = timingValue = 0; }
  cupParts.push(id);
  sound('pick');
  clearTimeout(stockTimer);
  render();
  const type = state.tokens[id].type;
  say(cupParts.length === 2 ? 'Ready! Stop the marker in green.' : () => t`${t(C.LABELS[type])} is in the cup. Add one more.`, 'A green hit adds 5 coins. Every other cup still earns money.');
  if (!reduced()) {
    const start = appPoint(buttons.get(id)), end = appPoint(q('[data-cup]'));
    const img = Object.assign(document.createElement('img'), {src:sprite(type), className:'fly-prop', alt:''});
    img.style.left = start.x+'px'; img.style.top = start.y+'px'; effects.append(img);
    img.animate([{transform:'scale(.8)',opacity:1},{transform:'translate('+(end.x-start.x)+'px,'+(end.y-start.y)+'px) scale(.2)',opacity:0}], {duration:320,easing:'ease-in'}).finished.then(()=>img.remove(),()=>img.remove());
  }
}
function stopMix() {
  if (!session.active || busy || cupParts.length !== 2 || drag || document.hidden || root.querySelector('dialog[open]')) return;
  const perfect = C.perfectTiming(timingValue);
  commit(cupParts[0], cupParts[1], perfect);
}

function commit(idA, idB, perfect) {
  if (busy || idA === idB) return;
  const a = state.tokens[idA], b = state.tokens[idB];
  if (!a || !b) return;
  const startA = appPoint(q('[data-cup]')), startB = startA, line = JSON.parse(JSON.stringify(state.queue));
  const result = state.prep ? C.prepare(state, idA, idB, perfect) : C.serve(state, idA, idB, perfect);
  rememberLetters(result?.chapters);
  if (!result) {
    resetCup();
    clearTarget();
    render();
    if (state.prep) say('Your shelf is full.', 'Tap a saved cup to serve it, or switch to Serve now.');
    else say('Auntie Rosa is waiting for her Lantern latte.', 'Only that cup will do. Read her recipe card in the book.');
    return;
  }
  busy = true;
  clearTimeout(stockTimer);
  active = {result, line, focus: keyboardFocus(), fallback: idA};
  hint = null;
  lastTaste = perfect;
  cancelAnimationFrame(timingFrame); timingFrame = null;
  clearTarget();
  for (const id of [idA, idB]) buttons.get(id).dataset.consumed = 'true';
  save();
  render();
  clearTimeout(finishTimer);
  finishTimer = setTimeout(() => finish(result), reduced() ? 380 : 1500);
  sound('pour');
  try { mixing(a.type, b.type, startA, startB, result); } catch { effects.replaceChildren(); }
  if (result.stored) {
    say(() => (result.perfect ? '★ ' : '') + t`${t(result.name)} saved for later.`, result.perfect ? 'Perfect taste: +5 when served.' : 'Matching guests get it automatically. Tap a saved cup to serve anyone.');
    return;
  }
  if (result.favorite) say(() => t`${t(C.personName(result.person))}'s favorite! +${result.earned}${result.golden ? t(' · golden ×2') : ''}${result.sharp ? t(' · sharp eye!') : ''}`,
    () => result.isNew ? t`New recipe: ${t(result.name)}` : t(result.thanks || ''));
  else say(() => t`${t(result.name)} for ${t(C.personName(result.person))}. +${result.earned}`, () => result.isNew ? t`New recipe: ${t(result.name)}. Not quite their order, but they are happy.` : t('Not their favorite, but every cup counts.'));
}

const keyboardFocus = () => keyboardInput && root.contains(document.activeElement) ? document.activeElement : null;
function restoreFocus(previous, fallback) {
  if (!previous || (root.contains(document.activeElement) && document.activeElement !== previous) || root.querySelector('dialog[open]')) return;
  const usable = el => el?.isConnected && !el.disabled && el.getAttribute('aria-disabled') !== 'true' && !el.hidden && getComputedStyle(el).visibility !== 'hidden';
  const target = [previous, buttons.get(fallback), ...buttons.values()].find(usable);
  target?.focus({preventScroll: true});
}
function finish(result) {
  const pour = active;
  busy = false;
  active = null;
  cupParts = []; timingLast = null;
  effects.replaceChildren();
  for (const b of buttons.values()) b.dataset.consumed = 'false';
  focus = 0;
  render();
  const arrived = q(`[data-guest="${Math.min(result.index, state.queue.length - 1)}"]`);
  if (!result.stored && arrived && !reduced()) arrived.animate([{transform: 'translateX(calc(-50% + 40px))', opacity: 0}, {transform: 'translateX(-50%)', opacity: 1}], {duration: 450, easing: 'ease-out'});
  sound(result.isNew ? 'new' : 'reward');
  if (result.isNew) pulse(q('[data-book]'));
  queueMoments(result.chapters);
  restoreFocus(pour?.focus, pour?.fallback);
  if (result.heart?.gained) toast(result.person, () => result.heart.beat ? `♥${result.heart.hearts} · “${t(result.heart.beat)}”` :
    result.heart.gift ? t`Best friends! A gift of ${result.heart.gift} coins.` : t`Friendship grew to ♥${result.heart.hearts}.`);
  if (result.card) toast('rosa', () => t`Recipe card solved: “${t(result.card.title)}”. +${result.card.reward} coins`);
  if (result.goldenStart) {
    sound('golden');
    toast('rosa', 'Golden hour! The next 5 cups pay double.');
  }
  scheduleStock();
}

function deliverStock(index, automatic = false) {
  if (!session.active || busy || drag || cupParts.length || document.hidden || root.querySelector('dialog[open]')) return;
  const start = appPoint(q(`[data-stock="${index}"]`)), line = JSON.parse(JSON.stringify(state.queue));
  const result = C.serveStock(state, index, automatic);
  if (!result) return;
  rememberLetters(result.chapters);
  clearTimeout(stockTimer);
  busy = true;
  active = {result, line, focus: keyboardFocus(), fallback: 0};
  resetCup();
  lastTaste = result.perfect;
  hint = null;
  clearTarget();
  save();
  render();
  finishTimer = setTimeout(() => finish(result), reduced() ? 380 : 700);
  try { mixing(null, null, start, start, result); } catch { effects.replaceChildren(); }
  sound('pour');
  say(() => t`${t(result.name)} for ${t(C.personName(result.person))}. +${result.earned}`, result.favorite ? 'Ready right on time! Favorite tip included.' : 'Every saved cup earns coins.');
}

function scheduleStock() {
  clearTimeout(stockTimer);
  if (!session.active || busy || drag || cupParts.length || document.hidden || root.querySelector('dialog[open]') || C.stockMatch(state) < 0) return;
  stockTimer = setTimeout(() => {
    const index = C.stockMatch(state);
    if (index >= 0) deliverStock(index, true);
  }, 500);
}

function mixing(a, b, startA, startB, result) {
  effects.replaceChildren();
  const p = appPoint(table), target = result.stored ? q(`[data-stock="${result.index}"]`) : q(`[data-guest="${result.index}"]`), dest = appPoint(target || q('[data-order]'));
  const img = (name, pt, cls) => {
    const el = Object.assign(document.createElement('img'), {src: sprite(name), className: cls, alt: ''});
    el.style.left = pt.x + 'px';
    el.style.top = pt.y + 'px';
    effects.append(el);
    return el;
  };
  if (reduced()) return;
  if (result.fromStock) {
    img(result.art, startA, 'fly-drink').animate([{transform: 'scale(.5)'}, {transform: `translate(${dest.x - startA.x}px,${dest.y - startA.y}px) scale(.4)`, opacity: 0}],
      {duration: 650, fill: 'forwards', easing: 'ease-in-out'});
    return;
  }
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
  if (result.stored) return;
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
  shownToast = toasts.shift();
  if (!shownToast) { el.hidden = true; return; }
  paintToast();
  el.hidden = false;
  const text = messageText(shownToast.text);
  if (shownToast.person !== 'rosa' && text.startsWith('♥')) sound('heart');
  toastTimer = setTimeout(nextToast, Math.max(3200, text.length * 55));
}
function paintToast() {
  if (!shownToast) return;
  q('[data-toast-portrait]').src = sprite(shownToast.person + '-portrait');
  q('[data-toast-name]').textContent = t(C.personName(shownToast.person)) + ' ';
  q('[data-toast-text]').textContent = messageText(shownToast.text);
}

const TIP_FOR = {
  cards: 'The riddles are in the recipe book.', friends: 'Hearts are shown in Letters.', recipes: 'Try new pairs anywhere on the table.',
  golden: 'Every five favorites fill the sun.', favorites: 'Read the cups in the line.',
};
const PERSON_OF = {'Auntie Rosa': 'rosa', Jun: 'jun', Mina: 'mina', Sora: 'sora', Hana: 'hana', Leo: 'leo', Noor: 'noor'};
function queueMoments(chapters) {
  moments.push(...chapters);
  if (!q('[data-moment]').open) nextMoment();
}
function nextMoment() {
  const ch = moments.shift(), dlg = q('[data-moment]');
  shownMoment = ch || null;
  if (!ch) { if (dlg.open) dlg.close(); else nextToast(); return; }
  paintMoment();
  if (!dlg.open) dlg.showModal();
  sound('lantern');
  const lamp = q(`[data-garland] .lamp:nth-of-type(${ch.index + 1})`);
  if (lamp) pulse(lamp);
}
function paintMoment() {
  const ch = shownMoment;
  if (!ch) return;
  if (ch === 'intro') {
    q('[data-moment-eyebrow]').textContent = t('A letter from the seaside');
    q('[data-moment-title]').textContent = t('The key is under the flowerpot');
    q('[data-moment-portrait]').src = sprite('rosa-portrait');
    q('[data-moment-text]').textContent = '“' + t(C.CHAPTERS[0].letter) + '”';
    q('[data-moment-from]').textContent = '— ' + t('Auntie Rosa');
    q('[data-moment-reward]').textContent = '';
    q('[data-moment-next]').textContent = t('Light all twelve lanterns before the Lantern Festival.');
    q('[data-moment]').dataset.finale = 'false';
    return;
  }
  const last = ch.id === 'festival';
  if (state.letters?.includes(ch.index)) {
    state.letters = state.letters.filter(i => i !== ch.index);
    save();
  }
  q('[data-moment-eyebrow]').textContent = last ? t('All lanterns lit') : t`Lantern ${ch.index + 1} of ${LANTERNS} lit`;
  q('[data-moment-title]').textContent = t(ch.title);
  q('[data-moment-portrait]').src = sprite((PERSON_OF[ch.from] || 'rosa') + '-portrait');
  q('[data-moment-text]').textContent = '“' + t(ch.letter) + '”';
  q('[data-moment-from]').textContent = '— ' + t(ch.from);
  q('[data-moment-reward]').textContent = ch.reward ? t`A gift of ${ch.reward} coins.` : '';
  const next = C.CHAPTERS[ch.index + 1];
  q('[data-moment-next]').textContent = next ? t`Next lantern: ${t(next.task)}.${TIP_FOR[next.kind] ? ' ' + t(TIP_FOR[next.kind]) : ''}` :
    t('Petal Café is yours. Keep pouring, every night is lantern night.');
  q('[data-moment]').dataset.finale = String(last);
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
    const title = Object.assign(document.createElement('strong'), {textContent: t(known ? r.name : basket ? 'Undiscovered' : 'Locked')});
    const info = known ? partsChips(r) : Object.assign(document.createElement('small'), {textContent: basket ? t(r.clue) :
      t`Unlocks with the ${t(C.BASKETS[C.BASKET_ORDER.find(b => r.parts.every(p => C.BASKETS[b].items.includes(p)))].name).toLowerCase()}`});
    card.append(pic, title, info);
    card.disabled = !known;
    card.setAttribute('aria-label', known ? t`${t(r.name)}: ${r.parts.map(p => t(C.LABELS[p])).join(t(' and '))}. Highlight on the table.` : title.textContent + '. ' + info.textContent);
    card.addEventListener('click', () => {
      hint = r.parts;
      resetCup();
      save();
      render();
      q('[data-book-dialog]').close();
      say(() => `${t(r.name)}: ${r.parts.map(p => t(C.LABELS[p]).toLowerCase()).join(' + ')}.`, 'Serve it to anyone, or to the guest who ordered it for a tip.');
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
    el.querySelector('strong').textContent = t(c.title) + (solved ? ' ✓' : '');
    el.querySelector('p').textContent = solved ? t(C.recipeByKey(c.key).name) : '“' + t(c.riddle) + '”';
    return el;
  }));
  if (!q('[data-book-dialog]').open) q('[data-book-dialog]').showModal();
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
    el.querySelector('.hearts').innerHTML = here ? heartsHTML(p) : '<span class="empty">' + t('not yet') + '</span>';
    el.title = t(C.REGULARS[p].role);
    return el;
  }));
  const list = q('[data-letter-list]'), entries = letterEntries().reverse();
  list.replaceChildren(...entries.map(e => {
    const el = document.createElement('article');
    el.className = 'letter';
    const who = e.kind === 'chapter' ? (PERSON_OF[e.ch.from] || 'rosa') : e.person;
    el.innerHTML = '<img alt=""><div><small></small><h3></h3><p></p><span class="signature"></span></div>';
    el.querySelector('img').src = sprite(who + '-portrait');
    el.querySelector('small').textContent = e.kind === 'chapter' ? t`Lantern ${e.index + 1}` : t`♥${e.hearts} with ${C.REGULARS[e.person].name}`;
    el.querySelector('h3').textContent = e.kind === 'chapter' ? t(e.ch.title) : t(C.REGULARS[e.person].role).replace('the ', '').replace(/^./, c => c.toUpperCase());
    el.querySelector('p').textContent = '“' + t(e.kind === 'chapter' ? e.ch.letter : e.text) + '”';
    el.querySelector('.signature').textContent = '— ' + t(e.kind === 'chapter' ? e.ch.from : C.REGULARS[e.person].name);
    return el;
  }));
  if (!entries.length) list.textContent = t('Letters arrive as you light lanterns and make friends.');
  try { localStorage.setItem(C.STORAGE + ':letters', String(letterEntries().length)); } catch { /* storage optional */ }
  render();
  if (!q('[data-letters-dialog]').open) q('[data-letters-dialog]').showModal();
}

// ------------------------------------------------------------- ingredients ---
for (let i = 0; i < C.INGREDIENT_ORDER.length; i++) {
  const button = document.createElement('button');
  button.type = 'button'; button.className = 'ingredient'; button.dataset.item = i;
  button.append(Object.assign(document.createElement('img'), {alt:'',draggable:false}), Object.assign(document.createElement('span'), {className:'label'}));
  buttons.set(i, button); layer.append(button);
  const cell = document.createElement('i'); cell.dataset.cell = i; q('[data-cells]').append(cell);
  button.addEventListener('pointerdown', e => {
    if (!state.tokens[i] || busy || drag || cupParts.length === 2 || cupParts.includes(i) || e.button !== 0) return;
    const pos = gridPosition(i);
    drag = {id:i,pointer:e.pointerId,start:{x:e.clientX,y:e.clientY},origin:pos,pos,moved:false};
    button.setPointerCapture(e.pointerId);
  });
  button.addEventListener('pointermove', e => {
    if (!drag || drag.id !== i || drag.pointer !== e.pointerId) return;
    const dx=e.clientX-drag.start.x,dy=e.clientY-drag.start.y,{w,h}=dims();
    if (Math.hypot(dx,dy)>6) drag.moved=true;
    if (!drag.moved) return;
    drag.pos=bounded(drag.origin.x+dx/w,drag.origin.y+dy/h);
    button.dataset.lifted='true'; position(button,drag.pos);
    q('[data-cup]').dataset.target=String(overCup(e.clientX,e.clientY));
  });
  button.addEventListener('pointerup', e => {
    if (!drag || drag.id!==i || drag.pointer!==e.pointerId) return;
    const moved=drag.moved; drag=null; button.dataset.lifted='false'; clearTarget();
    position(button,gridPosition(i));
    if (moved) {
      suppress=performance.now()+220; suppressItem=i;
      if (overCup(e.clientX,e.clientY)) addIngredient(i);
      else say('Drop inside the cup, or tap an ingredient.');
    }
    scheduleStock();
  });
  const cancel=()=>{
    if (!drag || drag.id!==i) return;
    drag=null; button.dataset.lifted='false'; position(button,gridPosition(i));
    clearTarget(); suppress=performance.now()+220; suppressItem=i; scheduleStock();
  };
  button.addEventListener('pointercancel',cancel);
  button.addEventListener('lostpointercapture',cancel);
  button.addEventListener('click',e=>{if (!e.detail || i!==suppressItem || performance.now()>=suppress) addIngredient(i);});
  button.addEventListener('keydown',e=>{
    if (e.key==='Escape' && !busy) {resetCup();render();scheduleStock();return;}
    const direction={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[e.key];
    if (direction) {
      e.preventDefault();
      const origin=gridPosition(i), {w,h}=dims();
      const next=boardPositions.map((p,id)=>{
        const dx=(p.x-origin.x)*w,dy=(p.y-origin.y)*h;
        return {id,forward:dx*direction[0]+dy*direction[1],side:Math.abs(dx*direction[1]+dy*direction[0])};
      }).filter(p=>p.forward>1).sort((a,b)=>(a.forward+2*a.side)-(b.forward+2*b.side))[0];
      if (next) buttons.get(next.id).focus();
    }
    if ((e.code==='Space'||e.key==='Enter') && cupParts.length===2 && !e.repeat) {e.preventDefault();stopMix();}
  });
}
q('[data-cup]').addEventListener('click',()=>{
  if (cupParts.length===2) stopMix();
  else say('Drag or tap two different ingredients into the cup.');
});
q('[data-mix-stop]').addEventListener('click',stopMix);
// Judge the touch as it lands, rather than when the finger lifts off the bar.
for (const button of [q('[data-mix-stop]'), q('[data-cup]')]) button.addEventListener('pointerdown', e => {
  if (e.button === 0 && cupParts.length === 2) stopMix();
});

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
  if (!session.active || state.level < 3 || document.hidden) return;
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
q('[data-prep]').addEventListener('click', () => {
  if (busy || drag || state.level < 1) return;
  state.prep = !state.prep;
  resetCup();
  clearTarget();
  save();
  render();
  say(state.prep ? 'Fill the cup to make a drink for later.' : 'Back to serving your guests.', state.prep ? 'Three spaces. Matching orders serve automatically.' : 'Every drink earns coins. Favorites add a tip.');
  scheduleStock();
});
for (const button of root.querySelectorAll('[data-stock]')) button.addEventListener('click', () => deliverStock(Number(button.dataset.stock)));
q('[data-tidy]').addEventListener('click', () => {
  if (busy || drag) return;
  resetCup();
  save();
  render();
  say('The cup is empty. Try a fresh pair.');
  scheduleStock();
});
q('[data-buy]').addEventListener('click', () => {
  if (busy || drag) return;
  save();
  const res = C.buy(state);
  if (!res) return;
  rememberLetters(res.chapters);
  hint = null;
  save();
  render();
  scheduleStaff();
  sound('new');
  say(() => t`${t(res.action)}: done!`, res.level === 2 ? 'Banana and cocoa are on the table. Sora and Leo are coming by.' : res.level === 4 ? 'Blueberry, orange and tea are on the table. Noor is on her way.' :
    res.level === 5 ? 'Peach, honey and matcha are on the table. Someone special is coming.' : res.level === 1 ? 'Your prep shelf is open. Make ahead for the line of three!' : 'Mina is making coffees on her own.');
  queueMoments(res.chapters);
  scheduleStock();
});
q('[data-book]').addEventListener('click', openBook);
q('[data-chapter-open]').addEventListener('click', () => (C.chapterProgress(state)?.kind === 'friends' ? openLetters : openBook)());
q('[data-letters]').addEventListener('click', openLetters);
q('[data-sound]').addEventListener('click', () => { state.sound = !state.sound; sound('pick'); save(); render(); });
for (const d of root.querySelectorAll('dialog.sheet')) {
  d.addEventListener('close', scheduleStock);
  d.querySelector('[data-close]').addEventListener('click', () => d.close());
  d.addEventListener('click', e => {
    if (e.target !== d) return;
    const r = d.getBoundingClientRect();
    if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) d.close();
  });
}
q('[data-moment]').addEventListener('close', () => { if (moments.length) nextMoment(); else { nextToast(); render(); scheduleStock(); } });
q('[data-toast]').addEventListener('click', nextToast);
document.addEventListener('visibilitychange', () => {
  if (!session.active) return;
  if (document.hidden) { timingLast = null; clearTimeout(staffTimer); clearTimeout(stockTimer); save(); return; }
  const amount = C.offline(state);
  if (amount) say(() => t`Mina kept the café going: +${amount} coins.`, 'Up to five minutes of earnings while you were away.');
  save();
  render();
  scheduleStaff();
  scheduleStock();
});
let leaving = false;
window.addEventListener('pagehide', () => { save(); leaving = true; session.release(); });
window.addEventListener('pageshow', e => { if (e.persisted) { leaving = false; startSession(); } });
// Re-lay the table on the next frame, and only for a real size change: rendering inside
// the observer callback resizes the observed table again (WebKit reports a loop error).
let tableSize = '', resizeFrame = 0;
new ResizeObserver(() => {
  const size = table.clientWidth + 'x' + table.clientHeight;
  if (size === tableSize) return;
  tableSize = size;
  cancelAnimationFrame(resizeFrame);
  resizeFrame = requestAnimationFrame(() => { if (!drag) render(); });
}).observe(table);

function suspendSession() {
  for (const timer of [staffTimer, stockTimer, finishTimer, toastTimer]) clearTimeout(timer);
  busy = false; active = drag = hint = shownMoment = shownToast = null;
  resetCup();
  moments.length = toasts.length = 0;
  effects.replaceChildren();
  for (const button of buttons.values()) {
    button.dataset.lifted = button.dataset.consumed = 'false';
  }
  clearTarget();
  q('[data-toast]').hidden = true;
  for (const dialog of root.querySelectorAll('dialog[open]')) dialog.close();
  if (leaving) return;
  state = load() || C.freshState();
  render();
  sessionStatus = '';
  q('[data-session-status]').textContent = '';
  if (!q('[data-session-dialog]').open) q('[data-session-dialog]').showModal();
}
async function startSession() {
  const acquired = await session.acquire();
  state = load() || C.freshState();
  initialized = true;
  localizePage();
  if (!acquired) { suspendSession(); return; }
  q('[data-session-dialog]').close();
  welcome = C.offline(state);
  save();
  render();
  scheduleStaff();
  scheduleStock();
  if (migrated) say('Welcome back! Your café moved to Lantern Street.', 'Coins, renovations, recipes and friendships came with you.');
  else if (state.served === 0) {
    hint = C.recipeByKey(state.queue[0].key).parts;
    render();
    say('Mina would love a strawberry milk.', 'Drag the strawberry and milk into the center cup.');
    if (state.chapter === 0 && !letterEntries().length) {
      shownMoment = 'intro';
      paintMoment();
      q('[data-moment]').showModal();
    }
  } else say('Welcome back to Lantern Street.', welcome ? () => t`Mina earned ${welcome} coins while you were away.` : 'Your guests are waiting.');
  if (!storageOK) say('Your café is open. Saving is unavailable in this browser.');
  if (state.letters?.length) queueMoments(state.letters.map(index => ({...C.CHAPTERS[index], index})));
}
// Even synthetic clicks and keyboard events must not mutate a suspended tab.
for (const event of ['click', 'pointerdown', 'keydown']) root.addEventListener(event, e => {
  if (session.active || e.target.closest('[data-session-dialog], [data-language]')) return;
  e.preventDefault();
  e.stopImmediatePropagation();
}, true);
q('[data-session-dialog]').addEventListener('cancel', e => e.preventDefault());
// Browsers let a repeated Escape (or Android Back) close a modal even when cancel is prevented.
// A paused tab must keep this dialog: the input blocker above leaves no other way back in.
q('[data-session-dialog]').addEventListener('close', () => {
  setTimeout(() => { if (!session.active && !leaving && !q('[data-session-dialog]').open) q('[data-session-dialog]').showModal(); });
});
q('[data-session-continue]').addEventListener('click', async e => {
  const button = e.currentTarget;
  button.disabled = true;
  button.textContent = t('Connecting…');
  try {
    if (await session.takeOver()) await startSession();
    else q('[data-session-status]').textContent = t(sessionStatus = 'Close the other tab, then try again.');
  } finally {
    button.disabled = false;
    button.textContent = t('Continue in this tab');
  }
});
function changeLanguage(language) {
  setLanguage(language);
  localizePage();
  render();
  refreshFeedback();
  paintMoment();
  paintToast();
  q('[data-session-status]').textContent = sessionStatus ? t(sessionStatus) : '';
  if (q('[data-book-dialog]').open) openBook();
  if (q('[data-letters-dialog]').open) openLetters();
}
root.addEventListener('change', e => { if (e.target.matches('[data-language]')) changeLanguage(e.target.value); });
window.addEventListener('storage', e => { if (e.key === LANGUAGE_KEY && e.newValue && e.newValue !== getLanguage()) changeLanguage(e.newValue); });
startSession();
// Preload sprites so drinks never pop in mid-animation.
for (const name of [...Object.keys(C.LABELS), ...C.RECIPES.map(r => r.art), ...C.PEOPLE, 'rosa', ...C.PEOPLE.map(p => p + '-portrait'), 'rosa-portrait',
  'drink-house-blend', 'cafe-1', 'cafe-2', 'cafe-3', 'cafe-4', 'cafe-5', 'cafe-festival', 'icon-heart', 'icon-lantern', 'icon-lantern-dark', 'icon-card']) new Image().src = sprite(name);
