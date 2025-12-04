'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getUsers, getRecommendations, SteamUser, Recommendation } from '@/lib/api'
import { ArrowLeftIcon, SparklesIcon, ArrowPathIcon } from '@heroicons/react/24/outline'

type RecommendationType = 'hybrid' | 'collaborative' | 'content'

export default function RecommendationsPage() {
  const [users, setUsers] = useState<SteamUser[]>([])
  const [selectedUser, setSelectedUser] = useState<SteamUser | null>(null)
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingUsers, setLoadingUsers] = useState(true)
  const [recType, setRecType] = useState<RecommendationType>('hybrid')

  useEffect(() => {
    getUsers()
      .then((res) => setUsers(res.data))
      .catch(console.error)
      .finally(() => setLoadingUsers(false))
  }, [])

  const loadRecommendations = async (userId: string, type: RecommendationType) => {
    setLoading(true)
    try {
      const res = await getRecommendations(userId, type, 20)
      setRecommendations(res.data)
    } catch (error) {
      console.error('Failed to load recommendations:', error)
      setRecommendations([])
    } finally {
      setLoading(false)
    }
  }

  const handleUserSelect = (user: SteamUser) => {
    setSelectedUser(user)
    loadRecommendations(user.id, recType)
  }

  const handleTypeChange = (type: RecommendationType) => {
    setRecType(type)
    if (selectedUser) {
      loadRecommendations(selectedUser.id, type)
    }
  }

  return (
    <div className="space-y-6">
      <Link href="/ml" className="inline-flex items-center gap-2 text-gray-400 hover:text-white">
        <ArrowLeftIcon className="h-4 w-4" />
        Back to ML Analytics
      </Link>

      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Game Recommendations</h1>
      </div>

      {/* User Selection */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Select User</h2>
        
        {loadingUsers ? (
          <div className="text-gray-400 text-center py-4">Loading users...</div>
        ) : users.length === 0 ? (
          <p className="text-gray-400 text-center py-4">No users available</p>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {users.map((user) => (
              <button
                key={user.id}
                onClick={() => handleUserSelect(user)}
                className={`flex flex-col items-center gap-2 p-3 rounded transition-colors ${
                  selectedUser?.id === user.id
                    ? 'bg-steam-blue/30 border-2 border-steam-blue'
                    : 'bg-gray-700 hover:bg-gray-600'
                }`}
              >
                <img
                  src={user.avatar_url || '/default-avatar.png'}
                  alt={user.persona_name}
                  className="w-12 h-12 rounded-full"
                />
                <span className="text-sm truncate w-full text-center">{user.persona_name}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {selectedUser && (
        <>
          {/* Recommendation Type */}
          <div className="card">
            <h2 className="text-xl font-semibold mb-4">Recommendation Type</h2>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => handleTypeChange('hybrid')}
                className={`px-4 py-2 rounded transition-colors ${
                  recType === 'hybrid'
                    ? 'bg-steam-blue text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                🔀 Hybrid (Best)
              </button>
              <button
                onClick={() => handleTypeChange('collaborative')}
                className={`px-4 py-2 rounded transition-colors ${
                  recType === 'collaborative'
                    ? 'bg-steam-blue text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                👥 Collaborative
              </button>
              <button
                onClick={() => handleTypeChange('content')}
                className={`px-4 py-2 rounded transition-colors ${
                  recType === 'content'
                    ? 'bg-steam-blue text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                📊 Content-Based
              </button>
            </div>
            <p className="text-sm text-gray-400 mt-3">
              {recType === 'hybrid' && 'Combines collaborative and content-based filtering for best results'}
              {recType === 'collaborative' && 'Recommends games based on what similar players enjoy'}
              {recType === 'content' && 'Recommends games similar to ones already played'}
            </p>
          </div>

          {/* Recommendations */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold flex items-center gap-2">
                <SparklesIcon className="h-6 w-6 text-yellow-400" />
                Recommendations for {selectedUser.persona_name}
              </h2>
              {loading && <ArrowPathIcon className="h-5 w-5 animate-spin text-gray-400" />}
            </div>

            {loading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[...Array(6)].map((_, i) => (
                  <div key={i} className="animate-pulse">
                    <div className="aspect-[460/215] bg-gray-700 rounded"></div>
                    <div className="h-4 bg-gray-700 rounded w-3/4 mt-2"></div>
                  </div>
                ))}
              </div>
            ) : recommendations.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-400 mb-2">No recommendations available</p>
                <p className="text-sm text-gray-500">
                  Make sure to extract features and run clustering first
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {recommendations.map((rec, index) => (
                  <div
                    key={rec.game.id}
                    className="bg-gray-700/50 rounded-lg overflow-hidden hover:bg-gray-700 transition-colors"
                  >
                    <div className="aspect-[460/215] bg-gray-700 relative">
                      {rec.game.header_image ? (
                        <img
                          src={rec.game.header_image}
                          alt={rec.game.name}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-gray-500">
                          No Image
                        </div>
                      )}
                      <div className="absolute top-2 left-2 bg-steam-blue px-2 py-1 rounded text-sm font-medium">
                        #{index + 1}
                      </div>
                      <div className="absolute top-2 right-2 bg-yellow-500/90 px-2 py-1 rounded text-sm font-medium text-black">
                        {(rec.score * 100).toFixed(0)}% match
                      </div>
                    </div>
                    <div className="p-3">
                      <h3 className="font-medium truncate">{rec.game.name}</h3>
                      {rec.game.developer && (
                        <p className="text-sm text-gray-400 truncate">{rec.game.developer}</p>
                      )}
                      {rec.reason && (
                        <p className="text-xs text-gray-500 mt-2 line-clamp-2">{rec.reason}</p>
                      )}
                      <div className="flex items-center justify-between mt-2">
                        {rec.game.metacritic_score && (
                          <span
                            className={`px-2 py-0.5 rounded text-xs font-medium ${
                              rec.game.metacritic_score >= 75
                                ? 'bg-green-500/20 text-green-400'
                                : rec.game.metacritic_score >= 50
                                ? 'bg-yellow-500/20 text-yellow-400'
                                : 'bg-red-500/20 text-red-400'
                            }`}
                          >
                            {rec.game.metacritic_score}
                          </span>
                        )}
                        {rec.game.is_free && (
                          <span className="px-2 py-0.5 bg-steam-blue/20 text-steam-blue rounded text-xs">
                            Free
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
