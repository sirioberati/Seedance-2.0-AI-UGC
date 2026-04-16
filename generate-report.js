const PDFDocument = require('pdfkit');
const fs = require('fs');

const doc = new PDFDocument({ size: 'letter', margins: { top: 50, bottom: 50, left: 50, right: 50 } });
const out = fs.createWriteStream('api-bug-report.pdf');
doc.pipe(out);

const W = 512; // usable width
const RED = '#DC2626';
const GREEN = '#16A34A';
const BLUE = '#2563EB';
const DARK = '#1F2937';
const GRAY = '#6B7280';
const LIGHT_RED = '#FEE2E2';
const LIGHT_BLUE = '#DBEAFE';
const BG = '#F3F4F6';

// ── TITLE ──
doc.fontSize(24).fillColor(DARK).text('Enhancor API Bug Report', { align: 'center' });
doc.moveDown(0.3);
doc.fontSize(10).fillColor(GRAY).text('Seedance 2.0 Full Access  |  /queue endpoint  |  April 14, 2026', { align: 'center' });
doc.moveDown(0.3);
doc.moveTo(50, doc.y).lineTo(562, doc.y).strokeColor('#D1D5DB').stroke();
doc.moveDown(0.8);

// ── SUMMARY ──
doc.fontSize(16).fillColor(DARK).text('Summary');
doc.moveDown(0.4);
doc.fontSize(10).fillColor(DARK)
  .text('The /queue endpoint returns HTTP 503 when ', { continued: true })
  .font('Helvetica-Bold').text('images[]', { continued: true })
  .font('Helvetica').text(' contains 2 or more URLs. This affects every mode except ', { continued: true })
  .font('Helvetica-Bold').text('ugc', { continued: true })
  .font('Helvetica').text(' (which uses products[]/influencers[] instead). With 1 image, all modes return 200.');
doc.moveDown(0.3);
doc.font('Helvetica').text('The jobs still queue and complete on the backend (confirmed via webhook callbacks) \u2014 but the requestId is lost in the 503 response.');
doc.moveDown(0.8);

// ── BUG BOX ──
doc.fontSize(16).fillColor(DARK).text('The Bug');
doc.moveDown(0.4);
const bugY = doc.y;
doc.rect(50, bugY, W, 50).fill(LIGHT_RED).stroke();
doc.rect(50, bugY, W, 50).lineWidth(1.5).strokeColor(RED).stroke();
doc.fillColor(RED).fontSize(11).font('Helvetica-Bold');
doc.text('images[] with 2+ URLs \u2192 503 on every mode except ugc.', 62, bugY + 10, { width: W - 24 });
doc.font('Helvetica').text('Same images with 1 URL \u2192 200. Job queues anyway but requestId is lost.', 62, bugY + 28, { width: W - 24 });
doc.y = bugY + 60;
doc.moveDown(0.8);

// ── CORE TEST TABLE ──
doc.fontSize(16).fillColor(DARK).font('Helvetica-Bold').text('Core Test: 1 Image vs 2 Images');
doc.moveDown(0.5);
doc.font('Helvetica');

const coreRows = [
  ['Mode', '1 image + 1 audio', '2 images + 1 audio'],
  ['ugc (products[])', '200 OK', '200 OK'],
  ['multi_reference', '200 OK', '503'],
  ['lipsyncing', '200 OK', '503'],
  ['multi_frame', '200 OK', '503'],
  ['first_n_last_frames', '200 OK', '503'],
];

const colW = [170, 171, 171];
let ty = doc.y;

coreRows.forEach((row, ri) => {
  const x0 = 50;
  let bg = ri === 0 ? DARK : (ri % 2 === 0 ? BG : '#FFFFFF');
  doc.rect(x0, ty, W, 22).fill(bg);

  row.forEach((cell, ci) => {
    const cx = x0 + colW.slice(0, ci).reduce((a, b) => a + b, 0);
    let color = ri === 0 ? '#FFFFFF' : DARK;
    let font = ri === 0 ? 'Helvetica-Bold' : 'Helvetica';

    if (ri > 0 && ci > 0) {
      if (cell === '200 OK') { color = GREEN; font = 'Helvetica-Bold'; }
      if (cell === '503') { color = RED; font = 'Helvetica-Bold'; }
    }

    doc.font(font).fontSize(9).fillColor(color).text(cell, cx + 6, ty + 6, { width: colW[ci] - 12 });
  });
  ty += 22;
});

doc.rect(50, doc.y, W, ty - doc.y).strokeColor('#D1D5DB').stroke();
doc.y = ty + 5;
doc.moveDown(0.8);

// ── FULL MATRIX ──
doc.fontSize(16).fillColor(DARK).font('Helvetica-Bold').text('Full Test Matrix');
doc.moveDown(0.4);
doc.font('Helvetica');
doc.fontSize(9).fillColor(GRAY).text('All tests: type=image-to-video, full_access=true, 9:16, 5s, 720p, webhook_url included');
doc.moveDown(0.4);

const fullRows = [
  ['#', 'Mode', 'Images Field', '#', 'Audio', 'Result'],
  ['1', 'ugc', 'products[]', '1', 'none', '200'],
  ['2', 'ugc', 'products[]+influencers[]', '1+1', 'none', '200'],
  ['3', 'ugc', 'products[]', '2', 'none', '200'],
  ['4', 'ugc', 'products[]', '1', 'audios[] x1', '200'],
  ['5', 'ugc', 'products[]+influencers[]', '1+1', 'audios[] x1', '200'],
  ['6', 'ugc', 'products[]', '2', 'audios[] x1', '200'],
  ['7', 'ugc', 'images[]', '2', 'audios[] x1', '400'],
  ['8', 'multi_ref', 'images[]', '1', 'none', '200'],
  ['9', 'multi_ref', 'images[]', '1', 'audios[] x1', '200'],
  ['10', 'multi_ref', 'images[]', '2', 'none', '503'],
  ['11', 'multi_ref', 'images[]', '2', 'audios[] x1', '503'],
  ['12', 'multi_ref', 'image[] (singular)', '2', 'none', '200*'],
  ['13', 'multi_ref', 'image[] (singular)', '2', 'audio[] (singular)', '200*'],
  ['14', 'multi_ref', 'products[]+influencers[]', '1+1', 'none', '200'],
  ['15', 'multi_ref', 'products[]+influencers[]', '1+1', 'audios[] x1', '500'],
  ['16', 'lipsync', 'images[]', '1', 'lipsyncing_audio', '200'],
  ['17', 'lipsync', 'images[]', '2', 'lipsyncing_audio', '503'],
  ['18', 'multi_frame', 'images[]', '1', 'audios[] x1', '200'],
  ['19', 'multi_frame', 'images[]', '2', 'audios[] x1', '503'],
  ['20', 'first_n_last', 'first+last_frame_image', '2', 'audios[] x1', '503'],
];

const fColW = [25, 75, 155, 25, 105, 45];
const fColX = [50];
for (let i = 1; i < fColW.length; i++) fColX.push(fColX[i-1] + fColW[i-1]);

// Check if we need a new page
if (doc.y > 400) { doc.addPage(); }

ty = doc.y;
const rowH = 17;

fullRows.forEach((row, ri) => {
  if (ty + rowH > 740) {
    doc.addPage();
    ty = 50;
  }

  const bg = ri === 0 ? DARK : (ri % 2 === 0 ? BG : '#FFFFFF');
  doc.rect(50, ty, W, rowH).fill(bg);

  row.forEach((cell, ci) => {
    let color = ri === 0 ? '#FFFFFF' : DARK;
    let font = ri === 0 ? 'Helvetica-Bold' : 'Helvetica';

    if (ri > 0 && ci === 5) {
      if (cell === '200') { color = GREEN; font = 'Helvetica-Bold'; }
      else if (cell === '200*') { color = '#EA580C'; font = 'Helvetica-Bold'; }
      else if (cell === '503' || cell === '500') { color = RED; font = 'Helvetica-Bold'; }
      else if (cell === '400') { color = '#EA580C'; font = 'Helvetica-Bold'; }
    }

    doc.font(font).fontSize(7.5).fillColor(color)
      .text(cell, fColX[ci] + 3, ty + 4, { width: fColW[ci] - 6 });
  });
  ty += rowH;
});

doc.rect(50, doc.y, W, ty - doc.y).strokeColor('#D1D5DB').stroke();
doc.y = ty + 3;
doc.font('Helvetica').fontSize(7.5).fillColor(GRAY).text('* 200 but backend ignores singular field names \u2014 images not actually used in generation');
doc.moveDown(1);

// ── SECONDARY ISSUES ──
if (doc.y > 550) doc.addPage();
doc.fontSize(16).fillColor(DARK).font('Helvetica-Bold').text('Secondary Issues');
doc.moveDown(0.4);
doc.font('Helvetica').fontSize(10).fillColor(DARK);

doc.font('Helvetica-Bold').text('1. Singular field names bypass validation');
doc.font('Helvetica').fontSize(9.5)
  .text('Using "image" instead of "images" returns 200 with 2+ URLs, but the backend ignores the field \u2014 images are silently dropped. The gateway accepts unknown fields without error.');
doc.moveDown(0.5);

doc.font('Helvetica-Bold').fontSize(10).text('2. False "restricted material" error');
doc.font('Helvetica').fontSize(9.5)
  .text('multi_reference + products[]/influencers[] + audios[] returns HTTP 500 "restricted material" on completely clean images (water bottle, stock photo). Same images + audio work in ugc mode.');
doc.moveDown(0.5);

doc.font('Helvetica-Bold').fontSize(10).text('3. 503 jobs complete on backend');
doc.font('Helvetica').fontSize(9.5)
  .text('Confirmed via webhook callbacks: every 503 job generated a video and sent a COMPLETED webhook. The requestId is just lost. Callers who retry on 503 create duplicate jobs and waste credits.');
doc.moveDown(1);

// ── EXPECTED BEHAVIOR ──
doc.fontSize(16).fillColor(DARK).font('Helvetica-Bold').text('Expected Behavior');
doc.moveDown(0.4);
const expY = doc.y;
doc.rect(50, expY, W, 45).fill(LIGHT_BLUE).stroke();
doc.rect(50, expY, W, 45).lineWidth(1).strokeColor(BLUE).stroke();
doc.font('Helvetica').fontSize(10).fillColor(BLUE);
doc.text('/queue should return HTTP 200 with {"success": true, "requestId": "..."} immediately after accepting the job, regardless of the number of images. URL validation and content checks should happen asynchronously \u2014 same as ugc mode already does.', 62, expY + 8, { width: W - 24 });
doc.y = expY + 55;
doc.moveDown(0.8);

// ── HYPOTHESIS ──
doc.fontSize(16).fillColor(DARK).font('Helvetica-Bold').text('Root Cause Hypothesis');
doc.moveDown(0.4);
doc.font('Helvetica').fontSize(9.5).fillColor(DARK);
doc.text('The gateway downloads and validates all images[] URLs synchronously before returning a response. When there are 2+ images, this exceeds the gateway timeout and returns 503 \u2014 even though the job was already passed to the queue. ugc mode routes products[]/influencers[] through a different code path that handles them asynchronously, which is why it never returns 503.');
doc.moveDown(1.5);

// ── FOOTER ──
doc.moveTo(50, doc.y).lineTo(562, doc.y).strokeColor('#D1D5DB').stroke();
doc.moveDown(0.3);
doc.fontSize(8).fillColor(GRAY).text('Tested by Claude Code  |  API: apireq.enhancor.ai/api/enhancor-ugc-full-access/v1  |  April 14, 2026', { align: 'center' });

doc.end();
out.on('finish', () => console.log('PDF saved to api-bug-report.pdf'));
