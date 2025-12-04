'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import {
  getUser,
  getUserGames,
  getUserDashboard,
  getUserPlaytimeByGenre,
  syncUserProfile,
  syncUserGames,
  SteamUser,
  UserGame,
} from '@/lib/api'
import {
  ArrowLeftIcon,
  ArrowPathIcon,
  ClockIcon,
  TrophyIcon,
  Squares2X2Icon,
} from '@heroicons/react/24/outline'
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

const COLORS = ['#66C0F4', '#4FC3F7', '#29B6F6', '#03A9F4', '#039BE5', '#0288D1', '#0277BD', '#01579B']

interface UserDashboard {
  user: SteamUser
  stats: {
    total_games: number
    total_playtime: number
    total_playtime_hours: number
    games_played: number
    games_never_played: number
    total_achievements: number
    achievements_unlocked: number
    completion_rate: number
  }
  top_played_games: Array<{
    game: { name: string; app_id: number }
    playtime_forever: number
    playtime_hours: number
  }>
  recent_games: Array<{
    game: { name: string; app_id: number }
    playtime_2weeks: number
    last_played: string
  }>
}

interface GenrePlaytime {
  genre: string
  playtime_hours: number
}

export default function UserDetailPage() {
  const params = useParams()
  const userId = params.id as string

  const [user, setUser] = useState<SteamUser | null>(null)
  const [dashboard, setDashboard] = useState<UserDashboard | null>(null)
  const [games, setGames] = useState<UserGame[]>([])
  const [genreData, setGenreData] = useState<GenrePlaytime[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)

  const loadData = async () => {
    setLoading(true)
    try {
      const [userRes, dashboardRes, gamesRes, genreRes] = await Promise.all([
        getUser(userId),
        getUserDashboard(userId),
        getUserGames(userId, { limit: 500, sort_by: 'playtime' }),
        getUserPlaytimeByGenre(userId),
      ])
      setUser(userRes.data)
      setDashboard(dashboardRes.data)
      setGames(gamesRes.data)
      setGenreData(genreRes.data)
    } catch (error) {
      console.error('Failed to load user data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [userId])

  const handleSync = async () => {
    setSyncing(true)
    try {
      await syncUserProfile(userId)
      await syncUserGames(userId)
      await loadData()
    } catch (error) {
      console.error('Sync failed:', error)
    } finally {
      setSyncing(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="card animate-pulse">
          <div className="flex items-center gap-6">
            <div className="w-24 h-24 bg-gray-700 rounded-full"></div>
            <div className="flex-1">
              <div className="h-8 bg-gray-700 rounded w-1/3 mb-3"></div>
              <div className="h-4 bg-gray-700 rounded w-1/2"></div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="card text-center py-12">
        <p className="text-gray-400">User not found</p>
        <Link href="/users" className="btn-primary mt-4 inline-block">
          Back to Users
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <Link href="/users" className="inline-flex items-center gap-2 text-gray-400 hover:text-white">
          <ArrowLeftIcon className="h-4 w-4" />
          Back to Users
        </Link>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="btn-secondary flex items-center gap-2"
        >
          <ArrowPathIcon className={`h-5 w-5 ${syncing ? 'animate-spin' : ''}`} />
          Sync
        </button>
      </div>

      {/* User Profile Card */}
      <div className="card">
        <div className="flex items-center gap-6">
          <img
            src={user.avatar_full_url || user.avatar_url || '/default-avatar.png'}
            alt={user.persona_name}
            className="w-24 h-24 rounded-full"
          />
          <div className="flex-1">
            <h1 className="text-3xl font-bold">{user.persona_name}</h1>
            <p className="text-gray-400">Steam ID: {user.steam_id}</p>
            {user.country_code && (
              <p className="text-gray-500">Country: {user.country_code}</p>
            )}
            <a
              href={user.profile_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-steam-blue hover:underline text-sm"
            >
              View Steam Profile →
            </a>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center gap-3">
            <Squares2X2Icon className="h-8 w-8 text-purple-400" />
            <div>
              <p className="text-sm text-gray-400">Games</p>
              <p className="text-2xl font-bold">{dashboard?.stats?.total_games || 0}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <ClockIcon className="h-8 w-8 text-yellow-400" />
            <div>
              <p className="text-sm text-gray-400">Playtime</p>
              <p className="text-2xl font-bold">{(dashboard?.stats?.total_playtime_hours || 0).toFixed(0)}h</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <TrophyIcon className="h-8 w-8 text-orange-400" />
            <div>
              <p className="text-sm text-gray-400">Achievements</p>
              <p className="text-2xl font-bold">{dashboard?.stats?.achievements_unlocked || 0}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-green-500/20 flex items-center justify-center">
              <span className="text-green-400 font-bold">%</span>
            </div>
            <div>
              <p className="text-sm text-gray-400">Completion</p>
              <p className="text-2xl font-bold">{(dashboard?.stats?.completion_rate || 0).toFixed(1)}%</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Most Played Games */}
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Most Played Games</h2>
          <div className="space-y-3">
            {(dashboard?.top_played_games || []).slice(0, 5).map((item, index) => (
              <div key={index} className="flex items-center gap-3">
                <span className="text-gray-500 w-6 text-center">{index + 1}</span>
                <div className="flex-1 min-w-0">
                  <p className="truncate">{item.game.name}</p>
                  <p className="text-sm text-gray-400">
                    {(item.playtime_forever / 60).toFixed(1)} hours
                  </p>
                </div>
                <div className="w-24 bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-steam-blue h-2 rounded-full"
                    style={{
                      width: `${Math.min(100, (item.playtime_forever / (dashboard?.top_played_games[0]?.playtime_forever || 1)) * 100)}%`
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Playtime by Genre */}
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Playtime by Genre</h2>
          {genreData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={genreData.slice(0, 8)}
                  dataKey="playtime_hours"
                  nameKey="genre"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ genre, percent }) => `${genre} (${(percent * 100).toFixed(0)}%)`}
                >
                  {genreData.slice(0, 8).map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-400 text-center py-12">No genre data available</p>
          )}
        </div>
      </div>

      {/* Games List */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Game Library</h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-gray-400 border-b border-gray-700">
                <th className="pb-3 font-medium">Game</th>
                <th className="pb-3 font-medium text-right">Total Playtime</th>
                <th className="pb-3 font-medium text-right">Last 2 Weeks</th>
              </tr>
            </thead>
            <tbody>
              {games.map((item) => (
                <tr key={item.id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                  <td className="py-3">
                    <div className="flex items-center gap-3">
                      {item.game.header_image && (
                        <img
                          src={item.game.header_image}
                          alt={item.game.name}
                          className="w-16 h-8 object-cover rounded"
                        />
                      )}
                      <span className="truncate">{item.game.name}</span>
                    </div>
                  </td>
                  <td className="py-3 text-right text-gray-300">
                    {(item.playtime_forever / 60).toFixed(1)} hrs
                  </td>
                  <td className="py-3 text-right text-gray-400">
                    {item.playtime_2weeks > 0
                      ? `${(item.playtime_2weeks / 60).toFixed(1)} hrs`
                      : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
