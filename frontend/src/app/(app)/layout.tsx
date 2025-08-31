export default function AppLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="app-container">
      {/* App-specific layout wrapper */}
      {children}
    </div>
  )
}