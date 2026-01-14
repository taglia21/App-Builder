"use client";

import { useState, useEffect } from "react";
import { DataTable } from "@/components/ui/data-table";
import { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import Link from "next/link";
import { Lead } from "@/types/schema";

export default function LeadsPage() {
  const [data, setData] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate fetching data
    // In a real app, this would be a fetch call to /api/v1/leads
    const mockData: Lead[] = [
      {
        id: "1",
        name: "Sample Lead 1",
        status: "Active",
        created_at: new Date().toISOString(),
      } as any,
      {
        id: "2",
        name: "Sample Lead 2",
        status: "Draft",
        created_at: new Date().toISOString(),
      } as any,
      {
        id: "3",
        name: "Sample Lead 3",
        status: "Archived",
        created_at: new Date().toISOString(),
      } as any,
    ];
    setTimeout(() => {
      setData(mockData);
      setLoading(false);
    }, 1000);
  }, []);

  const columns: ColumnDef<Lead>[] = [
    {
      accessorKey: "name",
      header: "Name",
    },
    {
      accessorKey: "status",
      header: "Status",
    },
    {
      accessorKey: "created_at",
      header: "Created",
      cell: ({ row }) => {
        return new Date(row.getValue("created_at")).toLocaleDateString();
      },
    },
    {
      id: "actions",
      cell: ({ row }) => {
        return (
          <Button variant="ghost" size="sm">
            Edit
          </Button>
        );
      },
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Leads</h2>
          <p className="text-muted-foreground">Manage your leads here.</p>
        </div>
        <Link href="/dashboard/leads/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            New Lead
          </Button>
        </Link>
      </div>

      <DataTable columns={columns} data={data} searchKey="name" />
    </div>
  );
}
