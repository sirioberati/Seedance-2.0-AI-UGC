#!/usr/bin/env node
/**
 * Asset Wizard — Node.js Server
 * Drop-in replacement for asset_server.py when Python can't bind ports.
 * Mirrors all endpoints from the Python version.
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');

const BASE_DIR = __dirname;
const ASSETS_DIR = path.join(BASE_DIR, 'assets');
const REGISTRY_PATH = path.join(ASSETS_DIR, 'registry.json');
const BACKUPS_DIR = path.join(ASSETS_DIR, 'backups');
const APP_DIR = path.join(BASE_DIR, 'app');
const INBOX_DIR = path.join(ASSETS_DIR, 'inbox');
const PROJECTS_DIR = path.join(BASE_DIR, 'projects');
const BRANDS_PATH = path.join(BASE_DIR, 'config', 'brands.json');

const PORT = parseInt(process.env.ASSET_SERVER_PORT || '8099', 10);

const CATEGORY_DIRS = { product: 'products', subject: 'subjects', mood: 'moods', audio: 'audio' };
const IMAGE_EXTENSIONS = new Set(['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff']);
const AUDIO_EXTENSIONS = new Set(['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac']);
const VIDEO_EXTENSIONS = new Set(['.mp4', '.webm', '.mov']);

const MIME_TYPES = {
  '.html': 'text/html', '.css': 'text/css', '.js': 'application/javascript',
  '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.svg': 'image/svg+xml',
  '.mp4': 'video/mp4', '.webm': 'video/webm', '.mov': 'video/quicktime',
  '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.m4a': 'audio/mp4',
  '.aac': 'audio/aac', '.ogg': 'audio/ogg', '.flac': 'audio/flac',
  '.bmp': 'image/bmp', '.tiff': 'image/tiff', '.ico': 'image/x-icon',
};

function getMime(filepath) {
  return MIME_TYPES[path.extname(filepath).toLowerCase()] || 'application/octet-stream';
}

function loadRegistry() {
  try {
    return JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf8'));
  } catch {
    return { version: 1, updated_at: null, products: {}, subjects: {}, moods: {}, audio: {} };
  }
}

function saveRegistry(registry) {
  registry.updated_at = new Date().toISOString();
  fs.writeFileSync(REGISTRY_PATH, JSON.stringify(registry, null, 2));
}

function sendJson(res, data, status = 200) {
  const body = JSON.stringify(data);
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(body),
    'Access-Control-Allow-Origin': '*',
  });
  res.end(body);
}

function sendFile(res, filepath) {
  if (!fs.existsSync(filepath)) { res.writeHead(404); res.end('Not found'); return; }
  const data = fs.readFileSync(filepath);
  res.writeHead(200, {
    'Content-Type': getMime(filepath),
    'Content-Length': data.length,
    'Cache-Control': 'no-cache',
  });
  res.end(data);
}

function sendVideo(res, req, filepath) {
  if (!fs.existsSync(filepath)) { res.writeHead(404); res.end('Not found'); return; }
  const stat = fs.statSync(filepath);
  const size = stat.size;
  const range = req.headers.range;
  if (range) {
    const parts = range.replace('bytes=', '').split('-');
    const start = parseInt(parts[0], 10);
    const end = parts[1] ? parseInt(parts[1], 10) : size - 1;
    res.writeHead(206, {
      'Content-Range': `bytes ${start}-${end}/${size}`,
      'Content-Length': end - start + 1,
      'Content-Type': getMime(filepath),
      'Accept-Ranges': 'bytes',
    });
    fs.createReadStream(filepath, { start, end }).pipe(res);
  } else {
    res.writeHead(200, {
      'Content-Type': getMime(filepath),
      'Content-Length': size,
      'Accept-Ranges': 'bytes',
    });
    fs.createReadStream(filepath).pipe(res);
  }
}

function getOutputs() {
  const outputs = {};
  if (!fs.existsSync(PROJECTS_DIR)) return outputs;
  const dirs = fs.readdirSync(PROJECTS_DIR).filter(d => {
    const full = path.join(PROJECTS_DIR, d);
    return fs.statSync(full).isDirectory() && !d.startsWith('.');
  }).sort().reverse();

  for (const dir of dirs) {
    const matrixPath = path.join(PROJECTS_DIR, dir, 'matrix.json');
    if (!fs.existsSync(matrixPath)) continue;
    let matrix;
    try { matrix = JSON.parse(fs.readFileSync(matrixPath, 'utf8')); } catch { continue; }

    const product = (matrix.project || {}).product || 'Unknown';
    const productSlug = product.toLowerCase().replace(/ /g, '-');
    const created = (matrix.project || {}).created_at || '';

    const videos = (matrix.variants || []).map(v => {
      const videoFile = path.join(PROJECTS_DIR, dir, v.output_file || '');
      const hasVideo = fs.existsSync(videoFile);
      return {
        id: v.id || '', format: v.format || '', variant: v.variant || 0,
        angle: v.angle || '', status: v.status || 'pending',
        settings: v.settings || {}, has_video: hasVideo,
        video_path: hasVideo ? `projects/${dir}/${v.output_file || ''}` : null,
        video_size_mb: hasVideo ? +(fs.statSync(videoFile).size / 1048576).toFixed(1) : 0,
      };
    });

    const run = {
      project_dir: dir, product, product_slug: productSlug, created_at: created,
      total_variants: matrix.total_variants || 0,
      completed: videos.filter(v => v.has_video).length,
      videos,
      has_report: fs.existsSync(path.join(PROJECTS_DIR, dir, 'report.html')),
      report_path: fs.existsSync(path.join(PROJECTS_DIR, dir, 'report.html'))
        ? `projects/${dir}/report.html` : null,
    };

    if (!outputs[productSlug]) outputs[productSlug] = { product, runs: [] };
    outputs[productSlug].runs.push(run);
  }
  return outputs;
}

function getNextNumber(targetDir, slug, assetType) {
  if (!fs.existsSync(targetDir)) return 1;
  const files = fs.readdirSync(targetDir).filter(f => f.startsWith(`${slug}-${assetType}-`));
  const nums = files.map(f => {
    const parts = path.parse(f).name.split('-');
    return parseInt(parts[parts.length - 1], 10);
  }).filter(n => !isNaN(n));
  return nums.length ? Math.max(...nums) + 1 : 1;
}

function sortAsset(sourcePath, assetType, slug, name, description = '') {
  if (!fs.existsSync(sourcePath)) return { error: `File not found: ${sourcePath}` };
  slug = slug.toLowerCase().trim().replace(/ /g, '-').replace(/_/g, '-');
  const categoryDir = CATEGORY_DIRS[assetType];
  if (!categoryDir) return { error: `Invalid type: ${assetType}` };

  const targetDir = path.join(ASSETS_DIR, categoryDir, slug);
  fs.mkdirSync(targetDir, { recursive: true });

  const nextNum = getNextNumber(targetDir, slug, assetType);
  const ext = path.extname(sourcePath).toLowerCase();
  const newFilename = `${slug}-${assetType}-${String(nextNum).padStart(2, '0')}${ext}`;
  const targetPath = path.join(targetDir, newFilename);

  const isAudio = AUDIO_EXTENSIONS.has(ext);
  const originalName = path.basename(sourcePath);

  // Backup
  fs.mkdirSync(BACKUPS_DIR, { recursive: true });
  let backupPath = path.join(BACKUPS_DIR, `${slug}-${originalName}`);
  if (fs.existsSync(backupPath)) {
    let i = 1;
    const bp = path.parse(backupPath);
    while (fs.existsSync(backupPath)) {
      backupPath = path.join(bp.dir, `${bp.name}-${i}${bp.ext}`);
      i++;
    }
  }
  fs.copyFileSync(sourcePath, backupPath);
  fs.renameSync(sourcePath, targetPath);

  const registry = loadRegistry();
  if (!registry[categoryDir]) registry[categoryDir] = {};
  const itemsKey = isAudio ? 'audio' : 'images';
  if (!registry[categoryDir][slug]) {
    registry[categoryDir][slug] = { name, description, [itemsKey]: [] };
  }
  if (!registry[categoryDir][slug][itemsKey]) registry[categoryDir][slug][itemsKey] = [];

  const relPath = path.relative(BASE_DIR, targetPath);
  const entry = { path: relPath, original_name: originalName, added_at: new Date().toISOString(), ai_context: null };
  if (isAudio) {
    entry.file_size_mb = +(fs.statSync(targetPath).size / (1024 * 1024)).toFixed(2);
  } else {
    entry.dimensions = 'unknown';
  }
  registry[categoryDir][slug][itemsKey].push(entry);
  saveRegistry(registry);

  return { success: true, slug, name, type: assetType, category: categoryDir, new_path: relPath, original_name: originalName };
}

function parseMultipart(req, callback) {
  const boundary = req.headers['content-type'].split('boundary=')[1];
  const chunks = [];
  req.on('data', c => chunks.push(c));
  req.on('end', () => {
    const buf = Buffer.concat(chunks);
    const parts = {};
    const raw = buf.toString('binary');
    const segments = raw.split(`--${boundary}`);
    for (const seg of segments) {
      if (seg === '--\r\n' || seg.trim() === '' || seg.trim() === '--') continue;
      const headerEnd = seg.indexOf('\r\n\r\n');
      if (headerEnd === -1) continue;
      const headers = seg.slice(0, headerEnd);
      const body = seg.slice(headerEnd + 4, seg.endsWith('\r\n') ? seg.length - 2 : seg.length);
      const nameMatch = headers.match(/name="([^"]+)"/);
      const filenameMatch = headers.match(/filename="([^"]+)"/);
      if (nameMatch) {
        if (filenameMatch) {
          parts[nameMatch[1]] = { filename: filenameMatch[1], data: Buffer.from(body, 'binary') };
        } else {
          parts[nameMatch[1]] = body.trim();
        }
      }
    }
    callback(parts);
  });
}

function readBody(req, callback) {
  const chunks = [];
  req.on('data', c => chunks.push(c));
  req.on('end', () => callback(Buffer.concat(chunks).toString()));
}

const server = http.createServer((req, res) => {
  const parsed = new URL(req.url, `http://localhost:${PORT}`);
  const urlPath = decodeURIComponent(parsed.pathname);

  if (req.method === 'OPTIONS') {
    res.writeHead(200, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    });
    res.end();
    return;
  }

  if (req.method === 'GET') {
    if (urlPath === '/' || urlPath === '/index.html') {
      sendFile(res, path.join(APP_DIR, 'index.html'));
    } else if (urlPath.startsWith('/app/')) {
      sendFile(res, path.join(APP_DIR, urlPath.slice(5)));
    } else if (urlPath.startsWith('/assets/')) {
      sendFile(res, path.join(ASSETS_DIR, urlPath.slice(8)));
    } else if (urlPath.startsWith('/projects/')) {
      const fpath = path.join(PROJECTS_DIR, urlPath.slice(10));
      if (VIDEO_EXTENSIONS.has(path.extname(fpath).toLowerCase())) {
        sendVideo(res, req, fpath);
      } else {
        sendFile(res, fpath);
      }
    } else if (urlPath === '/api/registry') {
      sendJson(res, loadRegistry());
    } else if (urlPath === '/api/brands') {
      try { sendJson(res, JSON.parse(fs.readFileSync(BRANDS_PATH, 'utf8'))); }
      catch { sendJson(res, { version: 1, brands: {} }); }
    } else if (urlPath === '/api/outputs') {
      sendJson(res, getOutputs());
    } else if (urlPath === '/api/inbox') {
      const images = [];
      if (fs.existsSync(INBOX_DIR)) {
        for (const f of fs.readdirSync(INBOX_DIR).sort()) {
          const fp = path.join(INBOX_DIR, f);
          const ext = path.extname(f).toLowerCase();
          if (fs.statSync(fp).isFile() && (IMAGE_EXTENSIONS.has(ext) || AUDIO_EXTENSIONS.has(ext))) {
            images.push({ filename: f, size_mb: +(fs.statSync(fp).size / 1048576).toFixed(2), dimensions: 'unknown' });
          }
        }
      }
      sendJson(res, images);
    } else {
      res.writeHead(404); res.end('Not found');
    }
    return;
  }

  if (req.method === 'POST') {
    if (urlPath === '/api/upload') {
      const ct = req.headers['content-type'] || '';
      if (ct.includes('multipart/form-data')) {
        parseMultipart(req, (parts) => {
          const fileData = parts.file;
          if (!fileData || !fileData.filename) { sendJson(res, { error: 'No file uploaded' }, 400); return; }
          fs.mkdirSync(INBOX_DIR, { recursive: true });
          const inboxPath = path.join(INBOX_DIR, fileData.filename);
          fs.writeFileSync(inboxPath, fileData.data);
          const result = sortAsset(inboxPath, parts.category || 'product', parts.slug || 'unnamed', parts.name || (parts.slug || 'unnamed').replace(/-/g, ' '), parts.description || '');
          sendJson(res, result);
        });
      } else if (ct.includes('application/json')) {
        readBody(req, (raw) => {
          const body = JSON.parse(raw);
          const result = sortAsset(path.join(BASE_DIR, body.file), body.category, body.slug, body.name || body.slug.replace(/-/g, ' '), body.description || '');
          sendJson(res, result);
        });
      } else {
        sendJson(res, { error: 'Unsupported content type' }, 400);
      }
    } else if (urlPath === '/api/context') {
      readBody(req, (raw) => {
        const body = JSON.parse(raw);
        const imagePath = body.path;
        const aiContext = body.ai_context;
        if (!imagePath || !aiContext) { sendJson(res, { error: 'Missing path or ai_context' }, 400); return; }
        const registry = loadRegistry();
        let updated = false;
        for (const cat of ['products', 'subjects', 'moods', 'audio']) {
          for (const [, data] of Object.entries(registry[cat] || {})) {
            const items = [...(data.images || []), ...(data.audio || [])];
            for (const img of items) {
              if (img.path === imagePath) { img.ai_context = aiContext; updated = true; break; }
            }
            if (updated) break;
          }
          if (updated) break;
        }
        if (updated) { saveRegistry(registry); sendJson(res, { success: true }); }
        else { sendJson(res, { error: `Image path not found: ${imagePath}` }, 404); }
      });
    } else if (urlPath === '/api/delete') {
      readBody(req, (raw) => {
        const body = JSON.parse(raw);
        const { category, slug, path: imgPath } = body;
        if (!category || !slug) { sendJson(res, { error: 'Missing category or slug' }, 400); return; }
        const registry = loadRegistry();
        const catKey = CATEGORY_DIRS[category] || category;
        if (!registry[catKey] || !registry[catKey][slug]) { sendJson(res, { error: `Slug '${slug}' not found` }, 404); return; }
        const slugDir = path.join(ASSETS_DIR, catKey, slug);
        if (imgPath) {
          const fullPath = path.join(BASE_DIR, imgPath);
          if (fs.existsSync(fullPath)) fs.unlinkSync(fullPath);
          registry[catKey][slug].images = (registry[catKey][slug].images || []).filter(i => i.path !== imgPath);
          if (!registry[catKey][slug].images.length) {
            delete registry[catKey][slug];
            if (fs.existsSync(slugDir) && fs.readdirSync(slugDir).length === 0) fs.rmdirSync(slugDir);
          }
        } else {
          for (const img of (registry[catKey][slug].images || [])) {
            const fp = path.join(BASE_DIR, img.path);
            if (fs.existsSync(fp)) fs.unlinkSync(fp);
          }
          delete registry[catKey][slug];
          if (fs.existsSync(slugDir)) fs.rmSync(slugDir, { recursive: true, force: true });
        }
        saveRegistry(registry);
        sendJson(res, { success: true });
      });
    } else if (urlPath === '/api/webhook') {
      readBody(req, (raw) => {
        const body = JSON.parse(raw);
        const requestId = body.requestId || body.request_id || '';
        const status = (body.status || '').toUpperCase();
        const videoUrl = body.result || body.video_url || '';
        const cost = body.cost || 0;
        console.log(`  [WEBHOOK] requestId=${requestId} status=${status} cost=${cost}`);
        if (!requestId) { sendJson(res, { error: 'Missing requestId' }, 400); return; }

        // Log webhook
        const logPath = path.join(PROJECTS_DIR, 'webhook_log.jsonl');
        try { fs.appendFileSync(logPath, JSON.stringify({ timestamp: new Date().toISOString(), payload: body }) + '\n'); } catch {}

        let updated = false;
        if (fs.existsSync(PROJECTS_DIR)) {
          const dirs = fs.readdirSync(PROJECTS_DIR).filter(d => fs.statSync(path.join(PROJECTS_DIR, d)).isDirectory()).sort().reverse();
          for (const dir of dirs) {
            const matrixPath = path.join(PROJECTS_DIR, dir, 'matrix.json');
            if (!fs.existsSync(matrixPath)) continue;
            let matrix;
            try { matrix = JSON.parse(fs.readFileSync(matrixPath, 'utf8')); } catch { continue; }
            for (const v of (matrix.variants || [])) {
              const genId = v.generation_id || v.request_id || '';
              if (genId === requestId) {
                if (status === 'COMPLETED' && videoUrl) {
                  v.status = 'completed';
                  v.video_url = videoUrl;
                  v.cost = cost;
                  // Download handled by polling in Claude
                } else if (status === 'FAILED') {
                  v.status = 'error';
                  v.error = body.error || 'Generation failed';
                }
                fs.writeFileSync(matrixPath, JSON.stringify(matrix, null, 2));
                updated = true;
                console.log(`  [WEBHOOK] Updated ${dir}/${v.id} -> ${v.status}`);
                break;
              }
            }
            if (updated) break;
          }
        }
        if (updated) sendJson(res, { success: true, request_id: requestId });
        else sendJson(res, { warning: 'No matching variant found', request_id: requestId });
      });
    } else {
      res.writeHead(404); res.end('Not found');
    }
    return;
  }

  res.writeHead(405); res.end('Method not allowed');
});

server.listen(PORT, () => {
  console.log(`Asset Wizard UI running at http://localhost:${PORT}`);
  console.log(`Serving from: ${BASE_DIR}`);
});
