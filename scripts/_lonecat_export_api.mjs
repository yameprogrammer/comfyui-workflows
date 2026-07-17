/**
 * Export Lonecat UI workflow → ComfyUI API format using the REAL frontend
 * graphToPrompt (same as Save (API Format)), then optionally queue a smoke run.
 *
 *   node scripts/_lonecat_export_api.mjs           # export only
 *   node scripts/_lonecat_export_api.mjs --queue    # export + queue smoke
 */
import fs from "fs";
import path from "path";
import { createRequire } from "module";
import http from "http";

const require = createRequire(import.meta.url);
const puppeteer = require("puppeteer-core");

const WF_UI =
  process.env.LONECAT_WF ||
  "F:/ComfyUI_windows_portable/ComfyUI/user/default/workflows/Lonecat's AIO Z-Image ver 17.json";
const OUT_API =
  process.env.LONECAT_API_OUT ||
  "F:/ComfyUI_workflows/agent_custom/workflows/agent/Lonecat_AIO_Z-Image_ver17.api.json";
const COMFY = process.env.COMFY_URL || "http://127.0.0.1:8188";
const CHROME =
  process.env.CHROME_PATH ||
  "C:/Program Files/Google/Chrome/Application/chrome.exe";
const DO_QUEUE = process.argv.includes("--queue");

const SMOKE_PROMPT =
  process.env.SMOKE_PROMPT ||
  "cinematic photoreal film still, medium shot waist-up, mid-20s Korean woman, oval face, warm dark brown eyes, collarbone-length dark soft waves, natural skin pores freckles, cream knit cardigan over white blouse, light wash jeans, convenience store checkout, translucent plastic shopping bag in both hands, stocked snack shelves fluorescent light behind, rain on glass door outside, 35mm eye level, film grain, sharp on face and bag";

function httpJson(method, urlPath, body) {
  return new Promise((resolve, reject) => {
    const u = new URL(urlPath, COMFY);
    const data = body ? JSON.stringify(body) : null;
    const req = http.request(
      {
        hostname: u.hostname,
        port: u.port,
        path: u.pathname + u.search,
        method,
        headers: data
          ? { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(data) }
          : {},
      },
      (res) => {
        const chunks = [];
        res.on("data", (c) => chunks.push(c));
        res.on("end", () => {
          const raw = Buffer.concat(chunks).toString("utf8");
          try {
            resolve({ status: res.statusCode, json: raw ? JSON.parse(raw) : null, raw });
          } catch {
            resolve({ status: res.statusCode, json: null, raw });
          }
        });
      }
    );
    req.on("error", reject);
    if (data) req.write(data);
    req.end();
  });
}

function patchPrompt(api, promptText) {
  // Prefer empty easy positive / long CLIP text that looks like main positive.
  // Do NOT rewrite the graph — only swap string widget values.
  let patched = 0;
  for (const [id, node] of Object.entries(api)) {
    const inputs = node.inputs || {};
    if (node.class_type === "easy positive" && typeof inputs.positive === "string") {
      // empty or very short = user scene prompt slot
      if (!inputs.positive.trim() || inputs.positive.length < 8) {
        inputs.positive = promptText;
        patched++;
        console.log("patch easy positive", id);
      }
    }
    if (node.class_type === "CLIPTextEncode" && typeof inputs.text === "string") {
      // leave detailer prompts alone; only blank encodes
      if (!inputs.text.trim()) {
        // skip — positive usually via bus already filled by frontend
      }
    }
    // Seed nodes
    if (typeof inputs.seed === "number" || typeof inputs.seed === "string") {
      // leave unless env forces
      if (process.env.SMOKE_SEED) {
        inputs.seed = Number(process.env.SMOKE_SEED);
        patched++;
      }
    }
  }
  // If no empty easy positive found, inject into the longest easy positive that isn't "Quality Prompt" style short tags
  if (patched === 0) {
    for (const [id, node] of Object.entries(api)) {
      if (node.class_type === "easy positive" && typeof node.inputs?.positive === "string") {
        const p = node.inputs.positive;
        if (p.includes("photorealistic") && p.length < 80) {
          // quality tags only — prepend scene
          node.inputs.positive = promptText + ", " + p;
          patched++;
          console.log("patch quality easy positive", id);
          break;
        }
      }
    }
  }
  // Last resort: set Final Prompt-like ShowText is not executable; find CLIPTextEncode with long cinematic template and replace
  if (patched === 0) {
    let best = null;
    for (const [id, node] of Object.entries(api)) {
      if (node.class_type === "CLIPTextEncode" && typeof node.inputs?.text === "string") {
        const t = node.inputs.text;
        if (t.length > 100 && /portrait|cinematic|woman/i.test(t)) {
          if (!best || t.length > best.len) best = { id, len: t.length };
        }
      }
    }
    if (best) {
      api[best.id].inputs.text = promptText;
      patched++;
      console.log("patch CLIPTextEncode", best.id);
    }
  }
  return patched;
}

async function main() {
  const ui = JSON.parse(fs.readFileSync(WF_UI, "utf8"));
  console.log("UI nodes:", (ui.nodes || []).length);

  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: "new",
    args: ["--no-sandbox", "--disable-gpu"],
  });
  const page = await browser.newPage();
  page.setDefaultTimeout(180000);
  page.on("console", (m) => {
    if (m.type() === "error") console.log("BROWSER_ERR:", m.text().slice(0, 200));
  });

  console.log("Open", COMFY);
  await page.goto(COMFY, { waitUntil: "networkidle2", timeout: 120000 });
  await page.waitForFunction(
    () => window.app && typeof window.app.graphToPrompt === "function",
    { timeout: 120000 }
  );

  // load + convert entirely inside page; return STRING to avoid CDP object issues
  const result = await page.evaluate(async (graph) => {
    await window.app.loadGraphData(graph);
    await new Promise((r) => setTimeout(r, 5000));
    const p = await window.app.graphToPrompt();
    const output = p.output || {};
    return {
      count: Object.keys(output).length,
      json: JSON.stringify(output),
    };
  }, ui);

  await browser.close();

  console.log("API nodes from graphToPrompt:", result.count);
  if (!result.count) {
    console.error("Empty API prompt — abort");
    process.exit(2);
  }

  fs.mkdirSync(path.dirname(OUT_API), { recursive: true });
  fs.writeFileSync(OUT_API, result.json, "utf8");
  console.log("Saved API format:", OUT_API);

  // port index for humans
  const api = JSON.parse(result.json);
  const ports = [];
  for (const [id, node] of Object.entries(api)) {
    const interesting = {};
    for (const [k, v] of Object.entries(node.inputs || {})) {
      if (typeof v === "string" || typeof v === "number" || typeof v === "boolean") {
        if (
          /text|prompt|positive|negative|seed|denoise|steps|cfg|filename|image/i.test(k) ||
          (typeof v === "string" && v.length > 15)
        ) {
          interesting[k] =
            typeof v === "string" && v.length > 100 ? v.slice(0, 100) + "…" : v;
        }
      }
    }
    if (Object.keys(interesting).length) {
      ports.push({ id, class_type: node.class_type, inputs: interesting });
    }
  }
  const portsPath = OUT_API.replace(/\.json$/i, ".ports.json");
  fs.writeFileSync(portsPath, JSON.stringify(ports, null, 2), "utf8");
  console.log("Ports index:", portsPath, "n=", ports.length);

  if (!DO_QUEUE) {
    console.log("Export only. Re-run with --queue to POST /prompt.");
    return;
  }

  // Minimal caller: clone API json, patch prompt strings, POST /prompt
  const prompt = JSON.parse(result.json);
  const n = patchPrompt(prompt, SMOKE_PROMPT);
  console.log("patched fields:", n);

  const q = await httpJson("POST", "/prompt", { prompt });
  console.log("queue status", q.status, q.json);
  if (!q.json?.prompt_id) {
    console.error("Queue failed", q.raw?.slice(0, 1000));
    process.exit(3);
  }
  const promptId = q.json.prompt_id;
  console.log("prompt_id", promptId);

  // poll history
  const outDir =
    "D:/뮤직비디오 작업/소나기_v2/03_키프레임/v3_smoke_lonecat_v17";
  fs.mkdirSync(outDir, { recursive: true });

  const deadline = Date.now() + 15 * 60 * 1000;
  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 3000));
    const h = await httpJson("GET", `/history/${promptId}`);
    const entry = h.json?.[promptId];
    if (!entry) {
      process.stdout.write(".");
      continue;
    }
    const status = entry.status?.status_str;
    console.log("\nstatus", status);
    if (status === "error") {
      console.error(JSON.stringify(entry.status, null, 2).slice(0, 2000));
      process.exit(4);
    }
    const outputs = entry.outputs || {};
    // find first image
    for (const [nid, o] of Object.entries(outputs)) {
      const images = o.images || [];
      if (!images.length) continue;
      const img = images[0];
      const viewPath = `/view?filename=${encodeURIComponent(img.filename)}&subfolder=${encodeURIComponent(img.subfolder || "")}&type=${encodeURIComponent(img.type || "output")}`;
      const bin = await new Promise((resolve, reject) => {
        const u = new URL(viewPath, COMFY);
        http
          .get(u, (res) => {
            const chunks = [];
            res.on("data", (c) => chunks.push(c));
            res.on("end", () => resolve(Buffer.concat(chunks)));
          })
          .on("error", reject);
      });
      const dest = path.join(outDir, "S01_lonecat_v17_api_smoke.png");
      fs.writeFileSync(dest, bin);
      console.log("OK saved", dest, "from node", nid);
      fs.writeFileSync(
        path.join(outDir, "S01_lonecat_v17_api_smoke.meta.json"),
        JSON.stringify(
          {
            workflow_api: OUT_API,
            prompt_id: promptId,
            prompt: SMOKE_PROMPT,
            node: nid,
            image: img,
          },
          null,
          2
        ),
        "utf8"
      );
      return;
    }
    if (status === "success") {
      console.error("success but no images in outputs", Object.keys(outputs));
      process.exit(5);
    }
  }
  console.error("timeout waiting for history");
  process.exit(6);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
