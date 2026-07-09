import { PrismaClient } from "@prisma/client";
import bcrypt from "bcryptjs";

const prisma = new PrismaClient();

async function main() {
  const email = process.env.SEED_ADMIN_EMAIL ?? "maya@grupomactral.com";
  const password = process.env.SEED_ADMIN_PASSWORD ?? "Mactral2026!";

  const existing = await prisma.user.findUnique({ where: { email } });
  if (existing) {
    console.log(`El usuario administrador ${email} ya existe, no se crea de nuevo.`);
    return;
  }

  const passwordHash = await bcrypt.hash(password, 10);

  await prisma.user.create({
    data: {
      name: "Maya Lozada",
      email,
      passwordHash,
      role: "GERENCIA",
      lineaNegocio: "AMBAS",
      status: "ACTIVO",
    },
  });

  console.log(`Usuario administrador creado: ${email} / ${password}`);
}

main()
  .catch((error) => {
    console.error(error);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
