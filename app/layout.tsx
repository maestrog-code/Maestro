import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Maestro | Operations overview',
  description: 'Coordinate intelligent workflows and monitor business operations in Maestro.',
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>
}
