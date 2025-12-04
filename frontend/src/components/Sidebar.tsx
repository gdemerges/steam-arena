'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  HomeIcon,
  UserGroupIcon,
  UsersIcon,
  ChartBarIcon,
  CpuChipIcon,
  Squares2X2Icon,
} from '@heroicons/react/24/outline'
import clsx from 'clsx'

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Users', href: '/users', icon: UsersIcon },
  { name: 'Groups', href: '/groups', icon: UserGroupIcon },
  { name: 'Games', href: '/games', icon: Squares2X2Icon },
  { name: 'Compare', href: '/compare', icon: ChartBarIcon },
  { name: 'ML Analytics', href: '/ml', icon: CpuChipIcon },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <div className="fixed inset-y-0 left-0 w-64 bg-steam-dark">
      <div className="flex h-16 items-center justify-center border-b border-gray-700">
        <Link href="/" className="text-2xl font-bold text-steam-blue">
          🎮 Steam Arena
        </Link>
      </div>
      <nav className="mt-6 px-3">
        <ul className="space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href || 
              (item.href !== '/' && pathname.startsWith(item.href))
            
            return (
              <li key={item.name}>
                <Link
                  href={item.href}
                  className={clsx(
                    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-steam-blue text-white'
                      : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                  )}
                >
                  <item.icon className="h-5 w-5" />
                  {item.name}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>
      
      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-700">
        <div className="text-xs text-gray-500 text-center">
          <p>Steam Arena v1.0</p>
          <p className="mt-1">Powered by Steam API</p>
        </div>
      </div>
    </div>
  )
}
