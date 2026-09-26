// Petal Café v5 · Lantern Street — pure game rules shared by the browser and the tests.
export const STORAGE = 'petal-cafe-v5';
export const LEGACY_V4 = 'petal-cafe-v4';
export const LEGACY_V3 = 'tiny-dessert-table-v3';

export const BASE_PAY = 10, TIP = 5, SHARP_EYE = 10, GLOW_MAX = 5, GOLDEN_CUPS = 5, MAX_HEARTS = 5;
export const BEST_FRIEND_GIFT = 40, STAFF_PAY = 10, STAFF_MS = 20000, OFFLINE_CAP_MS = 300000;

export const LABELS = {
  strawberry: 'Strawberry', mango: 'Mango', milk: 'Milk', coffee: 'Coffee', banana: 'Banana', cocoa: 'Cocoa',
  blueberry: 'Blueberry', orange: 'Orange', tea: 'Tea', peach: 'Peach', honey: 'Honey', matcha: 'Matcha',
};
// Adjectives in the clues teach which ingredient a picture order needs.
export const FLAVOR = {
  strawberry: 'berry-pink', mango: 'sunny', milk: 'creamy', coffee: 'bold', banana: 'mellow yellow',
  cocoa: 'chocolatey', blueberry: 'violet', orange: 'zesty', tea: 'steeped', peach: 'blushing',
  honey: 'golden', matcha: 'leaf-green',
};

// Baskets unlock with renovations (level = renovations bought).
export const BASKETS = {
  sunrise: {name: 'Sunrise basket', short: 'Sunrise', items: ['strawberry', 'mango', 'milk', 'coffee'], level: 0},
  bakery: {name: 'Bakery basket', short: 'Bakery', items: ['banana', 'cocoa', 'milk', 'coffee'], level: 2},
  garden: {name: 'Garden basket', short: 'Garden', items: ['blueberry', 'orange', 'milk', 'tea'], level: 4},
  lantern: {name: 'Lantern basket', short: 'Lantern', items: ['peach', 'honey', 'matcha', 'milk'], level: 5},
};
export const BASKET_ORDER = Object.keys(BASKETS);

export const pairKey = (a, b) => [a, b].sort().join('+');
const ORDER = ['strawberry', 'mango', 'banana', 'blueberry', 'orange', 'peach', 'cocoa', 'honey', 'matcha', 'coffee', 'tea', 'milk'];
const R = (a, b, name, art, clue) => ({
  key: pairKey(a, b), parts: [a, b].sort((x, y) => ORDER.indexOf(x) - ORDER.indexOf(y)), name, art: 'drink-' + art, clue,
});
export const RECIPES = [
  R('strawberry', 'milk', 'Strawberry milk', 'strawberry-milk', 'Creamy and berry-pink.'),
  R('mango', 'milk', 'Mango milk', 'mango-milk', 'Creamy and sunny.'),
  R('coffee', 'milk', 'Café latte', 'latte', 'Creamy and bold, with a heart on top.'),
  R('coffee', 'strawberry', 'Strawberry cold brew', 'strawberry-brew', 'Bold on top, berry-pink below.'),
  R('coffee', 'mango', 'Mango cold brew', 'mango-brew', 'Bold on top, sunny below.'),
  R('mango', 'strawberry', 'Sunrise smoothie', 'sunrise-smoothie', 'Berry-pink melting into sunny.'),
  R('banana', 'milk', 'Banana milk', 'banana-milk', 'Creamy and mellow yellow.'),
  R('cocoa', 'milk', 'Hot chocolate', 'hot-chocolate', 'Creamy and chocolatey, with marshmallows.'),
  R('banana', 'coffee', 'Banana cold brew', 'banana-brew', 'Bold on top, mellow yellow below.'),
  R('cocoa', 'coffee', 'Café mocha', 'mocha', 'Bold and chocolatey under whipped cream.'),
  R('banana', 'cocoa', 'Banana cocoa shake', 'banana-cocoa-shake', 'Chocolatey below, mellow yellow above.'),
  R('blueberry', 'milk', 'Blueberry milk', 'blueberry-milk', 'Creamy and violet.'),
  R('milk', 'orange', 'Orange cream', 'orange-cream', 'Creamy and zesty.'),
  R('milk', 'tea', 'Bubble milk tea', 'bubble-tea', 'Creamy and steeped, with pearls.'),
  R('blueberry', 'tea', 'Blueberry iced tea', 'blueberry-tea', 'Steeped and violet, with mint.'),
  R('orange', 'tea', 'Orange iced tea', 'orange-tea', 'Steeped and zesty.'),
  R('blueberry', 'orange', 'Twilight smoothie', 'twilight-smoothie', 'Violet melting into zesty.'),
  R('milk', 'peach', 'Peach milk', 'peach-milk', 'Creamy and blushing.'),
  R('honey', 'milk', 'Honey moon milk', 'honey-milk', 'Creamy and golden.'),
  R('matcha', 'milk', 'Matcha latte', 'matcha-latte', 'Leaf-green below, creamy above.'),
  R('matcha', 'peach', 'Peach matcha', 'peach-matcha', 'Leaf-green over blushing.'),
  R('honey', 'matcha', 'Lantern latte', 'lantern-latte', "Golden and leaf-green: Auntie Rosa's cup."),
  R('honey', 'peach', 'Honey peach fizz', 'honey-peach-fizz', 'Golden, blushing and fizzy.'),
];
const BY_KEY = new Map(RECIPES.map(r => [r.key, r]));
export const recipeByKey = key => BY_KEY.get(key) || null;
export const recipe = (a, b) => BY_KEY.get(pairKey(a, b)) || null;

export const REGULARS = {
  mina: {name: 'Mina', role: 'the illustrator', joins: 0, likes: ['milk'],
    beats: {2: 'I used to draw the lanterns every autumn. My sketchbook has been empty since the café closed.',
      4: 'I am painting a poster for the festival. Can I put your café right in the middle?'},
    thanks: ['“Just how I like it!”', '“This is going in my sketchbook.”', '“You remembered!”']},
  jun: {name: 'Jun', role: 'the bike courier', joins: 0, likes: ['coffee'],
    beats: {2: 'Auntie Rosa gave me my first job: cocoa deliveries to the bakery. I was eight.',
      4: 'I will ride the festival invitations to every door on the hill. Nobody gets missed.'},
    thanks: ['“Fuel for the hill!”', '“Perfect, gotta fly!”', '“Best stop on my route.”']},
  hana: {name: 'Hana', role: 'the fruit seller', joins: 0, likes: ['strawberry', 'mango', 'peach', 'orange', 'blueberry'],
    beats: {2: 'Rosa always bought the funny-shaped peaches. “They are the sweetest,” she said. She was right.',
      4: 'I planted a peach tree behind my stall. Next festival, peach everything!'},
    thanks: ['“Sunshine in a cup!”', '“My fruit never tasted this good.”', '“Ooh, that colour!”']},
  sora: {name: 'Sora', role: 'the baker', joins: 2, likes: ['cocoa', 'banana', 'honey'],
    beats: {2: 'Your aunt and I argued about cocoa for twenty years. She was right. Do not tell her.',
      4: 'Found this behind my old oven: one of her recipe cards. She must have hidden it from me.'},
    thanks: ['“Hm. Nearly as good as mine.”', '“Better than my croissants. Almost.”', '“Rosa would approve.”']},
  leo: {name: 'Leo', role: 'the music teacher', joins: 2, likes: ['tea', 'coffee', 'honey'],
    beats: {2: 'Every festival the whole street sang one song under the lanterns. I have forgotten half the words.',
      4: 'I remembered the second verse! It is about a little window that never closed.'},
    thanks: ['“That hits the right note.”', '“Bravo!”', '“Music in a mug.”']},
  noor: {name: 'Noor', role: 'the gardener', joins: 4, likes: ['blueberry', 'orange', 'matcha', 'peach'],
    beats: {2: 'Lantern paper is made from mulberry bark. I have been growing some in the garden, just in case.',
      4: 'The mulberry is ready. There is enough paper for every lantern on the street.'},
    thanks: ['“Fresh as morning dew.”', '“The garden says thank you.”', '“Lovely and bright!”']},
};
export const ROSA = {name: 'Auntie Rosa', role: 'your aunt', key: pairKey('honey', 'matcha')};
export const PEOPLE = Object.keys(REGULARS);
export const personName = p => p === 'rosa' ? ROSA.name : REGULARS[p]?.name || p;

// Auntie's recipe box: riddles that each point at one pair.
export const CARDS = [
  {id: 'cloud', key: pairKey('strawberry', 'milk'), title: 'Pink cloud', riddle: 'A pink cloud poured over breakfast.', level: 0, reward: 25},
  {id: 'sunrise', key: pairKey('coffee', 'mango'), title: 'Sunrise brew', riddle: 'The sun climbing over the dark bean.', level: 0, reward: 25},
  {id: 'baker', key: pairKey('banana', 'cocoa'), title: "The baker's secret", riddle: 'Brown on brown, wearing a yellow smile.', level: 2, reward: 25},
  {id: 'night', key: pairKey('blueberry', 'tea'), title: 'Night sky', riddle: 'The night sky, steeped slow.', level: 4, reward: 30},
  {id: 'dusk', key: pairKey('blueberry', 'orange'), title: 'Where dusk begins', riddle: 'Where the sunset meets the first stars.', level: 4, reward: 30},
  {id: 'lantern', key: pairKey('honey', 'matcha'), title: 'The light in my window', riddle: 'Gold from the bees, green from the hill.', level: 5, reward: 40},
];

// Twelve chapters, one lantern each. Purchases are chapter tasks, so there is always exactly one goal.
export const CHAPTERS = [
  {id: 'shutters', title: 'Open the shutters', task: 'Serve 3 cups', kind: 'served', target: 3, reward: 20, from: 'Auntie Rosa',
    letter: 'The key is under the flowerpot. The machine is older than you and the sign has faded, but open the shutters and make three cups. The street remembers how.'},
  {id: 'sign', title: 'A sign for Lantern Street', task: 'Paint the sign', kind: 'buy', level: 1, cost: 60, action: 'Paint sign', from: 'Jun',
    letter: 'Whoa, PETAL CAFÉ is back! I am telling everyone on my route. Expect a line tomorrow.'},
  {id: 'cups', title: 'Reading the cups', task: 'Serve 6 favorites', kind: 'favorites', target: 6, reward: 30, from: 'Mina',
    letter: 'You can tell what we want just by looking at the cup now. Rosa could too. She hung a lantern in the window for every regular.'},
  {id: 'bench', title: 'A seat for the baker', task: 'Add a bench', kind: 'buy', level: 2, cost: 220, action: 'Add bench', from: 'Sora',
    letter: 'A proper bench. Fine. I brought bananas and cocoa, since you clearly need a baker around here.'},
  {id: 'box', title: "Auntie's recipe box", task: 'Solve 2 recipe cards', kind: 'cards', target: 2, reward: 50, from: 'Sora',
    letter: 'That tin box behind the counter holds Rosa’s recipe cards. She wrote them as riddles so I could never copy her. Solve them and the café will taste like it used to.'},
  {id: 'golden', title: 'Golden hour', task: 'Light a golden hour', kind: 'golden', target: 1, reward: 40, from: 'Hana',
    letter: 'When the sun hits the window just right, the whole café glows. Rosa called it golden hour, and everything tasted twice as good.'},
  {id: 'mina', title: 'Two aprons', task: 'Invite Mina to help', kind: 'buy', level: 3, cost: 400, action: 'Hire Mina', from: 'Mina',
    letter: 'You make the colorful things; I will handle the simple coffees. And I am saving for festival poster paint!'},
  {id: 'garden', title: "Hana's garden gate", task: 'Open the garden', kind: 'buy', level: 4, cost: 550, action: 'Open garden', from: 'Hana',
    letter: 'Blueberries, mandarins and a pot of tea, fresh every morning. Noor from the community garden wants to meet you!'},
  {id: 'menu', title: 'The whole menu', task: 'Discover 16 recipes', kind: 'recipes', target: 16, reward: 60, from: 'Noor',
    letter: 'Sixteen recipes! Rosa kept a list like this on the fridge. I found it in the garden shed, and your handwriting fits right under hers.'},
  {id: 'friends', title: 'Friends of Lantern Street', task: 'Reach ♥3 with all 6 regulars', kind: 'friends', target: 6, reward: 80, from: 'Leo',
    letter: 'Everyone is talking about the festival again. I have the song, Noor has the paper, Jun has the invitations. We only need a place for it.'},
  {id: 'terrace', title: 'The lantern terrace', task: 'Build the terrace', kind: 'buy', level: 5, cost: 900, action: 'Build terrace', from: 'Noor',
    letter: 'Peaches from Hana’s tree, honey from my bees, matcha from the hill. Oh! And a letter came from the seaside…'},
  {id: 'festival', title: 'The Lantern Festival', task: "Serve Auntie Rosa's Lantern latte", kind: 'festival', target: 1, reward: 150, from: 'Auntie Rosa',
    letter: 'I could see the lanterns from the bus. Every window on the street is glowing. You did not just reopen a café, you lit up a whole street. Keep the key. It is yours now.'},
];
export const FESTIVAL = CHAPTERS.findIndex(c => c.id === 'festival');
const BOX = CHAPTERS.findIndex(c => c.id === 'box');
const PICTURE_ORDERS = CHAPTERS.findIndex(c => c.id === 'cups');

export const home = [[.27, .3], [.73, .3], [.27, .74], [.73, .74]];

// ------------------------------------------------------------ helpers ---
function mulberry(seed) {
  let t = seed >>> 0;
  return () => {
    t = (t + 0x6d2b79f5) >>> 0;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r;
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}
const rngFor = (s, id) => mulberry((s.seed ^ Math.imul(id + 1, 0x9e3779b1)) >>> 0);

export const unlockedBaskets = s => BASKET_ORDER.filter(b => s.level >= BASKETS[b].level);
export const basketFor = (s, r) => unlockedBaskets(s).find(b => r.parts.every(p => BASKETS[b].items.includes(p))) || null;
export const available = s => RECIPES.filter(r => basketFor(s, r));
export const onTable = (s, r) => r.parts.every(p => s.tokens.some(t => t.type === p));
export const picturesOnly = s => s.chapter >= PICTURE_ORDERS;
export const knows = (s, guest) => !!s.discovered[guest.key] || !picturesOnly(s) || !!guest.peeked;
export const regularsHere = s => PEOPLE.filter(p => s.level >= REGULARS[p].joins);
export const cardsOpen = s => s.chapter >= BOX ? CARDS.filter(c => s.level >= c.level) : [];
// Every two favorites for the same regular add one heart.
export const BOND_PER_HEART = 2;
export const hearts = (s, p) => Math.min(MAX_HEARTS, Math.floor((s.bond[p] || 0) / BOND_PER_HEART));
export const friends = s => PEOPLE.filter(p => hearts(s, p) >= 3).length;
export const queueSize = s => s.level >= 1 ? 3 : 1;

export function freshState(seed = Math.floor(Math.random() * 2 ** 31)) {
  const s = {
    version: 5, seed: seed >>> 0, coins: 0, served: 0, favorites: 0, level: 0, chapter: 0, mark: {served: 0, favorites: 0, golden: 0},
    glow: 0, golden: 0, goldenCount: 0, discovered: {}, bond: Object.fromEntries(PEOPLE.map(p => [p, 0])), beats: [],
    cards: [], queue: [], nextGuest: 0, festival: false, staffMillis: 0, sound: false, lastSeen: Date.now(),
    basket: 'sunrise', tokens: BASKETS.sunrise.items.map((type, i) => ({id: i, type, x: home[i][0], y: home[i][1]})),
  };
  ensureQueue(s);
  return s;
}

// The first three guests teach the loop with easy, fixed orders.
const TUTORIAL = [['mina', pairKey('strawberry', 'milk')], ['jun', pairKey('coffee', 'milk')], ['hana', pairKey('mango', 'strawberry')]];

function pickOrder(s, person, rnd) {
  const open = available(s), taken = new Set(s.queue.map(g => g.key));
  const fresh = open.filter(r => !s.discovered[r.key] && !taken.has(r.key));
  const liked = open.filter(r => r.parts.some(p => REGULARS[person].likes.includes(p)) && !taken.has(r.key));
  const any = open.filter(r => !taken.has(r.key));
  const pool = fresh.length && rnd() < .45 ? fresh : liked.length ? liked : any.length ? any : open;
  return pool[Math.floor(rnd() * pool.length)].key;
}

export function ensureQueue(s) {
  s.queue ??= [];
  const here = regularsHere(s);
  if (s.chapter === FESTIVAL && !s.festival && !s.queue.some(g => g.person === 'rosa')) {
    s.queue.unshift({id: s.nextGuest++, person: 'rosa', key: ROSA.key, peeked: false});
    if (s.queue.length > queueSize(s)) s.queue.pop();
  }
  while (s.queue.length < queueSize(s)) {
    const id = s.nextGuest++, rnd = rngFor(s, id);
    let person, key;
    if (id < TUTORIAL.length && s.served === id) [person, key] = TUTORIAL[id];
    else {
      const free = here.filter(p => !s.queue.some(g => g.person === p)), from = free.length ? free : here;
      person = from[Math.floor(rnd() * from.length)];
      key = pickOrder(s, person, rnd);
    }
    s.queue.push({id, person, key, peeked: false});
  }
  return s.queue;
}

export function chapterProgress(s) {
  const ch = CHAPTERS[s.chapter];
  if (!ch) return null;
  const value = ch.kind === 'served' ? s.served - s.mark.served
    : ch.kind === 'favorites' ? s.favorites - s.mark.favorites
      : ch.kind === 'golden' ? s.goldenCount - s.mark.golden
        : ch.kind === 'buy' ? (s.level >= ch.level ? 1 : 0)
          : ch.kind === 'cards' ? s.cards.length
            : ch.kind === 'recipes' ? Object.keys(s.discovered).length
              : ch.kind === 'friends' ? friends(s)
                : s.festival ? 1 : 0;
  const target = ch.kind === 'buy' ? 1 : ch.target;
  return {...ch, index: s.chapter, value: Math.min(value, target), target};
}

const markNow = s => ({served: s.served, favorites: s.favorites, golden: s.goldenCount});

// Completes every satisfied chapter in order and pays its gift.
export function advance(s) {
  const done = [], before = s.chapter;
  for (let p = chapterProgress(s); p && p.value >= p.target; p = chapterProgress(s)) {
    s.coins += p.reward || 0;
    done.push(p);
    s.chapter++;
    s.mark = markNow(s);
  }
  if (before < PICTURE_ORDERS && s.chapter >= PICTURE_ORDERS) for (const g of s.queue) g.peeked = true;
  return done;
}

// Replays satisfied chapters without gifts (repairing or migrating a save).
function settle(s) {
  for (let p = chapterProgress(s); p && p.value >= p.target; p = chapterProgress(s)) s.chapter++;
}

export function chooseBasket(s, basket) {
  if (!unlockedBaskets(s).includes(basket)) return false;
  s.basket = basket;
  BASKETS[basket].items.forEach((type, i) => { s.tokens[i].type = type; });
  return true;
}

export function peek(s, index) {
  const guest = s.queue[index];
  if (!guest) return null;
  const r = recipeByKey(guest.key);
  guest.peeked = true;
  const basket = basketFor(s, r);
  if (basket && !onTable(s, r)) chooseBasket(s, basket);
  return r;
}

// Who receives a drink: the first guest who ordered it, otherwise the first
// ordinary guest (Auntie Rosa only accepts her Lantern latte).
export function receiver(s, drink) {
  const match = s.queue.findIndex(g => g.key === drink.key);
  if (match >= 0) return {index: match, favorite: true};
  const index = s.queue.findIndex(g => g.person !== 'rosa');
  return index >= 0 ? {index, favorite: false} : null;
}

export function serve(s, idA, idB) {
  const a = s.tokens[idA], b = s.tokens[idB];
  if (!a || !b || a === b) return null;
  const drink = recipe(a.type, b.type), to = drink && receiver(s, drink);
  if (!to) return null;
  const guest = s.queue[to.index], person = guest.person, favorite = to.favorite;
  const isNew = !s.discovered[drink.key];
  const sharp = favorite && isNew && !guest.peeked && person !== 'rosa' && picturesOnly(s);
  const golden = s.golden > 0;
  let earned = BASE_PAY + (favorite ? TIP : 0) + (sharp ? SHARP_EYE : 0);
  if (golden) { earned *= 2; s.golden--; }
  s.coins += earned;
  s.served++;
  if (favorite) s.favorites++;
  s.discovered[drink.key] = (s.discovered[drink.key] || 0) + 1;

  let heart = null, goldenStart = false, card = null;
  if (favorite && REGULARS[person] && hearts(s, person) < MAX_HEARTS) {
    const before = hearts(s, person);
    s.bond[person]++;
    const now = hearts(s, person), gained = now > before, beat = gained && REGULARS[person].beats[now] || null;
    let gift = 0;
    if (beat) s.beats.push(`${person}:${now}`);
    if (gained && now === MAX_HEARTS) { gift = BEST_FRIEND_GIFT; s.coins += gift; }
    heart = {person, hearts: now, gained, bond: s.bond[person] % BOND_PER_HEART, beat, gift};
  }
  if (favorite && !golden && picturesOnly(s)) {
    s.glow++;
    if (s.glow >= GLOW_MAX) { s.glow = 0; s.golden = GOLDEN_CUPS; s.goldenCount++; goldenStart = true; }
  }
  const open = cardsOpen(s).find(c => c.key === drink.key && !s.cards.includes(c.id));
  if (open) { s.cards.push(open.id); s.coins += open.reward; card = open; }
  if (person === 'rosa' && favorite) s.festival = true;
  s.queue.splice(to.index, 1);
  const chapters = advance(s);
  ensureQueue(s);
  const thanks = favorite && REGULARS[person] ? REGULARS[person].thanks[s.served % 3] : null;
  return {...drink, favorite, index: to.index, person, earned, golden, goldenStart, sharp, isNew, heart, card, chapters, thanks};
}

export function buy(s) {
  const ch = CHAPTERS[s.chapter];
  if (!ch || ch.kind !== 'buy' || s.coins < ch.cost || s.level >= ch.level) return null;
  s.coins -= ch.cost;
  s.level = Math.max(s.level, ch.level);
  const chapters = advance(s);
  ensureQueue(s);
  return {...ch, chapters};
}

export function offline(s, now = Date.now()) {
  if (now < s.lastSeen) { s.lastSeen = now; return 0; }
  const elapsed = Math.min(OFFLINE_CAP_MS, Math.max(0, now - s.lastSeen));
  const total = s.level >= 3 ? elapsed + (s.staffMillis || 0) : 0, amount = Math.floor(total / STAFF_MS) * STAFF_PAY;
  s.staffMillis = total % STAFF_MS;
  s.coins += amount;
  s.lastSeen = Math.max(s.lastSeen, now);
  return amount;
}

// --------------------------------------------------------- persistence ---
const nat = v => Number.isSafeInteger(v) && v >= 0;
const validKey = key => typeof key === 'string' && BY_KEY.has(key);

export function validate(s) {
  if (!s || s.version !== 5 || !['coins', 'served', 'favorites', 'level', 'chapter', 'seed'].every(k => nat(s[k]))) return null;
  if (s.level > 5 || s.chapter > CHAPTERS.length || s.favorites > s.served || !Array.isArray(s.tokens) || s.tokens.length !== 4) return null;
  const clean = freshState(s.seed);
  const blocked = CHAPTERS.findIndex(c => c.kind === 'buy' && c.level > s.level);
  Object.assign(clean, {coins: s.coins, served: s.served, favorites: s.favorites, level: s.level,
    chapter: blocked >= 0 ? Math.min(s.chapter, blocked) : s.chapter});
  clean.goldenCount = nat(s.goldenCount) ? s.goldenCount : 0;
  clean.mark = {served: nat(s.mark?.served) ? Math.min(s.mark.served, s.served) : s.served,
    favorites: nat(s.mark?.favorites) ? Math.min(s.mark.favorites, s.favorites) : s.favorites,
    golden: nat(s.mark?.golden) ? Math.min(s.mark.golden, clean.goldenCount) : clean.goldenCount};
  clean.glow = nat(s.glow) ? Math.min(s.glow, GLOW_MAX - 1) : 0;
  clean.golden = nat(s.golden) ? Math.min(s.golden, GOLDEN_CUPS) : 0;
  for (const [k, v] of Object.entries(s.discovered || {})) if (validKey(k)) clean.discovered[k] = nat(v) && v > 0 ? v : 1;
  for (const p of PEOPLE) clean.bond[p] = nat(s.bond?.[p]) ? Math.min(s.bond[p], MAX_HEARTS * BOND_PER_HEART) : 0;
  clean.beats = Array.isArray(s.beats) ? [...new Set(s.beats.filter(b => typeof b === 'string' && /^[a-z]+:[24]$/.test(b) &&
    REGULARS[b.split(':')[0]] && hearts(clean, b.split(':')[0]) >= Number(b.split(':')[1])))] : [];
  clean.cards = Array.isArray(s.cards) ? [...new Set(s.cards.filter(id => CARDS.some(c => c.id === id)))] : [];
  clean.festival = s.festival === true && clean.chapter >= FESTIVAL;
  clean.sound = s.sound === true;
  clean.lastSeen = Number.isFinite(s.lastSeen) ? Math.min(s.lastSeen, Date.now()) : Date.now();
  clean.staffMillis = Number.isFinite(s.staffMillis) && s.staffMillis >= 0 && s.staffMillis < STAFF_MS ? s.staffMillis : 0;
  clean.basket = unlockedBaskets(clean).includes(s.basket) ? s.basket : 'sunrise';
  const items = BASKETS[clean.basket].items, unit = v => Math.min(1, Math.max(0, v));
  clean.tokens = s.tokens.map((t, i) => ({id: i, type: items[i],
    x: Number.isFinite(t?.x) ? unit(t.x) : home[i][0], y: Number.isFinite(t?.y) ? unit(t.y) : home[i][1]}));
  const people = new Set([...regularsHere(clean), ...(clean.chapter === FESTIVAL && !clean.festival ? ['rosa'] : [])]);
  clean.queue = (Array.isArray(s.queue) ? s.queue : [])
    .filter(g => g && nat(g.id) && people.has(g.person) && validKey(g.key) && basketFor(clean, recipeByKey(g.key)))
    .slice(0, queueSize(clean)).map(g => ({id: g.id, person: g.person, key: g.key, peeked: g.peeked === true}));
  if (new Set(clean.queue.map(g => g.id)).size !== clean.queue.length) clean.queue = [];
  clean.nextGuest = Math.max(nat(s.nextGuest) ? s.nextGuest : 0, ...clean.queue.map(g => g.id + 1), 0);
  settle(clean);
  ensureQueue(clean);
  return clean;
}

// Carries coins, renovations, recipes and friendships forward from v4 (and v3 through it).
export function migrate(old, seed) {
  if (old?.version === 3) {
    if (!nat(old.coins) || !nat(old.served) || ![0, 1, 2, 3].includes(old.upgrades)) return null;
    old = {version: 4, coins: old.coins, served: old.served, exact: Math.min(old.exact || 0, old.served),
      level: [0, 2, 3, 5][old.upgrades], discovered: {}, visits: {}, stock: []};
  }
  if (!old || old.version !== 4 || !nat(old.coins) || !nat(old.served) || !nat(old.level) || old.level > 5) return null;
  const s = freshState(seed);
  s.coins = old.coins + (Array.isArray(old.stock) ? old.stock.length * BASE_PAY : 0);
  s.served = old.served;
  s.favorites = Math.min(nat(old.exact) ? old.exact : 0, old.served);
  s.level = old.level;
  for (const k of Object.keys(old.discovered || {})) if (validKey(k)) s.discovered[k] = 1;
  for (const p of PEOPLE) {
    s.bond[p] = Math.min(4 * BOND_PER_HEART, Math.floor((nat(old.visits?.[p]) ? old.visits[p] : 0) / 2));
    for (const h of [2, 4]) if (hearts(s, p) >= h) s.beats.push(`${p}:${h}`);
  }
  s.staffMillis = Number.isFinite(old.staffMillis) && old.staffMillis >= 0 && old.staffMillis < STAFF_MS ? old.staffMillis : 0;
  s.sound = old.sound === true;
  // Replay chapters against lifetime totals, without paying their gifts again.
  s.mark = {served: 0, favorites: 0, golden: 0};
  settle(s);
  s.mark = markNow(s);
  s.queue = [];
  s.nextGuest = Math.max(s.served, TUTORIAL.length);
  ensureQueue(s);
  return s;
}
