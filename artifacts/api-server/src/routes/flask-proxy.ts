import { Router, type IRouter, type Request, type Response } from "express";
import * as http from "http";

const router: IRouter = Router();

const FLASK_PORT = 5000;

router.all("{*path}", (req: Request, res: Response) => {
  const options: http.RequestOptions = {
    hostname: "localhost",
    port: FLASK_PORT,
    path: "/api" + req.path + (req.url.includes("?") ? req.url.slice(req.url.indexOf("?")) : ""),
    method: req.method,
    headers: {
      ...req.headers,
      host: `localhost:${FLASK_PORT}`,
    },
  };

  const proxy = http.request(options, (flaskRes) => {
    res.status(flaskRes.statusCode || 500);
    Object.entries(flaskRes.headers).forEach(([key, value]) => {
      if (value !== undefined) res.setHeader(key, value);
    });
    flaskRes.pipe(res, { end: true });
  });

  proxy.on("error", () => {
    res.status(502).json({ error: "Flask backend unavailable" });
  });

  if (req.body && Object.keys(req.body).length > 0) {
    const bodyStr = JSON.stringify(req.body);
    proxy.setHeader("Content-Length", Buffer.byteLength(bodyStr));
    proxy.write(bodyStr);
  } else if (req.readable) {
    req.pipe(proxy, { end: true });
    return;
  }

  proxy.end();
});

export default router;
