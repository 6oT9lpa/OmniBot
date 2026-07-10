import { createReadStream } from "node:fs";
import { readFile, stat } from "node:fs/promises";
import { createServer, request } from "node:http";
import path from "node:path";
import { Transform } from "node:stream";
import { fileURLToPath } from "node:url";

const port = Number(process.env.PORT || 80);
const apiTarget = new URL(process.env.API_TARGET || "http://activity-api:8008");
const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "dist");
const maxApiBodyBytes = 128 * 1024;
const allowedApiMethods = new Set(["GET", "POST", "PUT", "PATCH", "DELETE"]);
const forwardedRequestHeaders = new Set([
  "accept",
  "accept-language",
  "authorization",
  "content-length",
  "content-type",
  "user-agent",
]);
const hopByHopHeaders = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

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
  try {
    if (!req.url) {
      sendText(res, 400, "Bad Request");
      return;
    }

    if (req.url.startsWith("/api/")) {
      proxyApi(req, res);
      return;
    }

    if (!new Set(["GET", "HEAD"]).has(req.method || "GET")) {
      res.setHeader("allow", "GET, HEAD");
      sendText(res, 405, "Method Not Allowed");
      return;
    }
    await serveStatic(req.url, res, req.method);
  } catch {
    // Malformed URL encodings and filesystem errors must not terminate the server.
    if (!res.headersSent) sendText(res, 400, "Bad Request");
    else res.end();
  }
}).listen(port, "0.0.0.0", () => {
  console.log(`Activity client listening on 0.0.0.0:${port}`);
});

function proxyApi(req, res) {
  if (!allowedApiMethods.has(req.method || "")) {
    res.setHeader("allow", [...allowedApiMethods].join(", "));
    sendText(res, 405, "Method Not Allowed");
    return;
  }
  const contentLength = Number(req.headers["content-length"] || 0);
  if (!Number.isFinite(contentLength) || contentLength < 0 || contentLength > maxApiBodyBytes) {
    sendText(res, 413, "Request body is too large");
    req.resume();
    return;
  }

  const target = new URL(req.url ?? "/", apiTarget);
  const proxyReq = request(
    {
      hostname: target.hostname,
      port: target.port || 80,
      path: `${target.pathname}${target.search}`,
      method: req.method,
      headers: {
        ...selectForwardHeaders(req.headers),
        host: apiTarget.host,
      },
    },
    (proxyRes) => {
      res.writeHead(proxyRes.statusCode || 502, sanitizeResponseHeaders(proxyRes.headers));
      proxyRes.pipe(res);
    },
  );

  proxyReq.on("error", () => {
    if (!res.headersSent) sendText(res, 502, "Activity API is unavailable");
    else res.end();
  });

  const limiter = new Transform({
    transform(chunk, _encoding, callback) {
      this.received = (this.received || 0) + chunk.length;
      if (this.received > maxApiBodyBytes) {
        const error = new Error("Request body is too large");
        error.code = "BODY_TOO_LARGE";
        callback(error);
        return;
      }
      callback(null, chunk);
    },
  });
  limiter.on("error", (error) => {
    proxyReq.destroy();
    if (!res.headersSent) sendText(res, error.code === "BODY_TOO_LARGE" ? 413 : 400, "Invalid request body");
  });
  req.pipe(limiter).pipe(proxyReq);
}

async function serveStatic(url, res, method) {
  const pathname = decodeURIComponent(new URL(url, "http://localhost").pathname);
  const relativePath = pathname.replace(/^[/\\]+/, "");
  let filePath = path.resolve(root, relativePath);

  if (path.relative(root, filePath).startsWith("..") || path.isAbsolute(path.relative(root, filePath))) {
    sendText(res, 403, "Forbidden");
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
  res.writeHead(200, securityHeaders({
    "content-type": contentTypes.get(ext) || "application/octet-stream",
  }));
  if (method === "HEAD") {
    res.end();
    return;
  }
  createReadStream(filePath).pipe(res);
}

function selectForwardHeaders(headers) {
  return Object.fromEntries(
    Object.entries(headers).filter(([name]) => forwardedRequestHeaders.has(name.toLowerCase())),
  );
}

function sanitizeResponseHeaders(headers) {
  const safe = Object.fromEntries(
    Object.entries(headers).filter(([name]) => !hopByHopHeaders.has(name.toLowerCase())),
  );
  return securityHeaders({ ...safe, "cache-control": "no-store" });
}

function securityHeaders(headers = {}) {
  return {
    ...headers,
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    "permissions-policy": "camera=(), microphone=(), geolocation=()",
  };
}

function sendText(res, status, body) {
  res.writeHead(status, securityHeaders({ "content-type": "text/plain; charset=utf-8" }));
  res.end(body);
}
