export default function PageWrapper({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div
      className="relative min-h-screen w-full flex items-center justify-center overflow-hidden"
      style={{
        background:
          "linear-gradient(154.57deg, #ecfdf5 0%, #ffffff 50%, rgba(236,253,245,0.3) 100%)",
      }}
    >
      {/* Blurred green orb kanan atas */}
      <div
        className="pointer-events-none absolute right-0 top-[-160px] size-80 rounded-full blur-[64px]"
        style={{ background: "rgba(164,244,207,0.5)" }}
      />
      {/* Blurred green orb kiri bawah */}
      <div
        className="pointer-events-none absolute bottom-[-160px] left-0 size-80 rounded-full blur-[64px]"
        style={{ background: "rgba(185,248,207,0.5)" }}
      />
      {/* Blurred green orb tengah */}
      <div
        className="pointer-events-none absolute left-1/2 top-1/2 size-96 -translate-x-1/2 -translate-y-1/2 rounded-full blur-[64px]"
        style={{ background: "rgba(208,250,229,0.3)" }}
      />

      <div className="relative z-10 w-full max-w-[448px] px-4 py-10">
        {children}
      </div>
    </div>
  )
}
