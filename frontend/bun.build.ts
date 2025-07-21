#!/usr/bin/env bun
import { $ } from "bun";

console.log("🏗️  Building React app with Vite...");

// Build using Vite
await $`bunx vite build`;

console.log("✅ Build complete!");