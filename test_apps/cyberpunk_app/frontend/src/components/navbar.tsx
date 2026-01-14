"use client";

import { usePathname } from "next/navigation";
import { Bell, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function Navbar() {
  const pathname = usePathname();
  const pageName = pathname.split("/").pop() || "Dashboard";

  return (
    <header className="h-16 bg-white border-b flex items-center justify-between px-8 sticky top-0 z-30">
      <h2 className="text-lg font-semibold capitalize hidden md:block">
        {pageName.replace(/-/g, " ")}
      </h2>

      <div className="flex items-center space-x-4 ml-auto">
        <div className="relative w-64 hidden md:block">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-500" />
          <Input
            type="search"
            placeholder="Search..."
            className="pl-9 h-9 bg-gray-50 border-gray-200 focus-visible:ring-1"
          />
        </div>

        <Button variant="ghost" size="icon" className="text-gray-500">
          <Bell size={20} />
        </Button>

        <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-blue-500 to-purple-500" />
      </div>
    </header>
  );
}
