import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { getCurrentSession } from "@/lib/currentUser";
import {
  activateUser,
  deactivateUser,
  ForbiddenError,
  UserNotFoundError,
} from "@/lib/userService";

export async function PATCH(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const session = await getCurrentSession();
  if (!session) {
    return NextResponse.json({ error: "No autenticado" }, { status: 401 });
  }

  const body = await request.json().catch(() => null);
  const status = body?.status;

  if (status !== "ACTIVO" && status !== "INACTIVO") {
    return NextResponse.json(
      { error: "El campo status debe ser ACTIVO o INACTIVO" },
      { status: 400 }
    );
  }

  try {
    const user =
      status === "INACTIVO"
        ? await deactivateUser(prisma.user, { role: session.role }, params.id)
        : await activateUser(prisma.user, { role: session.role }, params.id);

    return NextResponse.json({ id: user.id, status: user.status });
  } catch (error) {
    if (error instanceof ForbiddenError) {
      return NextResponse.json({ error: error.message }, { status: 403 });
    }
    if (error instanceof UserNotFoundError) {
      return NextResponse.json({ error: error.message }, { status: 404 });
    }
    console.error(error);
    return NextResponse.json({ error: "Error inesperado" }, { status: 500 });
  }
}
