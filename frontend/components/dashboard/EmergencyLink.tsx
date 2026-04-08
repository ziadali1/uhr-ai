"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { QrCode } from "lucide-react";
import { supabase } from "@/lib/supabase";

export function EmergencyLink() {
  const [href, setHref] = useState<string>("#");

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      const id = data.session?.user?.id;
      if (id) setHref(`/emergency?userId=${id}`);
    });
  }, []);

  return (
    <Link
      href={href}
      title="Emergência"
      className="relative flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-700 transition-all hover:shadow-sm hover:border-blue-300"
    >
      <div className="rounded p-1 text-red-600 bg-red-50">
        <QrCode className="h-3.5 w-3.5" />
      </div>
      Emergência
    </Link>
  );
}
