'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { createUser, syncUserProfile, syncUserGames, syncUserAchievements } from '@/lib/api'
import { ArrowLeftIcon, ArrowPathIcon } from '@heroicons/react/24/outline'

export default function AddUserPage() {
  const router = useRouter()
  const [steamId, setSteamId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!steamId.trim()) {
      setError('Please enter a Steam ID or profile URL')
      return
    }

    setLoading(true)
    setError('')
    setStatus('Creating user...')

    try {
      // Extract Steam ID from URL if needed
      let cleanSteamId = steamId.trim()
      const urlMatch = cleanSteamId.match(/steamcommunity\.com\/(id|profiles)\/([^\/]+)/)
      if (urlMatch) {
        cleanSteamId = urlMatch[2]
      }

      // Create user
      const userRes = await createUser(cleanSteamId)
      const userId = userRes.data.id

      // Sync profile
      setStatus('Syncing profile...')
      await syncUserProfile(userId)

      // Sync games
      setStatus('Syncing games...')
      await syncUserGames(userId)

      // Sync achievements
      setStatus('Syncing achievements...')
      await syncUserAchievements(userId)

      setStatus('Done!')
      router.push(`/users/${userId}`)
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 
        (typeof err === 'object' && err !== null && 'response' in err) 
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to add user'
          : 'Failed to add user'
      setError(errorMessage)
      setLoading(false)
    }
  }

  return (
    <div className="max-w-xl mx-auto">
      <Link href="/users" className="inline-flex items-center gap-2 text-gray-400 hover:text-white mb-6">
        <ArrowLeftIcon className="h-4 w-4" />
        Back to Users
      </Link>

      <div className="card">
        <h1 className="text-2xl font-bold mb-6">Add Steam User</h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="steamId" className="block text-sm font-medium text-gray-300 mb-2">
              Steam ID or Profile URL
            </label>
            <input
              type="text"
              id="steamId"
              value={steamId}
              onChange={(e) => setSteamId(e.target.value)}
              placeholder="76561198012345678 or https://steamcommunity.com/id/username"
              className="input w-full"
              disabled={loading}
            />
            <p className="text-xs text-gray-500 mt-2">
              You can use a 17-digit Steam ID, a custom URL ID, or a full profile URL
            </p>
          </div>

          {error && (
            <div className="p-3 bg-red-900/50 border border-red-700 rounded text-red-300 text-sm">
              {error}
            </div>
          )}

          {loading && status && (
            <div className="p-3 bg-steam-blue/20 border border-steam-blue rounded text-steam-blue text-sm flex items-center gap-2">
              <ArrowPathIcon className="h-4 w-4 animate-spin" />
              {status}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <ArrowPathIcon className="h-5 w-5 animate-spin" />
                Adding...
              </>
            ) : (
              'Add User'
            )}
          </button>
        </form>

        <div className="mt-6 pt-6 border-t border-gray-700">
          <h3 className="text-sm font-medium text-gray-300 mb-2">How to find your Steam ID:</h3>
          <ol className="text-xs text-gray-500 space-y-1 list-decimal list-inside">
            <li>Open Steam and go to your profile</li>
            <li>Click &quot;Edit Profile&quot;</li>
            <li>Your custom URL or Steam ID is shown in the URL field</li>
            <li>Or visit steamid.io to look up any profile</li>
          </ol>
        </div>
      </div>
    </div>
  )
}
