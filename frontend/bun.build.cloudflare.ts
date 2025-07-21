import { build } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// Build configuration for Cloudflare Workers
async function buildForCloudflare() {
  console.log("Building for Cloudflare Workers...");

  await build({
    plugins: [react()],
    build: {
      outDir: "dist",
      emptyOutDir: true,
      sourcemap: false,
      minify: true,
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ["react", "react-dom", "react-router-dom"],
            utils: ["axios", "clsx", "tailwind-merge"],
          },
        },
      },
    },
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    define: {
      "process.env.NODE_ENV": JSON.stringify("production"),
    },
  });

  console.log("Build completed!");
}

buildForCloudflare().catch((err) => {
  console.error("Build failed:", err);
  process.exit(1);
});
