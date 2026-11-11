// AIトレンド朝刊 ブラウザ用の補助関数 ver1.0 (2026-11-12) ChatGPT で画像を作り、クリップボード経由で note・X に渡す
// 使い方：ページを開くたびに、該当する部分（=== CHATGPT === か === TARGET ===）を javascript_tool でそのまま実行して定義する。
// 流れ（ダウンロードフォルダやコンテナを通さない。画像のデータは Claude の会話に入らない）：
//   1. ChatGPT のタブ：__send(指示文) → __state() で完成を待つ → __copy() で最後の画像をクリップボードへ
//   2. note・X のタブ：__sinkOn() → computer の key "ctrl+v" → __sinkGet() で画像を受け取り、__fit() で寸法を合わせる
//   3. note の見出し画像・本文の画像・X の添付は、ファイル選択の input を __captured で捕まえ、__setFile() で渡す

// === CHATGPT ===
window.__sleep = ms => new Promise(r => setTimeout(r, ms));
window.__imgs = () => [...document.querySelectorAll('main img')].filter(i => i.naturalWidth >= 500);
window.__btn = () => document.querySelector('[data-testid="send-button"]') || document.querySelector('#composer-submit-button') || document.querySelector('button[aria-label="送信"]');
window.__bad = () => { const t = document.body.innerText; return ['Too many requests', 'リクエストが多すぎ', '上限に達', 'しばらくしてから', 'Rate limit'].filter(k => t.includes(k)); };
window.__mode = () => [...document.querySelectorAll('button')].filter(b => b.innerText.trim() === 'Chat').map(b => b.getAttribute('aria-pressed')).join() === 'true';
window.__state = () => { const im = __imgs(); const last = im[im.length - 1];
  return JSON.stringify({ n: im.length, last: last ? last.src.slice(-36) + ' ' + last.naturalWidth + 'x' + last.naturalHeight : null,
    stop: !!document.querySelector('[data-testid="stop-button"]') || !!document.querySelector('button[aria-label*="停止"]'), bad: __bad() }); };
// 完成の見分け方：n が1以上、stop が false、last が 1536x1024 前後。生成中は stop が true で、途中の画像（プレビュー）が出ることがある
window.__send = async (t) => {
  const ed = document.querySelector('.ProseMirror[contenteditable="true"]'); if (!ed) return 'NOEDITOR';
  ed.focus(); document.execCommand('selectAll'); document.execCommand('delete'); await __sleep(200);
  if (ed.innerText.trim()) return 'NOTEMPTY';
  const dt = new DataTransfer(); dt.setData('text/plain', t);
  ed.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true })); await __sleep(800);
  const got = ed.innerText.replace(/\s+/g, ''); const want = t.replace(/\s+/g, '');
  if (got.slice(0, 30) !== want.slice(0, 30) || Math.abs(got.length - want.length) > 20) return 'MISMATCH ' + got.length + '/' + want.length;
  const b = __btn(); if (!b) return 'NOBTN'; b.click(); return 'SENT ' + got.length;
};
window.__copy = async () => { // 最後の画像を PNG でクリップボードへ（タブが前面にあること）
  const im = __imgs().pop(); if (!im) return 'NOIMG'; im.scrollIntoView({ block: 'center' });
  const c = document.createElement('canvas'); c.width = im.naturalWidth; c.height = im.naturalHeight; c.getContext('2d').drawImage(im, 0, 0);
  const blob = await new Promise(r => c.toBlob(r, 'image/png'));
  try { await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]); return 'COPIED ' + blob.size; }
  catch (e) { return 'COPY_NG ' + e.name + ' ' + e.message; }
};

// === TARGET ===（note のエディタ・X の投稿画面）
window.__sleep = ms => new Promise(r => setTimeout(r, ms));
window.__sinkOn = () => { // 受け取り用の欄を置いて、そこにフォーカスする。次に computer の key "ctrl+v"
  window.__got = null; document.getElementById('__sink')?.remove();
  const s = document.createElement('textarea'); s.id = '__sink';
  s.style.cssText = 'position:fixed;left:0;top:0;width:20px;height:20px;opacity:0.01;z-index:2147483647';
  document.body.appendChild(s);
  s.addEventListener('paste', e => { const f = [...(e.clipboardData.files || [])]; window.__got = f[0] || null; e.preventDefault(); e.stopPropagation(); }, true);
  s.focus(); return document.activeElement === s ? 'READY' : 'NOFOCUS';
};
window.__sinkGet = () => { document.getElementById('__sink')?.remove(); return window.__got ? (window.__got.type + ' ' + window.__got.size) : 'NONE'; };
window.__fit = async (file, W, H, name) => { // 外側の背景色の余白を削り、背景色で足して W×H の JPEG にする（tools/fit_image.py と同じ考え方）
  const bmp = await createImageBitmap(file); const w = bmp.width, h = bmp.height;
  const c = document.createElement('canvas'); c.width = w; c.height = h; const x = c.getContext('2d'); x.drawImage(bmp, 0, 0);
  const d = x.getImageData(0, 0, w, h).data; const px = (i, j) => { const k = (j * w + i) * 4; return [d[k], d[k + 1], d[k + 2]].join(','); };
  const cs = [px(2, 2), px(w - 3, 2), px(2, h - 3), px(w - 3, h - 3)];
  const bgS = cs.sort((a, b) => cs.filter(v => v === b).length - cs.filter(v => v === a).length)[0]; const bg = bgS.split(',').map(Number);
  let x0 = w, y0 = h, x1 = 0, y1 = 0;
  for (let j = 0; j < h; j += 2) for (let i = 0; i < w; i += 2) { const k = (j * w + i) * 4;
    if (Math.abs(d[k] - bg[0]) + Math.abs(d[k + 1] - bg[1]) + Math.abs(d[k + 2] - bg[2]) > 54) { if (i < x0) x0 = i; if (i > x1) x1 = i; if (j < y0) y0 = j; if (j > y1) y1 = j; } }
  if (x1 <= x0) { x0 = 0; y0 = 0; x1 = w - 1; y1 = h - 1; }
  const cw = x1 - x0 + 1, ch = y1 - y0 + 1; let tw = cw * 1.1, th = ch * 1.1; if (tw / th < W / H) tw = th * W / H; else th = tw * H / W;
  const s = W / tw; const o = document.createElement('canvas'); o.width = W; o.height = H; const ox = o.getContext('2d');
  ox.fillStyle = `rgb(${bg})`; ox.fillRect(0, 0, W, H); ox.imageSmoothingQuality = 'high';
  ox.drawImage(c, x0, y0, cw, ch, (W - cw * s) / 2, (H - ch * s) / 2, cw * s, ch * s);
  const blob = await new Promise(r => o.toBlob(r, 'image/jpeg', 0.9));
  return { file: new File([blob], name, { type: 'image/jpeg' }), info: `${w}x${h} -> ${W}x${H} ${blob.size}B` };
};
window.__capture = () => { // ファイル選択の input を、開かずに捕まえる（次に押すボタンが作る input が window.__captured に入る）
  window.__captured = null;
  if (!window.__patched) { window.__patched = 1; const oc = HTMLInputElement.prototype.click;
    HTMLInputElement.prototype.click = function () { if (this.type === 'file') { window.__captured = this; if (!this.isConnected) { this.style.display = 'none'; document.body.appendChild(this); } return; } return oc.apply(this, arguments); }; }
  return 'OK';
};
window.__setFile = async (inp, file) => { // input にファイルを渡して change を起こす。X の投稿画面は input[data-testid="fileInput"] をそのまま使う
  inp = inp || window.__captured; if (!inp) return 'NOINPUT';
  const dt = new DataTransfer(); dt.items.add(file); inp.files = dt.files;
  inp.dispatchEvent(new Event('input', { bubbles: true })); inp.dispatchEvent(new Event('change', { bubbles: true }));
  await __sleep(2000); return 'SET ' + inp.files.length;
};
window.__placeAfter = async (h2text) => { // note：見出しの直後に空の段落を作り、そこにカーソルを置く（本文の図を入れる場所）
  const pm = document.querySelector('.ProseMirror'); const kids = [...pm.children];
  const hits = kids.filter(k => k.tagName === 'H2' && k.textContent.trim() === h2text);
  if (hits.length !== 1) return 'NOTFOUND ' + hits.length;
  const idx = kids.indexOf(hits[0]); pm.focus();
  const r = document.createRange(); r.setStart(pm, idx); r.setEnd(pm, idx + 1);
  const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r); document.dispatchEvent(new Event('selectionchange')); await __sleep(300);
  const dt = new DataTransfer(); dt.setData('text/html', hits[0].outerHTML + '<p>__IMG_HERE__</p>'); dt.setData('text/plain', 'x');
  pm.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true })); await __sleep(500);
  const ph = [...pm.children].find(k => k.textContent.trim() === '__IMG_HERE__'); if (!ph) return 'NOPH';
  const r2 = document.createRange(); r2.selectNodeContents(ph); sel.removeAllRanges(); sel.addRange(r2); document.dispatchEvent(new Event('selectionchange')); await __sleep(200);
  document.execCommand('delete'); await __sleep(300); return 'PLACED';
};
window.__dropEmptyBefore = async (h2text) => { // note：見出しと図の間に残った空の段落を消す
  const pm = document.querySelector('.ProseMirror'); const h = [...pm.children].find(k => k.tagName === 'H2' && k.textContent.trim() === h2text);
  const p = h && h.nextElementSibling; if (!p || p.tagName !== 'P' || p.textContent.trim()) return 'SKIP';
  pm.focus(); const r = document.createRange(); r.setStart(p, 0); r.collapse(true); const s = getSelection(); s.removeAllRanges(); s.addRange(r);
  document.dispatchEvent(new Event('selectionchange')); await __sleep(200); document.execCommand('delete'); await __sleep(300); return 'DROPPED';
};
window.__order = () => [...document.querySelector('.ProseMirror').children].map(e => e.tagName + (e.tagName === 'H2' ? ':' + e.textContent : '')).join(','); // 並びの確認用
