import { NextRequest, NextResponse } from "next/server";
import { ZodError } from "zod";
import { prisma } from "@/lib/prisma";
import { InvalidActivationTokenError, setPasswordWithToken } from "@/lib/authService";

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => null);

  try {
    const user = await setPasswordWithToken(prisma.user, body);
    return NextResponse.json({ id: user.id, email: user.email });
  } catch (error) {
    if (error instanceof ZodError) {
      return NextResponse.json({ error: error.issues[0]?.message }, { status: 400 });
    }
    if (error instanceof InvalidActivationTokenError) {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }
    console.error(error);
    return NextResponse.json({ error: "Error inesperado" }, { status: 500 });
  }
}
