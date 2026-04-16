// UGC Ad Pipeline — Asset Library
const API = '';

let registry = { products: {}, subjects: {}, moods: {}, audio: {} };
let queue = [];

// ─── Init ───
document.addEventListener('DOMContentLoaded', async () => {
    setupDropZones();
    await loadRegistry();
    await loadOutputs();
    await checkFirstLaunch();
});

// ─── Top-Level Drop Zones ───
function setupDropZones() {
    document.querySelectorAll('.drop-zone').forEach(zone => {
        const category = zone.dataset.category;
        const input = zone.querySelector('input[type="file"]');

        zone.addEventListener('click', (e) => {
            if (e.target.closest('input')) return;
            input.click();
        });

        input.addEventListener('change', (e) => {
            [...e.target.files].forEach(f => addToQueue(f, category));
            input.value = '';
        });

        zone.addEventListener('dragenter', e => { e.preventDefault(); zone.classList.add('dragover'); });
        zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
        zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
        zone.addEventListener('drop', e => {
            e.preventDefault();
            zone.classList.remove('dragover');
            [...e.dataTransfer.files].forEach(f => {
                if (category === 'audio') {
                    if (f.type.startsWith('audio/')) addToQueue(f, category);
                } else {
                    if (f.type.startsWith('image/')) addToQueue(f, category);
                }
            });
        });
    });
}

// ─── Queue Management ───
function addToQueue(file, category, existingSlug) {
    const id = Date.now() + '_' + Math.random().toString(36).slice(2, 8);
    const slug = existingSlug || file.name
        .replace(/\.[^.]+$/, '')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-|-$/g, '')
        .slice(0, 30);

    queue.push({ id, file, category, slug, description: '', status: 'pending', existingSlug: !!existingSlug });
    renderQueue();

    // Auto-scroll to queue
    document.getElementById('queue-section').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function renderQueue() {
    const container = document.getElementById('queue-list');
    const section = document.getElementById('queue-section');
    const countEl = document.getElementById('queue-count');

    if (!queue.length) { section.style.display = 'none'; return; }
    section.style.display = 'block';
    countEl.textContent = queue.length;

    container.innerHTML = queue.map(item => {
        const badgeClass = `badge-${item.category}`;
        const categoryLabel = { product: 'Product', subject: 'Subject', mood: 'Mood', audio: 'Audio' }[item.category];
        const isAudio = item.category === 'audio';
        const thumbUrl = isAudio ? '' : URL.createObjectURL(item.file);
        const disabled = item.status === 'uploading';

        const thumbHtml = isAudio
            ? `<div class="queue-thumb queue-thumb-audio"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg></div>`
            : `<img class="queue-thumb" src="${thumbUrl}" alt="">`;

        return `
            <div class="queue-item">
                ${thumbHtml}
                <div class="queue-info">
                    <div class="queue-filename">${item.file.name}</div>
                    <div class="queue-meta">
                        ${(item.file.size / 1048576).toFixed(1)} MB
                        <span class="badge ${badgeClass}">${categoryLabel}</span>
                        ${item.existingSlug ? '<span style="color:var(--accent);font-weight:500">Adding to ' + item.slug + '</span>' : ''}
                    </div>
                </div>
                <div class="queue-form">
                    <input class="input" type="text" placeholder="Name slug"
                           value="${item.slug}"
                           oninput="updateQueueItem('${item.id}','slug',this.value)"
                           ${disabled || item.existingSlug ? 'disabled' : ''}>
                    <input class="input input-wide" type="text" placeholder="Description (optional)"
                           value="${item.description}"
                           oninput="updateQueueItem('${item.id}','description',this.value)"
                           ${disabled ? 'disabled' : ''}>
                    <button class="btn btn-primary btn-sm" onclick="uploadItem('${item.id}')" ${disabled ? 'disabled' : ''}>
                        ${disabled ? 'Adding...' : 'Add'}
                    </button>
                    <button class="btn btn-ghost btn-sm" onclick="removeFromQueue('${item.id}')" ${disabled ? 'disabled' : ''}>&times;</button>
                </div>
            </div>`;
    }).join('');
}

function updateQueueItem(id, field, value) {
    const item = queue.find(q => q.id === id);
    if (item) item[field] = value;
}

function removeFromQueue(id) {
    queue = queue.filter(q => q.id !== id);
    renderQueue();
}

// ─── Upload ───
async function uploadItem(id) {
    const item = queue.find(q => q.id === id);
    if (!item || item.status === 'uploading') return;

    const slug = item.slug.trim();
    if (!slug) { toast('Enter a name for this asset', 'error'); return; }

    item.status = 'uploading';
    renderQueue();

    const fd = new FormData();
    fd.append('file', item.file);
    fd.append('category', item.category);
    fd.append('slug', slug);
    fd.append('name', slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()));
    fd.append('description', item.description || '');

    try {
        const resp = await fetch(`${API}/api/upload`, { method: 'POST', body: fd });
        const data = await resp.json();
        if (data.success) {
            queue = queue.filter(q => q.id !== id);
            renderQueue();
            toast(`Added to ${data.category} / ${data.slug}`, 'success');
            loadRegistry();
        } else {
            item.status = 'pending';
            renderQueue();
            toast(data.error || 'Upload failed', 'error');
        }
    } catch (err) {
        item.status = 'pending';
        renderQueue();
        toast('Server not reachable', 'error');
    }
}

async function uploadAll() {
    for (const item of [...queue]) {
        if (item.status === 'pending' && item.slug.trim()) {
            await uploadItem(item.id);
        }
    }
}

// ─── Add More to Existing Group ───
function triggerAddMore(category, slug) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = category === 'audio' ? 'audio/*' : 'image/*';
    input.multiple = true;
    input.onchange = (e) => {
        [...e.target.files].forEach(f => addToQueue(f, category, slug));
    };
    input.click();
}

function setupAddMoreDropZone(el, category, slug) {
    el.addEventListener('dragenter', e => { e.preventDefault(); el.classList.add('dragover'); });
    el.addEventListener('dragover', e => { e.preventDefault(); el.classList.add('dragover'); });
    el.addEventListener('dragleave', () => el.classList.remove('dragover'));
    el.addEventListener('drop', e => {
        e.preventDefault();
        el.classList.remove('dragover');
        [...e.dataTransfer.files].forEach(f => {
            if (f.type.startsWith('image/')) addToQueue(f, category, slug);
        });
    });
}

// ─── Library ───
async function loadRegistry() {
    try {
        const resp = await fetch(`${API}/api/registry`);
        registry = await resp.json();
        renderLibrary();
    } catch (err) {
        console.error('Registry load failed:', err);
    }
}

function renderLibrary() {
    const container = document.getElementById('library');
    const categories = [
        { key: 'products', type: 'product', label: 'Products', dot: 'dot-product' },
        { key: 'subjects', type: 'subject', label: 'Subjects', dot: 'dot-subject' },
        { key: 'moods', type: 'mood', label: 'Moods', dot: 'dot-mood' },
        { key: 'audio', type: 'audio', label: 'Audio', dot: 'dot-audio' },
    ];

    let html = '';
    let total = 0;

    for (const cat of categories) {
        const isAudioCat = cat.key === 'audio';
        const items = registry[cat.key] || {};
        const slugs = Object.keys(items);
        const count = slugs.reduce((s, k) => s + ((isAudioCat ? items[k].audio?.length : items[k].images?.length) || 0), 0);
        total += count;
        const unitLabel = isAudioCat ? 'file' : 'image';

        html += `<div class="library-category">
            <div class="library-category-header">
                <div class="library-category-dot ${cat.dot}"></div>
                <span class="library-category-title">${cat.label}</span>
                <span class="library-category-count">${count} ${unitLabel}${count !== 1 ? 's' : ''}</span>
            </div>`;

        if (!slugs.length) {
            html += `<div class="empty-state">No ${cat.label.toLowerCase()} yet</div>`;
        } else {
            for (const slug of slugs) {
                const asset = items[slug];
                const assetItems = isAudioCat ? (asset.audio || []) : (asset.images || []);
                const desc = asset.description ? `<span class="asset-group-desc">${asset.description}</span>` : '';
                const addLabel = isAudioCat ? '+ Add audio' : '+ Add image';

                html += `<div class="asset-group">
                    <div class="asset-group-header">
                        <div>
                            <span class="asset-group-name">${asset.name}</span>
                            ${desc}
                        </div>
                        <div class="asset-group-actions">
                            <button class="btn btn-ghost btn-sm" onclick="triggerAddMore('${cat.type}','${slug}')">${addLabel}</button>
                        </div>
                    </div>
                    <div class="asset-grid">`;

                for (const img of assetItems) {
                    const filename = img.path.split('/').pop();
                    const ctx = img.ai_context;
                    const analyzing = ctx === null;
                    const hasContext = ctx && typeof ctx === 'object' && !ctx.raw_analysis;

                    // Build context summary
                    let contextHtml = '';
                    if (analyzing) {
                        contextHtml = `<div class="ai-context-status">Analyzing...</div>`;
                    } else if (hasContext) {
                        const notes = ctx.ad_notes || '';
                        const topLine = ctx.product_type || ctx.gender || ctx.setting || ctx.tone || '';
                        const detail = ctx.colors || ctx.appearance || ctx.color_palette || ctx.speaking_style || '';
                        contextHtml = `
                            <div class="ai-context" onclick="toggleContext(this)">
                                <div class="ai-context-label">AI Context</div>
                                <div class="ai-context-summary">${topLine}${detail ? ' · ' + detail : ''}</div>
                                <div class="ai-context-full" style="display:none">
                                    ${Object.entries(ctx).map(([k,v]) =>
                                        `<div class="ai-ctx-row"><span class="ai-ctx-key">${k.replace(/_/g,' ')}</span><span class="ai-ctx-val">${v}</span></div>`
                                    ).join('')}
                                </div>
                            </div>`;
                    }

                    if (isAudioCat) {
                        // Audio card with inline player
                        html += `<div class="asset-card ${hasContext ? 'has-context' : ''}">
                            <button class="asset-card-remove" onclick="deleteAsset('${cat.type}','${slug}','${img.path}')" title="Remove">&times;</button>
                            <div class="asset-card-audio">
                                <div class="audio-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg></div>
                                <audio controls preload="metadata" src="/${img.path}"></audio>
                            </div>
                            <div class="asset-card-info">
                                <div class="asset-card-filename">${filename}</div>
                                <div class="asset-card-dims">${img.file_size_mb ? img.file_size_mb + ' MB' : 'audio'}</div>
                                ${contextHtml}
                            </div>
                        </div>`;
                    } else {
                        // Image card
                        html += `<div class="asset-card ${hasContext ? 'has-context' : ''}">
                            <button class="asset-card-remove" onclick="deleteAsset('${cat.type}','${slug}','${img.path}')" title="Remove">&times;</button>
                            <img class="asset-card-image" src="/${img.path}" alt="${asset.name}" loading="lazy">
                            <div class="asset-card-info">
                                <div class="asset-card-filename">${filename}</div>
                                <div class="asset-card-dims">${img.dimensions}</div>
                                ${contextHtml}
                            </div>
                        </div>`;
                    }
                }

                // "Add more" inline drop target
                html += `<div class="add-more-card" data-add-category="${cat.type}" data-add-slug="${slug}" onclick="triggerAddMore('${cat.type}','${slug}')">
                    <div class="add-more-icon">+</div>
                    <div class="add-more-label">Add more</div>
                </div>`;

                html += `</div></div>`;
            }
        }
        html += `</div>`;
    }

    container.innerHTML = html;

    // Wire up inline add-more drop targets
    container.querySelectorAll('.add-more-card').forEach(el => {
        setupAddMoreDropZone(el, el.dataset.addCategory, el.dataset.addSlug);
    });

    // Update stats
    const pending = getPendingCount();
    document.getElementById('total-assets').textContent = total;
    const analyzeBar = document.getElementById('analyze-bar');
    if (pending > 0) {
        analyzeBar.style.display = 'flex';
        analyzeBar.querySelector('.analyze-count').textContent = `${pending} image${pending > 1 ? 's' : ''} pending analysis`;
    } else {
        analyzeBar.style.display = 'none';
    }
    document.getElementById('total-products').textContent = Object.keys(registry.products || {}).length;
    document.getElementById('total-subjects').textContent = Object.keys(registry.subjects || {}).length;
    document.getElementById('total-moods').textContent = Object.keys(registry.moods || {}).length;
    document.getElementById('total-audio').textContent = Object.keys(registry.audio || {}).length;
}

async function deleteAsset(type, slug, path) {
    if (!confirm('Remove this image from the library?')) return;

    try {
        const resp = await fetch(`${API}/api/delete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category: type, slug, path }),
        });
        const data = await resp.json();
        if (data.success) {
            toast('Image removed', 'success');
            loadRegistry();
        } else {
            toast(data.error || 'Failed to remove', 'error');
        }
    } catch (err) {
        toast('Server not reachable', 'error');
    }
}

// ─── Outputs ───
let outputs = {};

async function loadOutputs() {
    try {
        const resp = await fetch(`${API}/api/outputs`);
        outputs = await resp.json();
        renderOutputs();
    } catch (err) {
        console.error('Outputs load failed:', err);
    }
}

function renderOutputs() {
    const container = document.getElementById('outputs');
    const productSlugs = Object.keys(outputs);

    let totalVideos = 0;
    let totalRuns = 0;
    for (const slug of productSlugs) {
        for (const run of outputs[slug].runs) {
            totalRuns++;
            totalVideos += run.completed;
        }
    }

    document.getElementById('total-videos').textContent = totalVideos;
    document.getElementById('total-runs').textContent = totalRuns;

    if (!productSlugs.length) {
        container.innerHTML = `<div class="empty-state">No outputs yet. Run <code>/ab-test</code> in Claude to generate video ads.</div>`;
        return;
    }

    const formatLabels = { podcast: 'Podcast', ugc: 'UGC', lifestyle: 'Lifestyle', greenscreen: 'Greenscreen' };
    const statusIcons = { completed: 'done', dry_run: 'queued', pending: 'queued', submitted: 'generating', error: 'failed' };

    let html = '';

    for (const slug of productSlugs) {
        const { product, runs } = outputs[slug];

        html += `<div class="output-product">
            <div class="output-product-header">
                <span class="output-product-name">${product}</span>
                <span class="library-category-count">${runs.length} run${runs.length !== 1 ? 's' : ''}</span>
            </div>`;

        for (const run of runs) {
            const date = run.created_at ? new Date(run.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '';

            html += `<div class="output-run">
                <div class="output-run-header">
                    <div class="output-run-meta">
                        <span class="output-run-date">${date}</span>
                        <span class="output-run-stats">${run.completed}/${run.total_variants} videos</span>
                        ${run.has_report ? `<a href="/${run.report_path}" target="_blank" class="output-report-link">View Report</a>` : ''}
                    </div>
                </div>
                <div class="output-videos-grid">`;

            for (const v of run.videos) {
                const label = formatLabels[v.format] || v.format;
                const statusClass = `output-status-${statusIcons[v.status] || 'queued'}`;

                if (v.has_video) {
                    html += `<div class="output-video-card">
                        <div class="output-video-wrap">
                            <video controls preload="auto" playsinline muted
                                   src="/${v.video_path}#t=0.5"
                                   onplay="this.muted=false">
                            </video>
                        </div>
                        <div class="output-video-info">
                            <div class="output-video-label">${label} v${v.variant}</div>
                            <div class="output-video-angle">${v.angle}</div>
                            <div class="output-video-size">${v.video_size_mb} MB</div>
                        </div>
                    </div>`;
                } else {
                    html += `<div class="output-video-card output-video-empty">
                        <div class="output-video-wrap output-placeholder">
                            <div class="output-status ${statusClass}">${v.status.replace('_', ' ')}</div>
                        </div>
                        <div class="output-video-info">
                            <div class="output-video-label">${label} v${v.variant}</div>
                            <div class="output-video-angle">${v.angle}</div>
                        </div>
                    </div>`;
                }
            }

            html += `</div></div>`;
        }
        html += `</div>`;
    }

    container.innerHTML = html;

    // Seek all videos to 0.5s to generate thumbnails (prevents black frames)
    container.querySelectorAll('video').forEach(video => {
        video.addEventListener('loadeddata', () => {
            if (video.currentTime < 0.1) {
                video.currentTime = 0.5;
            }
        }, { once: true });
    });
}

// ─── Context Toggle ───
function toggleContext(el) {
    const full = el.querySelector('.ai-context-full');
    if (full) full.style.display = full.style.display === 'none' ? 'block' : 'none';
}

function getPendingCount() {
    let count = 0;
    for (const cat of ['products', 'subjects', 'moods']) {
        for (const slug of Object.keys(registry[cat] || {})) {
            for (const img of registry[cat][slug].images || []) {
                if (img.ai_context === null) count++;
            }
        }
    }
    for (const slug of Object.keys(registry.audio || {})) {
        for (const aud of registry.audio[slug].audio || []) {
            if (aud.ai_context === null) count++;
        }
    }
    return count;
}

// ─── Auto-refresh ───
function isAnyVideoPlaying() {
    const videos = document.querySelectorAll('.outputs-section video');
    for (const v of videos) {
        if (!v.paused && !v.ended) return true;
    }
    return false;
}

setInterval(() => {
    if (getPendingCount() > 0) loadRegistry();
    // Don't rebuild the outputs DOM while a video is playing — it kills playback
    if (!isAnyVideoPlaying()) {
        loadOutputs();
    }
}, 5000);

// ─── Welcome / Onboarding ───
async function checkFirstLaunch() {
    // Show welcome if no brands configured
    try {
        const resp = await fetch(`${API}/api/brands`);
        const data = await resp.json();
        const hasBrands = Object.keys(data.brands || {}).length > 0;
        const dismissed = localStorage.getItem('welcome_dismissed');

        if (!hasBrands && !dismissed) {
            showWelcome();
        }
    } catch (err) {
        // Server not reachable — show welcome anyway
        showWelcome();
    }
}

function showWelcome() {
    document.getElementById('welcome-overlay').style.display = 'flex';
}

function dismissWelcome() {
    document.getElementById('welcome-overlay').style.display = 'none';
    localStorage.setItem('welcome_dismissed', 'true');
}

function copyText(text) {
    navigator.clipboard.writeText(text).then(() => {
        toast('Copied to clipboard', 'success');
    }).catch(() => {
        toast('Select and copy manually', 'error');
    });
}

// ─── Copy Analyze Prompt ───
function copyAnalyzePrompt() {
    const text = document.getElementById('analyze-command').textContent;
    navigator.clipboard.writeText(text).then(() => {
        toast('Copied — paste it in Claude', 'success');
    }).catch(() => {
        // Fallback: select the text
        const el = document.getElementById('analyze-command');
        const range = document.createRange();
        range.selectNodeContents(el);
        window.getSelection().removeAllRanges();
        window.getSelection().addRange(range);
        toast('Select all and copy (Cmd+C)', 'success');
    });
}

// ─── Toast ───
function toast(msg, type = 'info') {
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = msg;
    document.getElementById('toast-container').appendChild(el);
    setTimeout(() => el.remove(), 3500);
}
