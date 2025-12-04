'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { createGroup, getUsers, addGroupMembers, SteamUser } from '@/lib/api'
import { ArrowLeftIcon, ArrowPathIcon, PlusIcon, XMarkIcon } from '@heroicons/react/24/outline'

export default function CreateGroupPage() {
  const router = useRouter()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [selectedUsers, setSelectedUsers] = useState<SteamUser[]>([])
  const [availableUsers, setAvailableUsers] = useState<SteamUser[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingUsers, setLoadingUsers] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    getUsers()
      .then((res) => setAvailableUsers(res.data))
      .catch(console.error)
      .finally(() => setLoadingUsers(false))
  }, [])

  const handleAddUser = (user: SteamUser) => {
    if (!selectedUsers.find(u => u.id === user.id)) {
      setSelectedUsers([...selectedUsers, user])
    }
  }

  const handleRemoveUser = (userId: string) => {
    setSelectedUsers(selectedUsers.filter(u => u.id !== userId))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      setError('Please enter a group name')
      return
    }
    if (selectedUsers.length < 2) {
      setError('Please select at least 2 users to compare')
      return
    }

    setLoading(true)
    setError('')

    try {
      const groupRes = await createGroup({ name, description })
      const groupId = groupRes.data.id

      // Add members using the API function
      const steamIds = selectedUsers.map(u => u.steam_id)
      await addGroupMembers(groupId, steamIds)

      router.push(`/groups/${groupId}`)
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create group'
      setError(errorMessage)
      setLoading(false)
    }
  }

  const unselectedUsers = availableUsers.filter(
    u => !selectedUsers.find(s => s.id === u.id)
  )

  return (
    <div className="max-w-2xl mx-auto">
      <Link href="/groups" className="inline-flex items-center gap-2 text-gray-400 hover:text-white mb-6">
        <ArrowLeftIcon className="h-4 w-4" />
        Back to Groups
      </Link>

      <div className="card">
        <h1 className="text-2xl font-bold mb-6">Create Friend Group</h1>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-300 mb-2">
              Group Name *
            </label>
            <input
              type="text"
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Weekend Warriors, College Friends"
              className="input w-full"
              disabled={loading}
            />
          </div>

          <div>
            <label htmlFor="description" className="block text-sm font-medium text-gray-300 mb-2">
              Description (optional)
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe your group..."
              rows={3}
              className="input w-full"
              disabled={loading}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Members ({selectedUsers.length} selected)
            </label>
            
            {/* Selected Users */}
            {selectedUsers.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-4">
                {selectedUsers.map((user) => (
                  <div
                    key={user.id}
                    className="flex items-center gap-2 bg-steam-blue/20 border border-steam-blue rounded-full px-3 py-1"
                  >
                    <img
                      src={user.avatar_url || '/default-avatar.png'}
                      alt={user.persona_name}
                      className="w-6 h-6 rounded-full"
                    />
                    <span className="text-sm">{user.persona_name}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveUser(user.id)}
                      className="text-gray-400 hover:text-white"
                    >
                      <XMarkIcon className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Available Users */}
            {loadingUsers ? (
              <div className="text-gray-400 text-center py-4">Loading users...</div>
            ) : unselectedUsers.length === 0 ? (
              availableUsers.length === 0 ? (
                <div className="text-center py-4">
                  <p className="text-gray-400 mb-2">No users available</p>
                  <Link href="/users/add" className="text-steam-blue hover:underline">
                    Add some users first
                  </Link>
                </div>
              ) : (
                <p className="text-gray-400 text-center py-4">All users selected</p>
              )
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-60 overflow-y-auto">
                {unselectedUsers.map((user) => (
                  <button
                    key={user.id}
                    type="button"
                    onClick={() => handleAddUser(user)}
                    className="flex items-center gap-3 p-2 rounded bg-gray-700 hover:bg-gray-600 transition-colors text-left"
                  >
                    <img
                      src={user.avatar_url || '/default-avatar.png'}
                      alt={user.persona_name}
                      className="w-8 h-8 rounded-full"
                    />
                    <span className="truncate flex-1">{user.persona_name}</span>
                    <PlusIcon className="h-4 w-4 text-gray-400" />
                  </button>
                ))}
              </div>
            )}
          </div>

          {error && (
            <div className="p-3 bg-red-900/50 border border-red-700 rounded text-red-300 text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || selectedUsers.length < 2}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <ArrowPathIcon className="h-5 w-5 animate-spin" />
                Creating...
              </>
            ) : (
              'Create Group'
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
