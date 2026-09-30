// Hold one browser-wide write lock for the lifetime of the playing tab.
export function createSaveSession(key, onLost) {
  let active = false, release, pending;
  const id = [...crypto.getRandomValues(new Uint32Array(4))].map(n => n.toString(16)).join('-'), signalKey = key + ':takeover';
  let channel, persistent = !!navigator.locks;
  try { channel = new BroadcastChannel(signalKey); } catch { /* storage events also support handover */ }
  function relinquish() {
    if (!active) return;
    active = false;
    release?.();
    release = null;
    onLost();
  }
  const receive = value => { if (value && value !== id) relinquish(); };
  if (channel) channel.onmessage = e => receive(e.data);
  window.addEventListener('storage', e => { if (e.key === signalKey) receive(e.newValue); });
  async function acquire() {
    if (active) return true;
    // Without an atomic lock, play in memory rather than risk another tab's save.
    if (!persistent) { active = true; return true; }
    if (pending) return pending;
    pending = new Promise((resolve, reject) => {
      navigator.locks.request(key + ':play', {ifAvailable: true}, lock => {
        if (!lock) { resolve(false); return; }
        active = true;
        return new Promise(done => { release = done; resolve(true); });
      }).catch(reject);
    });
    try { return await pending; }
    catch { persistent = false; active = true; return true; } // Storage policy blocked locks: memory-only play.
    finally { pending = null; }
  }
  async function takeOver() {
    if (await acquire()) return true;
    channel?.postMessage(id);
    try { localStorage.setItem(signalKey, id); } catch { /* BroadcastChannel can still hand over. */ }
    for (let i = 0; i < 10; i++) {
      if (await acquire()) return true;
      await new Promise(resolve => setTimeout(resolve, 150));
    }
    return false;
  }
  return {get active() { return active; }, get persistent() { return persistent; }, acquire, takeOver, release: relinquish};
}
