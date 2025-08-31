export default function LandingLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="landing-container">
      {/* Landing page specific layout wrapper */}
      {children}
    </div>
  )
}