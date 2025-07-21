import { $ } from "bun";
import { watch } from "fs";
import { join } from "path";

// For now, let's use Bun to run the React dev server with proper handling
// This will compile TypeScript/JSX on the fly

const proc = Bun.spawn(["bunx", "vite"], {
  cwd: process.cwd(),
  stdio: ["inherit", "inherit", "inherit"],
  env: {
    ...process.env,
    PORT: "3000",
    REACT_APP_API_URL: "http://localhost:8000/api/v1"
  }
});

console.log("🚀 Starting development server...");
console.log("📍 Frontend: http://localhost:3000");
console.log("🔄 API Proxy: http://localhost:8000");

// Handle process termination
process.on("SIGINT", () => {
  proc.kill();
  process.exit(0);
});