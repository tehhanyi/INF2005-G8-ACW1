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
  const coverPreviewWrapper = byId('coverPreviewWrapper');
  const coverPreview = byId('coverPreview');
  const coverDetails = byId('coverDetails');
  const payloadInfo = byId('payloadInfo');
  const stegoInfo = byId('stegoInfo');

  let previewSequence = 0;

  const encodeBtn = byId('encodeBtn');
  const decodeBtn = byId('decodeBtn');

  const encodeResults = byId('encodeResults');
  const decodeResults = byId('decodeResults');

  // Helpers
  function setZoneHandlers(zone, input, infoBox, previewBox, detailsBox, previewContainer) {
    if (!zone || !input) return;
    zone.addEventListener('click', () => input.click());
    zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('bg-light'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('bg-light'));
    zone.addEventListener('drop', (e) => {
      e.preventDefault();
      zone.classList.remove('bg-light');
      if (e.dataTransfer.files && e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        showFileInfo(input, infoBox, previewBox, detailsBox, previewContainer);
        if (input === coverInput) triggerCapacity();
      }
    });
    input && input.addEventListener('change', () => {
      showFileInfo(input, infoBox, previewBox, detailsBox, previewContainer);
      if (input === coverInput) triggerCapacity();
    });
  }

  function showFileInfo(input, infoBox, previewBox, detailsBox, previewContainer) {
    const f = input && input.files && input.files[0];
    if (!f) {
      if (infoBox) infoBox.textContent = '';
      if (previewContainer) previewContainer.style.display = 'none';
      if (previewBox) hidePreview(previewBox);
      if (detailsBox) hideDetails(detailsBox);
      return;
    }
    if (infoBox) {
      infoBox.innerHTML = `<div class="text-muted small">${f.name} - ${fmtBytes(f.size)}</div>`;
    }
    if (previewContainer) previewContainer.style.display = 'block';
    if (previewBox || detailsBox) renderPreview(f, previewBox, detailsBox);
  }

  function hidePreview(box) {
    if (!box) return;
    delete box.dataset.previewToken;
    box.innerHTML = '';
    box.style.display = 'none';
  }

  function hideDetails(box) {
    if (!box) return;
    delete box.dataset.previewToken;
    box.innerHTML = '';
    box.style.display = 'none';
    const wrap = document.getElementById('coverDetailsWrapper');
    if (wrap) wrap.style.display = 'none';
  }


  function renderPreview(file, box, detailsBox) {
    if (!file) return;
    const token = String(++previewSequence);

    if (detailsBox) {
      detailsBox.dataset.previewToken = token;
      renderDetails(file, detailsBox, {}, token);
    }

    if (!box) return;

    box.dataset.previewToken = token;
    box.innerHTML = '';
    const type = (file.type || '').toLowerCase();

    if (type.startsWith('image/')) {
      const img = document.createElement('img');
      img.className = 'img-fluid';
      img.alt = `Preview of ${file.name}`;
      box.appendChild(img);
      const reader = new FileReader();
      reader.onload = () => {
        if (box.dataset.previewToken === token) {
          img.src = reader.result;
        }
      };
      img.addEventListener('load', () => {
        if (detailsBox && detailsBox.dataset.previewToken === token) {
          const dims = `${img.naturalWidth} x ${img.naturalHeight}`;
          renderDetails(file, detailsBox, { dimensions: dims }, token);
        }
      });
      reader.readAsDataURL(file);
      box.style.display = 'block';
      return;
    }

    if (type.startsWith('audio/') || /\.wav$/i.test(file.name || '')) {
      const audio = document.createElement('audio');
      audio.controls = true;
      box.appendChild(audio);
      const reader = new FileReader();
      reader.onload = () => {
        if (box.dataset.previewToken === token) {
          audio.src = reader.result;
        }
      };
      audio.addEventListener('loadedmetadata', () => {
        if (detailsBox && detailsBox.dataset.previewToken === token) {
          const dur = formatDuration(audio.duration);
          if (dur) renderDetails(file, detailsBox, { duration: dur }, token);
        }
      });
      reader.readAsDataURL(file);
      box.style.display = 'block';
      return;
    }

    box.textContent = 'Preview not available for this file type.';
    box.style.display = 'block';
  }

  function renderDetails(file, box, extra = {}, token) {
    if (!box) return;
    if (token && box.dataset.previewToken && box.dataset.previewToken !== token) return;
    if (token) box.dataset.previewToken = token;

    const rows = [];
    const name = file.name || 'Unknown';
    const type = file.type || inferTypeFromName(name);
    rows.push({ label: 'File name', value: name });
    rows.push({ label: 'File type', value: type });
    if (Number.isFinite(file.size)) {
      rows.push({ label: 'File size', value: fmtBytes(file.size) });
    }
    if (extra.dimensions) rows.push({ label: 'Dimensions', value: extra.dimensions });
    if (extra.duration) rows.push({ label: 'Duration', value: extra.duration });

    const bodyHtml = rows.map(({ label, value }) => {
      return `<div class="detail-row"><span class="detail-label">${escapeHtml(label)}</span><span class="detail-value">${escapeHtml(String(value))}</span></div>`;
    }).join('');

    box.innerHTML = bodyHtml;
    const wrap = document.getElementById('coverDetailsWrapper');
    if (wrap) wrap.style.display = 'block';
    box.style.display = 'block';

  }

  function inferTypeFromName(name) {
    if (!name) return 'Unknown';
    const idx = name.lastIndexOf('.');
    if (idx === -1 || idx === name.length - 1) return 'Unknown';
    return name.slice(idx + 1).toUpperCase();
  }

  function formatDuration(totalSeconds) {
    if (!Number.isFinite(totalSeconds) || totalSeconds <= 0) return null;
    const seconds = Math.round(totalSeconds);
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (hours) {
      return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }
    return `${minutes}:${String(secs).padStart(2, '0')}`;
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
  setZoneHandlers(coverDrop, coverInput, coverInfo, coverPreview, coverDetails, coverPreviewWrapper);
  setZoneHandlers(payloadDrop, payloadInput, payloadInfo);
  setZoneHandlers(stegoDrop, stegoInput, stegoInfo);

  lsbCount && lsbCount.addEventListener('change', triggerCapacity);
  startInput && startInput.addEventListener('change', triggerCapacity);
  encodeBtn && encodeBtn.addEventListener('click', onEncode);
  decodeBtn && decodeBtn.addEventListener('click', onDecode);
})();
