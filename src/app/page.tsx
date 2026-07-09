import { redirect } from "next/navigation";
import { getCurrentSession } from "@/lib/currentUser";

export default async function HomePage() {
  const session = await getCurrentSession();
  redirect(session ? "/usuarios" : "/login");
}
