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
  const startInput = byId('startLocation'); // may be null (removed); we manage start via key or click

  const decodeLsb = byId('decodeLsbCount');
  const decodeKey = byId('decodeKey');
  const decodeStart = byId('decodeStartLocation'); // removed in UI; keep reference null-safe

  const capInfo = byId('capacityInfo');
  const coverInfo = byId('coverInfo');
  const coverPreviewWrapper = byId('coverPreviewWrapper');
  const coverPreview = byId('coverPreview');
  const coverDetails = byId('coverDetails');
  const payloadInfo = byId('payloadInfo');
  const stegoInfo = byId('stegoInfo');
  const startLabel = byId('startLocationLabel');
  const decodeStartLabel = byId('decodeStartLocationLabel');

  let previewSequence = 0;
  let selectedXY = null; // current image selection (x,y) for cover
  const copyBtn = byId('copyKeyBtn');

  const encodeBtn = byId('encodeBtn');
  const decodeBtn = byId('decodeBtn');

  const encodeResults = byId('encodeResults');
  const decodeResults = byId('decodeResults');

  // Helpers
  function isImageFile(file) {
    const name = file && file.name ? file.name.toLowerCase() : '';
    const type = (file && file.type || '').toLowerCase();
    return !!file && (/(\.png|\.bmp|\.gif|\.jpg|\.jpeg)$/i.test(name) || type.startsWith('image/'));
  }
  function isWavFile(file) {
    const name = file && file.name ? file.name.toLowerCase() : '';
    const type = (file && file.type || '').toLowerCase();
    return !!file && (/\.wav$/i.test(name) || type === 'audio/wav' || type === 'audio/x-wav');
  }

  function updateStartUiForCover(file) {}

  function updateStartUiForStego(file) { /* no-op: decode start taken from key */ }

  function parseImageStartFromKey(keyStr) {
    if (!keyStr) return null;
    const at = keyStr.indexOf('@');
    if (at === -1) return null;
    let start = keyStr.slice(at + 1);
    if (start.startsWith('@')) start = start.replace(/^@+/, '');
    const m = /^\s*(\d+)\s*,\s*(\d+)\s*$/.exec(start);
    if (!m) return null;
    return [parseInt(m[1], 10), parseInt(m[2], 10)];
  }

  function computeImageStart(coverFile) {
    // priority: key-embedded -> selectedXY -> 0,0
    const keyVal = keyInput && keyInput.value || '';
    const fromKey = parseImageStartFromKey(keyVal);
    if (fromKey) return `${fromKey[0]},${fromKey[1]}`;
    if (selectedXY) return `${selectedXY[0]},${selectedXY[1]}`;
    return '0,0';
  }

  function computeStartParam(file) {
    if (isImageFile(file)) return computeImageStart(file);
    // audio or others: numeric
    const keyVal = keyInput && keyInput.value || '';
    // Extract @N if present
    const at = keyVal.indexOf('@');
    if (at !== -1) {
      const rest = keyVal.slice(at + 1);
      if (!rest.includes(',')) {
        const n = parseInt(rest, 10);
        if (Number.isFinite(n) && n >= 0) return String(n);
      }
    }
    // fallback to text box if present
    if (startInput && /^\s*\d+\s*$/.test(startInput.value || '')) return startInput.value.trim();
    return '0';
  }

  // Move cover marker when user types (x,y)
  function moveCoverMarkerToXY(x, y) {
    if (!coverPreview) return;
    const img = coverPreview.querySelector('img');
    if (!img || !Number.isFinite(img.naturalWidth) || !img.naturalWidth) return;
    // Ensure container allows absolute positioning
    if (!coverPreview.style.position) coverPreview.style.position = 'relative';
    let marker = coverPreview.querySelector('.click-marker');
    if (!marker) {
      marker = document.createElement('div');
      marker.className = 'click-marker';
      coverPreview.appendChild(marker);
    }
    const scaleX = img.naturalWidth / img.clientWidth;
    const scaleY = img.naturalHeight / img.clientHeight;
    const dispX = img.offsetLeft + Math.max(0, Math.min(img.clientWidth - 1, x / scaleX));
    const dispY = img.offsetTop + Math.max(0, Math.min(img.clientHeight - 1, y / scaleY));
    marker.style.left = `${dispX}px`;
    marker.style.top = `${dispY}px`;
    marker.title = `(${x}, ${y})`;
  }

  function onStartLocationTyped() {
    const coverFile = coverInput && coverInput.files && coverInput.files[0];
    if (!isImageFile(coverFile)) {
      // Remove marker for non-image covers
      const m = coverPreview && coverPreview.querySelector && coverPreview.querySelector('.click-marker');
      if (m) m.remove();
      return;
    }
    if (!startInput) return;
    const m = /^\s*(\d+)\s*,\s*(\d+)\s*$/.exec(startInput.value || '');
    if (!m) return; // invalid format; ignore
    const x = parseInt(m[1], 10);
    const y = parseInt(m[2], 10);
    const img = coverPreview && coverPreview.querySelector && coverPreview.querySelector('img');
    if (!img) return;
    const nx = Math.max(0, Math.min((img.naturalWidth || 1) - 1, x));
    const ny = Math.max(0, Math.min((img.naturalHeight || 1) - 1, y));
    moveCoverMarkerToXY(nx, ny);
  }
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
        if (input === coverInput) { updateStartUiForCover(input.files[0]); triggerCapacity(); }
        if (input === stegoInput) { updateStartUiForStego(input.files[0]); }
      }
    });
    input && input.addEventListener('change', () => {
      showFileInfo(input, infoBox, previewBox, detailsBox, previewContainer);
      if (input === coverInput) { updateStartUiForCover(input.files[0]); triggerCapacity(); }
      if (input === stegoInput) { updateStartUiForStego(input.files[0]); }
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

        // If this is the cover preview, enable click-to-set start location
        if (box === coverPreview) {
          // Ensure container allows absolute positioning of marker
          box.style.position = box.style.position || 'relative';

          // Remove any existing marker
          const old = box.querySelector('.click-marker');
          if (old) old.remove();

          // Create a reusable marker element
          const marker = document.createElement('div');
          marker.className = 'click-marker';
          box.appendChild(marker);

          function placeMarkerFromImageEvent(e) {
            // Coordinates relative to the IMG element
            const relX = e.offsetX;
            const relY = e.offsetY;
            const scaleX = img.naturalWidth / img.clientWidth;
            const scaleY = img.naturalHeight / img.clientHeight;
            const x = Math.max(0, Math.min(img.naturalWidth - 1, Math.floor(relX * scaleX)));
            const y = Math.max(0, Math.min(img.naturalHeight - 1, Math.floor(relY * scaleY)));

            // Position marker relative to the preview box, accounting for image offset
            const dispX = img.offsetLeft + Math.max(0, Math.min(img.clientWidth - 1, relX));
            const dispY = img.offsetTop + Math.max(0, Math.min(img.clientHeight - 1, relY));
            marker.style.left = `${dispX}px`;
            marker.style.top = `${dispY}px`;
            marker.title = `(${x}, ${y})`;

            // Remember selection; do not mutate the key here
            selectedXY = [x, y];
            try { triggerCapacity(); } catch {}
          }

          // Click handler strictly on image (avoid container clicks)
          img.style.cursor = 'crosshair';
          img.addEventListener('click', (e) => {
            placeMarkerFromImageEvent(e);
          });

          // If key already contains x,y (or we have a previous selection), show marker initially
          try {
            const fromKey = parseImageStartFromKey(keyInput && keyInput.value);
            if (fromKey && Array.isArray(fromKey)) {
              selectedXY = fromKey;
              moveCoverMarkerToXY(fromKey[0], fromKey[1]);
            } else if (selectedXY && Array.isArray(selectedXY)) {
              moveCoverMarkerToXY(selectedXY[0], selectedXY[1]);
            }
          } catch {}
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
    const isImg = isImageFile(f);
    const start = isImg ? computeImageStart(f) : computeStartParam(f);
    if (!f || !lsb) return;
    const fd = new FormData();
    fd.append('cover_file', f);
    fd.append('lsb_count', String(lsb));
    fd.append('start_location', start);
    try {
      const data = await postForm('/calculate_capacity', fd);
      const capacityText = `Capacity (after start offset): ${fmtBytes(data.capacity_bytes)} (${data.capacity_bytes} bytes)`;
      let extra = '';
      if (typeof data.start_offset_bytes === 'number') {
        extra += ` | Start offset: ${data.start_offset_bytes} carrier bytes`;
      } else if (typeof data.start_offset_bits === 'number') {
        extra += ` | Start offset: ${data.start_offset_bits} LSB slots`;
      }
      if (data.dimensions) {
        extra += ` | Dimensions: ${data.dimensions}`;
      }
      capInfo.textContent = capacityText + extra;
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
    const isImg = isImageFile(cover);
    const start = isImg ? computeImageStart(cover) : computeStartParam(cover);
    if (!cover) { encodeResults.textContent = 'Please select a cover file.'; return; }
    if (!payload && !payloadTextVal) { encodeResults.textContent = 'Please select a payload file or enter payload text.'; return; }
    if (!key) { encodeResults.textContent = 'Please enter a key.'; return; }

    // If cover is an image, enforce (x,y) format
    if (isImg && !/^\s*\d+\s*,\s*\d+\s*$/.test(start)) { return; }
    if (!isImg && !/^\s*\d+\s*$/.test(start)) {
      encodeResults.textContent = 'Start Location must be a whole number for audio files.';
      return;
    }
    const fd = new FormData();
    fd.append('cover_file', cover);
    if (payload) {
      fd.append('payload_file', payload);
    } else if (payloadTextVal) {
      fd.append('payload_text', payloadTextVal);
    }
    fd.append('key', key);
    fd.append('lsb_count', String(lsb));
    fd.append('start_location', start);
    try {
      const data = await postForm('/encode', fd);
      renderJSON(encodeResults, data);
      // If encoding succeeded and returned start_xy, ensure the key reflects it
      if (data && isImg && Array.isArray(data.start_xy) && data.start_xy.length === 2 && keyInput) {
        const hasAt = (keyInput.value || '').includes('@');
        const xyText = `${data.start_xy[0]},${data.start_xy[1]}`;
        if (!hasAt) {
          keyInput.value = `${keyInput.value || ''}@${xyText}`;
        }
      }
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
    const isImgStego = isImageFile(stego);
    let start;
    if (isImgStego) {
      const xy = parseImageStartFromKey(decodeKey.value || '');
      start = xy ? `${xy[0]},${xy[1]}` : '0,0';
    } else {
      // audio slots: try KEY@N, else 0
      const keyStr = decodeKey.value || '';
      const at = keyStr.indexOf('@');
      if (at !== -1) {
        const rest = keyStr.slice(at + 1);
        if (!rest.includes(',')) {
          const n = parseInt(rest, 10);
          start = Number.isFinite(n) && n >= 0 ? String(n) : '0';
        } else {
          start = '0';
        }
      } else {
        start = '0';
      }
    }
    if (!stego) { decodeResults.textContent = 'Please select a stego file.'; return; }
    if (!key) { decodeResults.textContent = 'Please enter a key.'; return; }

    // If stego is an image, enforce (x,y) format
    if (isImgStego && !/^\s*\d+\s*,\s*\d+\s*$/.test(start)) { return; }
    if (!isImgStego && !/^\s*\d+\s*$/.test(start)) { return; }
    const fd = new FormData();
    fd.append('stego_file', stego);
    fd.append('key', key);
    fd.append('lsb_count', String(lsb));
    fd.append('start_location', start);
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
  encodeBtn && encodeBtn.addEventListener('click', onEncode);
  decodeBtn && decodeBtn.addEventListener('click', onDecode);

  // Copy key to clipboard
  copyBtn && copyBtn.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(keyInput.value || '');
      copyBtn.textContent = 'Copied';
      setTimeout(() => { copyBtn.textContent = 'Copy'; }, 1200);
    } catch {}
  });

  // When the key changes and encodes an (x,y), reflect on the marker
  keyInput && keyInput.addEventListener('input', () => {
    const coverFile = coverInput && coverInput.files && coverInput.files[0];
    if (!isImageFile(coverFile)) return;
    const xy = parseImageStartFromKey(keyInput.value || '');
    if (xy) {
      selectedXY = xy;
      moveCoverMarkerToXY(xy[0], xy[1]);
      try { triggerCapacity(); } catch {}
    }
  });
})();
