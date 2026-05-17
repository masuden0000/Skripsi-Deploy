import BrandLogo from "@/components/BrandLogo"
import ReviewerNav from "@/components/layout/ReviewerNav"
import LogoutButton from "@/components/auth/LogoutButton"
import { ReviewerProfileLink } from "@/components/layout/ReviewerProfileLink"

export default function ReviewerLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside
        className="w-60 flex-none flex flex-col bg-white border-r h-full"
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
            <BrandLogo size={26} invert />
          </div>
          <div>
            <p className="text-sm font-semibold text-pkm-900 leading-tight">Sistem Review</p>
            <p className="text-xs leading-tight" style={{ color: "rgba(0,153,102,0.7)" }}>
              PKM — UPNVJ
            </p>
          </div>
        </div>

        {/* Navigation */}
        <ReviewerNav />

        {/* Sidebar footer */}
        <div
          className="px-5 py-4 border-t"
          style={{ borderColor: "rgba(0,153,102,0.12)" }}
        >
          <p className="text-xs" style={{ color: "rgba(0,0,0,0.3)" }}>
            Panel Reviewer
          </p>

          <div className="mt-3 flex flex-col gap-1">
            <ReviewerProfileLink />
            <LogoutButton />
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 h-full overflow-y-auto bg-pkm-50/40">{children}</main>
    </div>
  )
}