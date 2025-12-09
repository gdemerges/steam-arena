'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { getGame, getGameOwners } from '@/lib/api'
import { ArrowLeftIcon, UsersIcon, ClockIcon, TrophyIcon } from '@heroicons/react/24/outline'

interface Game {
  id: string
  app_id: number
  name: string
  img_icon_url?: string
  header_image?: string
  short_description?: string
  developer?: string
  publisher?: string
  metacritic_score?: number
  is_free: boolean
  created_at: string
}

interface GameOwner {
  user: {
    id: string
    steam_id: string
    persona_name: string
    avatar_url: string
  }
  playtime_forever: number
  playtime_2weeks: number
  rtime_last_played?: string
}

export default function GameDetailPage() {
  const params = useParams()
  const gameId = params.id as string

  const [game, setGame] = useState<Game | null>(null)
  const [owners, setOwners] = useState<GameOwner[]>([])
  const [loading, setLoading] = useState(true)

  const loadData = async () => {
    setLoading(true)
    try {
      const [gameRes, ownersRes] = await Promise.all([
        getGame(gameId),
        getGameOwners(gameId).catch(() => ({ data: [] })),
      ])
      setGame(gameRes.data)
      setOwners(Array.isArray(ownersRes.data) ? ownersRes.data : [])
    } catch (error) {
      console.error('Failed to load game data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [gameId])

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="card animate-pulse">
          <div className="h-8 bg-gray-700 rounded w-1/3 mb-3"></div>
          <div className="h-4 bg-gray-700 rounded w-1/2"></div>
        </div>
      </div>
    )
  }

  if (!game) {
    return (
      <div className="card text-center py-12">
        <p className="text-gray-400">Game not found</p>
        <Link href="/games" className="btn-primary mt-4 inline-block">
          Back to Games
        </Link>
      </div>
    )
  }

  const getGameImage = () => {
    if (game.header_image) return game.header_image
    if (game.app_id) return `https://cdn.cloudflare.steamstatic.com/steam/apps/${game.app_id}/header.jpg`
    return null
  }

  const totalPlaytime = owners.reduce((sum, o) => sum + (o.playtime_forever || 0), 0)
  const avgPlaytime = owners.length > 0 ? totalPlaytime / owners.length : 0

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <Link href="/games" className="inline-flex items-center gap-2 text-gray-400 hover:text-white">
          <ArrowLeftIcon className="h-4 w-4" />
          Back to Games
        </Link>
      </div>

      {/* Game Header */}
      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-1">
            {getGameImage() ? (
              <img
                src={getGameImage()!}
                alt={game.name}
                className="w-full rounded-lg"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none'
                }}
              />
            ) : (
              <div className="aspect-[460/215] bg-gray-700 rounded-lg flex items-center justify-center">
                <span className="text-gray-500">No Image</span>
              </div>
            )}
          </div>
          <div className="md:col-span-2">
            <h1 className="text-3xl font-bold mb-2">{game.name}</h1>
            
            {game.short_description && (
              <p className="text-gray-400 mb-4">{game.short_description}</p>
            )}

            <div className="grid grid-cols-2 gap-4">
              {game.developer && (
                <div>
                  <p className="text-sm text-gray-500">Developer</p>
                  <p className="font-medium">{game.developer}</p>
                </div>
              )}
              {game.publisher && (
                <div>
                  <p className="text-sm text-gray-500">Publisher</p>
                  <p className="font-medium">{game.publisher}</p>
                </div>
              )}
              {game.metacritic_score && (
                <div>
                  <p className="text-sm text-gray-500">Metacritic Score</p>
                  <p className={`font-bold text-lg ${
                    game.metacritic_score >= 75 ? 'text-green-400' :
                    game.metacritic_score >= 50 ? 'text-yellow-400' :
                    'text-red-400'
                  }`}>
                    {game.metacritic_score}
                  </p>
                </div>
              )}
            </div>

            {game.is_free && (
              <div className="mt-4">
                <span className="px-3 py-1 bg-steam-blue/20 text-steam-blue rounded-full text-sm font-medium">
                  Free to Play
                </span>
              </div>
            )}

            <div className="mt-4">
              <a
                href={`https://store.steampowered.com/app/${game.app_id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-steam-blue hover:underline text-sm"
              >
                View on Steam Store →
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Stats */}
      {owners.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="card">
            <div className="flex items-center gap-3">
              <UsersIcon className="h-8 w-8 text-purple-400" />
              <div>
                <p className="text-sm text-gray-400">Owners</p>
                <p className="text-2xl font-bold">{owners.length}</p>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="flex items-center gap-3">
              <ClockIcon className="h-8 w-8 text-yellow-400" />
              <div>
                <p className="text-sm text-gray-400">Total Playtime</p>
                <p className="text-2xl font-bold">{(totalPlaytime / 60).toFixed(0)}h</p>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="flex items-center gap-3">
              <ClockIcon className="h-8 w-8 text-green-400" />
              <div>
                <p className="text-sm text-gray-400">Avg Playtime</p>
                <p className="text-2xl font-bold">{(avgPlaytime / 60).toFixed(0)}h</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Owners List */}
      {owners.length > 0 && (
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Players ({owners.length})</h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-700">
                  <th className="pb-3 font-medium">Player</th>
                  <th className="pb-3 font-medium text-right">Total Playtime</th>
                  <th className="pb-3 font-medium text-right">Last 2 Weeks</th>
                  <th className="pb-3 font-medium text-right">Last Played</th>
                </tr>
              </thead>
              <tbody>
                {owners
                  .sort((a, b) => (b.playtime_forever || 0) - (a.playtime_forever || 0))
                  .map((owner) => (
                    <tr key={owner.user.id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                      <td className="py-3">
                        <Link
                          href={`/users/${owner.user.id}`}
                          className="flex items-center gap-3 hover:text-steam-blue"
                        >
                          <img
                            src={owner.user.avatar_url || '/default-avatar.png'}
                            alt={owner.user.persona_name}
                            className="w-10 h-10 rounded-full"
                          />
                          <span>{owner.user.persona_name}</span>
                        </Link>
                      </td>
                      <td className="py-3 text-right text-gray-300">
                        {(owner.playtime_forever / 60).toFixed(1)} hrs
                      </td>
                      <td className="py-3 text-right text-gray-400">
                        {owner.playtime_2weeks > 0
                          ? `${(owner.playtime_2weeks / 60).toFixed(1)} hrs`
                          : '-'}
                      </td>
                      <td className="py-3 text-right text-gray-400">
                        {owner.rtime_last_played
                          ? new Date(owner.rtime_last_played).toLocaleDateString()
                          : '-'}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
