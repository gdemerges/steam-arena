'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getGroups, deleteGroup, Group } from '@/lib/api'
import { PlusIcon, TrashIcon, EyeIcon, ArrowPathIcon, UserGroupIcon } from '@heroicons/react/24/outline'

export default function GroupsPage() {
  const [groups, setGroups] = useState<Group[]>([])
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState<string | null>(null)

  const loadGroups = async () => {
    setLoading(true)
    try {
      const res = await getGroups()
      setGroups(res.data)
    } catch (error) {
      console.error('Failed to load groups:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadGroups()
  }, [])

  const handleDelete = async (groupId: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!confirm('Are you sure you want to delete this group?')) return
    
    setDeleting(groupId)
    try {
      await deleteGroup(groupId)
      setGroups(groups.filter(g => g.id !== groupId))
    } catch (error) {
      console.error('Failed to delete group:', error)
      alert('Failed to delete group')
    } finally {
      setDeleting(null)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Friend Groups</h1>
        <div className="flex gap-3">
          <button onClick={loadGroups} className="btn-secondary flex items-center gap-2">
            <ArrowPathIcon className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <Link href="/groups/create" className="btn-primary flex items-center gap-2">
            <PlusIcon className="h-5 w-5" />
            Create Group
          </Link>
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="card animate-pulse">
              <div className="h-6 bg-gray-700 rounded w-3/4 mb-3"></div>
              <div className="h-4 bg-gray-700 rounded w-1/2"></div>
            </div>
          ))}
        </div>
      ) : groups.length === 0 ? (
        <div className="card text-center py-12">
          <UserGroupIcon className="h-16 w-16 mx-auto text-gray-600 mb-4" />
          <p className="text-gray-400 mb-4">No groups created yet</p>
          <p className="text-sm text-gray-500 mb-4">
            Create a group to compare playtime, achievements, and find games you all own!
          </p>
          <Link href="/groups/create" className="btn-primary inline-flex items-center gap-2">
            <PlusIcon className="h-5 w-5" />
            Create Your First Group
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {groups.map((group) => (
            <Link
              key={group.id}
              href={`/groups/${group.id}`}
              className="card hover:bg-gray-700 transition-colors group"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-lg truncate">{group.name}</h3>
                  {group.description && (
                    <p className="text-sm text-gray-400 mt-1 line-clamp-2">
                      {group.description}
                    </p>
                  )}
                  <div className="flex items-center gap-2 mt-3 text-sm text-gray-500">
                    <UserGroupIcon className="h-4 w-4" />
                    <span>{group.member_count} member{group.member_count !== 1 ? 's' : ''}</span>
                  </div>
                </div>
                <div className="flex flex-col gap-2 opacity-0 group-hover:opacity-100 transition-opacity ml-4">
                  <span className="p-2 bg-steam-blue rounded hover:bg-blue-600">
                    <EyeIcon className="h-4 w-4" />
                  </span>
                  <button
                    onClick={(e) => handleDelete(group.id, e)}
                    disabled={deleting === group.id}
                    className="p-2 bg-red-600 rounded hover:bg-red-700 disabled:opacity-50"
                  >
                    <TrashIcon className={`h-4 w-4 ${deleting === group.id ? 'animate-spin' : ''}`} />
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
