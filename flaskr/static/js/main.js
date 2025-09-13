// Minimal client logic to wire Encode/Decode/Capacity calls
(function () {
  function byId(id) { return document.getElementById(id); }
  function fmtBytes(n) {
    if (!Number.isFinite(n)) return String(n);
    const units = ['B','KB','MB','GB'];
    let u = 0; let v = n;
    while (v >= 1024 && u < units.length-1) { v /= 1024; u++; }
    return `${v.toFixed(1)} ${units[u]}`;
  }

  // Elements
  const coverDrop = byId('coverDropZone');
  const payloadDrop = byId('payloadDropZone');
  const stegoDrop = byId('stegoDropZone');

  const coverInput = byId('coverFile');
  const payloadInput = byId('payloadFile');
  const payloadText = byId('payloadText');
  const stegoInput = byId('stegoFile');

  const lsbCount = byId('lsbCount');
  const keyInput = byId('secretKey');
  const startInput = byId('startLocation');

  const decodeLsb = byId('decodeLsbCount');
  const decodeKey = byId('decodeKey');
  const decodeStart = byId('decodeStartLocation');

  const capInfo = byId('capacityInfo');
  const coverInfo = byId('coverInfo');
  const payloadInfo = byId('payloadInfo');
  const stegoInfo = byId('stegoInfo');

  const encodeBtn = byId('encodeBtn');
  const decodeBtn = byId('decodeBtn');

  const encodeResults = byId('encodeResults');
  const decodeResults = byId('decodeResults');

  // Helpers
  function setZoneHandlers(zone, input, infoBox) {
    if (!zone || !input) return;
    zone.addEventListener('click', () => input.click());
    zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('bg-light'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('bg-light'));
    zone.addEventListener('drop', (e) => {
      e.preventDefault();
      zone.classList.remove('bg-light');
      if (e.dataTransfer.files && e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        showFileInfo(input, infoBox);
        if (input === coverInput) triggerCapacity();
      }
    });
    input && input.addEventListener('change', () => { showFileInfo(input, infoBox); if (input === coverInput) triggerCapacity(); });
  }

  function showFileInfo(input, infoBox) {
    if (!infoBox) return;
    const f = input && input.files && input.files[0];
    if (!f) { infoBox.textContent = ''; return; }
    infoBox.textContent = `${f.name} • ${fmtBytes(f.size)}`;
  }

  async function postForm(path, formData) {
    const btn = document.activeElement;
    if (btn && btn.tagName === 'BUTTON') { btn.disabled = true; btn.dataset.text = btn.textContent; btn.textContent = 'Working...'; }
    try {
      const res = await fetch(path, { method: 'POST', body: formData });
      const text = await res.text();
      let data;
      try { data = JSON.parse(text); } catch { data = { raw: text }; }
      if (!res.ok) throw data;
      return data;
    } finally {
      if (btn && btn.tagName === 'BUTTON') { btn.disabled = false; btn.textContent = btn.dataset.text || 'Submit'; }
    }
  }

  function renderJSON(el, obj) {
    if (!el) return;
    el.innerHTML = `<pre style="white-space:pre-wrap">${escapeHtml(JSON.stringify(obj, null, 2))}</pre>`;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  // Capacity
  async function triggerCapacity() {
    capInfo.textContent = '';
    const f = coverInput.files && coverInput.files[0];
    const lsb = parseInt(lsbCount.value || '1', 10);
    const start = parseInt(startInput.value || '0', 10);
    if (!f || !lsb) return;
    const fd = new FormData();
    fd.append('cover_file', f);
    fd.append('lsb_count', String(lsb));
    fd.append('start_location', String(start));
    try {
      const data = await postForm('/calculate_capacity', fd);
      capInfo.textContent = `Capacity (after start offset): ${fmtBytes(data.capacity_bytes)} (${data.capacity_bytes} bytes)`;
    } catch (err) {
      capInfo.textContent = `Capacity error: ${JSON.stringify(err)}`;
    }
  }

  // Encode
  async function onEncode() {
    encodeResults.textContent = '';
    const cover = coverInput.files && coverInput.files[0];
    const payload = payloadInput.files && payloadInput.files[0];
    const payloadTextVal = (payloadText && payloadText.value) ? payloadText.value.trim() : '';
    const key = keyInput.value.trim();
    const lsb = parseInt(lsbCount.value || '1', 10);
    const start = parseInt(startInput.value || '0', 10);
    if (!cover) { encodeResults.textContent = 'Please select a cover file.'; return; }
    if (!payload && !payloadTextVal) { encodeResults.textContent = 'Please select a payload file or enter payload text.'; return; }
    if (!key) { encodeResults.textContent = 'Please enter a key.'; return; }
    const fd = new FormData();
    fd.append('cover_file', cover);
    if (payload) {
      fd.append('payload_file', payload);
    } else if (payloadTextVal) {
      fd.append('payload_text', payloadTextVal);
    }
    fd.append('key', key);
    fd.append('lsb_count', String(lsb));
    fd.append('start_location', String(start));
    try {
      const data = await postForm('/encode', fd);
      renderJSON(encodeResults, data);
      if (data && data.stego_url) {
        const a = document.createElement('a');
        a.href = data.stego_url; a.textContent = 'Download stego file'; a.className = 'btn btn-link p-0';
        encodeResults.appendChild(a);
      }
    } catch (err) {
      renderJSON(encodeResults, err);
    }
  }

  // Decode
  async function onDecode() {
    decodeResults.textContent = '';
    const stego = stegoInput.files && stegoInput.files[0];
    const key = decodeKey.value.trim();
    const lsb = parseInt(decodeLsb.value || '1', 10);
    const start = parseInt(decodeStart.value || '0', 10);
    if (!stego) { decodeResults.textContent = 'Please select a stego file.'; return; }
    if (!key) { decodeResults.textContent = 'Please enter a key.'; return; }
    const fd = new FormData();
    fd.append('stego_file', stego);
    fd.append('key', key);
    fd.append('lsb_count', String(lsb));
    fd.append('start_location', String(start));
    try {
      const data = await postForm('/decode', fd);
      renderJSON(decodeResults, data);
      if (data && data.payload_url) {
        const a = document.createElement('a');
        a.href = data.payload_url; a.textContent = 'Download extracted payload'; a.className = 'btn btn-link p-0';
        decodeResults.appendChild(a);
      }
    } catch (err) {
      renderJSON(decodeResults, err);
    }
  }

  // Wire up
  setZoneHandlers(coverDrop, coverInput, coverInfo);
  setZoneHandlers(payloadDrop, payloadInput, payloadInfo);
  setZoneHandlers(stegoDrop, stegoInput, stegoInfo);

  lsbCount && lsbCount.addEventListener('change', triggerCapacity);
  startInput && startInput.addEventListener('change', triggerCapacity);
  encodeBtn && encodeBtn.addEventListener('click', onEncode);
  decodeBtn && decodeBtn.addEventListener('click', onDecode);
})();
