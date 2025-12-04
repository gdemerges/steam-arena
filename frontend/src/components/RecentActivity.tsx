'use client'

import { useEffect, useState } from 'react'
import { getUsers, SteamUser } from '@/lib/api'
import Link from 'next/link'

export function RecentActivity() {
  const [users, setUsers] = useState<SteamUser[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getUsers()
      .then((res) => setUsers(res.data.slice(0, 5)))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="card">
      <h2 className="text-xl font-semibold mb-4">Recent Users</h2>
      
      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex items-center gap-3 animate-pulse">
              <div className="w-10 h-10 bg-gray-700 rounded-full"></div>
              <div className="flex-1">
                <div className="h-4 bg-gray-700 rounded w-3/4"></div>
              </div>
            </div>
          ))}
        </div>
      ) : users.length === 0 ? (
        <div className="text-center py-8 text-gray-400">
          <p>No users yet</p>
          <Link href="/users/add" className="text-steam-blue hover:underline">
            Add your first user
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {users.map((user) => (
            <Link
              key={user.id}
              href={`/users/${user.id}`}
              className="flex items-center gap-3 p-2 rounded hover:bg-gray-700 transition-colors"
            >
              <img
                src={user.avatar_url || '/default-avatar.png'}
                alt={user.persona_name}
                className="w-10 h-10 rounded-full"
              />
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{user.persona_name}</p>
                <p className="text-sm text-gray-400 truncate">
                  {user.total_games || 0} games • {((user.total_playtime || 0) / 60).toFixed(0)} hrs
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}
      
      <Link
        href="/users"
        className="block mt-4 text-center text-steam-blue hover:underline"
      >
        View all users →
      </Link>
    </div>
  )
}
