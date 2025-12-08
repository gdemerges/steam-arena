'use client'

import { useEffect, useState } from 'react'
import { getUsers, compareUsers, SteamUser } from '@/lib/api'
import { XMarkIcon, PlusIcon, ChartBarIcon } from '@heroicons/react/24/outline'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
  LabelList,
} from 'recharts'

interface ComparisonUser {
  user_id: string
  steam_id: string
  persona_name: string
  avatar_url: string
  total_games: number
  total_playtime: number
  achievements_unlocked: number
  games_played: number
}

interface CommonGame {
  game: {
    name: string
    app_id: number
  }
  total_combined_playtime: number
  owner_count: number
}

interface ComparisonData {
  users: ComparisonUser[]
  common_games: CommonGame[]
  total_unique_games: number
}

const COLORS = ['#66C0F4', '#4ade80', '#a855f7', '#fb923c', '#f43f5e']

export default function ComparePage() {
  const [users, setUsers] = useState<SteamUser[]>([])
  const [selectedUsers, setSelectedUsers] = useState<SteamUser[]>([])
  const [comparison, setComparison] = useState<ComparisonData | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadingUsers, setLoadingUsers] = useState(true)

  useEffect(() => {
    getUsers()
      .then((res) => setUsers(res.data))
      .catch(console.error)
      .finally(() => setLoadingUsers(false))
  }, [])

  const handleAddUser = (user: SteamUser) => {
    if (selectedUsers.length < 5 && !selectedUsers.find(u => u.id === user.id)) {
      setSelectedUsers([...selectedUsers, user])
    }
  }

  const handleRemoveUser = (userId: string) => {
    setSelectedUsers(selectedUsers.filter(u => u.id !== userId))
    setComparison(null)
  }

  const handleCompare = async () => {
    if (selectedUsers.length < 2) return

    setLoading(true)
    try {
      const userIds = selectedUsers.map(u => u.id)
      const res = await compareUsers(userIds)
      setComparison(res.data)
    } catch (error) {
      console.error('Comparison failed:', error)
    } finally {
      setLoading(false)
    }
  }

  const unselectedUsers = users.filter(
    u => !selectedUsers.find(s => s.id === u.id)
  )

  // Prepare chart data
  const barChartData = comparison?.users.map(u => ({
    name: u.persona_name,
    playtime: Math.round(u.total_playtime / 60),
    games: u.total_games,
    achievements: u.achievements_unlocked,
  })) || []

  const radarChartData = comparison?.users.length ? [
    {
      metric: 'Games Owned',
      ...Object.fromEntries(comparison.users.map(u => [u.persona_name, u.total_games]))
    },
    {
      metric: 'Playtime (h)',
      ...Object.fromEntries(comparison.users.map(u => [u.persona_name, Math.round(u.total_playtime / 60)]))
    },
    {
      metric: 'Achievements',
      ...Object.fromEntries(comparison.users.map(u => [u.persona_name, u.achievements_unlocked]))
    },
    {
      metric: 'Games Played',
      ...Object.fromEntries(comparison.users.map(u => [u.persona_name, u.games_played]))
    },
  ] : []

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Compare Users</h1>
      </div>

      {/* User Selection */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Select Users to Compare (max 5)</h2>

        {/* Selected Users */}
        {selectedUsers.length > 0 && (
          <div className="flex flex-wrap gap-3 mb-6">
            {selectedUsers.map((user, index) => (
              <div
                key={user.id}
                className="flex items-center gap-2 px-3 py-2 rounded-full"
                style={{ backgroundColor: `${COLORS[index % COLORS.length]}20`, borderColor: COLORS[index % COLORS.length], borderWidth: 1 }}
              >
                <img
                  src={user.avatar_url || '/default-avatar.png'}
                  alt={user.persona_name}
                  className="w-6 h-6 rounded-full"
                />
                <span className="text-sm">{user.persona_name}</span>
                <button
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
          <p className="text-gray-400 text-center py-4">
            {users.length === 0 ? 'No users available' : 'All users selected'}
          </p>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {unselectedUsers.map((user) => (
              <button
                key={user.id}
                onClick={() => handleAddUser(user)}
                disabled={selectedUsers.length >= 5}
                className="flex flex-col items-center gap-2 p-3 rounded bg-gray-700 hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <img
                  src={user.avatar_url || '/default-avatar.png'}
                  alt={user.persona_name}
                  className="w-12 h-12 rounded-full"
                />
                <span className="text-sm truncate w-full text-center">{user.persona_name}</span>
                <PlusIcon className="h-4 w-4 text-gray-400" />
              </button>
            ))}
          </div>
        )}

        {/* Compare Button */}
        <div className="mt-6 flex justify-center">
          <button
            onClick={handleCompare}
            disabled={selectedUsers.length < 2 || loading}
            className="btn-primary flex items-center gap-2 px-8"
          >
            <ChartBarIcon className="h-5 w-5" />
            {loading ? 'Comparing...' : 'Compare'}
          </button>
        </div>
      </div>

      {/* Comparison Results */}
      {comparison && (
        <div className="space-y-6">
          {/* Summary */}
          <div className="grid grid-cols-2 gap-4">
            <div className="card text-center">
              <p className="text-3xl font-bold text-steam-blue">{comparison.common_games.length}</p>
              <p className="text-gray-400">Common Games</p>
            </div>
            <div className="card text-center">
              <p className="text-3xl font-bold text-purple-400">{comparison.total_unique_games || 0}</p>
              <p className="text-gray-400">Total Unique Games</p>
            </div>
          </div>

          {/* Playtime Chart */}
          <div className="card">
            <h2 className="text-xl font-semibold mb-4">Playtime Comparison (hours)</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={barChartData}>
                <XAxis dataKey="name" tick={{ fill: '#9ca3af' }} />
                <YAxis tick={{ fill: '#9ca3af' }} />
                <Tooltip
                  contentStyle={{ background: '#1a1a2e', border: 'none', borderRadius: '8px' }}
                />
                <Bar dataKey="playtime" fill="#66C0F4" radius={[4, 4, 0, 0]}>
                  <LabelList dataKey="playtime" position="top" fill="#fff" />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Radar Chart */}
          <div className="card">
            <h2 className="text-xl font-semibold mb-4">Overall Comparison</h2>
            <ResponsiveContainer width="100%" height={400}>
              <RadarChart data={radarChartData}>
                <PolarGrid stroke="#374151" />
                <PolarAngleAxis dataKey="metric" tick={{ fill: '#9ca3af' }} />
                <PolarRadiusAxis tick={{ fill: '#9ca3af' }} />
                {comparison.users.map((u, index) => (
                  <Radar
                    key={u.steam_id}
                    name={u.persona_name}
                    dataKey={u.persona_name}
                    stroke={COLORS[index % COLORS.length]}
                    fill={COLORS[index % COLORS.length]}
                    fillOpacity={0.2}
                  />
                ))}
                <Legend />
                <Tooltip
                  contentStyle={{ background: '#1a1a2e', border: 'none', borderRadius: '8px' }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          {/* Detailed Stats Table */}
          <div className="card">
            <h2 className="text-xl font-semibold mb-4">Detailed Statistics</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-gray-700">
                    <th className="pb-3 font-medium">User</th>
                    <th className="pb-3 font-medium text-right">Games</th>
                    <th className="pb-3 font-medium text-right">Playtime</th>
                    <th className="pb-3 font-medium text-right">Played</th>
                    <th className="pb-3 font-medium text-right">Achievements</th>
                  </tr>
                </thead>
                <tbody>
                  {comparison.users.map((u, index) => (
                    <tr key={u.steam_id} className="border-b border-gray-700/50">
                      <td className="py-3">
                        <div className="flex items-center gap-2">
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: COLORS[index % COLORS.length] }}
                          />
                          <img
                            src={u.avatar_url || '/default-avatar.png'}
                            alt={u.persona_name}
                            className="w-8 h-8 rounded-full"
                          />
                          <span>{u.persona_name}</span>
                        </div>
                      </td>
                      <td className="py-3 text-right">{u.total_games}</td>
                      <td className="py-3 text-right">{Math.round(u.total_playtime / 60)}h</td>
                      <td className="py-3 text-right">{u.games_played}</td>
                      <td className="py-3 text-right">{u.achievements_unlocked}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Common Games List */}
          {comparison.common_games.length > 0 && (
            <div className="card">
              <h2 className="text-xl font-semibold mb-4">Common Games ({comparison.common_games.length})</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {comparison.common_games.slice(0, 12).map((item, index) => (
                  <div key={index} className="flex items-center gap-3 p-3 bg-gray-700/50 rounded">
                    <span className="text-sm font-medium truncate flex-1">{item.game.name}</span>
                    <span className="text-xs text-gray-400">
                      {Math.round(item.total_combined_playtime / 60)}h
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
