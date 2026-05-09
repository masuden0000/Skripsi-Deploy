import Image from "next/image"
import AdminNav from "@/components/layout/AdminNav"
import LogoutButton from "@/components/auth/LogoutButton"

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside
        className="w-60 flex-none flex flex-col bg-white border-r"
        style={{ borderColor: "rgba(0,153,102,0.12)" }}
      >
        {/* Brand */}
        <div
          className="px-5 py-5 flex items-center gap-3 border-b"
          style={{ borderColor: "rgba(0,153,102,0.12)" }}
        >
          <div
            className="size-9 rounded-xl flex items-center justify-center flex-none overflow-hidden"
            style={{ background: "linear-gradient(135deg, #009966 0%, #007a55 100%)" }}
          >
            <Image
              src="/logo-upnvj.png"
              alt="UPNVJ"
              width={26}
              height={26}
              className="object-contain brightness-0 invert"
            />
          </div>
          <div>
            <p className="text-sm font-semibold text-pkm-900 leading-tight">Sistem Review</p>
            <p className="text-xs leading-tight" style={{ color: "rgba(0,153,102,0.7)" }}>
              PKM — UPNVJ
            </p>
          </div>
        </div>

        {/* Navigation */}
        <AdminNav />

        {/* Sidebar footer */}
        <div
          className="px-5 py-4 border-t"
          style={{ borderColor: "rgba(0,153,102,0.12)" }}
        >
          <p className="text-xs" style={{ color: "rgba(0,0,0,0.3)" }}>
            Admin Panel
          </p>

          <div className="mt-3">
            <LogoutButton />
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 min-h-screen bg-pkm-50/40">{children}</main>
    </div>
  )
}
