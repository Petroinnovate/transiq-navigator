
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight, ArrowUpDown } from 'lucide-react';

interface TableData {
  id: string;
  title: string;
  columns: Array<{
    key?: string;
    id?: string;
    label: string;
    type?: string;
    format?: string;
  }>;
  data: Array<Record<string, any>>;
  pagination: boolean;
  sortable: boolean;
}

interface DataTableProps {
  tableData: TableData;
}

const DataTable = ({ tableData }: DataTableProps) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const itemsPerPage = 5;

  // Normalize columns: support both `key` and `id` as the column identifier
  const columns = React.useMemo(
    () => tableData.columns.map(col => ({ ...col, key: col.key || col.id || col.label })),
    [tableData.columns]
  );

  const handleSort = (columnKey: string) => {
    if (!tableData.sortable) return;

    if (sortColumn === columnKey) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(columnKey);
      setSortDirection('asc');
    }
  };

  const sortedData = React.useMemo(() => {
    if (!sortColumn) return tableData.data;

    return [...tableData.data].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];

      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
      }

      const aStr = String(aVal).toLowerCase();
      const bStr = String(bVal).toLowerCase();

      if (sortDirection === 'asc') {
        return aStr.localeCompare(bStr);
      } else {
        return bStr.localeCompare(aStr);
      }
    });
  }, [tableData.data, sortColumn, sortDirection]);

  const paginatedData = React.useMemo(() => {
    if (!tableData.pagination) return sortedData;

    const startIndex = (currentPage - 1) * itemsPerPage;
    return sortedData.slice(startIndex, startIndex + itemsPerPage);
  }, [sortedData, currentPage, tableData.pagination]);

  const totalPages = Math.ceil(sortedData.length / itemsPerPage);

  const formatValue = (value: any, column: any) => {
    if (column.type === 'currency' || (column.type === 'number' && column.format === 'currency')) {
      return (
        <span className="text-green-400 font-medium">
          {new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
          }).format(value)}
        </span>
      );
    }

    if (column.type === 'percentage') {
      const numValue = typeof value === 'number' ? value : parseFloat(value);
      const colorClass = numValue >= 0 ? 'text-green-400' : 'text-red-400';
      return (
        <span className={`${colorClass} font-medium`}>
          {numValue >= 0 ? '+' : ''}{numValue}%
        </span>
      );
    }

    if (column.type === 'number') {
      return (
        <span className="text-slate-200 font-medium">
          {typeof value === 'number' ? value.toLocaleString() : value}
        </span>
      );
    }

    // Status column styling
    if (column.key === 'status') {
      const statusColors = {
        'Active': 'bg-green-500/20 text-green-400 border-green-500/30',
        'Growing': 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
        'Stable': 'bg-blue-500/20 text-blue-400 border-blue-500/30',
        'At Risk': 'bg-red-500/20 text-red-400 border-red-500/30',
        'Inactive': 'bg-slate-500/20 text-slate-400 border-slate-500/30'
      };
      const colorClass = statusColors[value as keyof typeof statusColors] || 'bg-slate-500/20 text-slate-400 border-slate-500/30';
      return (
        <span className={`px-2 py-1 rounded-full text-xs font-medium border ${colorClass}`}>
          {value}
        </span>
      );
    }

    return value;
  };

  return (
    <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm hover:border-cyan-500/50 transition-all duration-300">
      <CardHeader>
        <CardTitle className="text-xl font-semibold text-white">
          {tableData.title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="rounded-lg border border-slate-700 bg-slate-900/30">
          <Table>
            <TableHeader>
              <TableRow className="border-slate-700 hover:bg-slate-800/50">
                {columns.map((column) => (
                  <TableHead
                    key={column.key}
                    className={`text-slate-300 ${tableData.sortable ? 'cursor-pointer hover:bg-slate-800/50' : ''}`}
                    onClick={() => handleSort(column.key)}
                  >
                    <div className="flex items-center space-x-1">
                      <span>{column.label}</span>
                      {tableData.sortable && (
                        <ArrowUpDown className="h-4 w-4 text-slate-400" />
                      )}
                    </div>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedData.map((row, index) => (
                <TableRow key={row.id || `row-${index}`} className="border-slate-700 hover:bg-slate-800/30">
                  {columns.map((column) => (
                    <TableCell key={`${row.id || index}-${column.key}`} className="text-slate-300">
                      {formatValue(row[column.key!], column)}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {tableData.pagination && totalPages > 1 && (
          <div className="flex items-center justify-between mt-4">
            <p className="text-sm text-slate-400">
              Showing {(currentPage - 1) * itemsPerPage + 1} to{' '}
              {Math.min(currentPage * itemsPerPage, sortedData.length)} of{' '}
              {sortedData.length} entries
            </p>
            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                className="bg-slate-700 border-slate-600 text-white hover:bg-slate-600"
                onClick={() => setCurrentPage(currentPage - 1)}
                disabled={currentPage === 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-sm text-slate-300">
                Page {currentPage} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                className="bg-slate-700 border-slate-600 text-white hover:bg-slate-600"
                onClick={() => setCurrentPage(currentPage + 1)}
                disabled={currentPage === totalPages}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default DataTable;
