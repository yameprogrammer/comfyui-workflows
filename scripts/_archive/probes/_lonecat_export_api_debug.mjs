import fs from "fs";
import { createRequire } from "module";
const require = createRequire(import.meta.url);
const puppeteer = require("puppeteer-core");

const WF_UI =
  "F:/ComfyUI_windows_portable/ComfyUI/user/default/workflows/Lonecat's AIO Z-Image ver 17.json";
const COMFY = "http://127.0.0.1:8188";
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";

const ui = JSON.parse(fs.readFileSync(WF_UI, "utf8"));
const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: "new",
  args: ["--no-sandbox"],
});
const page = await browser.newPage();
page.on("console", (msg) => console.log("BROWSER:", msg.type(), msg.text()));
page.on("pageerror", (err) => console.log("PAGEERROR:", err.message));

await page.goto(COMFY, { waitUntil: "networkidle2", timeout: 120000 });
await page.waitForFunction(() => window.app && window.app.loadGraphData, {
  timeout: 120000,
});

const meta = await page.evaluate(async (graph) => {
  const out = { steps: [] };
  try {
    out.appKeys = Object.keys(window.app || {}).slice(0, 40);
    out.hasGraphToPrompt = typeof window.app.graphToPrompt === "function";
    out.hasQueuePrompt = typeof window.app.queuePrompt === "function";
    await window.app.loadGraphData(graph);
    out.steps.push("loaded");
    await new Promise((r) => setTimeout(r, 5000));
    const g = window.app.graph;
    out.nodeCount = g ? (g._nodes || g.nodes || []).length : -1;
    out.steps.push("count=" + out.nodeCount);

    // try graphToPrompt
    let p = null;
    try {
      p = await window.app.graphToPrompt();
      out.promptType = typeof p;
      out.promptKeys = p && typeof p === "object" ? Object.keys(p) : [];
      out.outputType = p && p.output ? typeof p.output : null;
      out.outputKeys =
        p && p.output && typeof p.output === "object"
          ? Object.keys(p.output).length
          : 0;
      // maybe structure is different
      if (p && !p.output && p.prompt) {
        out.altPromptKeys = Object.keys(p.prompt).length;
      }
      // string sample
      out.sample = JSON.stringify(p).slice(0, 500);
    } catch (e) {
      out.gtpError = String(e && e.stack ? e.stack : e);
    }

    // try LiteGraph serialize API style
    try {
      if (window.graphToPrompt) {
        out.hasGlobalGraphToPrompt = true;
      }
    } catch {}

    // ComfyUI frontend API in newer versions
    try {
      const api = window.app.api || window.api;
      out.hasApi = !!api;
    } catch {}

    return out;
  } catch (e) {
    return { fatal: String(e && e.stack ? e.stack : e) };
  }
}, ui);

console.log(JSON.stringify(meta, null, 2));
await browser.close();
