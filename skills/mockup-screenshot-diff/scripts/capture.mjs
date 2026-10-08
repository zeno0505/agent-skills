#!/usr/bin/env node
// capture.mjs — capture same-state screenshots + computed styles for one side (mockup or app).
//
// Usage:
//   node capture.mjs <states.json> --side mockup|app --out <dir> [--full-page] [--headed]
//
// Requires Playwright resolvable from the current directory (npm i -D playwright, or
// playwright-chromium) with a Chromium browser installed (npx playwright install chromium).
// Output: <dir>/<state>-<width>.png and <dir>/styles.json
// Optional config keys: "height" (viewport height, default 900), "deviceScaleFactor" (default 1),
// "stepTimeoutMs" (per action, default 10000).
//   styles.json = { "<state>-<width>": { "<pair>": { "<prop>": "<value>" | null } } }
// A state that cannot be reached is recorded under "_errors" and skipped — never faked.
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

function arg(name, def = null) {
  const i = process.argv.indexOf(name);
  return i > -1 ? process.argv[i + 1] : def;
}
const statesFile = process.argv[2];
const side = arg("--side");
const outDir = arg("--out");
const fullPage = process.argv.includes("--full-page");
const headed = process.argv.includes("--headed");
if (!statesFile || !["mockup", "app"].includes(side) || !outDir) {
  console.error("usage: capture.mjs <states.json> --side mockup|app --out <dir> [--full-page] [--headed]");
  process.exit(2);
}

const require = createRequire(path.join(process.cwd(), "noop.js"));
let chromium;
for (const mod of ["playwright", "playwright-chromium", "@playwright/test"]) {
  try { ({ chromium } = require(mod)); break; } catch { /* try next */ }
}
if (!chromium) {
  console.error("Playwright not found from cwd. Install it in your project: npm i -D playwright && npx playwright install chromium");
  process.exit(2);
}

const cfg = JSON.parse(fs.readFileSync(statesFile, "utf8"));
const base = cfg[side]?.baseUrl;
if (!base) { console.error(`missing ${side}.baseUrl in ${statesFile}`); process.exit(2); }
const widths = cfg.widths?.length ? cfg.widths : [1440];
fs.mkdirSync(outDir, { recursive: true });

function join(baseUrl, p = "") {
  if (!p) return baseUrl;
  if (/^[a-z]+:\/\//i.test(p)) return p;
  if (p.startsWith("#") || p.startsWith("?")) return baseUrl.replace(/[#?].*$/, "") + p;
  return baseUrl.replace(/\/$/, "") + (p.startsWith("/") ? p : "/" + p);
}

async function runSteps(page, steps = []) {
  for (const s of steps) {
    if (s.click) await page.click(s.click);
    else if (s.hover) await page.hover(s.hover);
    else if (s.press) await page.keyboard.press(s.press);
    else if (s.scroll) await page.locator(s.scroll).scrollIntoViewIfNeeded();
    else if (s.waitFor) await page.waitForSelector(s.waitFor);
    else if (s.wait) await page.waitForTimeout(Number(s.wait));
    else throw new Error(`unknown step ${JSON.stringify(s)} (allowed: click, hover, press, scroll, waitFor, wait)`);
  }
}

const browser = await chromium.launch({ headless: !headed });
const styles = { _errors: {} };
let shots = 0;
try {
  for (const width of widths) {
    const ctx = await browser.newContext({
      viewport: { width, height: cfg.height || 900 },
      deviceScaleFactor: cfg.deviceScaleFactor || 1,
    });
    for (const st of cfg.states) {
      const key = `${st.name}-${width}`;
      const page = await ctx.newPage();
      page.setDefaultTimeout(Number(cfg.stepTimeoutMs || 10000));
      try {
        const spec = st[side] || {};
        await page.goto(join(base, spec.path), { waitUntil: "networkidle" });
        await runSteps(page, spec.steps);
        await page.evaluate(() => document.fonts && document.fonts.ready);
        await page.screenshot({ path: path.join(outDir, `${key}.png`), fullPage });
        shots++;
        const pairs = {};
        for (const p of st.styles || []) {
          const sel = p[side];
          pairs[p.pair] = await page.evaluate(({ sel, props }) => {
            const el = sel && document.querySelector(sel);
            if (!el) return null;
            const cs = getComputedStyle(el);
            return Object.fromEntries(props.map((k) => [k, cs.getPropertyValue(k)]));
          }, { sel, props: p.props || [] });
        }
        styles[key] = pairs;
      } catch (e) {
        styles._errors[key] = String(e.message || e).split("\n")[0];
        console.error(`[capture] ${side} ${key}: not captured — ${styles._errors[key]}`);
      } finally {
        await page.close();
      }
    }
    await ctx.close();
  }
} finally {
  await browser.close();
}
fs.writeFileSync(path.join(outDir, "styles.json"), JSON.stringify(styles, null, 2));
const errs = Object.keys(styles._errors).length;
console.log(`[capture] ${side}: ${shots} screenshot(s), ${errs} not captured → ${outDir}`);
process.exit(errs ? 1 : 0);
