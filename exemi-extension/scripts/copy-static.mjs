import { cp, mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";

const root = new URL("..", import.meta.url).pathname;
const dist = join(root, "dist");

async function ensureDir(path) {
  await mkdir(path, { recursive: true });
}

async function main() {
  await ensureDir(dist);
  await ensureDir(join(dist, "icons"));

  // Copy manifest and icons into dist so you can "Load unpacked" from dist/.
  await cp(join(root, "icons", "exemi-48.png"), join(dist, "icons", "exemi-48.png"));

  const manifestRaw = await readFile(join(root, "manifest.json"), "utf8");
  await writeFile(join(dist, "manifest.json"), manifestRaw, "utf8");

  // Optional: keep the non-bundled assets if you still use them later.
  // (Not required for current React bundle.)
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

