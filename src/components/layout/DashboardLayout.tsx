// ============================================================================
// DashboardLayout - Board-Grade Executive Dashboard Layout
// Purpose: Professional layout wrapper for all dashboard components
// ============================================================================

import React, { ReactNode } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'

interface DashboardLayoutProps {
  children: ReactNode
  header?: ReactNode
  footer?: ReactNode
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({ 
  children, 
  header, 
  footer 
}) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-950 dark:to-gray-900">
      <div className="container mx-auto">
        {/* Optional Header */}
        {header && (
          <>
            <div className="py-6">
              {header}
            </div>
            <Separator className="mb-6" />
          </>
        )}

        {/* Main Content */}
        <ScrollArea className="h-full">
          <div className="space-y-6 pb-8">
            {children}
          </div>
        </ScrollArea>

        {/* Optional Footer */}
        {footer && (
          <>
            <Separator className="my-6" />
            <div className="py-6">
              {footer}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
