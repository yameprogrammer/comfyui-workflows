/**
 * Export a WAN22 human UI workflow (with subgraphs) via Comfy graphToPrompt → API JSON.
 *
 *   node scripts/_export_wan22_subgraph_preset.mjs face_enhance
 *   node scripts/_export_wan22_subgraph_preset.mjs upscale
 *   node scripts/_export_wan22_subgraph_preset.mjs upscale_face
 *
 * Requires ComfyUI at COMFY_URL (default http://127.0.0.1:8188) and Chrome.
 */
import fs from "fs";
import path from "path";
import { createRequire } from "module";
import http from "http";

const require = createRequire(import.meta.url);
const puppeteer = require("puppeteer-core");

const ROOT = "F:/ComfyUI_workflows/agent_custom";
const COMFY = process.env.COMFY_URL || "http://127.0.0.1:8188";
const CHROME =
  process.env.CHROME_PATH ||
  "C:/Program Files/Google/Chrome/Application/chrome.exe";

const PRESETS = {
  face_enhance: {
    ui: `${ROOT}/workflows/human/wan22/wan22_face_enhance.json`,
    api: `${ROOT}/workflows/agent/presets/wan22_face_enhance.api.json`,
    ports: `${ROOT}/workflows/agent/presets/wan22_face_enhance.ports.json`,
    name: "wan22_face_enhance",
  },
  upscale: {
    ui: `${ROOT}/workflows/human/wan22/wan22_upscale.json`,
    api: `${ROOT}/workflows/agent/presets/wan22_upscale.api.json`,
    ports: `${ROOT}/workflows/agent/presets/wan22_upscale.ports.json`,
    name: "wan22_upscale",
  },
  upscale_face: {
    ui: `${ROOT}/workflows/human/wan22/wan22_upscale_face_enhance.json`,
    api: `${ROOT}/workflows/agent/presets/wan22_upscale_face_enhance.api.json`,
    ports: `${ROOT}/workflows/agent/presets/wan22_upscale_face_enhance.ports.json`,
    name: "wan22_upscale_face_enhance",
  },
};

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
          ? {
              "Content-Type": "application/json",
              "Content-Length": Buffer.byteLength(data),
            }
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

function draftPorts(api, presetName) {
  const ports = {};
  for (const [id, node] of Object.entries(api)) {
    const ct = node.class_type || "";
    const inp = node.inputs || {};
    if (ct === "VHS_LoadVideo" || ct === "LoadVideo") {
      if ("video" in inp) ports.input_video = { node: id, key: "video", copy_to_input_dir: true };
      else if ("file" in inp) ports.input_video = { node: id, key: "file", copy_to_input_dir: true };
    }
    if (ct === "LoadImage" && !ports.input_image) {
      ports.input_image = { node: id, key: "image", copy_to_input_dir: true };
    }
    if (ct === "VHS_VideoCombine" && "filename_prefix" in inp) {
      ports.filename_prefix = { node: id, key: "filename_prefix", optional: true };
    }
    if (ct === "SaveVideoWithPath" || ct === "SaveVideo") {
      if ("filename_prefix" in inp)
        ports.filename_prefix = { node: id, key: "filename_prefix", optional: true };
    }
  }
  return {
    preset: presetName,
    workflow_api: `presets/${presetName}.api.json`,
    description: `Exported from human wan22 pack via graphToPrompt (${presetName})`,
    ports,
    defaults: { filename_prefix: presetName },
    notes: [
      "Subgraph-expanded API export. Verify ports after first smoke.",
      "Video loaders may need copy_to_input_dir + Comfy input folder.",
    ],
  };
}

async function main() {
  const key = (process.argv[2] || "face_enhance").toLowerCase();
  const cfg = PRESETS[key];
  if (!cfg) {
    console.error("Unknown preset. Choose:", Object.keys(PRESETS).join(", "));
    process.exit(2);
  }
  if (!fs.existsSync(cfg.ui)) {
    console.error("UI missing", cfg.ui);
    process.exit(3);
  }
  const ui = JSON.parse(fs.readFileSync(cfg.ui, "utf8"));
  console.log("UI nodes", (ui.nodes || []).length, "→", cfg.name);

  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: "new",
    args: ["--no-sandbox", "--disable-gpu"],
  });
  const page = await browser.newPage();
  page.setDefaultTimeout(240000);
  page.on("console", (m) => {
    if (m.type() === "error") console.log("BROWSER_ERR:", m.text().slice(0, 240));
  });

  console.log("Open", COMFY);
  await page.goto(COMFY, { waitUntil: "networkidle2", timeout: 120000 });
  await page.waitForFunction(
    () => window.app && typeof window.app.graphToPrompt === "function",
    { timeout: 120000 }
  );

  const result = await page.evaluate(async (graph) => {
    await window.app.loadGraphData(graph);
    await new Promise((r) => setTimeout(r, 8000));
    const p = await window.app.graphToPrompt();
    const output = p.output || {};
    return { count: Object.keys(output).length, json: JSON.stringify(output) };
  }, ui);

  await browser.close();
  console.log("API nodes", result.count);
  if (!result.count) {
    console.error("Empty graphToPrompt — abort");
    process.exit(4);
  }

  fs.mkdirSync(path.dirname(cfg.api), { recursive: true });
  fs.writeFileSync(cfg.api, JSON.stringify(JSON.parse(result.json), null, 2), "utf8");
  const ports = draftPorts(JSON.parse(result.json), cfg.name);
  fs.writeFileSync(cfg.ports, JSON.stringify(ports, null, 2), "utf8");
  console.log("Saved", cfg.api);
  console.log("Saved", cfg.ports, "ports=", Object.keys(ports.ports || {}));

  // optional queue smoke not default — graphs are heavy
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
