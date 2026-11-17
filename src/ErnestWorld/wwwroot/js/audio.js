/*
  LE MONDE D'ERNEST - sons
  Tous les sons sont synthétisés en direct avec la Web Audio API : aucun fichier à télécharger.
  Le son ne démarre qu'après un clic du visiteur (règle des navigateurs) et se coupe d'un bouton.
*/

let ctx = null;
let master = null;
let ambient = null;
let enabled = true;
let night = false;

try { enabled = localStorage.getItem("ernest-sound") !== "off"; } catch { /* stockage indisponible */ }

function ensure() {
  if (!enabled) return null;
  // Pas de son tant que le visiteur n'a pas cliqué ou tapé une touche (règle des navigateurs)
  if (!ctx && navigator.userActivation && !navigator.userActivation.hasBeenActive) return null;
  if (!ctx) {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return null;
    ctx = new AudioCtx();
    master = ctx.createGain();
    master.gain.value = 0.32;
    master.connect(ctx.destination);
  }
  if (ctx.state === "suspended") ctx.resume();
  return ctx;
}

function tone(freq, start, dur, { type = "sine", gain = 0.3, slide = 0, attack = 0.01 } = {}) {
  const osc = ctx.createOscillator();
  const env = ctx.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, start);
  if (slide) osc.frequency.exponentialRampToValueAtTime(Math.max(30, freq * slide), start + dur);
  env.gain.setValueAtTime(0.0001, start);
  env.gain.exponentialRampToValueAtTime(gain, start + attack);
  env.gain.exponentialRampToValueAtTime(0.0001, start + dur);
  osc.connect(env).connect(master);
  osc.start(start);
  osc.stop(start + dur + 0.05);
}

function noise(start, dur, { gain = 0.3, freq = 1200, q = 0.8, type = "bandpass" } = {}) {
  const length = Math.max(1, Math.floor(ctx.sampleRate * dur));
  const buffer = ctx.createBuffer(1, length, ctx.sampleRate);
  const data = buffer.getChannelData(0);
  for (let i = 0; i < length; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / length);
  const src = ctx.createBufferSource();
  src.buffer = buffer;
  const filter = ctx.createBiquadFilter();
  filter.type = type;
  filter.frequency.value = freq;
  filter.Q.value = q;
  const env = ctx.createGain();
  env.gain.value = gain;
  src.connect(filter).connect(env).connect(master);
  src.start(start);
}

const arpeggio = (notes, t, step, opts) => notes.forEach((f, i) => tone(f, t + i * step, opts.dur ?? 0.35, opts));

const SOUNDS = {
  discover: (t) => arpeggio([523.25, 659.25, 783.99], t, 0.08, { type: "triangle", gain: 0.16 }),
  achievement: (t) => {
    arpeggio([659.25, 783.99, 1046.5, 1318.5], t, 0.07, { type: "sine", gain: 0.14, dur: 0.5 });
    tone(1567.98, t + 0.3, 0.9, { type: "sine", gain: 0.05 });
  },
  levelup: (t) => arpeggio([392, 523.25, 659.25, 783.99, 1046.5], t, 0.09, { type: "square", gain: 0.06, dur: 0.45 }),
  start: (t) => arpeggio([261.63, 329.63, 392, 523.25], t, 0.06, { type: "square", gain: 0.05, dur: 0.25 }),
  hit: (t) => {
    noise(t, 0.18, { gain: 0.5, freq: 900, q: 0.7 });
    tone(150, t, 0.22, { type: "sine", gain: 0.45, slide: 0.45 });
  },
  crit: (t) => {
    noise(t, 0.32, { gain: 0.6, freq: 1700, q: 0.6 });
    tone(230, t, 0.35, { type: "sawtooth", gain: 0.16, slide: 0.4 });
    arpeggio([880, 1318.5, 1760], t + 0.05, 0.06, { type: "triangle", gain: 0.1, dur: 0.3 });
  },
  hurt: (t) => {
    tone(210, t, 0.45, { type: "sawtooth", gain: 0.18, slide: 0.35 });
    noise(t, 0.28, { gain: 0.35, freq: 380, q: 0.5, type: "lowpass" });
  },
  roar: (t) => {
    noise(t, 1.2, { gain: 0.5, freq: 240, q: 0.9, type: "lowpass" });
    tone(95, t, 1.0, { type: "sawtooth", gain: 0.13, slide: 0.6 });
    tone(58, t, 1.25, { type: "sine", gain: 0.3, slide: 0.8 });
  },
  hint: (t) => arpeggio([1046.5, 1318.5, 1567.98], t, 0.05, { type: "sine", gain: 0.1, dur: 0.3 }),
  victory: (t) => {
    const notes = [523.25, 523.25, 523.25, 659.25, 783.99, 659.25, 783.99, 1046.5];
    const lengths = [0.12, 0.12, 0.12, 0.26, 0.18, 0.12, 0.18, 0.9];
    let s = t;
    notes.forEach((f, i) => {
      tone(f, s, lengths[i] + 0.1, { type: "square", gain: 0.07 });
      tone(f / 2, s, lengths[i] + 0.1, { type: "triangle", gain: 0.09 });
      s += lengths[i];
    });
  },
  defeat: (t) => arpeggio([392, 349.23, 311.13, 261.63], t, 0.28, { type: "triangle", gain: 0.11, dur: 0.5 }),
  pigeon: (t) => { for (let i = 0; i < 7; i++) noise(t + i * 0.08, 0.06, { gain: 0.25, freq: 2600, q: 2 }); },
  night: (t) => tone(330, t, 1.4, { type: "sine", gain: 0.07, slide: 0.65 }),
  day: (t) => arpeggio([392, 493.88, 587.33], t, 0.12, { type: "sine", gain: 0.06, dur: 0.6 }),
  click: (t) => tone(880, t, 0.06, { type: "sine", gain: 0.06 }),
};

export function play(name) {
  const c = ensure();
  if (!c || !SOUNDS[name]) return;
  SOUNDS[name](c.currentTime + 0.01);
}

export const isOn = () => enabled;

export function toggle() {
  enabled = !enabled;
  try { localStorage.setItem("ernest-sound", enabled ? "on" : "off"); } catch { /* ignoré */ }
  if (enabled) startAmbient(); else stopAmbient();
  return enabled;
}

export function setNightAmbience(on) { night = !!on; }

/* Ambiance : ressac (bruit filtré qui respire lentement) et chants d'oiseaux le jour. */
export function startAmbient() {
  const c = ensure();
  if (!c || ambient) return;

  const length = c.sampleRate * 2;
  const buffer = c.createBuffer(1, length, c.sampleRate);
  const data = buffer.getChannelData(0);
  for (let i = 0; i < length; i++) data[i] = Math.random() * 2 - 1;
  const src = c.createBufferSource();
  src.buffer = buffer;
  src.loop = true;
  const filter = c.createBiquadFilter();
  filter.type = "lowpass";
  filter.frequency.value = 520;
  const waves = c.createGain();
  waves.gain.value = 0.05;
  const lfo = c.createOscillator();
  lfo.frequency.value = 0.09;
  const depth = c.createGain();
  depth.gain.value = 0.035;
  lfo.connect(depth).connect(waves.gain);
  src.connect(filter).connect(waves).connect(master);
  src.start();
  lfo.start();

  const chirp = () => {
    if (!ambient) return;
    const t = c.currentTime + 0.05;
    if (!night) {
      const base = 2200 + Math.random() * 1600;
      for (let i = 0; i < 2 + Math.floor(Math.random() * 3); i++) tone(base, t + i * 0.11, 0.09, { type: "sine", gain: 0.025, slide: 1.35 });
    } else {
      for (let i = 0; i < 3; i++) tone(4200, t + i * 0.07, 0.04, { type: "triangle", gain: 0.012 });
    }
    ambient.timer = setTimeout(chirp, 3500 + Math.random() * 6000);
  };
  ambient = { src, lfo, waves, timer: 0 };
  ambient.timer = setTimeout(chirp, 2500);
}

export function stopAmbient() {
  if (!ambient) return;
  clearTimeout(ambient.timer);
  try { ambient.src.stop(); ambient.lfo.stop(); } catch { /* déjà arrêté */ }
  ambient = null;
}
