import { createReadStream } from "node:fs";
import { readFile, stat } from "node:fs/promises";
import { createServer, request } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

const port = Number(process.env.PORT || 80);
const apiTarget = new URL(process.env.API_TARGET || "http://activity-api:8008");
const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "dist");

const contentTypes = new Map([
  [".css", "text/css; charset=utf-8"],
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".png", "image/png"],
  [".svg", "image/svg+xml"],
  [".ico", "image/x-icon"],
  [".webp", "image/webp"],
]);

createServer(async (req, res) => {
  if (!req.url) {
    res.writeHead(400);
    res.end("Bad Request");
    return;
  }

  if (req.url.startsWith("/api/")) {
    proxyApi(req, res);
    return;
  }

  await serveStatic(req.url, res);
}).listen(port, "0.0.0.0", () => {
  console.log(`Activity client listening on 0.0.0.0:${port}`);
});

function proxyApi(req, res) {
  const target = new URL(req.url ?? "/", apiTarget);
  const proxyReq = request(
    {
      hostname: target.hostname,
      port: target.port || 80,
      path: `${target.pathname}${target.search}`,
      method: req.method,
      headers: {
        ...req.headers,
        host: apiTarget.host,
      },
    },
    (proxyRes) => {
      res.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
      proxyRes.pipe(res);
    },
  );

  proxyReq.on("error", () => {
    res.writeHead(502, { "content-type": "text/plain; charset=utf-8" });
    res.end("Activity API is unavailable");
  });

  req.pipe(proxyReq);
}

async function serveStatic(url, res) {
  const pathname = decodeURIComponent(new URL(url, "http://localhost").pathname);
  const safePath = path.normalize(pathname).replace(/^(\.\.[/\\])+/, "");
  let filePath = path.join(root, safePath);

  if (!filePath.startsWith(root)) {
    res.writeHead(403);
    res.end("Forbidden");
    return;
  }

  try {
    const info = await stat(filePath);
    if (info.isDirectory()) {
      filePath = path.join(filePath, "index.html");
    }
    await stat(filePath);
  } catch {
    filePath = path.join(root, "index.html");
  }

  const ext = path.extname(filePath).toLowerCase();
  res.writeHead(200, {
    "content-type": contentTypes.get(ext) || "application/octet-stream",
  });
  createReadStream(filePath).pipe(res);
}
