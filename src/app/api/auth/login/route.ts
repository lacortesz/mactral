import { NextRequest, NextResponse } from "next/server";
import { ZodError } from "zod";
import { prisma } from "@/lib/prisma";
import {
  InactiveAccountError,
  InvalidCredentialsError,
  loginUser,
} from "@/lib/authService";
import { SESSION_COOKIE_NAME, SESSION_MAX_AGE, signSessionToken } from "@/lib/session";
import type { Rol } from "@/lib/domain";

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => null);

  try {
    const user = await loginUser(prisma.user, body);

    const token = await signSessionToken({
      sub: user.id,
      name: user.name,
      email: user.email,
      role: user.role as Rol,
    });

    const response = NextResponse.json({
      id: user.id,
      name: user.name,
      email: user.email,
      role: user.role,
    });

    response.cookies.set(SESSION_COOKIE_NAME, token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: SESSION_MAX_AGE,
      path: "/",
    });

    return response;
  } catch (error) {
    if (error instanceof ZodError) {
      return NextResponse.json({ error: error.issues[0]?.message }, { status: 400 });
    }
    if (error instanceof InvalidCredentialsError) {
      return NextResponse.json({ error: error.message }, { status: 401 });
    }
    if (error instanceof InactiveAccountError) {
      return NextResponse.json({ error: error.message }, { status: 403 });
    }
    console.error(error);
    return NextResponse.json({ error: "Error inesperado" }, { status: 500 });
  }
}
