/// <reference types="@cloudflare/workers-types" />
import { getAssetFromKV } from "@cloudflare/kv-asset-handler";

export interface Env {
  __STATIC_CONTENT: KVNamespace;
  VITE_GOOGLE_CLIENT_ID: string;
  VITE_API_URL: string;
  VITE_AUTH_API_URL: string;
  VITE_SUPABASE_URL: string;
  VITE_SUPABASE_ANON_KEY: string;
}

export default {
  async fetch(
    request: Request,
    env: Env,
    ctx: ExecutionContext,
  ): Promise<Response> {
    try {
      // Serve static assets
      return await getAssetFromKV(
        {
          request,
          waitUntil: ctx.waitUntil.bind(ctx),
        },
        {
          ASSET_NAMESPACE: env.__STATIC_CONTENT,
          ASSET_MANIFEST: JSON.parse(ASSET_MANIFEST),
        },
      );
    } catch (e) {
      // If asset not found, serve index.html for client-side routing
      try {
        const notFoundResponse = await getAssetFromKV(
          {
            request: new Request(
              new URL("/index.html", request.url).toString(),
            ),
            waitUntil: ctx.waitUntil.bind(ctx),
          },
          {
            ASSET_NAMESPACE: env.__STATIC_CONTENT,
            ASSET_MANIFEST: JSON.parse(ASSET_MANIFEST),
          },
        );
        return new Response(notFoundResponse.body, {
          ...notFoundResponse,
          status: 200,
        });
      } catch (err) {
        return new Response("Not Found", { status: 404 });
      }
    }
  },
};

declare const ASSET_MANIFEST: string;
