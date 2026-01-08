import Link from "next/link"
import { LayoutDashboard, Users, Settings, LogOut, FileText } from "lucide-react"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <div className="w-64 bg-slate-900 text-white p-4 flex flex-col">
        <div className="text-xl font-bold mb-8 px-4">TestDash</div>
        
        <nav className="flex-1 space-y-2">
          <Link href="/dashboard" className="flex items-center space-x-2 px-4 py-2 hover:bg-slate-800 rounded transition">
            <LayoutDashboard size={20} />
            <span>Dashboard</span>
          </Link>
          <Link href="/dashboard/projects" className="flex items-center space-x-2 px-4 py-2 hover:bg-slate-800 rounded transition">
            <FileText size={20} />
            <span>Projects</span>
          </Link>
          <Link href="/dashboard/settings" className="flex items-center space-x-2 px-4 py-2 hover:bg-slate-800 rounded transition">
            <Settings size={20} />
            <span>Settings</span>
          </Link>
        </nav>
        
        <button className="flex items-center space-x-2 px-4 py-2 hover:bg-slate-800 rounded transition text-red-400 mt-auto">
          <LogOut size={20} />
          <span>Logout</span>
        </button>
      </div>

      {/* Main Content */}
      <div className="flex-1 bg-gray-50">
        <header className="h-16 bg-white border-b flex items-center justify-between px-8">
            <h2 className="text-lg font-semibold">Overview</h2>
            <div className="flex items-center space-x-4">
                <div className="h-8 w-8 rounded-full bg-slate-200" />
            </div>
        </header>
        <main className="p-8">
            {children}
        </main>
      </div>
    </div>
  )
}
