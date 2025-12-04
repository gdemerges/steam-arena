'use client'

import { useEffect, useState } from 'react'
import { getDashboardStats, DashboardStats } from '@/lib/api'
import {
  UsersIcon,
  UserGroupIcon,
  Squares2X2Icon,
  ClockIcon,
  TrophyIcon,
} from '@heroicons/react/24/outline'

export function StatsCards() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getDashboardStats()
      .then((res) => setStats(res.data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="card animate-pulse">
            <div className="h-12 bg-gray-700 rounded"></div>
          </div>
        ))}
      </div>
    )
  }

  if (!stats) {
    return null
  }

  const cards = [
    {
      name: 'Total Users',
      value: stats.total_users,
      icon: UsersIcon,
      color: 'text-blue-400',
    },
    {
      name: 'Groups',
      value: stats.total_groups,
      icon: UserGroupIcon,
      color: 'text-green-400',
    },
    {
      name: 'Games Tracked',
      value: stats.total_games_tracked.toLocaleString(),
      icon: Squares2X2Icon,
      color: 'text-purple-400',
    },
    {
      name: 'Total Playtime',
      value: `${(stats.total_playtime_hours / 1000).toFixed(1)}k hrs`,
      icon: ClockIcon,
      color: 'text-yellow-400',
    },
    {
      name: 'Achievements',
      value: stats.total_achievements_unlocked.toLocaleString(),
      icon: TrophyIcon,
      color: 'text-orange-400',
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
      {cards.map((card) => (
        <div key={card.name} className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">{card.name}</p>
              <p className="text-2xl font-bold mt-1">{card.value}</p>
            </div>
            <card.icon className={`h-10 w-10 ${card.color}`} />
          </div>
        </div>
      ))}
    </div>
  )
}
