'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getUsers, deleteUser, SteamUser } from '@/lib/api'
import { PlusIcon, TrashIcon, EyeIcon, ArrowPathIcon } from '@heroicons/react/24/outline'

export default function UsersPage() {
  const [users, setUsers] = useState<SteamUser[]>([])
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState<string | null>(null)

  const loadUsers = async () => {
    setLoading(true)
    try {
      const res = await getUsers()
      setUsers(res.data)
    } catch (error) {
      console.error('Failed to load users:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadUsers()
  }, [])

  const handleDelete = async (userId: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!confirm('Are you sure you want to delete this user?')) return
    
    setDeleting(userId)
    try {
      await deleteUser(userId)
      setUsers(users.filter(u => u.id !== userId))
    } catch (error) {
      console.error('Failed to delete user:', error)
      alert('Failed to delete user')
    } finally {
      setDeleting(null)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Steam Users</h1>
        <div className="flex gap-3">
          <button onClick={loadUsers} className="btn-secondary flex items-center gap-2">
            <ArrowPathIcon className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <Link href="/users/add" className="btn-primary flex items-center gap-2">
            <PlusIcon className="h-5 w-5" />
            Add User
          </Link>
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="card animate-pulse">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 bg-gray-700 rounded-full"></div>
                <div className="flex-1">
                  <div className="h-5 bg-gray-700 rounded w-3/4 mb-2"></div>
                  <div className="h-4 bg-gray-700 rounded w-1/2"></div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : users.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-400 mb-4">No Steam users added yet</p>
          <Link href="/users/add" className="btn-primary inline-flex items-center gap-2">
            <PlusIcon className="h-5 w-5" />
            Add Your First User
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {users.map((user) => (
            <Link
              key={user.id}
              href={`/users/${user.id}`}
              className="card hover:bg-gray-700 transition-colors group"
            >
              <div className="flex items-center gap-4">
                <img
                  src={user.avatar_full_url || user.avatar_url || '/default-avatar.png'}
                  alt={user.persona_name}
                  className="w-16 h-16 rounded-full"
                />
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-lg truncate">{user.persona_name}</h3>
                  <p className="text-sm text-gray-400">
                    {user.total_games || 0} games • {((user.total_playtime || 0) / 60).toFixed(0)} hrs
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {user.total_achievements || 0} achievements
                  </p>
                </div>
                <div className="flex flex-col gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <span className="p-2 bg-steam-blue rounded hover:bg-blue-600">
                    <EyeIcon className="h-4 w-4" />
                  </span>
                  <button
                    onClick={(e) => handleDelete(user.id, e)}
                    disabled={deleting === user.id}
                    className="p-2 bg-red-600 rounded hover:bg-red-700 disabled:opacity-50"
                  >
                    <TrashIcon className={`h-4 w-4 ${deleting === user.id ? 'animate-spin' : ''}`} />
                  </button>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
