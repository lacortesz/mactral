import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    environment: "node",
    include: ["tests/**/*.test.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
      include: ["src/lib/**/*.ts"],
      // currentUser.ts y prisma.ts son adaptadores delgados sobre next/headers
      // y el singleton de PrismaClient: no tienen lógica propia que probar de
      // forma aislada sin un runtime de Next.js o una base de datos real.
      exclude: ["src/lib/currentUser.ts", "src/lib/prisma.ts"],
      thresholds: {
        lines: 90,
        statements: 90,
        functions: 90,
        branches: 80,
      },
    },
  },
});
